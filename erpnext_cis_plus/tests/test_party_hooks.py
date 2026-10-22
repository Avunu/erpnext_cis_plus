# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

import json
from typing import Any, cast

import frappe
import requests
from frappe.contacts.doctype.address.address import Address
from frappe.contacts.doctype.contact.contact import Contact
from frappe.tests import IntegrationTestCase
from frappe.utils import get_link_to_form

from erpnext_cis_plus.erpnext_cis_plus.hooks import customer as customer_hooks
from erpnext_cis_plus.erpnext_cis_plus.hooks import party_utils
from erpnext_cis_plus.erpnext_cis_plus.hooks import supplier as supplier_hooks
from erpnext_cis_plus.tests.utils import NOMINATIM_RESULT, GeocodingTestCase, nominatim_response

PARTIES: dict[str, dict[str, Any]] = {
	"Customer": {
		"name_field": "customer_name",
		"prefix": "customer",
		"values": {
			"customer_type": "Company",
			"customer_group": "_Test Customer Group",
			"territory": "_Test Territory",
		},
	},
	"Supplier": {
		"name_field": "supplier_name",
		"prefix": "supplier",
		"values": {"supplier_group": "_Test Supplier Group"},
	},
}


def make_party(party_type: str, **fields):
	spec = PARTIES[party_type]
	values = {
		"doctype": party_type,
		spec["name_field"]: f"CIS Plus {party_type} {frappe.generate_hash(length=8)}",
		**spec["values"],
		**fields,
	}
	return frappe.get_doc(values).insert()


