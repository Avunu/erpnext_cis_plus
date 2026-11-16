# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Who a Sales Invoice is emailed to: the invoice's Contact Person, or else the customer's billing
contact, and always the email on the customer's billing address. The virtual `email_recipients`
field (custom/sales_invoice.json) carries the list to the form, where it fills the email composer,
and lets a Notification address it through "Receiver By Document Field"."""

import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.email.doctype.notification.notification import Notification


def get_email_recipients(
	customer: str | None, contact_person: str | None = None, customer_address: str | None = None
) -> list[str]:
	contact_email = contact_person and frappe.db.get_value("Contact", contact_person, "email_id")
	if not contact_email and customer:
		contact_email = get_billing_contact_email(customer)

	address_email = get_billing_address_email(customer, customer_address)

	recipients: list[str] = []
	for email in (contact_email, address_email):
		if email and email.lower() not in (r.lower() for r in recipients):
			recipients.append(email)
	return recipients


def get_billing_contact_email(customer: str) -> str | None:
	emails = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", customer],
			["is_billing_contact", "=", 1],
			["email_id", "is", "set"],
		],
		pluck="email_id",
		order_by="is_primary_contact desc, creation asc",
		limit=1,
	)
	return emails[0] if emails else None


def get_billing_address_email(customer: str | None, customer_address: str | None) -> str | None:
	"""The invoice's billing address, or else the customer's own billing address."""
	if customer_address:
		return frappe.db.get_value("Address", customer_address, "email_id")
	if not customer:
		return None
	emails = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", customer],
			["address_type", "=", "Billing"],
			["disabled", "=", 0],
			["email_id", "is", "set"],
		],
		pluck="email_id",
		order_by="is_primary_address desc, creation asc",
		limit=1,
	)
	return emails[0] if emails else None


@frappe.whitelist()
def get_sales_invoice_email_recipients(
	customer: str, contact_person: str | None = None, customer_address: str | None = None
) -> list[str]:
	"""For the form, whose contact and address may have changed since it loaded."""
	frappe.has_permission("Customer", "read", customer, throw=True)
	return get_email_recipients(customer, contact_person, customer_address)


class SalesInvoiceEmailRecipients(SalesInvoice):
	@property
	def email_recipients(self) -> str:
		# one per line: Notification splits a receiver field on commas without trimming the spaces
		return "\n".join(get_email_recipients(self.customer, self.contact_person, self.customer_address))


class VirtualReceiverNotification(Notification):
	def get_list_of_recipients(self, doc, context):
		"""Core reads a receiver field from the document's values, where a virtual field has none;
		fill those in from the field's property first."""
		for recipient in self.recipients:
			fieldname = recipient.receiver_by_document_field
			if not fieldname or "," in fieldname or doc.__dict__.get(fieldname) is not None:
				continue
			df = doc.meta.get_field(fieldname)
			if df and df.is_virtual and isinstance(getattr(type(doc), fieldname, None), property):
				doc.set(fieldname, getattr(doc, fieldname))
		return super().get_list_of_recipients(doc, context)
