# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Demo data for frappe-demo and the screenshots in docs/screenshots/.

A handful of Customers around York, Pennsylvania, each made the way a user would make
one with this app: the Customer is created, then an Address and a Contact are added to it
in the side panel (party_utils.save_party_record, which the panel's Save calls), and the
form makes them its primary ones and saves. The Address is geocoded on save; the demo must
not reach the network, so Nominatim answers from the table below instead. Saving the
Customer with its primary address fetches the address's map point onto it, which puts it
on the Customer's Location map.
"""

from typing import Any
from unittest.mock import patch

import frappe

from erpnext_cis_plus.erpnext_cis_plus.hooks import address as address_hooks
from erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils import save_party_record

# customer name: (address line 1, city, state, postal code, latitude, longitude, county,
# contact first name, last name, department, phone, mobile)
CUSTOMERS: dict[str, tuple[str, str, str, str, float, float, str, str, str, str, str, str]] = {
	"Codorus Timber Works": (
		"120 North George Street",
		"York",
		"PA",
		"17401",
		39.963600,
		-76.727700,
		"York County",
		"Grace",
		"Miller",
		"Purchasing",
		"(717) 555-0142",
		"717-555-0143",
	),
	"Susquehanna Mill Supply": (
		"25 Front Street",
		"Wrightsville",
		"PA",
		"17368",
		40.025700,
		-76.529700,
		"York County",
		"Daniel",
		"Brandt",
		"Operations",
		"(717) 555-0151",
		"",
	),
	"Hanover Barn Restoration": (
		"44 Carlisle Street",
		"Hanover",
		"PA",
		"17331",
		39.800700,
		-76.983000,
		"York County",
		"Ruth",
		"Keller",
		"",
		"(717) 555-0163",
		"",
	),
	"Red Lion Joinery": (
		"2 West Broadway",
		"Red Lion",
		"PA",
		"17356",
		39.900900,
		-76.605800,
		"York County",
		"Samuel",
		"Hess",
		"",
		"(717) 555-0174",
		"",
	),
	"Lancaster Beam and Post": (
		"1 Penn Square",
		"Lancaster",
		"PA",
		"17602",
		40.037900,
		-76.305500,
		"Lancaster County",
		"Esther",
		"Zimmerman",
		"Accounts",
		"(717) 555-0185",
		"",
	),
	"Gettysburg Frame Company": (
		"1 Lincoln Square",
		"Gettysburg",
		"PA",
		"17325",
		39.830900,
		-77.231100,
		"Adams County",
		"Thomas",
		"Weaver",
		"",
		"(717) 555-0196",
		"",
	),
}


class NominatimAnswer:
	"""The part of a requests.Response geolocate_address reads."""

	def __init__(self, results: list[dict[str, Any]]):
		self.results = results

	def raise_for_status(self) -> None:
		return None

	def json(self) -> list[dict[str, Any]]:
		return self.results


def nominatim(url: str, params: dict[str, Any], **kwargs: Any) -> NominatimAnswer:
	"""Answer a Nominatim search from CUSTOMERS, as the service would."""
	del url, kwargs  # requests.get's other arguments: the URL is always Nominatim's
	for line1, city, _state, pincode, lat, lon, county, *_ in CUSTOMERS.values():
		if str(params.get("q", "")).startswith(line1):
			address = {
				"city": city,
				"county": county,
				"state": "Pennsylvania",
				"postcode": pincode,
				"country": "United States",
			}
			return NominatimAnswer([{"lat": str(lat), "lon": str(lon), "address": address}])
	return NominatimAnswer([])


def default_leaf(doctype: str, setting: str) -> str | None:
	"""Selling Settings' default for a tree field, else the first non-group node."""
	value = frappe.db.get_single_value("Selling Settings", setting)
	if value:
		return str(value)
	leaf = frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="lft asc")
	return str(leaf) if leaf else None


def setup(ctx):
	"""Create the demo Customers once, with their Addresses and Contacts.

	Nothing here is dated, so `ctx["today"]` is not needed.
	"""
	del ctx  # nothing in the demo is dated or random
	customer_group = default_leaf("Customer Group", "customer_group")
	territory = default_leaf("Territory", "territory")

	with (
		patch.object(address_hooks.requests, "get", side_effect=nominatim),
		patch.object(address_hooks, "acquire_rate_limit_slot", return_value=True),
	):
		for customer_name, row in CUSTOMERS.items():
			if frappe.db.exists("Customer", {"customer_name": customer_name}):
				continue
			line1, city, state, pincode, _lat, _lon, _county, first, last, department, phone, mobile = row
			customer = frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": customer_name,
					"customer_type": "Company",
					"customer_group": customer_group,
					"territory": territory,
				}
			).insert(ignore_permissions=True)
			address = save_party_record(
				{
					"doctype": "Address",
					"address_title": customer_name,
					"address_type": "Billing",
					"address_line1": line1,
					"city": city,
					"state": state,
					"pincode": pincode,
				},
				"Customer",
				customer.name,
			)["doc"]
			email = f"{first.lower()}@{customer_name.lower().replace(' ', '-')}.example.com"
			numbers = [{"phone": phone, "is_primary_phone": 1}]
			if mobile:
				numbers.append({"phone": mobile, "is_primary_mobile_no": 1})
			contact = save_party_record(
				{
					"doctype": "Contact",
					"first_name": first,
					"last_name": last,
					"department": department,
					"email_ids": [{"email_id": email, "is_primary": 1}],
					"phone_nos": numbers,
				},
				"Customer",
				customer.name,
			)["doc"]
			# The form makes a party's first Address and Contact its primary ones and saves,
			# which fetches the Address's map point onto the Customer.
			customer.reload()
			customer.update(
				{"customer_primary_address": address["name"], "customer_primary_contact": contact["name"]}
			)
			customer.save(ignore_permissions=True)
