// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

import type { ShotSpec } from "./shots.d.ts";

// The demo Customers from erpnext_cis_plus/demo.py.
const CUSTOMER = "/app/customer/Codorus%20Timber%20Works";
const ADDRESS = "/app/address/Codorus%20Timber%20Works-Billing";
const READY = 'window.cur_frm && cur_frm.doc && cur_frm.doc.name === "Codorus Timber Works"';

export default {
	demo: { date: "2026-01-15", seed: 1 },
	shots: [
		{
			name: "customer-form",
			route: CUSTOMER,
			alt: "A Customer's Address & Contact tab: its primary address and contact, and the address's geocoded point on the Customer's map",
			waitForFn: READY,
			actions: [
				{
					eval: 'cur_frm.layout.tabs.find((tab) => tab.df.fieldname === "contact_and_address_tab").set_active();',
				},
				{ waitFor: '[data-fieldname="location"] .leaflet-marker-icon' },
				{ wait: 2000 },
			],
			mask: [".frappe-timestamp"],
			readme: "hero",
			featured: true,
		},
		{
			name: "address-form",
			route: ADDRESS,
			// Tall enough for the geocoded fields and the whole map.
			viewport: { width: 1440, height: 1120, deviceScaleFactor: 2 },
			alt: "An Address after it was geocoded: county and country filled in, and its point on the Location map",
			waitForFn: 'window.cur_frm && cur_frm.doc && cur_frm.doc.name === "Codorus Timber Works-Billing"',
			actions: [
				{ waitFor: '[data-fieldname="location"] .leaflet-marker-icon' },
				// The County field just under the sticky page head, the whole map below it.
				{
					eval: 'const county = document.querySelector(\'[data-fieldname="county"]\'); county.style.scrollMarginTop = "80px"; county.scrollIntoView({ block: "start" });',
				},
				{ wait: 2000 },
			],
			mask: [".frappe-timestamp"],
			readme: "feature",
			featured: true,
		},
	],
} satisfies ShotSpec;
