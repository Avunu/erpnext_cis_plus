# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Remove the primary address and contact fields the app used to add to Customer and Supplier.

Addresses and Contacts are now edited in the side panel of the Customer and Supplier forms
(public/js/party_records.js), so the copies of their fields on the party go, with the property
setters that showed ERPNext's hidden "Primary Address and Contact" section and hid its
read-only fields. Customizations sync only adds and updates, so the records are deleted here.

No data is lost. Every one of these fields was fetched from, and saved back to, the party's
primary Address or Contact, which keep their values. Deleting a Custom Field leaves its
database column in place, so the copies stay in the Customer and Supplier tables too.
"""

import frappe

ADDRESS_FIELDS = ("address_line1", "address_line2", "city", "state", "pincode", "email_id", "phone", "fax")
CONTACT_FIELDS = ("first_name", "last_name", "email_id", "phone", "mobile_no", "department")
# Each party, and the name of its "Primary Address and Contact" section
PARTIES = {
	"Customer": "primary_address_and_contact_detail",
	"Supplier": "primary_address_and_contact_detail_section",
}


def removed_fields(party_type: str) -> list[str]:
	prefix = party_type.lower()
	return [f"{prefix}_primary_address_{field}" for field in ADDRESS_FIELDS] + [
		f"{prefix}_primary_contact_{field}" for field in CONTACT_FIELDS
	]


def removed_property_setters(party_type: str, section: str) -> list[str]:
	return [
		f"{party_type}-{section}-hidden",
		f"{party_type}-{section}-description",
		f"{party_type}-primary_address-hidden",
		f"{party_type}-mobile_no-hidden",
		f"{party_type}-email_id-hidden",
	]


def execute():
	for party_type, section in PARTIES.items():
		for name in frappe.get_all(
			"Custom Field",
			filters={"dt": party_type, "fieldname": ["in", removed_fields(party_type)]},
			pluck="name",
		):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

		frappe.db.delete("Property Setter", {"name": ["in", removed_property_setters(party_type, section)]})
		frappe.clear_cache(doctype=party_type)
