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


def create_address(doc, address_fields, address_prefix, party_type, party_name):
    """Create a new address record for a party"""
    address = frappe.new_doc("Address")
    
    # Copy address fields from the party document
    for field in address_fields:
        value = getattr(doc, f"{address_prefix}{field}", None)
        if value:
            setattr(address, field, value)
    
    # Add the link to the party
    address.append("links", {
        "link_doctype": party_type,
        "link_name": party_name
    })
    
    # Set as primary address
    address.is_primary_address = 1
    
    # Save the address
    address.insert(ignore_permissions=True)
    
    return address


def create_contact(doc, contact_fields, child_fields, contact_prefix, party_type, party_name):
    """Create a new contact record for a party
    
    Note: Since this is creating a new contact, we don't need to check for duplicate
    child entries as the contact starts with empty child tables.
    """
    contact = frappe.new_doc("Contact")
    
    # Copy simple contact fields from the party document
    for field in contact_fields:
        value = getattr(doc, f"{contact_prefix}{field}", None)
        if value:
            setattr(contact, field, value)
    
    # Add the link to the party
    contact.append("links", {
        "link_doctype": party_type,
        "link_name": party_name
    })
    
    # Set as primary contact
    contact.is_primary_contact = 1
    
    # Handle child table fields (email, phone, mobile_no)
    # Since this is a new contact, child tables are empty, so no need to check for duplicates
    for field, (method_name, kwargs) in child_fields.items():
        value = getattr(doc, f"{contact_prefix}{field}", None)
        if value and hasattr(contact, method_name):
            method = getattr(contact, method_name)
            method(value, **kwargs)
    
    # Save the contact
    contact.insert(ignore_permissions=True)
    
    return contact


def update_party_address_and_contact(doc, primary_address_field, primary_contact_field, contact_prefix):
    """Generic method to update or create address and contact for a party (Customer/Supplier)
    
    This function handles both new and existing documents. It will:
    - Update existing address/contact if they exist
    - Create new address/contact if data is provided but no primary exists
    - Validate that all required fields are present when creating new records
    """
    # Required fields for creating new address
    required_address_fields = ["address_line1"]
    # Required fields for creating new contact
    required_contact_fields = ["first_name"]
    
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

    # Determine the party type and name from the doc
    party_type = doc.doctype
    party_name = doc.name

    # Handle Address - works for both new and existing documents
    primary_address = getattr(doc, primary_address_field, None)
    address_prefix = f"{primary_address_field}_"
    
    # Check if any address fields have data
    has_address_data = any(getattr(doc, f"{address_prefix}{field}", None) for field in address_fields)
    
    if primary_address:
        # Update existing address
        address = frappe.get_doc("Address", primary_address)
        update_doc_fields(address, address_fields, doc, address_prefix)
    elif has_address_data:
        # Validate required fields before creating new address
        missing_fields = []
        for field in required_address_fields:
            if not getattr(doc, f"{address_prefix}{field}", None):
                missing_fields.append(field.replace("_", " ").title())
        
        if missing_fields:
            frappe.throw(
                f"To create a new address, please provide: {', '.join(missing_fields)}"
            )
        
        # Create new address if data is provided but no primary address exists
        if party_name:
            address = create_address(doc, address_fields, address_prefix, party_type, party_name)
            if address:
                setattr(doc, primary_address_field, address.name)

    # Handle Contact - works for both new and existing documents
    primary_contact = getattr(doc, primary_contact_field, None)
    
    # Check if any contact fields have data
    has_contact_data = any(getattr(doc, f"{contact_prefix}{field}", None) for field in contact_fields + list(child_fields.keys()))
    
    if primary_contact:
        # Update existing contact
        contact = frappe.get_doc("Contact", primary_contact)
        update_doc_fields(contact, contact_fields, doc, contact_prefix)
        update_child_fields(contact, child_fields, doc, contact_prefix)
        contact.save(ignore_permissions=True)
    elif has_contact_data:
        # Validate required fields before creating new contact
        missing_fields = []
        for field in required_contact_fields:
            if not getattr(doc, f"{contact_prefix}{field}", None):
                missing_fields.append(field.replace("_", " ").title())
        
        if missing_fields:
            frappe.throw(
                f"To create a new contact, please provide: {', '.join(missing_fields)}"
            )
        
        # Create new contact if data is provided but no primary contact exists
        if party_name:
            contact = create_contact(doc, contact_fields, child_fields, contact_prefix, party_type, party_name)
            if contact:
                setattr(doc, primary_contact_field, contact.name)


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
