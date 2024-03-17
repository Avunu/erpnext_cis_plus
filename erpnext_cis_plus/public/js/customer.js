// Copyright (c) 2024, Avunu LLC and contributors
// For license information, please see license.txt

// Customize the customer form
frappe.ui.form.on("Customer", {
    setup: async function (frm) {
        try {
            if (frm.doc.customer_name && !frm.doc.customer_primary_address) {
                const addresses = await get_customer_records("Address", frm.doc.customer_name);
                if (addresses.length) {
                    const first_address = addresses[0].name;
                    frm.set_value("customer_primary_address", first_address);
                }
            } else if (frm.doc.customer_primary_address) {
                const address_fields = ["address_line1", "address_line2", "city", "state", "pincode", "email_id", "phone", "fax"];
                const result = await frappe.db.get_value("Address", frm.doc.customer_primary_address, address_fields);
                if (result && result.message) {
                    let updates = {};
                    address_fields.forEach(field => {
                        let docfield = "customer_primary_address_" + field;
                        if (result.message[field] != frm.doc[docfield]) {
                            updates[docfield] = result.message[field];
                        }
                    });
                    if (Object.keys(updates).length > 0) {
                        frm.set_value(updates);
                    }
                }
            }

            if (frm.doc.customer_name && !frm.doc.customer_primary_contact) {
                const contacts = await get_customer_records("Contact", frm.doc.customer_name);
                if (contacts.length) {
                    const first_contact = contacts[0].name;
                    frm.set_value("customer_primary_contact", first_contact);
                }
            } else if (frm.doc.customer_primary_contact) {
                const contact_fields = ["first_name", "last_name", "email_id", "phone", "mobile_no", "department"];
                const result = await frappe.db.get_value("Contact", frm.doc.customer_primary_contact, contact_fields);
                if (result && result.message) {
                    let updates = {};
                    contact_fields.forEach(field => {
                        let docfield = "customer_primary_contact_" + field;
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
            frappe.msgprint(__("There was an error setting up the customer form. Please contact support."));
        }
        // setup the form layout
        setup_form_layout(frm);
    }
});

async function setup_form_layout(frm) {
    frm.layout.sections_dict.primary_address_and_contact_detail.columns.forEach(column => {
        let column_form = column.wrapper[0].children[0];
        console.log("column_form: ", column_form);
        $(column_form).addClass("input-group");
    });
    const layout_fields = {
        "customer_primary_address_address_line1": 6,
        "customer_primary_address_address_line2": 6,
        "customer_primary_address_city": 5,
        "customer_primary_address_state": 5,
        "customer_primary_address_pincode": 2,
        "customer_primary_address_email_id": 6,
        "customer_primary_address_phone": 6,
        "customer_primary_address_fax": 6,
        "customer_primary_contact_first_name": 6,
        "customer_primary_contact_last_name": 6,
        "customer_primary_contact_email_id": 6,
        "customer_primary_contact_phone": 6,
        "customer_primary_contact_mobile_no": 6,
        "customer_primary_contact_department": 6
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

async function get_customer_records(dt, customer_name) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_customer_records',
            args: { dt, customer_name },
            callback: function (r) {
                if (r.message) {
                    resolve(r.message);
                } else {
                    reject("No records found");
                }
            },
            error: function (err) {
                console.error("Error in get_customer_records: ", err);
                reject("Error fetching customer records");
            }
        });
    });
}
