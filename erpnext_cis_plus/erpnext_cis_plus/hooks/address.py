# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import json
import time

import frappe
import requests
import us
from frappe.model.document import Document
from frappe.utils import flt

from erpnext_cis_plus import __version__

# Geocoding uses the public Nominatim service, so it follows its usage policy
# (https://operations.osmfoundation.org/policies/nominatim/): an identifying User-Agent,
# at most one request per second from the bench, no repeated queries for an address that
# has not changed (the coordinates stored on the Address are the cache), and a timeout so
# a slow service never holds a save open.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = f"erpnext_cis_plus/{__version__} (+https://github.com/Avunu/erpnext_cis_plus)"
REQUEST_TIMEOUT = (5, 10)  # seconds: (connect, read)
RATE_LIMIT_KEY = "erpnext_cis_plus:nominatim:last-request"
RATE_LIMIT_INTERVAL_MS = 1000
RATE_LIMIT_MAX_WAIT = 5.0  # seconds to wait for a free slot before skipping this lookup
GEOCODED_FIELDS = ("address_line1", "city", "state", "pincode", "country")


def get_state_abbrev(state_name: str | None, country: str | None) -> str | None:
	"""Convert a state name to its abbreviation for supported countries."""
	if not state_name:
		return state_name

	if country == "United States":
		state = us.states.lookup(state_name)
		return state.abbr if state else state_name
	return state_name


def acquire_rate_limit_slot() -> bool:
	"""Wait for Nominatim's one-request-per-second slot, shared by every site on the bench.

	Return False when no slot came free within RATE_LIMIT_MAX_WAIT.
	"""
	cache = frappe.cache
	if cache is None:  # no Redis connection to coordinate through
		return True
	deadline = time.monotonic() + RATE_LIMIT_MAX_WAIT
	while True:
		# SET NX PX: the key exists for one interval after the last request (bench-wide,
		# deliberately not namespaced by site)
		if cache.set(RATE_LIMIT_KEY, 1, nx=True, px=RATE_LIMIT_INTERVAL_MS):
			return True
		if time.monotonic() >= deadline:
			return False
		time.sleep(0.1)


def needs_geocoding(doc: Document) -> bool:
	"""Whether the address has something to look up that was not looked up already."""
	if not any(doc.get(f) for f in GEOCODED_FIELDS):
		return False
	if doc.is_new() or not (doc.get("latitude") and doc.get("longitude")):
		return True
	return any(doc.has_value_changed(f) for f in GEOCODED_FIELDS)


def clear_coordinates(doc: Document) -> None:
	"""Drop coordinates that no longer belong to the address, so the next save retries."""
	doc.set("latitude", None)
	doc.set("longitude", None)


def geolocate_address(doc: Document, method: str | None = None) -> Document:
	"""Set the coordinates, and fill empty address components, from Nominatim.

	A lookup that fails (timeout, HTTP error, bad response), finds nothing or gets no rate
	limit slot clears the coordinates, which may belong to the address as it was before
	this change, and the Address saves without them. A failure is logged and reported as
	an alert. An Address without coordinates is looked up again on its next save.
	"""
	if not needs_geocoding(doc):
		return doc

	address_str = ", ".join([doc.get(f) for f in GEOCODED_FIELDS if doc.get(f)])

	if not acquire_rate_limit_slot():
		clear_coordinates(doc)
		frappe.msgprint(
			frappe._("Geolocation skipped: the geocoding service is busy. Save again to retry."),
			alert=True,
		)
		return doc

	try:
		response = requests.get(
			NOMINATIM_URL,
			params={"q": address_str, "format": "json", "limit": 1, "addressdetails": 1},
			headers={"User-Agent": USER_AGENT},
			timeout=REQUEST_TIMEOUT,
		)
		response.raise_for_status()
		results = response.json()
	except (requests.RequestException, ValueError) as e:
		frappe.log_error("Geolocation Error", f"{address_str}\n\n{e!s}")
		frappe.msgprint(frappe._("Geolocation failed: {0}").format(str(e)), alert=True)
		clear_coordinates(doc)
		return doc

	if not results:
		clear_coordinates(doc)
		return doc

	result = results[0]
	address = result.get("address", {})

	# Update coordinates
	doc.set("latitude", flt(result.get("lat")))
	doc.set("longitude", flt(result.get("lon")))

	# Fill empty Frappe fields from Nominatim's address components
	if not doc.get("pincode") and address.get("postcode"):
		doc.set("pincode", address.get("postcode"))
	if not doc.get("country") and address.get("country"):
		doc.set("country", address.get("country"))
	if not doc.get("state") and address.get("state"):
		doc.set("state", get_state_abbrev(address.get("state"), doc.get("country")))
	if not doc.get("county") and address.get("county"):
		doc.set("county", address.get("county"))
	city = address.get("city") or address.get("town") or address.get("village")
	if not doc.get("city") and city:
		doc.set("city", city)

	return doc


def generate_point(doc: Document, method: str | None = None) -> Document:
	"""Store the coordinates as the GeoJSON point the Geolocation field shows.

	An Address without coordinates gets no point, so a cleared lookup clears it too.
	"""
	if not (doc.get("latitude") and doc.get("longitude")):
		doc.set("location", None)
	else:
		doc.set(
			"location",
			json.dumps(
				{
					"type": "FeatureCollection",
					"features": [
						{
							"type": "Feature",
							"properties": {"point_type": "Point"},
							"geometry": {
								"type": "Point",
								"coordinates": [doc.get("longitude"), doc.get("latitude")],
							},
						}
					],
				}
			),
		)
	return doc
