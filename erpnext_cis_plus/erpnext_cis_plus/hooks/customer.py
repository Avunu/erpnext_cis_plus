# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe


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
    doctype = "Customer"
    customers = frappe.get_all(
        doctype,
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
        "address_line1", "address_line2", "city", "state", "pincode", "fax"
    ]
    contact_fields = [
        "first_name", "last_name", "department"
    ]
    child_fields = {
        "email_id": ("add_email", {}),
        "phone": ("add_phone", {"is_primary_phone": 1}),
        "mobile_no": ("add_phone", {"is_primary_mobile_no": 1})
    }

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
