---
title: How it works
description: The hooks, document events, side panel wrapper and save method behind CIS Plus for ERPNext, and how data flows between an Address and its parties.
nav_title: How it works
order: 10
updated: 2026-10-26
---

CIS Plus is a small app with no doctypes of its own. It adds custom fields, three Address document events, two form scripts and a list script, and four whitelisted methods. This page follows the data through them.

## Hooks

`erpnext_cis_plus/hooks.py` registers:

- `doctype_js` for Customer and Supplier: `public/js/party_records.js` followed by `customer.js` or `supplier.js`. Frappe concatenates them into one doctype script, so `party_records.js` defines `erpnext_cis_plus.party_records` once and both form scripts call it.
- `doctype_list_js` for Customer: `customer_list.js`, which merges `get_coords_method` into ERPNext's own list settings for Customer.
- `doc_events` for Address: `validate`, `before_save` and `on_update`, all in `erpnext_cis_plus/erpnext_cis_plus/hooks/address.py`.

There are no class overrides, scheduled jobs, install hooks or fixtures. The custom fields live in `erpnext_cis_plus/erpnext_cis_plus/custom/` with `sync_on_migrate`, so Frappe syncs them on install and on every migrate.

## Geocoding an Address

Frappe runs an Address's `validate` hooks before its `before_save` hooks, and checks mandatory fields after both.

1. **`validate`: `geolocate_address`.** `needs_geocoding` decides whether to look the address up: not when the five geocoded fields (`address_line1`, `city`, `state`, `pincode`, `country`) are all blank; always when the Address is new or has no coordinates; otherwise only when one of those fields changed. The lookup waits for a rate limit slot (`acquire_rate_limit_slot`): a Redis key, `erpnext_cis_plus:nominatim:last-request`, set with `NX` and a one-second expiry, shared by every site on the bench. It polls every 0.1 seconds for up to five seconds. With no Redis connection it does not coordinate. Then one `requests.get` to `https://nominatim.openstreetmap.org/search` with `format=json`, `limit=1` and `addressdetails=1`, an identifying User-Agent and a `(5, 10)` second timeout. The first result sets `latitude` and `longitude` and fills blank fields; `get_state_abbrev` uses the `us` package to shorten a United States state. A failed request is logged (`frappe.log_error`, title **Geolocation Error**) and shown as an alert. A failure, an empty result or no slot calls `clear_stale_coordinates`, which drops coordinates only when they belong to the address as it was before this save, and sets `doc.flags.coordinates_cleared`.
2. **`before_save`: `set_default_country`.** When the Address still has no country and `doc.flags.default_country` is set, it takes that country. Only `save_party_record` sets the flag, for a new Address from the side panel.
3. **`before_save`: `generate_point`.** With coordinates, it writes the GeoJSON `FeatureCollection` with one point that the Geolocation field `location` shows. Without them it leaves `location` alone, so a hand-drawn point stays, unless `coordinates_cleared` says this save dropped them.
4. **`on_update`: `update_party_locations`.** When `latitude`, `longitude` or `location` changed, it writes them with `frappe.db.set_value` (without touching `modified`) to every Customer whose `customer_primary_address` and every Supplier whose `supplier_primary_address` is this Address. A missing coordinate is written as 0, because the parties' Float columns are not nullable.

On the parties, `latitude`, `longitude` and `location` have `fetch_from` set to the primary address's fields, so saving the party, or changing its primary address in the form, also fetches them.

## The side panel editor

Frappe v16's side panel (`frappe/public/js/frappe/ui/side_panel.js`, loaded as `side_panel.bundle.js`) only previews documents read-only and has no hook for a view of its own. `party_records.js` therefore wraps the prototype of `frappe.ui.SidePanel` once the bundle has loaded, the way [avunu_erp](https://github.com/Avunu/avunu_erp/pull/11) gives the Email Queue a view there:

- `render_doc` draws an editor only for the records in the script's `editors` map, which holds the records opened from a party's cards with the form they belong to. Every other preview falls through to Frappe's own `render_doc`.
- `set_header` titles a new record **New Address** or **New Contact**.
- `close` clears the `editors` map.

