# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils import (
    update_party_address_and_contact,
    get_party_records
)


# get related records for the supplier
@frappe.whitelist()
def get_supplier_records(dt, supplier_name):
    return get_party_records(dt, "Supplier", supplier_name)


def before_save(doc, method=None):
    update_party_address_and_contact(
        doc,
        primary_address_field="supplier_primary_address",
        primary_contact_field="supplier_primary_contact",
        contact_prefix="supplier_primary_contact_"
    )
