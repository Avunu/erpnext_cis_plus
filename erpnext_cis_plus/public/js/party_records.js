// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// The Addresses and Contacts of a Customer or a Supplier, edited in the side panel
// (frappe/public/js/frappe/ui/side_panel.js, Frappe 16.50+) without leaving the party's form.
//
// On the Address & Contact tab, a click on an address or contact card opens that record in the
// panel as a form to edit, and the + Address and + Contact buttons open a new one there. Saving
// goes through party_utils.save_party_record, which saves it with the user's own permissions,
// links a new record to the party and writes new phone numbers in E.164. The party's cards and
// map point are then refreshed in place. When split view is off (on mobile, or turned off in
// the desk settings) the cards and buttons keep ERPNext's own behaviour.
//
// The panel itself only previews a document read-only and has no hook for anything else, so
// its prototype is wrapped once it has loaded, as avunu_erp does for the Email Queue
// (https://github.com/Avunu/avunu_erp/pull/11). The wrap only takes over the documents this
// script opened; every other preview renders as Frappe draws it.
//
// customer.js and supplier.js call this, and are concatenated after it into one doctype script.

frappe.provide("erpnext_cis_plus");

if (!erpnext_cis_plus.party_records) {
	const SAVE_METHOD = "erpnext_cis_plus.erpnext_cis_plus.hooks.party_utils.save_party_record";
	const RECORD_DOCTYPES = /** @type {const} */ (["Address", "Contact"]);
	/** How each record doctype shows on the party's Address & Contact tab. */
	const CARDS = {
		Address: { wrapper_field: "address_html", card: ".address-box", button: ".btn-address" },
		Contact: { wrapper_field: "contact_html", card: ".contact-box", button: ".btn-contact" },
	};
	const TABLE_FIELDTYPES = new Set(["Table", "Table MultiSelect"]);
	// Not edited in the panel: layout-only and display-only fieldtypes, and the map, which the
	// address lookup draws when the Address is saved.
	const SKIPPED_FIELDTYPES = new Set(["Tab Break", "HTML", "Button", "Fold", "Heading", "Geolocation"]);
	const NO_VALUE_FIELDTYPES = new Set(["Section Break", "Column Break", ...SKIPPED_FIELDTYPES]);
	// The links table is what makes the record the party's; it is kept as it is.
	const KEPT_FIELDS = new Set(["links"]);

	/** The records the panel shows as an editor, by "doctype/name", and the form each belongs to. */
	/** @type {Map<string, erpnext_cis_plus.PartyRecordEditor>} */
	const editors = new Map();
	const key = (/** @type {string} */ doctype, /** @type {string} */ name) => `${doctype}/${name}`;

	frappe.dom.set_style(
		`.cis-plus-editable { cursor: pointer; }
		.cis-plus-editable:hover { background-color: var(--subtle-fg); }
		.cis-plus-editor-actions {
			display: flex; justify-content: flex-end; gap: var(--margin-sm);
			padding: var(--padding-sm) var(--padding-md) 0;
		}`,
		"cis-plus-party-records",
	);

	// Same rule as frappe.ui.split_view_enabled, which report.bundle.js defines on every desk
	// page: on unless the user turned it off, never on mobile.
	const split_view_enabled = () => {
		if (frappe.ui.split_view_enabled) return frappe.ui.split_view_enabled();
		if (frappe.is_mobile()) return false;
		const enabled = frappe.boot.desk_settings?.report_split_view;
		return enabled === undefined || cint(enabled) === 1;
	};

	/** The permlevels of `doctype` the user may read, as the panel's preview lists them. */
	const readable_permlevels = (/** @type {string} */ doctype) =>
		(frappe.perm.get_perm(doctype) || []).flatMap((perm, permlevel) => (perm?.read ? [permlevel] : []));

	/**
	 * The fields the editor shows: the doctype's own, with the ones the user may not write
	 * read-only and the ones they may not read left out.
	 *
	 * @param {string} doctype
	 * @param {Record<string, unknown>} doc
	 * @param {number[]} permlevels
	 * @returns {erpnext_cis_plus.FieldDefinition[]}
	 */
	function editor_fields(doctype, doc, permlevels) {
		const fields = [];
		for (const df of frappe.get_meta(doctype)?.fields || []) {
			if (SKIPPED_FIELDTYPES.has(df.fieldtype) || KEPT_FIELDS.has(df.fieldname)) continue;
			const permlevel = cint(df.permlevel);
			if (!permlevels.includes(permlevel)) continue;

			/** @type {erpnext_cis_plus.FieldDefinition} */
			const field = { ...df };
			if (!frappe.perm.has_perm(doctype, permlevel, "write")) field.read_only = 1;
			if (TABLE_FIELDTYPES.has(String(df.fieldtype)) && typeof df.options === "string") {
				// A table outside a form takes its columns and rows from the field itself.
				field.fields = (frappe.get_meta(df.options)?.fields || []).map((child) => ({
					...child,
				}));
				const rows = /** @type {Record<string, unknown>[] | undefined} */ (doc[df.fieldname]);
				field.data = (rows || []).map((row) => ({ ...row }));
			}
			if (doctype === "Address" && df.fieldname === "country" && doc.__islocal) {
				// The address lookup fills it in, else the party's or System Settings' country.
				field.reqd = 0;
				field.description = __("Leave empty to take the country the address lookup finds.");
			}
			fields.push(field);
		}
		return fields;
	}

	/**
	 * The record as the editor holds it: the shown document with the edited fields put back.
	 *
	 * @param {frappe.ui.FieldGroup} group
	 * @param {Record<string, unknown>} doc
	 */
	function edited_doc(group, doc) {
		/** @type {Record<string, unknown>} */
		const edited = { ...doc };
		for (const field of group.fields_list) {
			const df = field.df;
			if (!df.fieldname || NO_VALUE_FIELDTYPES.has(String(df.fieldtype)) || cint(df.read_only)) {
				continue;
			}
			const value = group.get_value(df.fieldname);
			edited[df.fieldname] = value === undefined || value === "" ? null : value;
		}
		return edited;
	}

	/**
	 * Fill the panel with a form for the record, and a Save button.
	 *
	 * @param {JQuery<HTMLElement>} $wrapper
	 * @param {erpnext_cis_plus.SidePanelInternals} panel
	 * @param {erpnext_cis_plus.SidePanelPreview} preview
	 * @param {erpnext_cis_plus.PartyRecordEditor} editor
	 */
	function render_editor($wrapper, panel, preview, editor) {
		const doc = preview.doc;
		const doctype = String(doc.doctype);
		$wrapper.empty();

		const $actions = $('<div class="cis-plus-editor-actions"></div>').appendTo($wrapper);
		const $form = $("<div></div>").appendTo($wrapper);
		const group = new frappe.ui.FieldGroup({
			fields: editor_fields(doctype, doc, (preview.permlevels || []).map(cint)),
			body: $form,
			card_layout: true,
		});
		group.make();
		/** @type {Record<string, unknown>} */
		const values = {};
		for (const field of group.fields_list) {
			const fieldname = field.df.fieldname;
			if (fieldname && !TABLE_FIELDTYPES.has(String(field.df.fieldtype)) && fieldname in doc) {
				values[fieldname] = doc[fieldname];
			}
		}
		group.set_values(values);
		$wrapper.data("field-group", group);

		/** @type {() => Promise<void>} */
		const save = () => save_record(panel, group, preview, editor, $save);
		/** @type {JQuery<HTMLElement>} */
		const $save = frappe.ui
			.button({
				label: __("Save"),
				variant: "solid",
				size: "sm",
				tooltip: __("Save this {0} (Ctrl+S)", [__(doctype)]),
				onclick: save,
			})
			.appendTo($actions);

		// Ctrl+S in the panel saves the record, not the party's form underneath it.
		$wrapper.off("keydown.cis-plus").on("keydown.cis-plus", (e) => {
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
				e.preventDefault();
				e.stopPropagation();
				save();
			}
		});
	}

	/**
	 * @param {erpnext_cis_plus.SidePanelInternals} panel
	 * @param {frappe.ui.FieldGroup} group
	 * @param {erpnext_cis_plus.SidePanelPreview} preview
	 * @param {erpnext_cis_plus.PartyRecordEditor} editor
	 * @param {JQuery<HTMLElement>} $save
	 */
	async function save_record(panel, group, preview, editor, $save) {
		if ($save.attr("aria-busy") || !group.get_values()) return; // get_values names what is missing
		const doc = edited_doc(group, preview.doc);
		const doctype = String(doc.doctype);
		const was_new = Boolean(doc.__islocal);
		const { frm } = editor;
		const party_name = frm.docname;

		$save.attr("aria-busy", "true").prop("disabled", true);
		/** @type {erpnext_cis_plus.SavePartyRecordResponse} */
		let saved;
		try {
			saved = await frappe.xcall(SAVE_METHOD, {
				doc,
				party_type: frm.doctype,
				party_name,
			});
		} catch {
			// frappe.call has already shown the error
			$save.removeAttr("aria-busy").prop("disabled", false);
			return;
		}
		frappe.show_alert({ message: __("{0} saved", [__(doctype)]), indicator: "green" });

		// Show the saved record: under its real name if it was new.
		const name = String(saved.doc.name);
		const previews = /** @type {erpnext_cis_plus.SidePanelInternals} */ (panel).previews;
		if (was_new) {
			editors.delete(key(doctype, String(preview.doc.name)));
			delete previews[key(doctype, String(preview.doc.name))];
		}
		editors.set(key(doctype, name), editor);
		previews[key(doctype, name)] = { doc: saved.doc, permlevels: saved.permlevels };
		if (panel.is_open() && panel.current?.doctype === doctype) {
			panel.current = { doctype, docname: name };
			/** @type {erpnext_cis_plus.SidePanelInternals} */ (panel).render();
		}

		// The form may have moved on to another party while the record was saved.
		if (frm.docname === party_name) {
			await after_save(frm, editor.primary_fields, doctype, name, was_new, saved);
		}
	}

	/**
	 * Bring the party's form up to date without reloading it, so unsaved edits on it survive.
	 *
	 * @param {erpnext_cis_plus.PartyForm} frm
	 * @param {erpnext_cis_plus.PrimaryFields} primary_fields
	 * @param {string} doctype
	 * @param {string} name
	 * @param {boolean} was_new
	 * @param {erpnext_cis_plus.SavePartyRecordResponse} saved
	 */
	async function after_save(frm, primary_fields, doctype, name, was_new, saved) {
		const onload = /** @type {Record<string, unknown>} */ (frm.doc.__onload || {});
		onload.addr_list = saved.addr_list;
		onload.contact_list = saved.contact_list;
		/** @type {Record<string, unknown>} */ (frm.doc).__onload = onload;

		// An Address save may have moved the map point, which the server already stored on the
		// party; show it without marking the form changed.
		if (saved.location) {
			Object.assign(frm.doc, saved.location);
			frm.refresh_field("location");
		}

		// A party's first Address or Contact becomes its primary one, as a record picked when
		// the form loads does (select_default_primary). Saving the party fetches the address's
		// map point onto it.
		const primary_field = primary_fields[/** @type {"Address" | "Contact"} */ (doctype)];
		if (was_new && !frm.doc[primary_field]) {
			const was_clean = !frm.is_dirty();
			await frm.set_value(primary_field, name);
			if (was_clean) {
				await frm.save();
				return; // the save refreshes the form, cards included
			}
		}

		frappe.contacts.render_address_and_contact(frm);
		bind_cards(frm, primary_fields);
	}

	// The panel has no hook for a view of its own, so its prototype is wrapped once it has
	// loaded. Only the documents in `editors` are taken over.
	/** @param {erpnext_cis_plus.SidePanelInternals} proto */
	function patch(proto) {
		if (proto.__cis_plus_party_records) return;
		proto.__cis_plus_party_records = true;

		const { render_doc, set_header, close } = proto;

		/** @param {erpnext_cis_plus.SidePanelInternals} panel */
		const editor_for = (panel) =>
			panel.current ? editors.get(key(panel.current.doctype, panel.current.docname)) : undefined;

		proto.render_doc = function (doctype, preview) {
			const editor = editor_for(this);
			if (!editor) return render_doc.call(this, doctype, preview);

			// One wrapper per doctype, like the panel's own layouts; .side-panel-doc gets the
			// same hide/show and ready-state handling.
			this.cis_plus_editors ||= {};
			const $wrapper = (this.cis_plus_editors[doctype] ||= $(
				'<div class="side-panel-doc cis-plus-party-editor"></div>',
			).appendTo(this.$body));

			this.$body.find(".side-panel-doc").addClass("hidden");
			$wrapper.removeClass("hidden");
			render_editor($wrapper, this, preview, editor);
		};

		proto.set_header = function (doctype, docname, preview) {
			set_header.call(this, doctype, docname, preview);
			if (preview?.doc.__islocal && editor_for(this)) {
				this.$panel.find(".side-panel-title").text(__("New {0}", [__(doctype)]));
			}
		};

		proto.close = function () {
			close.call(this);
			editors.clear();
		};
	}

	/** @returns {Promise<erpnext_cis_plus.SidePanelInternals>} */
	async function get_side_panel() {
		await frappe.require("side_panel.bundle.js");
		const { SidePanel, get_side_panel: panel } = frappe.ui;
		if (!SidePanel || !panel) throw new Error("side_panel.bundle.js did not load");
		patch(/** @type {erpnext_cis_plus.SidePanelInternals} */ (SidePanel.prototype));
		return /** @type {erpnext_cis_plus.SidePanelInternals} */ (panel());
	}

	/**
	 * Open one of the party's records in the panel, as a form to edit.
	 *
	 * @param {erpnext_cis_plus.PartyForm} frm
	 * @param {erpnext_cis_plus.PrimaryFields} primary_fields
	 * @param {"Address" | "Contact"} doctype
	 * @param {string} name
	 */
	async function open_record(frm, primary_fields, doctype, name) {
		const panel = await get_side_panel();
		editors.set(key(doctype, name), { frm, primary_fields });
		const current = panel.current;
		if (panel.is_open() && current?.doctype === doctype && current.docname === name) {
			// Already shown, perhaps as a read-only preview: draw it again as the editor.
			/** @type {erpnext_cis_plus.SidePanelInternals} */ (panel).render();
			return;
		}
		panel.open(doctype, name);
	}

	/**
	 * Open a new record for the party in the panel. It is linked to the party when it is saved.
	 *
	 * @param {erpnext_cis_plus.PartyForm} frm
	 * @param {erpnext_cis_plus.PrimaryFields} primary_fields
	 * @param {"Address" | "Contact"} doctype
	 */
	async function open_new_record(frm, primary_fields, doctype) {
		await frappe.model.with_doctype(doctype);
		const panel = await get_side_panel();
		// With the defaults a new form would have (an Address Type, a Contact's status). It
		// stays in locals, so the panel's "Open in full page" opens it as a new form.
		/** @type {Record<string, unknown>} */
		const doc = { ...frappe.model.get_new_doc(doctype), links: [] };
		const name = String(doc.name);
		if (doctype === "Address") {
			// Frappe would name the Address after its link anyway; show it in the form.
			doc.address_title = frm.doc.customer_name || frm.doc.supplier_name || frm.docname;
		}
		editors.set(key(doctype, name), { frm, primary_fields });
		// The panel shows a document it already has without fetching it.
		/** @type {erpnext_cis_plus.SidePanelInternals} */ (panel).previews[key(doctype, name)] = {
			doc,
			permlevels: readable_permlevels(doctype),
		};
		panel.open(doctype, name);
	}

	/**
	 * Make the party's address and contact cards, and its + Address and + Contact buttons,
	 * open the side panel. Runs after ERPNext has drawn them, on every refresh.
	 *
	 * @param {erpnext_cis_plus.PartyForm} frm
	 * @param {erpnext_cis_plus.PrimaryFields} primary_fields
	 */
	function bind_cards(frm, primary_fields) {
		if (frm.is_new() || !split_view_enabled()) return;
		for (const doctype of RECORD_DOCTYPES) {
			const { wrapper_field, card, button } = CARDS[doctype];
			const $wrapper = $(frm.fields_dict[wrapper_field]?.wrapper || []);
			// Without write access the cards keep ERPNext's behaviour (the menu opens the form).
			if (!$wrapper.length || !frappe.model.can_write(doctype)) continue;

			$wrapper
				.find(card)
				.addClass("cis-plus-editable")
				.attr({ tabindex: 0, role: "button", title: __("Edit in the side panel") });

			// Delegated, so cards drawn again by ERPNext are covered; set up once per wrapper.
			$wrapper
				.off(".cis-plus")
				.on("click.cis-plus", card, (e) => {
					// The card's menu, its phone and e-mail links and its buttons keep their meaning.
					if ($(e.target).closest("a, button, .btn, .card-menu-btn").length) return;
					const name = e.currentTarget.dataset.name;
					if (name) open_record(frm, primary_fields, doctype, name);
				})
				.on("keydown.cis-plus", card, (e) => {
					if (e.key !== "Enter" || e.target !== e.currentTarget) return;
					const name = e.currentTarget.dataset.name;
					if (name) open_record(frm, primary_fields, doctype, name);
				});

			if (frappe.model.can_create(doctype)) {
				$wrapper
					.find(button)
					.off("click")
					.on("click", (e) => {
						e.preventDefault();
						open_new_record(frm, primary_fields, doctype);
					});
			}
		}
	}

	/**
	 * When the party has no primary Address or Contact, select the first one linked to it.
	 * The form is left changed; saving it keeps the choice.
	 *
	 * @param {erpnext_cis_plus.PartyForm} frm
	 * @param {erpnext_cis_plus.PrimaryFields} primary_fields
	 * @param {string} records_method lists the Addresses or Contacts linked to the party
	 * @param {string} party_arg the method's argument naming the party
	 */
	async function select_default_primary(frm, primary_fields, records_method, party_arg) {
		if (frm.is_new()) return;
		for (const doctype of RECORD_DOCTYPES) {
			const fieldname = primary_fields[doctype];
			if (frm.doc[fieldname]) continue;
			try {
				/** @type {{ name: string }[]} */
				const records = await frappe.xcall(records_method, {
					dt: doctype,
					[party_arg]: frm.doc.name,
				});
				if (records?.[0]) await frm.set_value(fieldname, records[0].name);
			} catch (error) {
				// frappe.call has already shown the error
				console.error(error);
			}
		}
	}

	erpnext_cis_plus.party_records = { bind_cards, select_default_primary, open_record, open_new_record };
}
