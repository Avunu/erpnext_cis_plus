# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

import json
from typing import Any, cast
from unittest.mock import patch

import frappe
import requests
from frappe.contacts.doctype.address.address import Address
from frappe.contacts.doctype.contact.contact import Contact
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_link_to_form, now_datetime

from erpnext_cis_plus.erpnext_cis_plus.hooks import customer as customer_hooks
from erpnext_cis_plus.erpnext_cis_plus.hooks import party_utils
from erpnext_cis_plus.erpnext_cis_plus.hooks import supplier as supplier_hooks
from erpnext_cis_plus.patches import remove_inline_party_fields
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


def new_address(**fields) -> dict[str, Any]:
	"""A new Address as the side panel sends it."""
	return {
		"doctype": "Address",
		"name": "new-address-1",
		"__islocal": 1,
		"address_type": "Billing",
		"address_line1": "1 Penn Square",
		"city": "Lancaster",
		"links": [],
		**fields,
	}


def new_contact(**fields) -> dict[str, Any]:
	"""A new Contact as the side panel sends it, with a desk-named new row."""
	return {
		"doctype": "Contact",
		"name": "new-contact-1",
		"__islocal": 1,
		"first_name": "Ada",
		"last_name": "Lovelace",
		"email_ids": [
			{"name": "new-contact-email-1", "__islocal": 1, "email_id": "ada@example.com", "is_primary": 1}
		],
		"phone_nos": [
			{"name": "new-contact-phone-1", "__islocal": 1, "phone": "(201) 555-0123", "is_primary_phone": 1},
			{"phone": "201-555-0124", "is_primary_mobile_no": 1},
		],
		**fields,
	}


