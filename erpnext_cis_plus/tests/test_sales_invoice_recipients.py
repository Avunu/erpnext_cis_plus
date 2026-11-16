# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""bench --site avunu_test_site run-tests --module erpnext_cis_plus.tests.test_sales_invoice_recipients"""

from typing import cast

import frappe
from frappe.email.doctype.notification.notification import Notification

from erpnext_cis_plus.erpnext_cis_plus.hooks.sales_invoice import (
	SalesInvoiceEmailRecipients,
	get_email_recipients,
)
from erpnext_cis_plus.tests.utils import GeocodingTestCase


def make_contact(customer: str, first_name: str, email: str, **values):
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name,
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"links": [{"link_doctype": "Customer", "link_name": customer}],
			**values,
		}
	).insert()
	return contact.name


def make_address(customer: str, title: str, email: str | None, address_type="Billing"):
	return (
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": title,
				"address_type": address_type,
				"address_line1": "1 Main Street",
				"city": "Lancaster",
				"country": "United States",
				"latitude": 40.0379,
				"longitude": -76.3055,
				"email_id": email,
				"links": [{"link_doctype": "Customer", "link_name": customer}],
			}
		)
		.insert()
		.name
	)


class TestSalesInvoiceRecipients(GeocodingTestCase):
	def setUp(self):
		super().setUp()
		# a customer of its own per test: the contacts and addresses of the others aren't rolled back
		self.customer = (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": f"_Test CIS Plus Recipients {frappe.generate_hash(length=6)}",
					"customer_type": "Company",
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
				}
			)
			.insert()
			.name
		)

	def test_contact_person_and_billing_address(self):
		person = make_contact(self.customer, "Invoice", "person@example.com")
		make_contact(self.customer, "Billing", "billing@example.com", is_billing_contact=1)
		address = make_address(self.customer, "Recipients A", "ap@example.com")
		self.assertEqual(
			get_email_recipients(self.customer, person, address), ["person@example.com", "ap@example.com"]
		)

	def test_billing_contact_when_no_contact_person(self):
		make_contact(self.customer, "Other", "other@example.com")
		make_contact(self.customer, "Billing", "billing@example.com", is_billing_contact=1)
		self.assertEqual(get_email_recipients(self.customer), ["billing@example.com"])

	def test_billing_contact_when_contact_person_has_no_email(self):
		person = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "No Email",
				"links": [{"link_doctype": "Customer", "link_name": self.customer}],
			}
		).insert()
		make_contact(self.customer, "Billing", "billing@example.com", is_billing_contact=1)
		self.assertEqual(get_email_recipients(self.customer, person.name), ["billing@example.com"])

	def test_customer_billing_address_when_invoice_has_none(self):
		make_address(self.customer, "Recipients Shipping", "dock@example.com", address_type="Shipping")
		make_address(self.customer, "Recipients Billing", "ap@example.com")
		self.assertEqual(get_email_recipients(self.customer), ["ap@example.com"])

	def test_duplicate_address_email_is_dropped(self):
		person = make_contact(self.customer, "Same", "same@example.com")
		address = make_address(self.customer, "Recipients Same", "SAME@example.com")
		self.assertEqual(get_email_recipients(self.customer, person, address), ["same@example.com"])

	def test_virtual_field_and_notification_receiver(self):
		person = make_contact(self.customer, "Invoice", "person@example.com")
		address = make_address(self.customer, "Recipients N", "ap@example.com")
		invoice = frappe.new_doc("Sales Invoice")
		invoice.update({"customer": self.customer, "contact_person": person, "customer_address": address})
		self.assertIsInstance(invoice, SalesInvoiceEmailRecipients)
		self.assertEqual(invoice.email_recipients, "person@example.com\nap@example.com")
		self.assertEqual(invoice.as_dict().email_recipients, "person@example.com\nap@example.com")

		notification = cast(Notification, frappe.new_doc("Notification"))
		notification.update(
			{
				"document_type": "Sales Invoice",
				"channel": "Email",
				"recipients": [{"receiver_by_document_field": "email_recipients"}],
			}
		)
		recipients, _cc, _bcc = notification.get_list_of_recipients(invoice, {"doc": invoice})
		self.assertCountEqual(recipients, ["person@example.com", "ap@example.com"])
