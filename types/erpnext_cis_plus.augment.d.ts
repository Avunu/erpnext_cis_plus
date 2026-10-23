// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// The names erpnext_cis_plus's desk scripts add (public/js/party_records.js), and the parts of
// frappe's side panel (frappe/public/js/frappe/ui/side_panel.js) they wrap, which frappe-types
// does not declare.

import type { DocField, FieldGroup, Form, SidePanel } from "frappe-types";

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
		/** What `frappe.desk.doc_preview.get_preview` returns, and the panel caches. */
		interface SidePanelPreview {
			doc: Record<string, unknown> & { doctype?: string; name?: string; __islocal?: 0 | 1 };
			permlevels?: number[];
		}
		/** The side panel with the members party_records.js reads and wraps. */
		interface SidePanelInternals extends SidePanel {
			previews: Record<string, SidePanelPreview>;
			render(): void;
			render_doc(doctype: string, preview: SidePanelPreview): void;
			set_header(doctype: string, docname: string, preview: SidePanelPreview | null): void;
			__cis_plus_party_records?: boolean;
			cis_plus_editors?: Record<string, JQuery<HTMLElement>>;
		}
		/** What `party_utils.save_party_record` returns. */
		interface SavePartyRecordResponse {
			doc: SidePanelPreview["doc"];
			permlevels: number[];
			addr_list: unknown[];
			contact_list: unknown[];
			location: { latitude: number; longitude: number; location: string | null } | null;
		}
		type FieldDefinition = DocField & { data?: Record<string, unknown>[]; fields?: DocField[] };
		type EditorGroup = FieldGroup;
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
	interface Frappe {
		/** frappe/public/js/frappe/model/perm.js:50-76. */
		perm: {
			get_perm(doctype: string): Array<Record<string, number | undefined> | undefined>;
			has_perm(doctype: string, permlevel?: number, ptype?: string): boolean;
		};
		/** frappe/public/js/frappe/utils/address_and_contact.js. */
		contacts: {
			render_address_and_contact(frm: Form): void;
		};
	}
}
