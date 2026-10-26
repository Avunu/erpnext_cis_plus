---
title: Install and upgrade
description: Install CIS Plus for ERPNext on a Frappe v16 bench, see what the install adds to the site, and upgrade or remove it.
nav_title: Install
order: 1
updated: 2026-10-26
---

CIS Plus for ERPNext installs like any Frappe app. It has no build step of its own and no settings to fill in after installing.

## Before you start

- A bench with Frappe v16 and a site that already has ERPNext v16 installed. The app lists ERPNext in `required_apps`, so install ERPNext first.
- Outbound HTTPS from the bench to `nominatim.openstreetmap.org`. Without it the app still installs and every Address still saves, but none is geocoded: see [Troubleshooting](troubleshooting.md#troubleshooting).
- A System Manager login on the site.

## Install

Run these from the bench directory. `<SITE_NAME>` is your site, for example `site1.example.com`.

```bash
bench get-app https://github.com/Avunu/erpnext_cis_plus --branch version-16
bench --site <SITE_NAME> install-app erpnext_cis_plus
```

The `version-16` branch is created by the first release. Until it exists, install from `develop`:

```bash
bench get-app https://github.com/Avunu/erpnext_cis_plus --branch develop
bench --site <SITE_NAME> install-app erpnext_cis_plus
```

`bench get-app` also installs the app's Python packages (`phonenumbers`, `requests` and `us`) into the bench's environment.

## What installing sets up

Installing the app syncs its custom fields, listed in [Configuration](configuration.md#what-the-app-adds-to-your-site):

- A **Location** section on Address, after the **Links** table, with a **Map** and two hidden fields, **Latitude** and **Longitude**.
- A **Location** section on Customer and on Supplier, on the **Address & Contact** tab, with a read-only **Map** and hidden **Latitude** and **Longitude** that are fetched from the party's primary address.

The install creates no roles, no records and no settings, and it changes no existing data. Addresses saved before the install have no coordinates; each one is looked up the next time it is saved.

Frappe marks every patch of a newly installed app as done without running it, so the app's one patch (see [Upgrade](#upgrade)) does nothing on a new site.

## Upgrade

Update the app the way you update any Frappe app: `bench update`, or pull the new code in `apps/erpnext_cis_plus` and then run this from the bench directory.

```bash
bench --site <SITE_NAME> migrate
```

`bench migrate` syncs the custom fields again and runs any patch the site has not run yet.

### Removing the inline party fields

Earlier versions added copies of the primary address and contact fields to the Customer and Supplier forms, and property setters that showed ERPNext's hidden **Primary Address and Contact** section. The patch `erpnext_cis_plus.patches.remove_inline_party_fields` deletes those custom fields and property setters, so the forms are ERPNext's again and addresses and contacts are edited in the side panel.

No data is lost. The fields were copies of the primary Address and Contact, which keep their values, and deleting a custom field leaves its database column in place.

## Uninstall

```bash
bench --site <SITE_NAME> uninstall-app erpnext_cis_plus
```

Frappe backs up the site first (unless you pass `--no-backup`), then deletes the records that belong to the app's module, **ERPNext CIS Plus**: its twelve custom fields on Address, Customer and Supplier. The **Location** sections disappear from the forms.

What stays behind:

- The `latitude`, `longitude` and `location` columns of the Address, Customer and Supplier tables, with their values. Frappe does not drop the columns of a deleted custom field.
- E.164 phone numbers already written to Contacts, countries, states, counties and cities filled in by geocoding, and the primary addresses and contacts the app selected or set. They are ordinary data of those records.
- **Geolocation Error** entries in the Error Log.
- The app's code in `apps/erpnext_cis_plus` until you run `bench remove-app erpnext_cis_plus`.
