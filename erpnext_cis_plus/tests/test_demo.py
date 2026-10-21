# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The demo hook frappe-demo calls (`erpnext_cis_plus.demo.setup`)."""

import datetime
import json

import frappe
from frappe.tests import IntegrationTestCase

from erpnext_cis_plus import demo

CTX = {"today": datetime.date(2026, 1, 15), "seed": 1, "company": None, "erpnext_demo": False}
HERO = "Codorus Timber Works"


class TestDemo(IntegrationTestCase):
	def setUp(self):
		frappe.db.set_single_value("System Settings", "country", "United States")

	def test_setup_creates_customers_with_address_contact_and_map_point(self):
		demo.setup(CTX)
		values = frappe.db.get_value(
			"Customer",
			{"customer_name": HERO},
			["customer_primary_address", "customer_primary_contact", "latitude", "longitude", "location"],
			as_dict=True,
		)
		assert values is not None
		self.assertTrue(values.customer_primary_address)
		self.assertTrue(values.customer_primary_contact)
		self.assertAlmostEqual(values.latitude, 39.9636)
		self.assertAlmostEqual(values.longitude, -76.7277)
		point = json.loads(values.location)["features"][0]["geometry"]["coordinates"]
		self.assertEqual(point, [-76.7277, 39.9636])

		address = frappe.db.get_value(
			"Address", values.customer_primary_address, ["city", "county", "country"], as_dict=True
		)
		assert address is not None
		self.assertEqual(
			(address.city, address.county, address.country), ("York", "York County", "United States")
		)

		phone = frappe.db.get_value("Contact", values.customer_primary_contact, "phone")
		self.assertEqual(phone, "+17175550142")

	def test_unknown_addresses_are_not_found(self):
		self.assertEqual(demo.nominatim("", {"q": "1 Nowhere Lane"}).json(), [])

	def test_setup_is_idempotent(self):
		demo.setup(CTX)
		demo.setup(CTX)
		for customer_name in demo.CUSTOMERS:
			self.assertEqual(frappe.db.count("Customer", {"customer_name": customer_name}), 1)
