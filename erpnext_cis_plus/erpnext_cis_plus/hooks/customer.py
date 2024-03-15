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
