# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
import phonenumbers

# Get a list of coordinates for the map view
@frappe.whitelist()
def get_coords(filters):
    popup_template = """
        <div class="map-popup">
            <strong>{{ frappe.utils.get_link_to_form('Customer', name, customer_name) }}</strong>
            {% if customer_primary_contact %}
                <p>{{ frappe.utils.get_link_to_form('Contact', customer_primary_contact) }}</p>
            {% endif %}
            <p>{{ primary_address }}</p>
        </div>
        """
    filters = frappe.parse_json(filters)
    customers = frappe.get_all(
        "Customer",
        filters=filters,
        fields=[
            "name",
            "customer_name",
            "customer_primary_contact",
            "primary_address",
            "latitude",
            "longitude",
        ],
    )
    geojson = {"type": "FeatureCollection", "features": None}
    features = []
    for customer in customers:
        if customer.latitude and customer.longitude:
            popup_contents = frappe.render_template(popup_template, customer)
            features.append(
                {
                    "type": "Feature",
                    "properties": {"name": popup_contents},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [customer.longitude, customer.latitude],
                    },
                }
            )
    geojson["features"] = features
    return geojson


# get related records for the customer
@frappe.whitelist()
def get_customer_records(dt, customer_name):

    dlink = frappe.qb.DocType("Dynamic Link")

    return (
        frappe.qb.from_(dlink)
        .select(dlink.parent.as_("name"))
        .where(
            (dlink.parenttype == dt)
            & (dlink.link_doctype == "Customer")
            & (dlink.link_name == customer_name)
        )
        .run(as_dict=True)
    )

def before_save(doc, method=None):
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
    country_code = get_country_code_for_customer(doc)
    validate_customer_phone_numbers(doc, country_code)

    # Update Address
    if doc.customer_primary_address:
        address = frappe.get_doc("Address", doc.customer_primary_address)
        update_doc_fields(address, address_fields, doc, "customer_primary_address_")

    # Update Contact
    if doc.customer_primary_contact:
        contact = frappe.get_doc("Contact", doc.customer_primary_contact)
        update_doc_fields(contact, contact_fields, doc, "customer_primary_contact_")
        update_child_fields(contact, child_fields, doc)

        contact.save(ignore_permissions=True)

def update_doc_fields(target_doc, fields, source_doc, prefix):
    has_changes = False
    for field in fields:
        doc_field = f"{prefix}{field}"
        doc_field_value = getattr(source_doc, doc_field, None)
        if doc_field_value != getattr(target_doc, field, None):
            setattr(target_doc, field, doc_field_value)
            has_changes = True
    if has_changes:
        target_doc.save(ignore_permissions=True)

def update_child_fields(contact, child_fields, source_doc):
    for field, (method_name, kwargs) in child_fields.items():
        doc_field = f"customer_primary_contact_{field}"
        value = getattr(source_doc, doc_field, None)
        if value:
            # Check if the add_{field} method exists on the contact and call it
            if hasattr(contact, method_name):
                method = getattr(contact, method_name)
                method(value, **kwargs)

def get_country_code_for_customer(doc):
    """Get country code for the customer's primary address"""
    country = ""
    if doc.customer_primary_address:
        country = frappe.get_value("Address", doc.customer_primary_address, "country")
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
    except:
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
    except:
        return None
    if phonenumbers.is_valid_number(numobj):
        return phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
    return None


def validate_customer_phone_numbers(doc, country_code):
    """Validate and convert phone numbers to E.164 format before saving"""
    phone_fields = ["customer_primary_contact_phone", "customer_primary_contact_mobile_no"]
    
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
