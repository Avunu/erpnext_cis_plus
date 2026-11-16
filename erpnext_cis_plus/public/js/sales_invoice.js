// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// The email composer starts with the invoice's recipients (erpnext_cis_plus/hooks/sales_invoice.py):
// the Contact Person, or else the customer's billing contact, and the billing address's email.
// The server sends them as the virtual email_recipients field; they're refetched when the
// customer, contact or address change on the form.
frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		// ERPNext's SellingController points this at contact_email (one address). The composer
		// takes its To list from this field, overwriting whatever get_email_recipients gave it.
		frm.email_field = "email_recipients";
	},

	get_email_recipients(frm, fieldname) {
		if (fieldname !== "recipients") return [];
		return (frm.doc.email_recipients || "")
			.split(/[,;\n]/)
			.map((email) => email.trim())
			.filter(Boolean);
	},

	customer: refresh_email_recipients,
	contact_person: refresh_email_recipients,
	customer_address: refresh_email_recipients,
});

/** @param {frappe.ui.form.Form} frm */
async function refresh_email_recipients(frm) {
	const { customer, contact_person, customer_address } = frm.doc;
	if (!customer) {
		frm.doc.email_recipients = "";
		return;
	}
	const r = await frappe.call({
		method: "erpnext_cis_plus.erpnext_cis_plus.hooks.sales_invoice.get_sales_invoice_email_recipients",
		args: { customer, contact_person, customer_address },
	});
	// a direct assignment: the field is virtual, so this must not mark the form dirty
	frm.doc.email_recipients = (r.message || []).join("\n");
}
