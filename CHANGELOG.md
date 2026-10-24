# Changelog

## [16.0.0](https://github.com/Avunu/erpnext_cis_plus/compare/v0.0.1...v16.0.0) (2026-10-24)


### Features

* add phone number validation and conversion to E.164 format ([0f86016](https://github.com/Avunu/erpnext_cis_plus/commit/0f860163c2dfe5adf12e31be713cde9c2d6a8489))
* add pincode to geocoding, lower logging ([58b9f01](https://github.com/Avunu/erpnext_cis_plus/commit/58b9f0115ee9f3eef563fe9fb7c9e0017b65bd32))
* enable address/contact creation from customer and supplier forms ([dd4cf6e](https://github.com/Avunu/erpnext_cis_plus/commit/dd4cf6e3273fc4806a5f208ec129914d32806152))
* enable address/contact creation from customer/supplier forms on any update ([958f9de](https://github.com/Avunu/erpnext_cis_plus/commit/958f9debbc5923289045302b4620d9920843c0af))
* extend address/contact integration to Supplier with shared utilities ([fd2bcc9](https://github.com/Avunu/erpnext_cis_plus/commit/fd2bcc94ae1ae8285d94765cc1c123ae5a14525d))
* fetch default address & contact ([74b4aa1](https://github.com/Avunu/erpnext_cis_plus/commit/74b4aa1301ccc468e88c9d483b4634935453d21c))
* implement supplier address and contact field integration with DRY shared utilities ([0464112](https://github.com/Avunu/erpnext_cis_plus/commit/04641125a6072f02f06f79399a6703a15d98e778))
* Initialize App ([e67513c](https://github.com/Avunu/erpnext_cis_plus/commit/e67513c8462b318a929120f56900e306f98dd6cd))
* new editable linked fields between customer, address, and contact ([8ccaf46](https://github.com/Avunu/erpnext_cis_plus/commit/8ccaf468a77ac184c8ffbb90f64ffe92b262ae99))
* **party:** edit a party's addresses and contacts in the side panel ([#35](https://github.com/Avunu/erpnext_cis_plus/issues/35)) ([52d001b](https://github.com/Avunu/erpnext_cis_plus/commit/52d001ba53fee3e0fe7c169debc73509160cb8ac))
* revert Nominatim library, call api directly ([4d07c86](https://github.com/Avunu/erpnext_cis_plus/commit/4d07c8616fc85510f0552a6589212673f06ef7fe))


### Bug Fixes

* add class to fix field layout in Frappe 16+ ([1599a66](https://github.com/Avunu/erpnext_cis_plus/commit/1599a66f40bcb57f842cd498d0341532aae88e6d))
* address code review feedback - remove console.log and use specific exception handling ([0b07132](https://github.com/Avunu/erpnext_cis_plus/commit/0b0713255359355c941ee4279a4eeaa537eed66b))
* **address:** give a party's new address a country when geocoding fails ([#31](https://github.com/Avunu/erpnext_cis_plus/issues/31)) ([7da3186](https://github.com/Avunu/erpnext_cis_plus/commit/7da3186097e058b09758f144bd2a89dc732dc12d))
* customer form layout ([679e535](https://github.com/Avunu/erpnext_cis_plus/commit/679e53538e4174368b849a7fdc892a2a7fe0aadf))
* enhance child field updates for email and phone in contact ([064f4ea](https://github.com/Avunu/erpnext_cis_plus/commit/064f4eaafae35f4b20c42393006856c796a8cb9c))
* force extra contact / address fields to display even if they ([9d567e4](https://github.com/Avunu/erpnext_cis_plus/commit/9d567e4157595a00e5fa1776b063b5f870dedc9b))
* **geolocation:** keep a party's map point in step with its primary address ([#32](https://github.com/Avunu/erpnext_cis_plus/issues/32)) ([50caa19](https://github.com/Avunu/erpnext_cis_plus/commit/50caa197fd1be63bddcdd0159ef806f9bb4b06d1))
* handle new document creation with after_insert hook ([22eacb3](https://github.com/Avunu/erpnext_cis_plus/commit/22eacb349369566858dd866a6ed2d1c7e9c3f365))
* is_system_generated on ([4ab868e](https://github.com/Avunu/erpnext_cis_plus/commit/4ab868ed9032b1a60ff948e38683cefcc1bdf0d9))
* **party:** select the default primary address on every record opened ([#33](https://github.com/Avunu/erpnext_cis_plus/issues/33)) ([840d328](https://github.com/Avunu/erpnext_cis_plus/commit/840d32883be3bb6c234090aaea0b001e3da65261))
* **party:** show the primary address and contact section on v16 ([#30](https://github.com/Avunu/erpnext_cis_plus/issues/30)) ([887c6b0](https://github.com/Avunu/erpnext_cis_plus/commit/887c6b028347f12bdb6ff8bf5f31579eb1e47fc0))
* pyproject unclosed array ([bbdce3f](https://github.com/Avunu/erpnext_cis_plus/commit/bbdce3f233e971bd60302c768f67fa2f05911393))
* readme links ([0aa2522](https://github.com/Avunu/erpnext_cis_plus/commit/0aa25228f185323c7ee028e1ddeea99af52d480c))
* readme links ([1ff233d](https://github.com/Avunu/erpnext_cis_plus/commit/1ff233dd61f3d0ffd686c533986d6e82161303d7))
* reflect address/contact creation immediately ([72c02f9](https://github.com/Avunu/erpnext_cis_plus/commit/72c02f90c99035dbb78c4c5d4b11b6a28f36c285))
* remove debug console.log from customer.js for consistency ([3c82da9](https://github.com/Avunu/erpnext_cis_plus/commit/3c82da9b290988c23866de2cf876303f2cd660f3))
* require the us package ([f829d82](https://github.com/Avunu/erpnext_cis_plus/commit/f829d829564ecca6da390b6e568149522e999353))
* skip custom hooks if doc created via quickentry ([c0f306f](https://github.com/Avunu/erpnext_cis_plus/commit/c0f306f546cbd04f0dee915da523e9c5d8137fb9))
* use validate and on_update hooks to handle new documents correctly ([2cff52e](https://github.com/Avunu/erpnext_cis_plus/commit/2cff52eb232005c7e6259f22def3fcc5137e7cf5))


### Reverts

* only update address details if missing ([cbefb57](https://github.com/Avunu/erpnext_cis_plus/commit/cbefb57bf1eca6a0bdcfb0aa0d983f44f7c191e6))


### Continuous Integration

* adopt the shared CI gates ([05b3e59](https://github.com/Avunu/erpnext_cis_plus/commit/05b3e59f7223d8c0510045a9a721a770bf55198e))