class TestSavePartyRecord(GeocodingTestCase):
	"""Saving a Customer's records from the side panel; TestSupplierRecords runs the same on a Supplier."""

	party_type = "Customer"

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("System Settings", "country", "United States")
		prefix = PARTIES[self.party_type]["prefix"]
		self.address_field = f"{prefix}_primary_address"
		self.contact_field = f"{prefix}_primary_contact"

	def tearDown(self):
		frappe.set_user("Administrator")

	def save(self, doc: dict[str, Any], party) -> dict[str, Any]:
		return party_utils.save_party_record(json.dumps(doc), self.party_type, party.name)

	def test_a_new_address_is_linked_geocoded_and_primary(self):
		party = make_party(self.party_type)
		saved = self.save(new_address(), party)

		address = cast(Address, frappe.get_doc("Address", saved["doc"]["name"]))
		self.assertNotEqual(address.name, "new-address-1", "the desk's placeholder name is not kept")
		self.assertEqual(
			[(link.link_doctype, link.link_name) for link in address.links], [(self.party_type, party.name)]
		)
		self.assertTrue(address.is_primary_address, "a party's first address is its primary one")
		self.assertEqual(address.get("latitude"), 40.0379, "the new address was geocoded")
		self.assertEqual(address.country, "United States")
		self.assertEqual([row["name"] for row in saved["addr_list"]], [address.name])
		self.assertIn(0, saved["permlevels"])

		# The form then makes it the party's primary address; saving the party fetches its point.
		party.reload()
		party.set(self.address_field, address.name)
		party.save()
		self.assertEqual(frappe.db.get_value(self.party_type, party.name, "latitude"), 40.0379)

		# A second address is not primary: the party has one.
		party.reload()
		second = self.save(new_address(address_type="Shipping", address_line1="2 Penn Square"), party)
		self.assertFalse(frappe.db.get_value("Address", second["doc"]["name"], "is_primary_address"))

	def test_editing_the_primary_address_moves_the_party_map(self):
		party = make_party(self.party_type)
		address_name = self.save(new_address(), party)["doc"]["name"]
		party.reload()
		party.set(self.address_field, address_name)
		party.save()

		self.get.return_value = nominatim_response([{**NOMINATIM_RESULT, "lat": "40.1", "lon": "-76.2"}])
		doc = frappe.get_doc("Address", address_name).as_dict(convert_dates_to_str=True)
		doc["address_line1"] = "2 Penn Square"
		saved = self.save(doc, party)

		self.assertEqual(frappe.db.get_value("Address", address_name, "address_line1"), "2 Penn Square")
		self.assertEqual(saved["location"]["latitude"], 40.1)
		point = json.loads(saved["location"]["location"])["features"][0]["geometry"]["coordinates"]
		self.assertEqual(point, [-76.2, 40.1])
		self.assertEqual(frappe.db.get_value(self.party_type, party.name, "longitude"), -76.2)

	def test_a_new_address_gets_a_country_when_geocoding_fails(self):
		for failure in (requests.ConnectionError("refused"), None):
			with self.subTest(failure=failure):
				if failure:
					self.get.side_effect = failure
				else:
					self.get.side_effect = None
					self.get.return_value = nominatim_response([])
				party = make_party(self.party_type)
				saved = self.save(new_address(), party)
				self.assertEqual(saved["doc"]["country"], "United States")
				self.assertFalse(saved["doc"]["latitude"])

	def test_geocoding_sets_the_country_of_a_new_address(self):
		# the lookup is not narrowed to the System Settings country, and its country wins
		frappe.db.set_single_value("System Settings", "country", "Canada")
		party = make_party(self.party_type)
		saved = self.save(new_address(), party)
		self.assertEqual(saved["doc"]["country"], "United States")
		self.assertNotIn("Canada", self.get.call_args.kwargs["params"]["q"])

	def test_a_country_entered_is_kept(self):
		self.get.return_value = nominatim_response([])
		party = make_party(self.party_type)
		saved = self.save(new_address(country="Canada"), party)
		self.assertEqual(saved["doc"]["country"], "Canada")

	def test_a_new_contact_is_linked_primary_and_its_numbers_in_e164(self):
		party = make_party(self.party_type)
		saved = self.save(new_contact(), party)

		contact = cast(Contact, frappe.get_doc("Contact", saved["doc"]["name"]))
		self.assertEqual((contact.first_name, contact.last_name), ("Ada", "Lovelace"))
		self.assertTrue(contact.is_primary_contact)
		self.assertEqual(contact.links[0].link_name, party.name)
		self.assertEqual(contact.email_id, "ada@example.com")
		self.assertEqual(contact.phone, "+12015550123")
		self.assertEqual(contact.mobile_no, "+12015550124")
		self.assertTrue(
			all(not str(row.name).startswith("new-") for row in contact.phone_nos + contact.email_ids)
		)
		self.assertEqual([row["name"] for row in saved["contact_list"]], [contact.name])

		# the whitelisted lookups the form uses to pick a default primary find them
		records = (
			customer_hooks.get_customer_records
			if self.party_type == "Customer"
			else supplier_hooks.get_supplier_records
		)
		self.assertEqual(records("Contact", party.name), [{"name": contact.name}])

	def test_numbers_are_read_in_the_country_of_the_primary_address(self):
		self.get.return_value = nominatim_response([])
		party = make_party(self.party_type)
		address_name = self.save(new_address(country="United Kingdom"), party)["doc"]["name"]
		party.reload()
		party.set(self.address_field, address_name)
		party.save()

		saved = self.save(new_contact(phone_nos=[{"phone": "020 7946 0958", "is_primary_phone": 1}]), party)
		self.assertEqual(saved["doc"]["phone"], "+442079460958")

	def test_only_new_numbers_are_rewritten(self):
		party = make_party(self.party_type)
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Grace",
				"phone_nos": [{"phone": "717 555 0142", "is_primary_phone": 1}],
				"links": [{"link_doctype": self.party_type, "link_name": party.name}],
			}
		).insert()

		doc = contact.as_dict(convert_dates_to_str=True)
		doc["phone_nos"].append({"phone": "717-555-0143", "is_primary_mobile_no": 1})
		# a row added in the side panel's table: its unticked boxes arrive as "0"
		doc["phone_nos"].append(
			{"phone": "12", "__islocal": 1, "is_primary_phone": "0", "is_primary_mobile_no": "0"}
		)
		with patch.object(frappe, "msgprint") as msgprint:
			self.save(doc, party)

		contact.reload()
		numbers = [row.phone for row in cast(Contact, contact).phone_nos]
		self.assertEqual(numbers, ["717 555 0142", "+17175550143", "12"])
		msgprint.assert_called_once()
		self.assertIn("12", msgprint.call_args.args[0])

	def test_a_contact_is_primary_only_without_one(self):
		party = make_party(self.party_type)
		first = self.save(new_contact(), party)["doc"]["name"]
		party.reload()
		party.set(self.contact_field, first)
		party.save()

		party.reload()
		second = self.save(new_contact(first_name="Grace", email_ids=[], phone_nos=[]), party)
		self.assertFalse(second["doc"]["is_primary_contact"])
		self.assertTrue(frappe.db.get_value("Contact", first, "is_primary_contact"))

	def test_a_record_of_another_party_is_refused(self):
		party, other = make_party(self.party_type), make_party(self.party_type)
		address_name = self.save(new_address(), other)["doc"]["name"]
		doc = frappe.get_doc("Address", address_name).as_dict(convert_dates_to_str=True)
		doc["city"] = "Lititz"
		with self.assertRaises(frappe.PermissionError):
			self.save(doc, party)
		self.assertEqual(frappe.db.get_value("Address", address_name, "city"), "Lancaster")

	def test_a_stale_record_is_not_overwritten(self):
		party = make_party(self.party_type)
		address_name = self.save(new_address(), party)["doc"]["name"]
		doc = frappe.get_doc("Address", address_name).as_dict(convert_dates_to_str=True)
		doc["modified"] = str(add_days(now_datetime(), -1))
		doc["city"] = "Lititz"
		with self.assertRaises(frappe.TimestampMismatchError):
			self.save(doc, party)

	def test_only_addresses_and_contacts_of_customers_and_suppliers(self):
		party = make_party(self.party_type)
		with self.assertRaises(frappe.PermissionError):
			self.save({"doctype": "ToDo", "description": "not a party record"}, party)
		with self.assertRaises(frappe.PermissionError):
			party_utils.save_party_record(json.dumps(new_address()), "Lead", party.name)
		with self.assertRaises(frappe.PermissionError):
			self.save(cast(Any, "not a document"), party)

	def test_the_user_must_be_able_to_read_the_party(self):
		party = make_party(self.party_type)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			self.save(new_address(), party)

	def test_the_record_is_saved_with_the_users_permissions(self):
		# Stock User reads Customers and Suppliers, but writes only the Contacts it owns
		party = make_party(self.party_type)
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Grace",
				"links": [{"link_doctype": self.party_type, "link_name": party.name}],
			}
		).insert()
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"cis-plus-{frappe.generate_hash(length=8)}@example.com",
				"first_name": "Reader",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock User"}],
			}
		).insert()
		doc = contact.as_dict(convert_dates_to_str=True)
		doc["last_name"] = "Hopper"

		frappe.set_user(str(user.name))
		self.assertTrue(frappe.has_permission(self.party_type, "read", party.name))
		with self.assertRaises(frappe.PermissionError):
			self.save(doc, party)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value("Contact", contact.name, "last_name"))


