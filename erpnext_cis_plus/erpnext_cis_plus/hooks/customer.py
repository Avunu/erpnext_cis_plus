# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.utils import get_link_to_form

from erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils import (
	get_party_records,
	update_party_address_and_contact,
	validate_party_address_and_contact_fields,
)


def render_map_popup(customer: dict) -> str:
	"""The HTML of a customer's map popup."""
	html = f"<strong>{get_link_to_form('Customer', customer['name'], customer['customer_name'])}</strong>"
	if customer.get("customer_primary_contact"):
		html += f"<p>{get_link_to_form('Contact', customer['customer_primary_contact'])}</p>"
	html += f"<p>{customer.get('primary_address') or ''}</p>"
	return f'<div class="map-popup">{html}</div>'


@frappe.whitelist()
def get_coords(filters: str | dict | list | None = None) -> dict:
	"""GeoJSON points for the customers the user may read.

	The Customer list names this as its get_coords_method, which on v16 only makes the Map
	view option appear; the map plots the list's rows itself and does not call this.
	"""
	customers = frappe.get_list(
		"Customer",
		filters=json.loads(filters) if isinstance(filters, str) else filters,
		fields=[
			"name",
			"customer_name",
			"customer_primary_contact",
			"primary_address",
			"latitude",
			"longitude",
		],
	)
	features = [
		{
			"type": "Feature",
			"properties": {"name": render_map_popup(customer)},
			"geometry": {
				"type": "Point",
				"coordinates": [customer.longitude, customer.latitude],
			},
		}
		for customer in customers
		if customer.latitude and customer.longitude
	]
	return {"type": "FeatureCollection", "features": features}


@frappe.whitelist()
def get_customer_records(dt: str, customer_name: str) -> list[dict]:
	"""The Addresses or Contacts (dt) linked to a Customer; customer_name is its name (ID)."""
	return get_party_records(dt, "Customer", customer_name)


def validate(doc, method=None):
	# Skip CIS Plus logic for new docs created via quick entry - let ERPNext handle it
	if doc.flags.get("is_new_doc"):
		return
	validate_party_address_and_contact_fields(
		doc,
		primary_address_field="customer_primary_address",
		primary_contact_field="customer_primary_contact",
		contact_prefix="customer_primary_contact_",
	)


def before_save(doc, method=None):
	# Keep for backward compatibility - no longer does creation
	pass


def on_update(doc, method=None):
	# Skip CIS Plus logic for new docs created via quick entry - let ERPNext handle it
	if doc.flags.get("is_new_doc"):
		return
	update_party_address_and_contact(
		doc,
		primary_address_field="customer_primary_address",
		primary_contact_field="customer_primary_contact",
		contact_prefix="customer_primary_contact_",
	)
