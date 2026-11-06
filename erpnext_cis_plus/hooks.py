# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

app_name = "erpnext_cis_plus"
app_title = "CIS Plus for ERPNext"
app_publisher = "Avunu LLC"
app_description = "Address geocoding and location maps for customers and suppliers"
app_email = "mail@avu.nu"
app_license = "MIT"

# Frappe's About dialog takes the logo from here. not_listed keeps the app off the apps screen.
# app_logo_url would change the site's own logo.
add_to_apps_screen = [
	{
		"name": "erpnext_cis_plus",
		"logo": "/assets/erpnext_cis_plus/images/erpnext_cis_plus-logo.svg",
		"title": "CIS Plus for ERPNext",
		"route": "/desk",
		"has_permission": "erpnext_cis_plus.apps_screen.not_listed",
	}
]
required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js in doctype views
doctype_js = {
	"Customer": ["public/js/party_records.js", "public/js/customer.js"],
	"Supplier": ["public/js/party_records.js", "public/js/supplier.js"],
}
doctype_list_js = {"Customer": "public/js/customer_list.js"}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Address": {
		"before_save": [
			"erpnext_cis_plus.erpnext_cis_plus.hooks.address.set_default_country",
			"erpnext_cis_plus.erpnext_cis_plus.hooks.address.generate_point",
		],
		"validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.address.geolocate_address",
		"on_update": "erpnext_cis_plus.erpnext_cis_plus.hooks.address.update_party_locations",
	},
}
