# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils import (
    validate_party_address_and_contact_fields,
    update_party_address_and_contact,
    get_party_records
)


# get related records for the supplier
@frappe.whitelist()
def get_supplier_records(dt, supplier_name):
    return get_party_records(dt, "Supplier", supplier_name)


def validate(doc, method=None):
    validate_party_address_and_contact_fields(
        doc,
        primary_address_field="supplier_primary_address",
        primary_contact_field="supplier_primary_contact",
        contact_prefix="supplier_primary_contact_"
    )


def before_save(doc, method=None):
    # Keep for backward compatibility - no longer does creation
    pass


def on_update(doc, method=None):
    update_party_address_and_contact(
        doc,
        primary_address_field="supplier_primary_address",
        primary_contact_field="supplier_primary_contact",
        contact_prefix="supplier_primary_contact_"
    )
