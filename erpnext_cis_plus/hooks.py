# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

app_name = "erpnext_cis_plus"
app_title = "CIS Plus for ERPNext"
app_publisher = "Avunu LLC"
app_description = "Address geocoding and location maps for customers and suppliers"
app_email = "mail@avu.nu"
app_license = "MIT"
required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js in doctype views
doctype_js = {"Customer": "public/js/customer.js", "Supplier": "public/js/supplier.js"}
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
	"Customer": {
		"validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.validate",
		"before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.before_save",
		"on_update": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.on_update",
	},
	"Supplier": {
		"validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.validate",
		"before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.before_save",
		"on_update": "erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.on_update",
	},
}
