<!-- Copyright (c) 2026, Avunu LLC and contributors
For license information, please see license.txt-->

<!-- frappe-nix:begin header -->

<div align="center">

<img src="erpnext_cis_plus/public/images/erpnext_cis_plus-logo.svg" width="80" alt="">

# CIS Plus for ERPNext

Address geocoding and location maps for customers and suppliers

[![CI](https://github.com/Avunu/erpnext_cis_plus/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Avunu/erpnext_cis_plus/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/Avunu/erpnext_cis_plus)](https://github.com/Avunu/erpnext_cis_plus/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](license.txt)
[![Frappe v16](https://img.shields.io/badge/Frappe-v16-blue)](https://github.com/frappe/frappe/tree/version-16)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/customer-form-dark.webp">
  <img src="docs/screenshots/customer-form-light.webp" alt="A Customer's Address & Contact tab: its address and contact cards, and the address's geocoded point on the Customer's map">
</picture>

</div>

<!-- frappe-nix:end header -->

## Overview

ERPNext keeps customers, contacts and addresses as separate records linked together. That is flexible, but for a small business, where most customers have one contact and one address, it means a lot of moving between forms. CIS Plus (originally "Customer Information System Enhancements for ERPNext") geocodes addresses through the free OpenStreetMap Nominatim service and shows each Address's, Customer's and Supplier's location on a map on its form.

It also lets you edit a Customer's or Supplier's addresses and contacts in Frappe's side panel, next to the party's form, so the common case is handled without moving between forms.

## Features

- **Address geocoding.** When an Address is saved with a new or changed address, or still has no coordinates, it is looked up on Nominatim. Its latitude and longitude are stored, a point is drawn on a new **Location** map on the Address, and its country, postal code, state, county and city are filled in where they are blank (a United States state name becomes its two-letter code).
- **Location on the Customer and Supplier.** A **Location** section on both forms shows the primary address's point on a map. It follows the address: a new primary address, another one chosen on the party, or a geocoded change to the Address itself moves the point.
- **Addresses and contacts edited in the side panel.** On the **Address & Contact** tab of a Customer or Supplier, clicking an address or contact card opens it in the side panel (Frappe v16's right-hand drawer) as a form, with a **Save** button (or Ctrl+S); the **+ Address** and **+ Contact** buttons open a new one there. The party's form stays open underneath, unsaved changes included, and its cards and map are brought up to date after each save. A new record is linked to the party, and a party's first address or contact becomes its primary one. The card menu keeps ERPNext's **Edit** (the full form), **Set as Primary** and **Unlink**.

  ![A Customer's address open in the side panel](docs/screenshots/address-side-panel-light.webp)

- **A new address's country.** A new Address saved from the side panel with no country takes the one the geocoding result gives; when the lookup fails or finds nothing, it takes the Supplier's own country, or the System Settings country.
- **Phone numbers in E.164.** Phone and mobile numbers added to a Contact in the side panel are converted to E.164 (`+17175550142`) with the [`phonenumbers`](https://pypi.org/project/phonenumbers/) package, using the country of the party's primary address, or the System Settings country. Numbers the Contact already had are left as they are. A number that cannot be parsed is kept as typed and an alert says so.
- **Primary address and contact by default.** When a Customer or Supplier is opened and has no primary address or contact, the first linked one is selected; saving the party keeps it.

<!-- frappe-nix:begin compatibility -->

## Compatibility

| Frappe | Branch       |
| ------ | ------------ |
| v16    | `version-16` |

| Requires                                     | Version            |
| -------------------------------------------- | ------------------ |
| [erpnext](https://github.com/frappe/erpnext) | `>=16.0.0,<17.0.0` |

<!-- frappe-nix:end compatibility -->

<!-- frappe-nix:begin installation -->

## Installation

```bash
bench get-app https://github.com/Avunu/erpnext_cis_plus --branch version-16
bench --site <site> install-app erpnext_cis_plus
```

<!-- frappe-nix:end installation -->

Until the first release creates the `version-16` branch, install from `develop` instead: `bench get-app https://github.com/Avunu/erpnext_cis_plus --branch develop`. The app needs ERPNext, and `bench --site <site> migrate` adds its custom fields if you update it later.

Updating from a version with primary address and contact fields on the Customer and Supplier form: `bench --site <site> migrate` runs a patch that removes those custom fields and the property setters that showed ERPNext's hidden **Primary Address and Contact** section. Nothing is lost: the fields were copies of the primary Address and Contact, which keep their values, and the database columns are left in place.

## Configuration

There is nothing to configure. Three things are worth knowing:

- Geocoding needs outbound HTTPS from the bench to `nominatim.openstreetmap.org`. The maps load their tiles from OpenStreetMap in the browser, as Frappe's maps always do.
- Phone numbers without a country code are read in the country of the party's primary address, or of **System Settings > Country** when there is none, so set that country.
- Editing in the side panel follows Frappe's split view setting: it is on unless a user turns off **Split View** in their desk settings (`report_split_view`), and never on a phone. When it is off, the cards and the **+ Address** and **+ Contact** buttons keep ERPNext's behaviour (the card menu's **Edit** opens the full form, and the buttons open the quick entry).

## How It Works

- `hooks.py` adds form scripts for Customer and Supplier, list settings for Customer, and `doc_events` for Address. The custom fields live in `erpnext_cis_plus/erpnext_cis_plus/custom/` and are synced on install and migrate.
- **Address `validate`** runs the Nominatim lookup. It follows [Nominatim's usage policy](https://operations.osmfoundation.org/policies/nominatim/): it identifies itself in its User-Agent, sends at most one request per second from the bench (shared through Redis; a lookup that gets no slot within five seconds is skipped), and gives up on a request after 10 seconds. The stored coordinates are the cache: an address that has coordinates is looked up again only when its address fields change. If the service cannot be reached, times out, errors or is busy, the Address is saved without coordinates and an alert says so; if it finds no match, the Address is saved without coordinates. Coordinates from before a change are cleared in both cases, and the next save tries again. **Address `before_save`** turns the coordinates into the GeoJSON point the map field shows.
- The Customer and Supplier **Location** map, latitude and longitude are fetched from the primary Address (`fetch_from`) when the party is saved, and **Address `on_update`** copies a changed point to the parties whose primary address it is.
- **The side panel** (`public/js/party_records.js`, which the Customer and Supplier form scripts share) wraps the prototype of Frappe's `SidePanel` once `side_panel.bundle.js` has loaded, the way [avunu_erp](https://github.com/Avunu/avunu_erp/pull/11) gives the Email Queue a view of its own there. Only the records it opened from a party's cards are drawn as an editor (a `frappe.ui.FieldGroup` of the doctype's fields, with fields the user may not write read-only and those they may not read left out); every other preview in the panel is Frappe's own. A new record is shown from a document made in the browser and is not fetched.
- **Save** calls `party_utils.save_party_record`, which checks that the user can read the party, saves an existing record the way `frappe.client.save` does (a newer version on the server is not overwritten) only if it is linked to that party, and inserts a new one linked to it, all with the user's own permissions. It writes new Contact phone numbers in E.164, sets the default country flag that **Address `before_save`** reads, and returns the saved record, the party's address and contact cards, and its map point. The form redraws its cards from those; when a new record is the party's first of its kind, the form sets it as the primary one and, if it had no other unsaved changes, saves.
- The form scripts call `get_customer_records` and `get_supplier_records`, which list the Addresses or Contacts linked to a party the user can read, to pick a default primary one. The Customer list names `get_coords` as its map method, which makes Frappe offer the **Map** view; Frappe's map view then plots the list's own `location` values.

## Limitations

- Addresses and contacts are added once the Customer or Supplier is saved: the **Address & Contact** tab shows its cards only then. A new party's first address and contact can still come from ERPNext's own quick entry.
- The side panel editor leaves out the map (the address lookup draws it when the Address is saved) and the **Links** table (the record stays linked to its parties; the full form, through **Open in full page** in the panel's header, edits both). A child-table row is edited in its grid, as in a dialog.
- Closing the panel, or moving to another page, drops unsaved edits in it without asking.
- Geocoding sends the address text (street, city, state, postal code, country) to the public Nominatim service, and is meant for modest volumes: one lookup per second for the whole bench. A bulk import of addresses will skip most lookups; saving each Address again retries it.
- **The Customer map view does not work on Frappe v16 at the moment.** The app sets the Customer list up for Frappe's **Map** view, which would put a pin on every customer whose location is set, but opening it fails in Frappe itself with `TypeError: this.load_lib is not a function` (`MapView.setup_view` calls `this.load_lib()`, which the base list view has replaced with a promise), so it shows no map until Frappe fixes it. The **Location** maps on the Address, Customer and Supplier forms are not affected.
- Only the Customer list has the map view settings; the Supplier list does not.

<!-- frappe-nix:begin support -->

## Support

- Bug reports and questions: [GitHub issues](https://github.com/Avunu/erpnext_cis_plus/issues)
- E-mail: <mail@avu.nu>

<!-- frappe-nix:end support -->

<!-- frappe-nix:begin development -->

## Development

```bash
nix develop        # or: direnv allow
prek install       # the git hooks CI runs
frappe-test        # the tests, the way CI runs them
```

The managed files, checks and release flow are described in the [app standards documentation](https://docs.avunu.net/frappe-nix/docs/app-standards/).

<!-- frappe-nix:end development -->

The source layout and the commands for tests and screenshots are described in [docs/development.md](docs/development.md).

<!-- frappe-nix:begin license -->

## License

MIT, Copyright (c) 2024–present Avunu LLC → [license.txt](license.txt)

<!-- frappe-nix:end license -->
