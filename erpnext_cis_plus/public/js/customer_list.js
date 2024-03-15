// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

// add a settings.get_coords_method to this list view
frappe.listview_settings['Customer'] = {
    get_coords_method: 'erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_coords'
};