// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// The names erpnext_cis_plus's desk scripts add (public/js/party_records.js). frappe's own,
// the side panel's included, come from frappe-types.

import type { DocPreview, Form } from "frappe-types";

declare global {
	namespace erpnext_cis_plus {
		/** A party's form: the Customer's or the Supplier's. */
		type PartyForm = Form;
		/** The party fields naming its primary Address and Contact. */
		type PrimaryFields = {
			readonly Address: "customer_primary_address" | "supplier_primary_address";
			readonly Contact: "customer_primary_contact" | "supplier_primary_contact";
		};
		/** Who a record shown as an editor in the side panel belongs to. */
		interface PartyRecordEditor {
			frm: PartyForm;
			primary_fields: PrimaryFields;
		}
		/** What `party_utils.save_party_record` returns: the saved record's preview, and more. */
		interface SavePartyRecordResponse extends DocPreview {
			addr_list: unknown[];
			contact_list: unknown[];
			location: { latitude: number; longitude: number; location: string | null } | null;
		}
		interface PartyRecords {
			bind_cards(frm: PartyForm, primary_fields: PrimaryFields): void;
			select_default_primary(
				frm: PartyForm,
				primary_fields: PrimaryFields,
				records_method: string,
				party_arg: string,
			): Promise<void>;
			open_record(
				frm: PartyForm,
				primary_fields: PrimaryFields,
				doctype: "Address" | "Contact",
				name: string,
			): Promise<void>;
			open_new_record(
				frm: PartyForm,
				primary_fields: PrimaryFields,
				doctype: "Address" | "Contact",
			): Promise<void>;
		}
	}

	// frappe.provide("erpnext_cis_plus") makes it; party_records.js fills it in before the
	// Customer and Supplier scripts, which are concatenated after it, run.
	var erpnext_cis_plus: { party_records: erpnext_cis_plus.PartyRecords };
}

declare module "frappe-types" {
	/** The members party_records.js adds to the side panel. */
	interface SidePanel {
		/** Set on the prototype once party_records.js has wrapped it. */
		__cis_plus_party_records?: boolean;
		/** The editor's wrapper, one per doctype, like the panel's own layouts. */
		cis_plus_editors?: Record<string, JQuery<HTMLElement>>;
	}
}
