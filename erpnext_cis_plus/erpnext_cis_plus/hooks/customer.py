# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils import (
    validate_party_address_and_contact_fields,
    update_party_address_and_contact,
    get_party_records
)

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
    return get_party_records(dt, "Customer", customer_name)


def validate(doc, method=None):
    validate_party_address_and_contact_fields(
        doc,
        primary_address_field="customer_primary_address",
        primary_contact_field="customer_primary_contact",
        contact_prefix="customer_primary_contact_"
    )


def before_save(doc, method=None):
    # Keep for backward compatibility - no longer does creation
    pass


def on_update(doc, method=None):
    update_party_address_and_contact(
        doc,
        primary_address_field="customer_primary_address",
        primary_contact_field="customer_primary_contact",
        contact_prefix="customer_primary_contact_"
    )
