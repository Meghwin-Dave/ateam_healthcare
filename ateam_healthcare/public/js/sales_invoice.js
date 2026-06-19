// Copyright (c) 2026, Meghwin Dave and contributors
// Sales Invoice — Ateam Healthcare Extension
// Adds "Create Insurance Claim" button when a policy is linked.

frappe.ui.form.on("Sales Invoice", {

	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		if (!frm.doc.custom_insurance_policy) return;

		// Check if a claim already exists for this invoice
		frappe.db.count("Insurance Claim", {
			sales_invoice: frm.doc.name,
			docstatus: ["!=", 2]   // not cancelled
		}).then(function (count) {
			if (count === 0) {
				frm.add_custom_button(__("Create Insurance Claim"), function () {
					frm.trigger("create_insurance_claim");
				}, __("Healthcare"));
			} else {
				// Show "View Insurance Claim" link instead
				frappe.db.get_value(
					"Insurance Claim",
					{ sales_invoice: frm.doc.name, docstatus: ["!=", 2] },
					"name"
				).then(function (r) {
					if (r && r.message && r.message.name) {
						frm.add_custom_button(__("View Insurance Claim"), function () {
							frappe.set_route("Form", "Insurance Claim", r.message.name);
						}, __("Healthcare"));
					}
				});
			}
		});

		// Show e-Claim status badge if set
		if (frm.doc.custom_eclaim_status) {
			const color = {
				"Submitted": "blue",
				"Settled": "green",
				"Rejected": "red",
				"Cancelled": "grey"
			}[frm.doc.custom_eclaim_status] || "orange";

			frm.page.set_indicator(
				__("e-Claim: {0}", [frm.doc.custom_eclaim_status]), color
			);
		}
	},

	create_insurance_claim(frm) {
		// Validate a patient (customer type) is linked
		if (!frm.doc.customer) {
			frappe.msgprint(__("No customer found on this invoice."));
			return;
		}

		// Open a quick dialog to confirm + pick claim number
		let d = new frappe.ui.Dialog({
			title: __("Create Insurance Claim"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "claim_number",
					label: __("Claim Number"),
					reqd: 1,
					default: `CLM-${frappe.datetime.now_date().replace(/-/g, "")}-${frm.doc.name.split("-").pop()}`
				},
				{
					fieldtype: "Date",
					fieldname: "claim_date",
					label: __("Claim Date"),
					reqd: 1,
					default: frappe.datetime.now_date()
				},
				{
					fieldtype: "Link",
					fieldname: "insurance_policy",
					label: __("Insurance Policy"),
					options: "Insurance Policy",
					reqd: 1,
					default: frm.doc.custom_insurance_policy,
					get_query: function () {
						return {
							filters: {
								patient: frm.doc.customer,
								status: "Active"
							}
						};
					}
				}
			],
			primary_action_label: __("Create & Open"),
			primary_action(values) {
				d.hide();
				frappe.call({
					method: "frappe.client.insert",
					args: {
						doc: {
							doctype: "Insurance Claim",
							naming_series: "IC-",
							claim_number: values.claim_number,
							claim_date: values.claim_date,
							patient: frm.doc.customer,
							insurance_policy: values.insurance_policy,
							sales_invoice: frm.doc.name,
							status: "Draft"
						}
					},
					freeze: true,
					freeze_message: __("Creating Insurance Claim…"),
					callback: function (r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Insurance Claim {0} created.", [r.message.name]),
								indicator: "green"
							});
							frappe.set_route("Form", "Insurance Claim", r.message.name);
						}
					}
				});
			}
		});

		d.show();
	}
});
