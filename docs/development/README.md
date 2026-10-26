---
title: Develop CIS Plus for ERPNext
description: Set up the dev shell, run the tests and checks, rebuild the demo and screenshots, and see what CI and the release flow do.
nav_title: Development
order: 9
updated: 2026-10-26
---

This page is for people changing the app. [How it works](architecture.md) explains how the code fits together. The managed files, shared checks and release flow are described once for every Avunu app in the [app standards documentation](https://docs.avunu.net/frappe-nix/docs/app-standards/); this page covers what is specific to this repository.

## Set up

The repository is a frappe-nix app. `nix develop --no-pure-eval` (or `direnv allow`, which uses the same flake) gives you Python, Node 24, yarn, the git hooks and a dev bench with Frappe and ERPNext v16 in `.frappe-nix/bench`:

```bash
nix develop --no-pure-eval
prek install
```

`prek install` installs the git hooks once per clone. The app has no front-end build: its desk scripts are plain JavaScript that Frappe serves as they are, with JSDoc types for the type checker.

## Commands

| Command                     | What it does                                                                                                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `frappe-test --reuse-site`  | Runs the Python tests on the dev site, with coverage. Nominatim is mocked, so the tests never reach it                              |
| `prek run --all-files`      | Runs every pre-commit hook the way CI's lint job does: ruff, ssort, oxfmt, oxlint, zizmor, actionlint and the Frappe project checks |
| `yarn typecheck`            | Type-checks the desk scripts (JavaScript with JSDoc types) and the screenshot spec                                                  |
| `yarn lint` / `yarn format` | Runs oxlint and oxfmt. oxfmt also formats the Markdown in `docs/`                                                                   |
| `frappe-demo`               | Sets up the demo Customers from `erpnext_cis_plus/demo.py` on the dev site                                                          |
| `frappe-shots`              | Rebuilds the demo site and retakes the screenshots in `docs/screenshots/`, as `marketplace/screenshots.ts` lists them               |
| `frappe-init --check`       | Checks that the files frappe-nix manages are unchanged; it prints `frappe-nix: clean`                                               |

Files whose header says they are managed by frappe-nix (`flake.nix`, `.envrc`, the workflows other than `docs.yml`, `.pre-commit-config.yaml` and others), and the regions between `frappe-nix:begin` and `frappe-nix:end` markers in `README.md`, are written by `frappe-init --sync`. Do not edit them by hand.

## Where things live

```text
erpnext_cis_plus/
  hooks.py                          form and list scripts, and the Address document events
  patches.txt                       one patch, after the model sync
  patches/remove_inline_party_fields.py   removes the inline party fields of earlier versions
  demo.py                           the demo Customers for frappe-demo and frappe-shots
  erpnext_cis_plus/                 the app's module, ERPNext CIS Plus
    custom/                         custom fields for Address, Customer and Supplier
    hooks/
      address.py                    the Nominatim lookup, the map point, the parties' points
      party_utils.py                save_party_record, phone numbers, listing a party's records
      customer.py                   get_customer_records and get_coords
      supplier.py                   get_supplier_records
  public/js/
    party_records.js                the side panel editor, shared by both form scripts
    customer.js, supplier.js        the Customer and Supplier form scripts
    customer_list.js                the Customer list settings
  tests/                            Python tests and their helpers
types/erpnext_cis_plus.augment.d.ts  types for the names the scripts add and the side panel internals they wrap
marketplace/                        the registry listing and the screenshot spec
```

## Tests

The Python tests are Frappe `IntegrationTestCase`s in `erpnext_cis_plus/tests/`. `utils.py` holds `GeocodingTestCase`, which mocks the Nominatim request and the rate limit slot so no test reaches the network.

| File                  | Covers                                                                                                                                                                                          |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_address.py`     | State abbreviations, the rate limit, the lookup and what it fills in, failures and busy slots, the map point, the default country, and when an Address is looked up again                       |
| `test_party_hooks.py` | `save_party_record` for Customers and Suppliers (linking, primary records, countries, E.164, refusals, stale records, user permissions), listing a party's records, `get_coords`, and the patch |
| `test_party_utils.py` | Phone number parsing and the country a number is read in                                                                                                                                        |
| `test_demo.py`        | That the demo set-up creates its Customers with an address, a contact and a map point, and can run twice                                                                                        |

Frappe only runs tests on a site that allows them. On a bench of your own, use a development or test site, never production:

```bash
bench --site <TEST_SITE> set-config allow_tests true
bench --site <TEST_SITE> run-tests --app erpnext_cis_plus
```

In the dev shell, `frappe-test --reuse-site` runs the same tests with coverage of the app alone; the floor is `fail_under` in `pyproject.toml` (80%). There are no JavaScript unit tests: `yarn typecheck`, `yarn lint` and `oxfmt --check` are the front-end gates.

## Continuous integration

`.github/workflows/ci.yml` is managed by frappe-nix and runs on every pull request, every push to `develop` and once a day. Each gate is a check named `ci / <gate>`:

- `ci / lint`: the pre-commit hooks, run with prek.
- `ci / typecheck`: the type checks, `yarn typecheck` among them.
- `ci / test`: the Python tests with coverage.
- `ci / marketplace`: the registry checks on `marketplace/listing.toml`, `hooks.py` and the logo.

`pr-policy.yml` adds `ci / pr-policy`, which checks a pull request's base, title and commits: conventional commit subjects, against `develop`. `nightly.yml` runs the integration suites, the screenshots and the link checks each night and is never a required check. `deps.yml` handles dependency pull requests (relocking them and merging them once green), with a daily sweep and a weekly relock.

## Docs

The `Docs` workflow (`.github/workflows/docs.yml`) runs on a pull request that changes `docs/` or the workflow itself. It calls the shared check of [Avunu/site-docs](https://github.com/Avunu/site-docs), pinned to a commit, which builds this documentation exactly as [docs.avunu.net](https://docs.avunu.net/erpnext-cis-plus/docs/) will. The workflow has a read-only token and cannot publish. The site picks up the documentation after a release.

The writing rules are in [Writing documentation](https://github.com/Avunu/site-docs/blob/main/docs/guide/writing-docs.md) in Avunu/site-docs. The screenshots in `docs/screenshots/` are generated by `frappe-shots`; do not edit them or their `manifest.json` by hand.

## Releases

`release.yml` runs release-please on every push to `develop`. Conventional commit subjects decide the next version and the release notes. release-please opens a release pull request that bumps `package.json` and `erpnext_cis_plus/__init__.py` and writes `CHANGELOG.md`. Merging it tags the release, publishes the notes on the [releases page](https://github.com/Avunu/erpnext_cis_plus/releases) and moves the `version-16` branch forward, which is the branch the install instructions use.
