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


def has_stale_coordinates(doc: Document) -> bool:
	"""Whether the coordinates were looked up for the address as it was before this save.

	That is a saved Address whose geocoded fields changed while its latitude and longitude
	did not. Coordinates on a new Address, or entered with this edit (by hand, an import or
	the API), belong to the address as it is now and are never stale.
	"""
	if doc.is_new() or not (doc.get("latitude") or doc.get("longitude")):
		return False
	if doc.has_value_changed("latitude") or doc.has_value_changed("longitude"):
		return False
	return any(doc.has_value_changed(f) for f in GEOCODED_FIELDS)


def clear_stale_coordinates(doc: Document) -> None:
	"""Drop coordinates that no longer belong to the address, so the next save retries.

	Coordinates that are not stale are kept. generate_point clears the map point only
	when this cleared the coordinates, so a hand-drawn point is kept too.
	"""
	if not has_stale_coordinates(doc):
		return
	doc.set("latitude", None)
	doc.set("longitude", None)
	doc.flags.coordinates_cleared = True


def geolocate_address(doc: Document, method: str | None = None) -> Document:
	"""Set the coordinates, and fill empty address components, from Nominatim.

	A lookup that fails (timeout, HTTP error, bad response), finds nothing or gets no rate
	limit slot leaves the Address as it is, except that coordinates looked up for the
	address as it was before this save are cleared (see has_stale_coordinates). A failure
	is logged and reported as an alert. An Address without coordinates is looked up again
	on its next save.
	"""
	doc.flags.coordinates_cleared = False
	if not needs_geocoding(doc):
		return doc

	address_str = ", ".join([doc.get(f) for f in GEOCODED_FIELDS if doc.get(f)])

	if not acquire_rate_limit_slot():
		clear_stale_coordinates(doc)
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
		clear_stale_coordinates(doc)
		return doc

	if not results:
		clear_stale_coordinates(doc)
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


def set_default_country(doc: Document, method: str | None = None) -> Document:
	"""Fall back to the default country the creator set in doc.flags, if geocoding left it blank.

	Runs after geolocate_address (before_save follows validate) and before Frappe checks the
	mandatory fields. An Address created from a party's primary address fields sets the flag.
	"""
	if not doc.get("country") and doc.flags.get("default_country"):
		doc.set("country", doc.flags.default_country)
	return doc


def generate_point(doc: Document, method: str | None = None) -> Document:
	"""Store the coordinates as the GeoJSON point the Geolocation field shows.

	Without coordinates the point is left alone (it may have been drawn by hand), unless
	clear_stale_coordinates cleared them in this save, in which case the point goes too.
	"""
	if not (doc.get("latitude") and doc.get("longitude")):
		if doc.flags.get("coordinates_cleared"):
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
