# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

from typing import Any

import frappe
import phonenumbers
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display_list
from frappe.contacts.doctype.contact.contact import get_contact_display_list
from frappe.model.document import Document
from frappe.utils import cint

# The DocTypes a party's records are, and the field of each party naming its primary one
PARTY_RECORD_DOCTYPES = ("Address", "Contact")
PRIMARY_RECORD_FIELDS: dict[str, dict[str, str]] = {
	"Customer": {"Address": "customer_primary_address", "Contact": "customer_primary_contact"},
	"Supplier": {"Address": "supplier_primary_address", "Contact": "supplier_primary_contact"},
}
# The flag that marks an Address or Contact primary for the parties it is linked to
PRIMARY_FLAGS = {"Address": "is_primary_address", "Contact": "is_primary_contact"}
# What a record sent from the side panel may not carry into the save
CLIENT_ONLY_KEYS = ("__islocal", "__unsaved", "__onload", "__last_sync_on", "docstatus")


def get_country_code_for_party(doc, primary_address_field):
	"""Get country code for the party's primary address"""
	country = ""
	primary_address = getattr(doc, primary_address_field, None)
	if primary_address:
		country = frappe.get_value("Address", primary_address, "country")
	if not country:
		country = frappe.db.get_single_value("System Settings", "country")
	country_code = str(frappe.get_value("Country", country, "code")).upper()
	return country_code


def is_valid_E164_number(number):
	"""Check if number is in valid E.164 format"""
	if not number or not number.startswith("+"):
		return False
	try:
		numobj = phonenumbers.parse(number, "")
	except phonenumbers.NumberParseException:
		return False
	if phonenumbers.is_valid_number(numobj):
		return phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164) == number
	return False


def convert_to_e164(number, country_code):
	"""Convert a phone number to E.164 format"""
	if not number:
		return None
	try:
		numobj = phonenumbers.parse(number, country_code)
	except phonenumbers.NumberParseException:
		return None
	if phonenumbers.is_valid_number(numobj):
		return phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
	return None


def normalise_contact_numbers(contact: Document, country_code: str, known: set[str]) -> None:
	"""Write the Contact's new phone numbers in E.164.

	Only numbers that are not in `known` (the ones the Contact already had) are touched, so
	saving a Contact never rewrites a number nobody edited. A number that cannot be parsed
	is kept as typed, and an alert says so.
	"""
	for row in contact.get("phone_nos") or []:
		number = row.get("phone")
		if not number or number in known or is_valid_E164_number(number):
			continue
		e164_number = convert_to_e164(number, country_code)
		if e164_number:
			row.set("phone", e164_number)
		else:
			frappe.msgprint(
				_("{0} could not be read as a phone number and was kept as entered").format(
					frappe.bold(number)
				),
				alert=True,
			)


def get_party_records(dt: str, link_doctype: str, link_name: str) -> list[dict]:
	"""The Addresses or Contacts (dt) linked to a party, as the current user may read them."""
	if dt not in PARTY_RECORD_DOCTYPES:
		frappe.throw(frappe._("Only Address and Contact records can be listed"), frappe.PermissionError)
	frappe.has_permission(link_doctype, "read", throw=True)
	if not frappe.db.exists(link_doctype, link_name):
		return []
	frappe.has_permission(link_doctype, "read", link_name, throw=True)

	return frappe.get_list(
		dt,
		filters=[
			["Dynamic Link", "link_doctype", "=", link_doctype],
			["Dynamic Link", "link_name", "=", link_name],
		],
		fields=["name"],
		order_by="creation asc",
		distinct=True,
	)


def clean_client_values(values: dict[str, Any]) -> dict[str, Any]:
	"""The record's values without the desk's bookkeeping, and without the placeholder names
	the desk gives new child rows, so the save names them."""

	def clean(row: dict[str, Any]) -> dict[str, Any]:
		return {
			key: value
			for key, value in row.items()
			if key not in CLIENT_ONLY_KEYS and not (key == "name" and row.get("__islocal"))
		}

	return {
		key: [clean(row) if isinstance(row, dict) else row for row in value]
		if isinstance(value, list)
		else value
		for key, value in clean(values).items()
	}


