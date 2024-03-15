app_name = "erpnext_cis_plus"
app_title = "ERPNext Customer Plus"
app_publisher = "Avunu LLC"
app_description = "Various enhancements to the customer, contact, and address management for ERPNext."
app_email = "mail@avu.nu"
app_license = "mit"
required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js in doctype views
doctype_js = {"Customer" : "public/js/customer.js"}
doctype_list_js = {"Customer" : "public/js/customer_list.js"}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Address": {
        "before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.address.generate_point",
		"validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.address.geolocate_address"
	},
    "Customer": {
        "before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.before_save"
    }
}