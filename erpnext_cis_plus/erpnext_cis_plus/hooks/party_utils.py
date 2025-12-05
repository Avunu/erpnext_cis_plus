# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
import phonenumbers


def update_doc_fields(target_doc, fields, source_doc, prefix):
    """Update fields in target doc from source doc with prefix"""
    has_changes = False
    for field in fields:
        doc_field = f"{prefix}{field}"
        doc_field_value = getattr(source_doc, doc_field, None)
        if doc_field_value != getattr(target_doc, field, None):
            setattr(target_doc, field, doc_field_value)
            has_changes = True
    if has_changes:
        target_doc.save(ignore_permissions=True)


def update_child_fields(contact, child_fields, source_doc, prefix):
    """Update child table fields in contact from source doc"""
    for field, (method_name, kwargs) in child_fields.items():
        doc_field = f"{prefix}{field}"
        value = getattr(source_doc, doc_field, None)
        if value:
            # Check if the add_{field} method exists on the contact and call it
            if hasattr(contact, method_name):
                method = getattr(contact, method_name)
                method(value, **kwargs)


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
        return (
            phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
            == number
        )
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


def validate_party_phone_numbers(doc, phone_fields, country_code):
    """Validate and convert phone numbers to E.164 format before saving"""
    for field in phone_fields:
        phone_value = getattr(doc, field, None)
        if phone_value:
            if not is_valid_E164_number(phone_value):
                e164_number = convert_to_e164(phone_value, country_code)
                if e164_number:
                    setattr(doc, field, e164_number)
                else:
                    frappe.msgprint(
                        f"Invalid phone number format for {field}: {phone_value}",
                        alert=True
                    )


def update_party_address_and_contact(doc, primary_address_field, primary_contact_field, contact_prefix):
    """Generic method to update address and contact for a party (Customer/Supplier)"""
    address_fields = [
        "address_line1", "address_line2", "city", "state", "pincode", "email_id", "phone", "fax"
    ]
    contact_fields = [
        "first_name", "last_name", "department"
    ]
    child_fields = {
        "email_id": ("add_email", {}),
        "phone": ("add_phone", {"is_primary_phone": 1}),
        "mobile_no": ("add_phone", {"is_primary_mobile_no": 1})
    }

    # Validate and convert phone numbers to E164 format
    country_code = get_country_code_for_party(doc, primary_address_field)
    phone_fields = [f"{contact_prefix}{field}" for field in ["phone", "mobile_no"]]
    validate_party_phone_numbers(doc, phone_fields, country_code)

    # Update Address
    primary_address = getattr(doc, primary_address_field, None)
    if primary_address:
        address = frappe.get_doc("Address", primary_address)
        address_prefix = f"{primary_address_field}_"
        update_doc_fields(address, address_fields, doc, address_prefix)

    # Update Contact
    primary_contact = getattr(doc, primary_contact_field, None)
    if primary_contact:
        contact = frappe.get_doc("Contact", primary_contact)
        update_doc_fields(contact, contact_fields, doc, contact_prefix)
        update_child_fields(contact, child_fields, doc, contact_prefix)
        contact.save(ignore_permissions=True)


@frappe.whitelist()
def get_party_records(dt, link_doctype, link_name):
    """Get related records for a party (Customer/Supplier)"""
    dlink = frappe.qb.DocType("Dynamic Link")

    return (
        frappe.qb.from_(dlink)
        .select(dlink.parent.as_("name"))
        .where(
            (dlink.parenttype == dt)
            & (dlink.link_doctype == link_doctype)
            & (dlink.link_name == link_name)
        )
        .run(as_dict=True)
    )
