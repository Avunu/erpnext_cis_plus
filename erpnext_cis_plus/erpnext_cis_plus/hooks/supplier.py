# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe

from erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils import get_party_records


@frappe.whitelist()
def get_supplier_records(dt: str, supplier_name: str) -> list[dict]:
	"""The Addresses or Contacts (dt) linked to a Supplier; supplier_name is its name (ID)."""
	return get_party_records(dt, "Supplier", supplier_name)
