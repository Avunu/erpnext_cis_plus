// Copyright (c) 2023, Avunu LLC and contributors
// For license information, please see license.txt

// customize the customer form
frappe.ui.form.on("Customer", {
    setup: async function (frm) {
        if (frm.doc.customer_name && !frm.doc.customer_primary_address) {
            const addresses = await get_customer_records("Address", frm.doc.customer_name);
            if (addresses.length) {
                const first_address = addresses[0].name;
                console.log(first_address);
                frm.set_value("customer_primary_address", first_address);
                frm.refresh_field("customer_primary_address");
            }
        }
        if (frm.doc.customer_name && !frm.doc.customer_primary_contact) {
            const contacts = await get_customer_records("Contact", frm.doc.customer_name);
            if (contacts.length) {
                const first_contact = contacts[0].name;
                console.log(first_contact);
                frm.set_value("customer_primary_contact", first_contact);
                frm.refresh_field("customer_primary_contact");
            }
        }
    }
});

async function get_customer_records(dt, customer_name) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_customer_records',
            args: {
                dt: dt,
                customer_name: customer_name
            },
            callback: function (r) {
                if (r.message) {
                    resolve(r.message);
                } else {
                    reject("No records found");
                }
            }
        });
    });
}
