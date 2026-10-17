# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

from typing import cast
from unittest.mock import patch

import frappe
from frappe.contacts.doctype.contact.contact import Contact
from frappe.tests import IntegrationTestCase

from erpnext_cis_plus.erpnext_cis_plus.hooks import party_utils
from erpnext_cis_plus.tests.utils import GeocodingTestCase


class TestPhoneNormalisation(IntegrationTestCase):
	def test_e164_numbers(self):
		self.assertTrue(party_utils.is_valid_E164_number("+12015550123"))
		self.assertFalse(party_utils.is_valid_E164_number("+1 201-555-0123"), "not in E.164 form")
		self.assertFalse(party_utils.is_valid_E164_number("2015550123"), "no country code")
		self.assertFalse(party_utils.is_valid_E164_number("+1201"), "too short to be valid")
		self.assertFalse(party_utils.is_valid_E164_number("+abc"), "unparseable")
		self.assertFalse(party_utils.is_valid_E164_number(""))
		self.assertFalse(party_utils.is_valid_E164_number(None))

	def test_convert_to_e164(self):
		self.assertEqual(party_utils.convert_to_e164("(201) 555-0123", "US"), "+12015550123")
		self.assertEqual(party_utils.convert_to_e164("+44 20 7946 0958", "US"), "+442079460958")
		self.assertEqual(party_utils.convert_to_e164("020 7946 0958", "GB"), "+442079460958")
		self.assertIsNone(party_utils.convert_to_e164("555", "US"), "not a valid number")
		self.assertIsNone(party_utils.convert_to_e164("not a number", "US"))
		self.assertIsNone(party_utils.convert_to_e164("2015550123", "NONE"), "no usable region")
		self.assertIsNone(party_utils.convert_to_e164("", "US"))

	def test_validate_party_phone_numbers(self):
		doc = frappe._dict(
			phone="(201) 555-0123",
			mobile="+12015550124",
			fax="12",
			empty=None,
		)
		with patch.object(frappe, "msgprint") as msgprint:
			party_utils.validate_party_phone_numbers(doc, ["phone", "mobile", "fax", "empty"], "US")

		self.assertEqual(doc.phone, "+12015550123")
		self.assertEqual(doc.mobile, "+12015550124")
		self.assertEqual(doc.fax, "12", "an invalid number is kept as entered")
		msgprint.assert_called_once()
		self.assertIn("fax", msgprint.call_args.args[0])


class TestCountryCode(GeocodingTestCase):
	def test_country_code_from_the_primary_address_or_system_settings(self):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "CIS Plus country test",
				"address_type": "Billing",
				"address_line1": "10 Downing Street",
				"city": "London",
				"country": "United Kingdom",
				"latitude": 51.5034,
				"longitude": -0.1276,
			}
		).insert()
		doc = frappe._dict(customer_primary_address=address.name)
		self.assertEqual(party_utils.get_country_code_for_party(doc, "customer_primary_address"), "GB")

		frappe.db.set_single_value("System Settings", "country", "United States")
		doc = frappe._dict(customer_primary_address=None)
		self.assertEqual(party_utils.get_country_code_for_party(doc, "customer_primary_address"), "US")


class TestUpdateChildFields(IntegrationTestCase):
	def test_empty_party_fields_leave_the_contact_alone(self):
		contact = cast(Contact, frappe.new_doc("Contact"))
		contact.add_email("ada@example.com", is_primary=1)
		child_fields = {
			"email_id": ("add_email", {"is_primary": 1}),
			"phone": ("add_phone", {"is_primary_phone": 1}),
		}
		party_utils.update_child_fields(
			contact, child_fields, frappe._dict(x_email_id="", x_phone=None), "x_"
		)
		self.assertEqual([row.email_id for row in contact.email_ids], ["ada@example.com"])
		self.assertEqual(contact.phone_nos, [])
