---
title: Limitations and troubleshooting
description: What CIS Plus for ERPNext does not do, and the messages it shows, with their cause and fix.
nav_title: Troubleshooting
order: 8
updated: 2026-10-26
---

## Limitations

- **The list map views do not open on Frappe v16.** Frappe offers **Map** among the views of any list whose doctype has `latitude` and `longitude` fields or a Geolocation field named `location`, so the app's custom fields put it on the Address, Customer and Supplier lists (the Customer list also names a map method). Opening it fails in Frappe itself with `TypeError: this.load_lib is not a function`: Frappe's `MapView.setup_view` calls `this.load_lib()`, but `ListView`, which `MapView` extends, replaces `load_lib` with a promise when it is created (`patch_refresh_and_load_lib` in `frappe/public/js/frappe/list/list_view.js`). The view shows no map until Frappe fixes it. The **Location** maps on the Address, Customer and Supplier forms are not affected.
- **Geocoding is for modest volumes.** The whole bench sends at most one request per second to Nominatim, and a save that gets no slot within five seconds skips its lookup. An import of many addresses is slowed to that pace, and when several saves compete for the slot (parallel imports, or an import while people work), some of them skip their lookup; saving each of those Addresses again retries it.
- **Geocoding sends address text to a public service.** Street, city, state, postal code and country go to the OpenStreetMap Foundation's Nominatim service. There is no setting to use another geocoder or to turn geocoding off.
- **Filled-in names come as Nominatim writes them.** The app asks for no particular language, and fills a blank **Country**, **State/Province**, **County** or **City/Town** with the name Nominatim returns. Only a United States state is shortened, to its two-letter code.
- **Addresses and contacts are added in the side panel only once the party is saved.** The **Address & Contact** tab shows its cards only then. A new party's first address and contact can still come from ERPNext's quick entry.
- **The side panel form leaves out the map and the Links table.** Open the full form, with **Open in full page** in the panel's header, to see the map or change the links. See [Edit addresses and contacts in the side panel](side-panel.md#what-the-side-panel-form-leaves-out).
- **Unsaved edits in the side panel are dropped without asking** when you close the panel or move to another page.
- **Only numbers added in the side panel are converted to E.164.** Numbers entered on the full Contact form, imported or added through the API are stored as typed.

## Troubleshooting

### "Geolocation failed: ..."

An alert after saving an Address, followed by the error from the request, such as a connection error, a timeout or an HTTP status. The bench could not get an answer from Nominatim, so the Address was saved without coordinates. The error is also in the **Error Log**, titled **Geolocation Error**, with the address that was looked up.

Check that the bench can reach `https://nominatim.openstreetmap.org` over HTTPS (a firewall or proxy may block it), then save the Address again.

### "Geolocation skipped: the geocoding service is busy. Save again to retry."

Another lookup on the bench held the one-request-per-second slot for the whole five seconds this save waited. That happens when many Addresses are saved at once, for example during an import. Save the Address again.

### An Address saves without a point and no message

Nominatim found no match for the address. Check the spelling of **Address Line 1**, **City/Town** and **Postal Code**, or draw the point on the **Map** by hand. See [Draw a point by hand](geocoding.md#draw-a-point-by-hand).

An Address whose **Address Line 1**, **City/Town**, **State/Province**, **Postal Code** and **Country** are all blank is not looked up at all.

### A Customer's or Supplier's map is empty

The map shows the point of the party's primary address. Check that the party has a primary address (the card with the **Primary** badge on the **Address & Contact** tab) and that the Address has a point on its own **Map**. If the Address has none, save it again to retry the lookup.

### Clicking a card opens nothing in the side panel

The cards keep their standard behaviour when split view is off (the **Split view** switch on the **Reports** tab of your **Settings**), on a phone, on a party that is not saved yet, and when you have no write access to Addresses or Contacts. See [Before you start](side-panel.md#before-you-start).

### `<NUMBER> could not be read as a phone number and was kept as entered`

An alert when you save a Contact from the side panel. The number is not a valid phone number in the country it was read in (the country of the party's primary address, or of System Settings), so it was saved as typed. Add the country code, starting with `+`, and save again.

### `<DOCTYPE> <NAME> is not linked to <PARTY_TYPE> <PARTY_NAME>`

Shown when the side panel saves an existing Address or Contact that is no longer linked to the Customer or Supplier, for example because it was unlinked in another tab. Reload the party's form, then open the record from its current cards.

### `Error: <NAME> (<DOCTYPE>) has been modified after you have opened it`

Frappe's message when the record changed on the server after the side panel opened it. The side panel saves the way the full form does, so it never overwrites the newer version. Close the panel, reload the party's form, open the record again and redo your change.

### `Error: Value missing for Address: Country`

Frappe's message when a new Address saved from the side panel ends up with no **Country**: you left it empty, the address lookup found none (it failed, found no match or was skipped), the party is a Customer or a Supplier without a **Country**, and the **Country** in System Settings is empty. Fill in **Country** and save again, and set the System Settings **Country** so a new address always has a fallback.

### "Only Address and Contact records can be saved here" or "Only a Customer's or a Supplier's records can be saved here"

The save method behind the side panel was called with another doctype. The side panel never does that; the message comes from a script or integration calling `save_party_record` directly.

### "Only Address and Contact records can be listed"

The same for `get_customer_records` and `get_supplier_records`, which the Customer and Supplier forms call to choose a default primary address and contact.

### Insufficient Permission when saving from the side panel

The record is saved with your own permissions. You need read access to the Customer or Supplier, and write access to the Address or Contact (create access for a new one). Ask your administrator for a role that gives them.