class TestCustomerHooks(GeocodingTestCase):
	"""The Customer hooks; TestSupplierHooks runs the same tests on Supplier's."""

	party_type = "Customer"

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("System Settings", "country", "United States")
		self.p = PARTIES[self.party_type]["prefix"]

	def field(self, name: str) -> str:
		return f"{self.p}_{name}"

	def test_a_new_party_is_left_to_erpnext(self):
		party = make_party(self.party_type, **{self.field("primary_address_address_line1"): "1 Penn Square"})
		self.assertFalse(party.get(self.field("primary_address")))
		self.assertFalse(party.get(self.field("primary_contact")))

	def test_address_and_contact_are_created_from_the_party(self):
		self.create_address_and_contact()

	def create_address_and_contact(self):
		party = make_party(self.party_type)
		party.update(
			{
				self.field("primary_address_address_line1"): "1 Penn Square",
				self.field("primary_address_city"): "Lancaster",
				self.field("primary_address_state"): "PA",
				self.field("primary_address_pincode"): "17602",
				self.field("primary_contact_first_name"): "Ada",
				self.field("primary_contact_last_name"): "Lovelace",
				self.field("primary_contact_email_id"): "ada@example.com",
				self.field("primary_contact_phone"): "(201) 555-0123",
				self.field("primary_contact_mobile_no"): "201-555-0124",
			}
		)
		party.save()

		# phone numbers were normalised before the save
		self.assertEqual(party.get(self.field("primary_contact_phone")), "+12015550123")
		self.assertEqual(party.get(self.field("primary_contact_mobile_no")), "+12015550124")

		# the new records are linked in the database, not only on the saved document
		address_name = frappe.db.get_value(self.party_type, party.name, self.field("primary_address"))
		contact_name = frappe.db.get_value(self.party_type, party.name, self.field("primary_contact"))
		self.assertTrue(address_name)
		self.assertTrue(contact_name)

		address = cast(Address, frappe.get_doc("Address", address_name))
		self.assertEqual(address.address_line1, "1 Penn Square")
		self.assertEqual(address.city, "Lancaster")
		self.assertTrue(address.is_primary_address)
		self.assertEqual(address.links[0].link_doctype, self.party_type)
		self.assertEqual(address.links[0].link_name, party.name)
		self.assertEqual(address.get("latitude"), 40.0379, "the new address was geocoded")

		contact = cast(Contact, frappe.get_doc("Contact", contact_name))
		self.assertEqual((contact.first_name, contact.last_name), ("Ada", "Lovelace"))
		self.assertTrue(contact.is_primary_contact)
		self.assertEqual(contact.email_id, "ada@example.com")
		self.assertEqual(contact.phone, "+12015550123")
		self.assertEqual(contact.mobile_no, "+12015550124")
		self.assertEqual(contact.links[0].link_name, party.name)

		# the whitelisted lookups the form uses find them
		records = (
			customer_hooks.get_customer_records
			if self.party_type == "Customer"
			else supplier_hooks.get_supplier_records
		)
		self.assertEqual(records("Address", party.name), [{"name": address_name}])
		self.assertEqual(records("Contact", party.name), [{"name": contact_name}])

		party.reload()
		return party, address, contact

	def test_editing_the_party_updates_its_address_and_contact(self):
		party, address, contact = self.create_address_and_contact()

		party.update(
			{
				self.field("primary_address_city"): "Lititz",
				self.field("primary_contact_last_name"): "King",
				self.field("primary_contact_email_id"): "ada.king@example.com",
				self.field("primary_contact_phone"): "+12015550199",
			}
		)
		party.save()

		address.reload()
		self.assertEqual(address.city, "Lititz")
		contact.reload()
		self.assertEqual(contact.last_name, "King")
		self.assertEqual(contact.email_id, "ada.king@example.com")
		self.assertEqual(contact.phone, "+12015550199")
		self.assertEqual(sum(row.is_primary_phone for row in contact.phone_nos), 1)
		self.assertEqual(sum(row.is_primary for row in contact.email_ids), 1)

		# back to an email and a phone the contact already has: the rows are reused
		party.reload()
		party.update(
			{
				self.field("primary_contact_email_id"): "ada@example.com",
				self.field("primary_contact_phone"): "+12015550123",
				self.field("primary_contact_mobile_no"): "+12015550199",
			}
		)
		party.save()
		contact.reload()
		self.assertEqual(len(contact.email_ids), 2)
		self.assertEqual(contact.email_id, "ada@example.com")
		self.assertEqual(contact.phone, "+12015550123")
		self.assertEqual(contact.mobile_no, "+12015550199")
		self.assertEqual(len(contact.phone_nos), 3)

		# a new mobile number becomes the only primary mobile; an emptied field is left alone
		party.reload()
		party.update(
			{
				self.field("primary_contact_email_id"): None,
				self.field("primary_contact_mobile_no"): "+12015550177",
			}
		)
		party.save()
		contact.reload()
		self.assertEqual(contact.email_id, "ada@example.com")
		self.assertEqual(contact.mobile_no, "+12015550177")
		self.assertEqual(sum(row.is_primary_mobile_no for row in contact.phone_nos), 1)

	def test_the_party_map_follows_its_primary_address(self):
		party, address, _ = self.create_address_and_contact()

		def point(name: str) -> list[float]:
			location = frappe.db.get_value(self.party_type, name, "location")
			return json.loads(location)["features"][0]["geometry"]["coordinates"]

		# the new primary address is on the party's map without another save
		self.assertEqual(frappe.db.get_value(self.party_type, party.name, "latitude"), 40.0379)
		self.assertEqual(point(party.name), [-76.3055, 40.0379])

		# the address moves: the party's point moves with it
		self.get.return_value = nominatim_response([{**NOMINATIM_RESULT, "lat": "40.1", "lon": "-76.2"}])
		address.reload()
		address.address_line1 = "2 Penn Square"
		address.save()
		self.assertEqual(frappe.db.get_value(self.party_type, party.name, "latitude"), 40.1)
		self.assertEqual(point(party.name), [-76.2, 40.1])

		# the address moves where the lookup finds nothing: the party loses its point
		self.get.return_value = nominatim_response([])
		address.reload()
		address.address_line1 = "3 Penn Square"
		address.save()
		self.assertEqual(frappe.db.get_value(self.party_type, party.name, "latitude"), 0)
		self.assertFalse(frappe.db.get_value(self.party_type, party.name, "location"))

		# another primary address: saving the party fetches its point
		self.get.return_value = nominatim_response([{**NOMINATIM_RESULT, "lat": "39.9", "lon": "-76.7"}])
		other = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": party.name,
				"address_type": "Shipping",
				"address_line1": "120 North George Street",
				"city": "York",
				"country": "United States",
				"links": [{"link_doctype": self.party_type, "link_name": party.name}],
			}
		).insert()
		party.reload()
		party.set(self.field("primary_address"), other.name)
		party.save()
		self.assertEqual(frappe.db.get_value(self.party_type, party.name, "latitude"), 39.9)
		self.assertEqual(point(party.name), [-76.7, 39.9])

	def test_a_new_address_gets_a_country_when_geocoding_fails(self):
		# the party has no country field, and a failed lookup cannot fill it in
		for failure in (requests.ConnectionError("refused"), None):
			with self.subTest(failure=failure):
				if failure:
					self.get.side_effect = failure
				else:
					self.get.side_effect = None
					self.get.return_value = nominatim_response([])
				party = make_party(self.party_type)
				party.update(
					{
						self.field("primary_address_address_line1"): "1 Penn Square",
						self.field("primary_address_city"): "Lancaster",
					}
				)
				party.save()

				address_name = frappe.db.get_value(self.party_type, party.name, self.field("primary_address"))
				self.assertTrue(address_name)
				self.assertEqual(frappe.db.get_value("Address", address_name, "country"), "United States")
				self.assertFalse(frappe.db.get_value("Address", address_name, "latitude"))

	def test_geocoding_sets_the_country_of_a_new_address(self):
		# the lookup is not narrowed to the System Settings country, and its country wins
		frappe.db.set_single_value("System Settings", "country", "Canada")
		party = make_party(self.party_type)
		party.set(self.field("primary_address_address_line1"), "1 Penn Square")
		party.save()

		address_name = frappe.db.get_value(self.party_type, party.name, self.field("primary_address"))
		self.assertEqual(frappe.db.get_value("Address", address_name, "country"), "United States")
		self.assertNotIn("Canada", self.get.call_args.kwargs["params"]["q"])

	def test_a_new_address_needs_its_first_line(self):
		party = make_party(self.party_type)
		party.set(self.field("primary_address_city"), "Lancaster")
		with self.assertRaisesRegex(frappe.ValidationError, "Address Line1"):
			party.save()

	def test_a_new_contact_needs_a_first_name(self):
		party = make_party(self.party_type)
		party.set(self.field("primary_contact_last_name"), "Lovelace")
		with self.assertRaisesRegex(frappe.ValidationError, "First Name"):
			party.save()


