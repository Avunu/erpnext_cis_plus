# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
import json
import requests
import us

# from erpnext.accounts.custom.address import ERPNextAddress

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "FrappeERP/1.0"

def get_state_abbrev(state_name, country):
    """Convert state name to abbreviation for supported countries"""
    if not state_name:
        return state_name
        
    if country == 'United States':
        try:
            state = us.states.lookup(state_name)
            return state.abbr if state else state_name
        except AttributeError:
            return state_name
    return state_name

@frappe.whitelist()
def geolocate_address(doc, method=None):
    """Get coordinates and normalized address components from Nominatim"""
    # if doc.latitude and doc.longitude and doc.pincode:
    #     return doc

    fields = ["address_line1", "city", "state", "pincode", "country"]
    if not any([doc.get(f) for f in fields]):
        return doc

    address_str = ", ".join([doc.get(f) for f in fields if doc.get(f)])

    try:
        params = {
            'q': address_str,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {'User-Agent': USER_AGENT}
        
        response = requests.get(NOMINATIM_URL, params=params, headers=headers)
        response.raise_for_status()
        results = response.json()

        if not results:
            # frappe.log_error(
            #     "Geolocation Error", 
            #     f"No geolocation found for address: {address_str}"
            # )
            return

        result = results[0]
        address = result.get('address', {})

        # Update coordinates
        doc.latitude = result.get('lat')
        doc.longitude = result.get('lon')

        # Map Nominatim address components to Frappe fields
        if not doc.pincode and address.get('postcode'):
            doc.pincode = address.get('postcode')
        if not doc.country and address.get('country'):
            doc.country = address.get('country')
        if not doc.state and address.get('state'):
            state_name = address.get('state')
            doc.state = get_state_abbrev(state_name, doc.country)
        if not doc.county and address.get('county'):
            doc.county = address.get('county')
        if not doc.city and address.get('city') or address.get('town') or address.get('village'):
            doc.city = address.get('city') or address.get('town') or address.get('village')

    except Exception as e:
        frappe.log_error("Geolocation Error", str(e))
        frappe.throw(f"Geolocation failed: {str(e)}")

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