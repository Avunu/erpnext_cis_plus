---
title: CIS Plus for ERPNext
description: Address geocoding and location maps for customers and suppliers, and their addresses and contacts edited in the side panel.
nav_title: Overview
order: 0
updated: 2026-10-26
---

ERPNext keeps customers, contacts and addresses as separate records linked together. That is flexible, but for a small business, where most customers have one contact and one address, it means a lot of moving between forms, and none of those forms shows where the customer is. CIS Plus for ERPNext looks up every Address on the free OpenStreetMap Nominatim service, shows its location on a map on the Address, Customer and Supplier forms, and lets you edit a Customer's or Supplier's addresses and contacts in the side panel next to the party's form.

It is for sales, purchasing and office staff who keep customer and supplier records in ERPNext, and for the administrators who run the site. It runs on Frappe v16 with ERPNext and is free software under the [MIT licence](../license.txt).

## What you get

### Address geocoding and maps

When an Address is saved with a new or changed address, the app looks it up on Nominatim, stores its latitude and longitude, draws its point on a **Map** in a new **Location** section, and fills in a blank country, postal code, state, county or city. The Customer and Supplier forms get a **Location** section that shows the point of their primary address and follows it when it moves. See [Address geocoding and maps](geocoding.md).

![A Customer's Address & Contact tab: its address and contact cards, and the address's geocoded point on the Customer's map](screenshots/customer-form-light.webp)

### Addresses and contacts edited in the side panel

On the **Address & Contact** tab of a Customer or Supplier, clicking an address or contact card opens it as a form in Frappe's side panel, and the add buttons open a new one there. The party's form stays open underneath, and its cards and map follow each save. Phone numbers added there are stored in E.164, and a party's first address and contact become its primary ones. See [Edit addresses and contacts in the side panel](side-panel.md).

![A Customer's address open in the side panel, edited without leaving the Customer](screenshots/address-side-panel-light.webp)

## Where to start

| You are                                      | Read                                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Staff who keep customer and supplier records | [Edit addresses and contacts in the side panel](side-panel.md), then [Address geocoding and maps](geocoding.md)                |
| The administrator setting it up              | [Install and upgrade](install.md), [Configuration](configuration.md) and [Limitations and troubleshooting](troubleshooting.md) |
| A developer changing the app                 | [Development](development/README.md) and [How it works](development/architecture.md)                                           |

## Requirements

- A bench with Frappe v16. The app declares `frappe >=16.0.0,<17.0.0`.
- ERPNext v16 (`erpnext >=16.0.0,<17.0.0`) on the same site, installed before this app. The app adds fields to ERPNext's Customer and Supplier and reads their primary address and contact fields.
- The Python packages `phonenumbers`, `requests` and `us`. `bench get-app` installs them from the app's `pyproject.toml`.
- Outbound HTTPS from the bench to `nominatim.openstreetmap.org` for geocoding, and from users' browsers to OpenStreetMap's tile servers for the maps.

> [!NOTE]
> These pages describe the code on the `develop` branch. Where a statement depends on Frappe's or ERPNext's own behaviour, it was checked against Frappe 16.52.0 and ERPNext 16.51.1.

## Source and changes

The source is at [github.com/Avunu/erpnext_cis_plus](https://github.com/Avunu/erpnext_cis_plus). Releases and their notes are on the [GitHub releases page](https://github.com/Avunu/erpnext_cis_plus/releases); release-please writes them, and a `CHANGELOG.md`, from the commit history when a release is cut.
