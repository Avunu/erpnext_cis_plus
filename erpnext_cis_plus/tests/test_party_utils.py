# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
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
