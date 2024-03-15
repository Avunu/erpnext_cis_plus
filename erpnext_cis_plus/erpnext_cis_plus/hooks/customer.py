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


# Update Address and Contact on customer save
def before_save(doc, method=None):
    address_fields = [
        "address_line1", "address_line2", "city", "state", "pincode", "email_id", "phone", "fax"
    ]
    contact_fields = [
        "first_name", "last_name", "email_id", "phone", "mobile_no", "department"
    ]

    # Update Address
    if doc.customer_primary_address:
        try:
            address = frappe.get_doc("Address", doc.customer_primary_address)
            has_changes = False
            for field in address_fields:
                doc_field = f"customer_primary_address_{field}"
                if getattr(doc, doc_field, None) != getattr(address, field, None):
                    setattr(address, field, getattr(doc, doc_field))
                    has_changes = True
            if has_changes:
                address.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(message=str(e), title="Failed to update Address in Contact hook")

    # Update Contact
    if doc.customer_primary_contact:
        try:
            contact = frappe.get_doc("Contact", doc.customer_primary_contact)
            has_changes = False
            for field in contact_fields:
                doc_field = f"customer_primary_contact_{field}"
                if getattr(doc, doc_field, None) != getattr(contact, field, None):
                    setattr(contact, field, getattr(doc, doc_field))
                    has_changes = True
            if has_changes:
                contact.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(message=str(e), title="Failed to update Contact in Contact hook")