class TestSupplierHooks(TestCustomerHooks):
	party_type = "Supplier"

	def test_a_new_address_falls_back_to_the_suppliers_country(self):
		# a Supplier has a country of its own, which beats the System Settings one
		self.get.return_value = nominatim_response([])
		party = make_party(self.party_type, country="Canada")
		party.update(
			{
				self.field("primary_address_address_line1"): "1 Penn Square",
				self.field("primary_address_city"): "Lancaster",
			}
		)
		party.save()

		address_name = frappe.db.get_value(self.party_type, party.name, self.field("primary_address"))
		self.assertEqual(frappe.db.get_value("Address", address_name, "country"), "Canada")


class TestPartyRecords(GeocodingTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_only_addresses_and_contacts(self):
		customer = make_party("Customer")
		with self.assertRaises(frappe.PermissionError):
			customer_hooks.get_customer_records("User", customer.name)

	def test_an_unknown_party_has_no_records(self):
		self.assertEqual(customer_hooks.get_customer_records("Address", "No such customer"), [])
		self.assertEqual(supplier_hooks.get_supplier_records("Contact", "No such supplier"), [])

	def test_the_user_must_be_able_to_read_the_party(self):
		customer = make_party("Customer")
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			party_utils.get_party_records("Address", "Customer", customer.name)


class TestCustomerMap(GeocodingTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_points_for_customers_with_coordinates(self):
		contact = frappe.get_doc({"doctype": "Contact", "first_name": "Grace"}).insert()
		located = make_party("Customer", latitude=40.0379, longitude=-76.3055)
		located.db_set(
			{"customer_primary_contact": contact.name, "primary_address": "1 Penn Square<br>Lancaster"}
		)
		unlocated = make_party("Customer")

		geojson = customer_hooks.get_coords(json.dumps({"name": ["in", [located.name, unlocated.name]]}))
		self.assertEqual(geojson["type"], "FeatureCollection")
		self.assertEqual(len(geojson["features"]), 1)
		feature = geojson["features"][0]
		self.assertEqual(feature["geometry"]["coordinates"], [-76.3055, 40.0379])
		popup = feature["properties"]["name"]
		self.assertIn(get_link_to_form("Customer", located.name, located.customer_name), popup)
		self.assertIn(get_link_to_form("Contact", contact.name), popup)
		self.assertIn("1 Penn Square<br>Lancaster", popup)

		# a dict of filters from Python, and a customer with no contact or address
		located.db_set({"customer_primary_contact": None, "primary_address": None})
		geojson = customer_hooks.get_coords({"name": located.name})
		self.assertEqual(geojson["features"][0]["properties"]["name"].count("<p>"), 1)

	def test_the_map_respects_read_permission(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			customer_hooks.get_coords()


class TestPartyForm(IntegrationTestCase):
	def test_the_primary_address_and_contact_section_is_shown(self):
		# ERPNext v16 hides this section; the app's fields sit in it, so it must show
		for party_type, section in (
			("Customer", "primary_address_and_contact_detail"),
			("Supplier", "primary_address_and_contact_detail_section"),
		):
			meta = frappe.get_meta(party_type)
			df = meta.get_field(section)
			self.assertIsNotNone(df)
			self.assertFalse(df.hidden, party_type)

			# the app's fields are laid out inside it, up to the next section or tab
			fieldnames = [df.fieldname for df in meta.fields]
			after = fieldnames[fieldnames.index(section) + 1 :]
			end = next(
				i
				for i, f in enumerate(after)
				if meta.get_field(f).fieldtype in ("Section Break", "Tab Break")
			)
			prefix = party_type.lower()
			self.assertIn(f"{prefix}_primary_address_address_line1", after[:end])
			self.assertIn(f"{prefix}_primary_contact_first_name", after[:end])
