## Customer Information System Enhancements for ERPNext

Various enhancements to the customer, contact, and address management for ERPNext, especially suitable to small business, where a single contact and address per customer is common. Frappe geolocation is used to provide a map view of the customer's address.

## What does it do?

- Adds geolocation and address validation to the Address Doctype (utilizes the free OpenStreetMap Nominatim service)
- Sets the default address and contact automatically on the Customer Doctype
- Enables default address and contact editing on the Customer Doctype
- Provides a map view with basic customer information for the Customer Doctype

## What does it look like?

Here's a screenshot of the Customer Doctype with the new primary address and contact editing functionality:

![screenshot](erpnext_cis_plus.png "ERPNext CIS Plus Screenshot")

## How to install?

Install the app using the following commands

```bash
bench get-app https://github.com/Avunu/erpnext_cis_plus
bench --site [site-name] install-app erpnext_cis_plus
```

## Show me the code!

Sure! The custom fields and properties doctype overrides are located in [erpnext_cis_plus/erpnext_cis_plus/erpnext_cis_plus/custom/](erpnext_cis_plus/erpnext_cis_plus/erpnext_cis_plus/custom/) and the doctype hooks are located in [erpnext_cis_plus/erpnext_cis_plus/erpnext_cis_plus/hooks/](erpnext_cis_plus/erpnext_cis_plus/erpnext_cis_plus/hooks/).

#### License

mit