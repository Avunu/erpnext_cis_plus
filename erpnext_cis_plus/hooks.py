app_name = "erpnext_cis_plus"
app_title = "ERPNext CIS Plus"
app_publisher = "Avunu LLC"
app_description = (
    "Various enhancements to the customer, contact, and address management for ERPNext."
)
app_email = "mail@avu.nu"
app_license = "mit"
required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js in doctype views
doctype_js = {
    "Customer": "public/js/customer.js",
    "Supplier": "public/js/supplier.js"
}
doctype_list_js = {"Customer": "public/js/customer_list.js"}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Address": {
        "before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.address.generate_point",
        "validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.address.geolocate_address",
    },
    "Customer": {
        "validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.validate",
        "before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.before_save",
        "on_update": "erpnext_cis_plus.erpnext_cis_plus.hooks.customer.on_update"
    },
    "Supplier": {
        "validate": "erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.validate",
        "before_save": "erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.before_save",
        "on_update": "erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.on_update"
    },
}