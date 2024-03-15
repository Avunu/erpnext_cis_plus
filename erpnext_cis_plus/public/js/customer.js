// Copyright (c) 2023, Avunu LLC and contributors
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
    }
});

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