class TestSupplierRecords(TestSavePartyRecord):
	party_type = "Supplier"

	def test_a_new_address_falls_back_to_the_suppliers_country(self):
		# a Supplier has a country of its own, which beats the System Settings one
		self.get.return_value = nominatim_response([])
		party = make_party(self.party_type, country="Canada")
		saved = self.save(new_address(), party)
		self.assertEqual(saved["doc"]["country"], "Canada")


class TestCleanClientValues(IntegrationTestCase):
	def test_bookkeeping_and_placeholder_names_are_dropped(self):
		cleaned = party_utils.clean_client_values(
			{
				"doctype": "Contact",
				"name": "CONTACT-1",
				"__unsaved": 1,
				"docstatus": 0,
				"phone_nos": [
					{"name": "row-1", "phone": "+12015550123"},
					{"name": "new-contact-phone-1", "__islocal": 1, "phone": "+12015550124"},
				],
				"tags": ["kept", 1],
			}
		)
		self.assertEqual(
			cleaned,
			{
				"doctype": "Contact",
				"name": "CONTACT-1",
				"phone_nos": [{"name": "row-1", "phone": "+12015550123"}, {"phone": "+12015550124"}],
				"tags": ["kept", 1],
			},
		)


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
	def test_the_inline_fields_are_gone_and_the_section_is_erpnexts_again(self):
		for party_type, section in remove_inline_party_fields.PARTIES.items():
			meta = frappe.get_meta(party_type)
			for fieldname in remove_inline_party_fields.removed_fields(party_type):
				self.assertIsNone(meta.get_field(fieldname), fieldname)
			# ERPNext v16 hides the section; the app no longer shows it
			self.assertTrue(meta.get_field(section).hidden, party_type)
			# the map stays, fetched from the primary address
			self.assertEqual(
				meta.get_field("location").fetch_from, f"{party_type.lower()}_primary_address.location"
			)


