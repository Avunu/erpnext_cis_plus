# Development

`nix develop` (or direnv) gives you Python, Node 24, yarn, the git hooks and a dev bench with ERPNext.

| Command                     | What it does                                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------------ |
| `frappe-test --reuse-site`  | Runs the Python tests on the dev site, with coverage. Nominatim is mocked, so the tests never reach it |
| `yarn typecheck`            | Type-checks the desk scripts (JavaScript with JSDoc types) and the screenshot spec                     |
| `yarn lint` / `yarn format` | Runs oxlint and oxfmt                                                                                  |
| `frappe-shots`              | Rebuilds the demo site (`erpnext_cis_plus/demo.py`) and retakes the screenshots in `docs/screenshots/` |

## Where things live

- `erpnext_cis_plus/hooks.py`: wires everything below into ERPNext: the form and list scripts, and the `doc_events` of Address.
- `erpnext_cis_plus/erpnext_cis_plus/custom/`: the custom fields for Address, Customer and Supplier (the map and its coordinates), synced on `bench migrate`.
- `erpnext_cis_plus/erpnext_cis_plus/hooks/address.py`: the Nominatim lookup (`geolocate_address`) and the map point (`generate_point`).
- `erpnext_cis_plus/erpnext_cis_plus/hooks/party_utils.py`: `save_party_record`, which the side panel's Save calls to insert or update a party's Address or Contact, and the phone number normalisation. `customer.py` and `supplier.py` list a party's records with it.
- `erpnext_cis_plus/erpnext_cis_plus/hooks/customer.py`: also `get_coords`, the Customer list's map method.
- `erpnext_cis_plus/public/js/`: `party_records.js` (the side panel editor, shared by the Customer and Supplier form scripts, which `hooks.py` loads after it), the form scripts and the Customer list settings. `types/erpnext_cis_plus.augment.d.ts` types the names it adds and the side panel internals it wraps.
- `erpnext_cis_plus/patches/remove_inline_party_fields.py`: removes the primary address and contact fields earlier versions added to Customer and Supplier.
- `erpnext_cis_plus/demo.py`: the demo Customers that `frappe-demo` and `frappe-shots` use.
