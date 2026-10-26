---
title: Configuration
description: The few settings that shape CIS Plus for ERPNext, the permissions it checks, and everything it adds to a site.
nav_title: Configuration
order: 2
updated: 2026-10-26
---

CIS Plus has no settings page of its own and reads no `site_config.json` key. Its behaviour follows a few standard Frappe settings and the permissions your users already have. This page lists them, then lists everything the app adds to your site.

## Settings it reads

| Setting                                                          | Where                                     | What it does                                                                                                                                                                                                                                                                              |
| ---------------------------------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Country**                                                      | System Settings                           | The country a phone number without a country code is read in when the party has no primary address, or its primary address has no country. Also the country a new Address saved from the side panel of a Customer takes when geocoding gives none. Set it to your own country.            |
| **Country**                                                      | Supplier form                             | The country a new Address saved from a Supplier's side panel takes when geocoding gives none, before the System Settings one.                                                                                                                                                             |
| **Customer Primary Address**, **Primary Address**                | Customer, Supplier                        | The party's primary address: its point is the one the **Location** map shows, and its country is the one the party's new phone numbers are read in. The field sits in ERPNext's hidden **Primary Address and Contact** section; set it with **Set as Primary** in an address card's menu. |
| **Split view** (stored on the User as **Split view in reports**) | Each user's **Settings**, **Reports** tab | On by default. While it is on, address and contact cards open in the side panel. When a user turns it off, and always on a phone, the cards and add buttons keep the standard behaviour.                                                                                                  |

Geocoding has no switch: every Address save that needs a lookup makes one. The limits it works within (one request per second for the whole bench, a five-second wait for that slot, a 10-second read timeout) are fixed in the code. See [Address geocoding and maps](geocoding.md#how-a-lookup-works).

## Permissions it checks

The app adds no roles. It uses the permissions your users already have on Customer, Supplier, Address and Contact:

- **Clicking a card opens the side panel** only for users who can write Addresses (for address cards) or Contacts (for contact cards). Others keep the standard card menu.
- **The add buttons open a new record in the side panel** only for users who can create that doctype.
- **Saving from the side panel** needs read access to the Customer or Supplier, and the usual write permission on the Address or Contact (or create permission for a new one). The record is saved with the user's own permissions. An existing record must already be linked to that party.
- **The side panel form** leaves out the fields the user may not read and makes the fields they may not write read-only, by permission level.
- **Listing a party's addresses and contacts**, which the form does to pick a default primary one, needs read access to the party.

## What the app adds to your site

This is the complete list, so you can see what installing or migrating changes.

### Custom fields

All of them belong to the module **ERPNext CIS Plus** and are synced on install and on every `bench migrate`.

| Doctype  | Field                        | Type          | Notes                                                                                                 |
| -------- | ---------------------------- | ------------- | ----------------------------------------------------------------------------------------------------- |
| Address  | **Location** (`geolocation`) | Section Break | After **Links**.                                                                                      |
| Address  | **Map** (`location`)         | Geolocation   | Set from the coordinates on save. A point drawn by hand is kept while the Address has no coordinates. |
| Address  | **Latitude**, **Longitude**  | Float         | Hidden. Set by geocoding.                                                                             |
| Customer | **Location** (`geolocation`) | Section Break | On the **Address & Contact** tab, after ERPNext's hidden **Primary Address and Contact** section.     |
| Customer | **Map** (`location`)         | Geolocation   | Read-only. Fetched from **Customer Primary Address**.                                                 |
| Customer | **Latitude**, **Longitude**  | Float         | Hidden and read-only. Fetched from **Customer Primary Address**.                                      |
| Supplier | **Location** (`geolocation`) | Section Break | On the **Address & Contact** tab, after ERPNext's hidden **Primary Address and Contact** section.     |
| Supplier | **Map** (`location`)         | Geolocation   | Read-only. Fetched from **Primary Address**.                                                          |
| Supplier | **Latitude**, **Longitude**  | Float         | Hidden and read-only. Fetched from **Primary Address**.                                               |

The app adds no doctypes, property setters, roles, workspaces or scheduled jobs.

### Document events and scripts

| Where                   | What                                                                                                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Address `validate`      | Looks the address up on Nominatim when it needs it, and fills in blank fields from the result.                                                                                  |
| Address `before_save`   | Gives a new Address from the side panel a default country when it still has none, and turns the coordinates into the point the **Map** shows.                                   |
| Address `on_update`     | Copies a changed point to every Customer and Supplier whose primary address it is.                                                                                              |
| Customer, Supplier form | A form script (`doctype_js`) that selects a default primary address and contact, and opens address and contact cards in the side panel.                                         |
| Customer list           | List settings (`doctype_list_js`) that add **Map** to the list's views. That view does not open on Frappe v16 at the moment: see [Limitations](troubleshooting.md#limitations). |

The app does not override or extend any doctype class.

### Whitelisted methods

| Method                                                                         | Used by                                                                                                                   |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils.save_party_record` (POST) | The side panel's **Save**: saves an Address or Contact of a Customer or Supplier                                          |
| `erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_customer_records`        | The Customer form: lists the Addresses or Contacts linked to a Customer                                                   |
| `erpnext_cis_plus.erpnext_cis_plus.hooks.supplier.get_supplier_records`        | The Supplier form: lists the Addresses or Contacts linked to a Supplier                                                   |
| `erpnext_cis_plus.erpnext_cis_plus.hooks.customer.get_coords`                  | Named as the Customer list's map method. Returns the customers' points as GeoJSON; Frappe v16's map view does not call it |

## Related

- [Install and upgrade](install.md)
- [How it works](development/architecture.md) for the code behind each row above
