// Copyright (c) 2024, Avunu LLC and contributors
// For license information, please see license.txt

// Customize the supplier form
frappe.ui.form.on("Supplier", {
    refresh: function (frm) {
        // Refresh the form layout to ensure newly created address/contact fields are displayed
        setup_form_layout(frm);
    },
    setup: async function (frm) {
        try {
            if (frm.doc.supplier_name && !frm.doc.supplier_primary_address) {
                const addresses = await get_supplier_records("Address", frm.doc.supplier_name);
                if (addresses.length) {
                    const first_address = addresses[0].name;
                    frm.set_value("supplier_primary_address", first_address);
                }
            } else if (frm.doc.supplier_primary_address) {
                const address_fields = ["address_line1", "address_line2", "city", "state", "pincode", "email_id", "phone", "fax"];
                const result = await frappe.db.get_value("Address", frm.doc.supplier_primary_address, address_fields);
                if (result && result.message) {
                    let updates = {};
                    address_fields.forEach(field => {
                        let docfield = "supplier_primary_address_" + field;
                        if (result.message[field] != frm.doc[docfield]) {
                            updates[docfield] = result.message[field];
                        }
                    });
                    if (Object.keys(updates).length > 0) {
                        frm.set_value(updates);
                    }
                }
            }

            if (frm.doc.supplier_name && !frm.doc.supplier_primary_contact) {
                const contacts = await get_supplier_records("Contact", frm.doc.supplier_name);
                if (contacts.length) {
                    const first_contact = contacts[0].name;
                    frm.set_value("supplier_primary_contact", first_contact);
                }
            } else if (frm.doc.supplier_primary_contact) {
                const contact_fields = ["first_name", "last_name", "email_id", "phone", "mobile_no", "department"];
                const result = await frappe.db.get_value("Contact", frm.doc.supplier_primary_contact, contact_fields);
                if (result && result.message) {
                    let updates = {};
                    contact_fields.forEach(field => {
                        let docfield = "supplier_primary_contact_" + field;
                        if (result.message[field] != frm.doc[docfield]) {
                            updates[docfield] = result.message[field];
                        }
                    });
                    if (Object.keys(updates).length > 0) {
                        frm.set_value(updates);
                    }
                }
            }
        } catch (error) {
            console.error("Error in setup: ", error);
            frappe.msgprint(__("There was an error setting up the supplier form. Please contact support."));
        }
        // setup the form layout
        setup_form_layout(frm);
    }
});

async function setup_form_layout(frm) {
    frm.layout.sections_dict.primary_address_and_contact_detail_section.columns.forEach(column => {
        let column_form = column.wrapper[0].children[0];
        $(column_form).addClass("input-group");
    });
    const layout_fields = {
        "supplier_primary_address": 12,
        "supplier_primary_address_address_line1": 6,
        "supplier_primary_address_address_line2": 6,
        "supplier_primary_address_city": 5,
        "supplier_primary_address_state": 5,
        "supplier_primary_address_pincode": 2,
        "supplier_primary_address_email_id": 6,
        "supplier_primary_address_phone": 6,
        "supplier_primary_address_fax": 6,
        "supplier_primary_contact": 12,
        "supplier_primary_contact_first_name": 6,
        "supplier_primary_contact_last_name": 6,
        "supplier_primary_contact_email_id": 6,
        "supplier_primary_contact_phone": 6,
        "supplier_primary_contact_mobile_no": 6,
        "supplier_primary_contact_department": 6
    };
    const colend_fields = [
        "supplier_primary_address_address_line2",
        "supplier_primary_address_pincode",
        "supplier_primary_address_phone",
        "supplier_primary_contact_last_name",
        "supplier_primary_contact_phone",
        "supplier_primary_contact_department",
    ];
    // assign each field the classes col-md-{width} float-left pl-0
    for (let field in layout_fields) {
        let width = layout_fields[field];
        let classes = "col-md-" + width + " float-left clearfix";
        // colend_fields should have no padding on the left or right
        if (colend_fields.includes(field)) {
            classes += " px-0";
        } else {
            classes += " pl-0";
        }
        // Ensure frm.fields_dict[field] exists before attempting to add classes to avoid potential errors
        if(frm.fields_dict[field] && frm.fields_dict[field].$wrapper) {
            frm.fields_dict[field].$wrapper.addClass(classes);
        }
    }
}

async function get_supplier_records(dt, supplier_name) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.get_supplier_records',
            args: { dt, supplier_name },
            callback: function (r) {
                if (r.message) {
                    resolve(r.message);
                } else {
                    reject("No records found");
                }
            },
            error: function (err) {
                console.error("Error in get_supplier_records: ", err);
                reject("Error fetching supplier records");
            }
        });
    });
}
