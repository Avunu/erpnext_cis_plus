# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
import json
from nominatim import Nominatim

@frappe.whitelist()
def geolocate_address(doc, method=None):
    """
    Get coordinates from address
    """
    # check if address is already geocoded
    if doc.latitude and doc.longitude and doc.pincode:
        return doc
    fields = ["address_line1", "city", "state", "country"]
    # check if address is empty
    if not any([doc.get(f) for f in fields]):
        return doc
    address_string = ", ".join([doc.get(f) for f in fields if doc.get(f)])
    try:
        geolocator = Nominatim()
        geolocation = geolocator.query(address_string)
    except Exception as e:
        frappe.throw(e)
    # check if geolocation contains a result
    if not geolocation:
        frappe.log_error("Geolocation Error", "No geolocation found for address: {0}".format(address_string))
        return doc
    geolocation = geolocation[0]
    if geolocation:
        lat = geolocation['lat']
        lng = geolocation['lon']
        if lat and lng:
            doc.latitude = lat
            doc.longitude = lng
        # parse address components
        components = geolocation['display_name'].split(', ')
        doc.pincode = components[-2]
        doc.state = components[-3]
        if not doc.country:
            doc.country = components[-1]
        if not doc.county:
            doc.county = components[-4]
    return doc

@frappe.whitelist()
def generate_point(doc, method=None):
    if doc.latitude and doc.longitude:
        doc.location = json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "point_type": "Point"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [doc.longitude, doc.latitude]
                }
            }]
        })
    return doc