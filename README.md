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
  <img src="docs/screenshots/customer-form-light.webp" alt="A Customer's Address & Contact tab: its primary address and contact, and the address's geocoded point on the Customer's map">
</picture>

</div>

<!-- frappe-nix:end header -->

## Overview

ERPNext keeps customers, contacts and addresses as separate records linked together. That is flexible, but for a small business, where most customers have one contact and one address, it means a lot of moving between forms. CIS Plus (originally "Customer Information System Enhancements for ERPNext") geocodes addresses through the free OpenStreetMap Nominatim service and shows each Address's, Customer's and Supplier's location on a map on its form.

It also adds primary address and contact fields to the Customer and the Supplier form, which create or update the linked Address and Contact when the party is saved, so the common case is edited on one form.

## Features

- **Address geocoding.** When an Address is saved with a new or changed address, or still has no coordinates, it is looked up on Nominatim. Its latitude and longitude are stored, a point is drawn on a new **Location** map on the Address, and its country, postal code, state, county and city are filled in where they are blank (a United States state name becomes its two-letter code).
- **Location on the Customer and Supplier.** A **Location** section on both forms shows the primary address's point on a map. It follows the address: a new primary address, another one chosen on the party, or a geocoded change to the Address itself moves the point.
- **Primary address and contact fields on the party.** Customer and Supplier carry fields for the primary address (address lines, city, state, postal code, e-mail, phone, fax) and the primary contact (first and last name, e-mail, phone, mobile, department). They are in the **Primary Address and Contact** section of the **Address & Contact** tab, which ERPNext v16 hides and the app shows again. Saving an existing Customer or Supplier with these set creates the Address and Contact, links them and marks them primary, or updates the ones already linked. A new Address takes its country from the geocoding result; when the lookup fails or finds nothing, it takes the Supplier's own country, or the System Settings country.
- **Phone numbers in E.164.** The primary contact's phone and mobile in those fields are converted to E.164 (`+17175550142`) with the [`phonenumbers`](https://pypi.org/project/phonenumbers/) package, using the country of the primary address, or the System Settings country. A number that cannot be parsed is kept as typed and an alert says so.
- **Primary address and contact by default.** When a Customer or Supplier is opened and has no primary address or contact, the first linked one is selected; saving the party keeps it.
- ERPNext's read-only **Primary Address**, **Mobile No** and **Email Id** fields on Customer and Supplier are hidden, since the fields above replace them.

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

On Frappe Cloud, install CIS Plus for ERPNext from the [Frappe marketplace](https://cloud.frappe.io/marketplace/apps/erpnext_cis_plus).

On a bench of your own:

```bash
bench get-app https://github.com/Avunu/erpnext_cis_plus --branch version-16
bench --site <site> install-app erpnext_cis_plus
```

<!-- frappe-nix:end installation -->

Until the first release creates the `version-16` branch, install from `develop` instead: `bench get-app https://github.com/Avunu/erpnext_cis_plus --branch develop`. The app needs ERPNext, and `bench --site <site> migrate` adds its custom fields if you update it later.

## Configuration

There is nothing to configure. Two things are worth knowing:

- Geocoding needs outbound HTTPS from the bench to `nominatim.openstreetmap.org`. The maps load their tiles from OpenStreetMap in the browser, as Frappe's maps always do.
- Phone numbers without a country code are read in the country of the party's primary address, or of **System Settings > Country** when there is none, so set that country.

## How It Works

- `hooks.py` adds form scripts for Customer and Supplier, list settings for Customer, and `doc_events` for Address, Customer and Supplier. The custom fields and property setters live in `erpnext_cis_plus/erpnext_cis_plus/custom/` and are synced on install and migrate.
- **Address `validate`** runs the Nominatim lookup. It follows [Nominatim's usage policy](https://operations.osmfoundation.org/policies/nominatim/): it identifies itself in its User-Agent, sends at most one request per second from the bench (shared through Redis; a lookup that gets no slot within five seconds is skipped), and gives up on a request after 10 seconds. The stored coordinates are the cache: an address that has coordinates is looked up again only when its address fields change. If the service cannot be reached, times out, errors or is busy, the Address is saved without coordinates and an alert says so; if it finds no match, the Address is saved without coordinates. Coordinates from before a change are cleared in both cases, and the next save tries again. **Address `before_save`** turns the coordinates into the GeoJSON point the map field shows.
- The Customer and Supplier **Location** map, latitude and longitude, and the primary address and contact fields, are fetched from the linked Address and Contact (`fetch_from`, only when the field is empty).
- **Customer and Supplier `validate`** normalises the phone numbers and checks that a new address has its first line and a new contact a first name. **`on_update`** then creates or updates the Address and Contact, and links new ones with `db_set`, so the party's hooks do not run twice. A party being inserted is left to ERPNext, which has its own quick-entry address and contact.
- The form scripts call `get_customer_records` and `get_supplier_records`, which list the Addresses or Contacts linked to a party the user can read. The Customer list names `get_coords` as its map method, which makes Frappe offer the **Map** view; Frappe's map view then plots the list's own `location` values.

## Limitations

- The fields only act on a party that already exists: filling them in on a new Customer or Supplier and saving creates nothing.
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