The editor is a `frappe.ui.FieldGroup` built from the doctype's meta. It skips layout-only and display-only fieldtypes, the Geolocation map and the `links` table; it leaves out fields whose permission level the user cannot read and makes read-only those they cannot write. Table fields get their child doctype's fields and the record's rows. On a new Address, `country` is made optional.

`bind_cards` runs after ERPNext's `refresh` has drawn the cards. It does nothing on a new party or when `frappe.ui.split_view_enabled()` is false (the same rule as Frappe's: on unless the user's `report_split_view` is off, never on mobile). For each of Address and Contact that the user can write, it binds delegated click and Enter handlers on the cards (ignoring clicks on links, buttons and the card menu), and, when the user can create the doctype, replaces the add buttons' handler with `open_new_record`.

`open_new_record` builds a new document with `frappe.model.get_new_doc` and puts it straight into the panel's `previews`, so the panel shows it without fetching it.

## Saving a record

**Save** (or Ctrl+S in the panel) sends the whole edited record to `party_utils.save_party_record` (POST only), with the party's doctype and name. The method:

1. Accepts only an Address or Contact, of a Customer or Supplier, and checks that the user can read the party.
2. Drops the desk's bookkeeping keys (`__islocal`, `__unsaved` and the like) and the placeholder names of new child rows.
3. For a new record (no name, or `__islocal`), links it to the party, marks it primary when the party has no primary record of its kind, and for an Address sets `flags.default_country` to the party's `country` (Suppliers have one) or the System Settings country. For an existing record, refuses it unless a Dynamic Link already ties it to the party, and remembers the Contact's current phone numbers.
4. Turns every Check value into 0 or 1, because a table outside a form sends an unticked default as `"0"`.
5. On a Contact, writes each new number of `phone_nos` in E.164 with `phonenumbers`, read in the country of the party's primary address or of System Settings.
6. Inserts or saves the record with the user's own permissions. An existing record carries the `modified` it was opened with, so Frappe refuses to overwrite a newer version, as `frappe.client.save` does.
7. Returns the saved record (with field-level read permissions applied), its readable permission levels, the party's address and contact cards (`get_address_display_list`, `get_contact_display_list`) and the party's map point.

Back in the browser, `save_record` puts the saved record into the panel under its real name and redraws it, then `after_save` replaces the party's `__onload` card lists and map point in place, without marking the form changed. When a new record is the party's first of its kind, it sets the party's primary field and saves the party if it had no other unsaved changes; otherwise it redraws the cards with `frappe.contacts.render_address_and_contact`.

## The default primary record

On `onload`, `select_default_primary` checks each of the party's primary address and contact fields. When one is empty it calls `get_customer_records` or `get_supplier_records`, which return the Addresses or Contacts linked to the party (oldest first) through `frappe.get_list`, after checking that the user can read the party, and sets the first one. The form is left changed.

## The Customer map method

`customer.get_coords` returns a GeoJSON `FeatureCollection` of the customers the user may read that have coordinates, with a popup linking the Customer and its primary contact. `customer_list.js` names it as the list's `get_coords_method`, which on Frappe v16 is one of the conditions that make the Map view available (`list_view_select.js`); the `latitude`, `longitude` and Geolocation `location` custom fields meet the others, so the Address and Supplier lists offer it too. The view plots the list's own `location` values and does not call the method. The view itself does not open on v16; see [Limitations](../troubleshooting.md#limitations).

## The patch

`patches/remove_inline_party_fields.py`, in the `post_model_sync` section of `patches.txt`, deletes the custom fields earlier versions added to Customer and Supplier (copies of the primary address's and contact's fields, named `customer_primary_address_*`, `customer_primary_contact_*` and the Supplier equivalents) and the property setters that showed ERPNext's hidden **Primary Address and Contact** section. Customization sync only adds and updates, so the records are deleted by this patch. The columns stay in the tables.
