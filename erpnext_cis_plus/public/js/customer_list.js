// Copyright (c) 2024, Avunu LLC and contributors
// For license information, please see license.txt

/**
 * On v16, get_coords_method only makes the Map view option appear in the Customer list;
 * the map itself plots the list's own rows from their location fields and does not call
 * get_coords. Merged into ERPNext's settings for the list, which load first, rather than
 * replacing them.
 *
 * @type {frappe.views.ListViewSettings<"Customer">}
 */
const settings = {
	get_coords_method: "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_coords",
};
frappe.listview_settings["Customer"] = { ...frappe.listview_settings["Customer"], ...settings };
