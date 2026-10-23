// Copyright (c) 2024, Avunu LLC and contributors
// For license information, please see license.txt

// The Customer's Addresses and Contacts are edited in the side panel: see party_records.js,
// which runs just before this file.

/** The Customer fields naming its primary Address and Contact. */
const PRIMARY_FIELDS = /** @type {const} */ ({
	Address: "customer_primary_address",
	Contact: "customer_primary_contact",
});

frappe.ui.form.on("Customer", {
	// onload runs once for each record opened, setup only once for the form
	onload(frm) {
		erpnext_cis_plus.party_records.select_default_primary(
			frm,
			PRIMARY_FIELDS,
			"erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_customer_records",
			"customer_name",
		);
	},
	// After ERPNext's refresh, which draws the address and contact cards
	refresh(frm) {
		erpnext_cis_plus.party_records.bind_cards(frm, PRIMARY_FIELDS);
	},
});