class TestRemoveInlinePartyFieldsPatch(IntegrationTestCase):
	def test_the_fields_and_property_setters_are_removed(self):
		kept = []
		for party_type, section in remove_inline_party_fields.PARTIES.items():
			# db_insert: the records as an older version left them, without adding a column
			for fieldname in remove_inline_party_fields.removed_fields(party_type):
				frappe.get_doc(
					{
						"doctype": "Custom Field",
						"name": f"{party_type}-{fieldname}",
						"dt": party_type,
						"fieldname": fieldname,
						"fieldtype": "Data",
						"label": fieldname,
						"insert_after": section,
					}
				).db_insert()
			for name in remove_inline_party_fields.removed_property_setters(party_type, section):
				field_name = name.removeprefix(f"{party_type}-").rsplit("-", 1)[0]
				frappe.get_doc(
					{
						"doctype": "Property Setter",
						"name": name,
						"doc_type": party_type,
						"doctype_or_field": "DocField",
						"field_name": field_name,
						"property": name.rsplit("-", 1)[1],
						"property_type": "Data",
						"value": "0",
					}
				).db_insert()
			# A customization of the same party that is not the app's is left alone
			other = frappe.get_doc(
				{
					"doctype": "Property Setter",
					"name": f"{party_type}-{section}-collapsible",
					"doc_type": party_type,
					"doctype_or_field": "DocField",
					"field_name": section,
					"property": "collapsible",
					"property_type": "Check",
					"value": "1",
				}
			)
			other.db_insert()
			kept.append(other.name)

		remove_inline_party_fields.execute()
		# Running it again, as a re-run migrate would, finds nothing left to do
		remove_inline_party_fields.execute()

		for party_type, section in remove_inline_party_fields.PARTIES.items():
			self.assertFalse(
				frappe.get_all(
					"Custom Field",
					filters={
						"dt": party_type,
						"fieldname": ["in", remove_inline_party_fields.removed_fields(party_type)],
					},
				)
			)
			for name in remove_inline_party_fields.removed_property_setters(party_type, section):
				self.assertFalse(frappe.db.exists("Property Setter", name), name)
			# the map fields stay
			self.assertTrue(frappe.db.exists("Custom Field", {"dt": party_type, "fieldname": "location"}))
		for name in kept:
			self.assertTrue(frappe.db.exists("Property Setter", name), name)
