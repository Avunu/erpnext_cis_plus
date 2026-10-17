// Copyright (c) 2024, Avunu LLC and contributors
// For license information, please see license.txt

/** The Address fields the Customer form edits, as `customer_primary_address_<field>`. */
const ADDRESS_FIELDS = /** @type {const} */ ([
	"address_line1",
	"address_line2",
	"city",
	"state",
	"pincode",
	"email_id",
	"phone",
	"fax",
]);

/** The Contact fields the Customer form edits, as `customer_primary_contact_<field>`. */
const CONTACT_FIELDS = /** @type {const} */ ([
	"first_name",
	"last_name",
	"email_id",
	"phone",
	"mobile_no",
	"department",
]);

// Customize the customer form
frappe.ui.form.on("Customer", {
	refresh(frm) {
		// Refresh the form layout to ensure newly created address/contact fields are displayed
		setup_form_layout(frm);
	},
	async setup(frm) {
		try {
			if (!frm.is_new() && !frm.doc.customer_primary_address) {
				const [first_address] = await get_customer_records("Address", frm.doc.name);
				if (first_address) {
					frm.set_value("customer_primary_address", first_address.name);
				}
			} else if (frm.doc.customer_primary_address) {
				const result = await frappe.db.get_value("Address", frm.doc.customer_primary_address, [
					...ADDRESS_FIELDS,
				]);
				set_changed_values(frm, "customer_primary_address_", ADDRESS_FIELDS, result?.message);
			}

			if (!frm.is_new() && !frm.doc.customer_primary_contact) {
				const [first_contact] = await get_customer_records("Contact", frm.doc.name);
				if (first_contact) {
					frm.set_value("customer_primary_contact", first_contact.name);
				}
			} else if (frm.doc.customer_primary_contact) {
				const result = await frappe.db.get_value("Contact", frm.doc.customer_primary_contact, [
					...CONTACT_FIELDS,
				]);
				set_changed_values(frm, "customer_primary_contact_", CONTACT_FIELDS, result?.message);
			}
		} catch (error) {
			console.error("Error in setup: ", error);
			frappe.msgprint(__("There was an error setting up the customer form. Please contact support."));
		}
		// setup the form layout
		setup_form_layout(frm);
	},
});

/**
 * Copy the linked record's values into the form's `<prefix><field>` fields where they differ.
 *
 * @param {frappe.ui.form.Form<"Customer">} frm
 * @param {string} prefix
 * @param {readonly string[]} fields
 * @param {Record<string, unknown> | undefined} values
 */
function set_changed_values(frm, prefix, fields, values) {
	if (!values) return;
	/** @type {Record<string, unknown>} */
	const updates = {};
	for (const field of fields) {
		const docfield = /** @type {frappe.FieldName<"Customer">} */ (prefix + field);
		if (values[field] != frm.doc[docfield]) {
			updates[docfield] = values[field];
		}
	}
	if (Object.keys(updates).length > 0) {
		frm.set_value(updates);
	}
}

/** @param {frappe.ui.form.Form<"Customer">} frm */
function setup_form_layout(frm) {
	frm.layout.sections_dict.primary_address_and_contact_detail?.columns.forEach((column) => {
		column.wrapper.children().first().addClass("input-group");
	});
	const layout_fields = {
		customer_primary_address: 12,
		customer_primary_address_address_line1: 6,
		customer_primary_address_address_line2: 6,
		customer_primary_address_city: 5,
		customer_primary_address_state: 5,
		customer_primary_address_pincode: 2,
		customer_primary_address_email_id: 6,
		customer_primary_address_phone: 6,
		customer_primary_address_fax: 6,
		customer_primary_contact: 12,
		customer_primary_contact_first_name: 6,
		customer_primary_contact_last_name: 6,
		customer_primary_contact_email_id: 6,
		customer_primary_contact_phone: 6,
		customer_primary_contact_mobile_no: 6,
		customer_primary_contact_department: 6,
	};
	const colend_fields = [
		"customer_primary_address_address_line2",
		"customer_primary_address_pincode",
		"customer_primary_address_phone",
		"customer_primary_contact_last_name",
		"customer_primary_contact_phone",
		"customer_primary_contact_department",
	];
	// assign each field the classes col-md-{width} float-left pl-0
	for (const [field, width] of Object.entries(layout_fields)) {
		let classes = "col-md-" + width + " float-left clearfix mx-0";
		// colend_fields should have no padding on the left or right
		if (colend_fields.includes(field)) {
			classes += " px-0";
		} else {
			classes += " pl-0";
		}
		// Ensure frm.fields_dict[field] exists before attempting to add classes to avoid potential errors
		const control = frm.get_field(field);
		if (control && "$wrapper" in control && control.$wrapper) {
			control.$wrapper.addClass(classes);
		}
	}
}

/**
 * The Addresses or Contacts linked to the customer.
 *
 * @param {"Address" | "Contact"} dt
 * @param {string} customer_name the Customer's name (ID)
 * @returns {Promise<{ name: string }[]>}
 */
function get_customer_records(dt, customer_name) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_customer_records",
			args: { dt, customer_name },
			callback: function (r) {
				if (r.message) {
					resolve(/** @type {{ name: string }[]} */ (r.message));
				} else {
					reject("No records found");
				}
			},
			error: function (err) {
				console.error("Error in get_customer_records: ", err);
				reject("Error fetching customer records");
			},
		});
	});
}