def fix_check_values(record: Document) -> None:
	"""Make the record's checkboxes 0 or 1.

	A table outside a form, as in the side panel, gives a new row its defaults as the
	docfields hold them, so an unticked box arrives as "0", which Python reads as true and
	Contact's "only one primary" validation would count.
	"""
	for doc in (record, *record.get_all_children()):
		for df in doc.meta.get("fields", {"fieldtype": "Check"}):
			doc.set(df.fieldname, cint(doc.get(df.fieldname)))


def is_linked_to(doctype: str, name: str, party_type: str, party_name: str) -> bool:
	"""Whether the saved Address or Contact `name` is linked to the party."""
	return bool(
		frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": doctype,
				"parent": name,
				"link_doctype": party_type,
				"link_name": party_name,
			},
		)
	)


def new_party_record(values: dict[str, Any], party: Document) -> Document:
	"""A new Address or Contact for the party, from the side panel's values, ready to insert.

	It is linked to the party. When the party has no primary record of its kind yet, the new
	one is marked primary, as ERPNext marks the party's primary record. A new Address with no
	country takes the geocoding result's, and failing that the Supplier's own country or the
	System Settings one (see address.set_default_country).
	"""
	doctype = values["doctype"]
	record = frappe.get_doc({key: value for key, value in values.items() if key != "name"})
	if not any(
		link.link_doctype == party.doctype and link.link_name == party.name for link in record.get("links")
	):
		record.append("links", {"link_doctype": party.doctype, "link_name": party.name})

	if not party.get(PRIMARY_RECORD_FIELDS[party.doctype][doctype]):
		record.set(PRIMARY_FLAGS[doctype], 1)

	if doctype == "Address":
		record.flags.default_country = party.get("country") or frappe.db.get_single_value(
			"System Settings", "country"
		)
	return record


@frappe.whitelist(methods=["POST"])
def save_party_record(doc: str | dict, party_type: str, party_name: str) -> dict[str, Any]:
	"""Insert or update an Address or Contact of a Customer or Supplier, from the side panel.

	`doc` is the whole record as the panel edited it: an existing one is saved as
	frappe.client.save would (so a newer version on the server is not overwritten), a new
	one (no name, or `__islocal`) is inserted and linked to the party. Both are saved with
	the user's own permissions. New phone numbers on a Contact are written in E.164, read
	in the country of the party's primary address, or of System Settings.

	Returns the saved record, the party's address and contact cards, and the party's map
	point, which an Address save may have moved.
	"""
	values = frappe.parse_json(doc) if isinstance(doc, str) else doc
	if not isinstance(values, dict) or values.get("doctype") not in PARTY_RECORD_DOCTYPES:
		frappe.throw(_("Only Address and Contact records can be saved here"), frappe.PermissionError)
	if party_type not in PRIMARY_RECORD_FIELDS:
		frappe.throw(_("Only a Customer's or a Supplier's records can be saved here"), frappe.PermissionError)

	party = frappe.get_doc(party_type, party_name)
	party.check_permission("read")

	doctype = values["doctype"]
	is_new = bool(values.get("__islocal")) or not values.get("name")
	values = clean_client_values(values)
	if is_new:
		record = new_party_record(values, party)
		known_numbers: set[str] = set()
	else:
		if not is_linked_to(doctype, values["name"], party_type, party_name):
			frappe.throw(
				_("{0} {1} is not linked to {2} {3}").format(
					_(doctype), frappe.bold(values["name"]), _(party_type), frappe.bold(party_name)
				),
				frappe.PermissionError,
			)
		record = frappe.get_doc(values)
		known_numbers = set(
			frappe.get_all(
				"Contact Phone",
				filters={"parenttype": "Contact", "parent": values["name"]},
				pluck="phone",
			)
			if doctype == "Contact"
			else []
		)

	fix_check_values(record)
	if doctype == "Contact":
		country_code = get_country_code_for_party(party, PRIMARY_RECORD_FIELDS[party_type]["Address"])
		normalise_contact_numbers(record, country_code, known_numbers)

	if is_new:
		record.insert()
	else:
		record.save()

	record.apply_fieldlevel_read_permissions()
	return {
		"doc": record.as_dict(),
		"permlevels": record.get_permlevel_access("read"),
		"addr_list": get_address_display_list(party_type, party_name),
		"contact_list": get_contact_display_list(party_type, party_name),
		"location": frappe.db.get_value(
			party_type, party_name, ["latitude", "longitude", "location"], as_dict=True
		),
	}
