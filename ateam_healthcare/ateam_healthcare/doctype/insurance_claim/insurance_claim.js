// Copyright (c) 2026, Meghwin Dave and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insurance Claim", {

	// -------------------------------------------------------
	// Form Setup
	// -------------------------------------------------------

	setup(frm) {
		// Filter Insurance Policy by patient
		frm.set_query("insurance_policy", function () {
			return {
				filters: {
					patient: frm.doc.patient,
					status: "Active"
				}
			};
		});

		// Filter Sales Invoice by patient
		frm.set_query("sales_invoice", function () {
			return {
				filters: {
					customer: frm.doc.patient,
					docstatus: 1
				}
			};
		});

		// Filter accounts to receivable type
		frm.set_query("patient_receivable_account", function () {
			return {
				filters: {
					account_type: "Receivable",
					is_group: 0
				}
			};
		});

		frm.set_query("insurance_receivable_account", function () {
			return {
				filters: {
					account_type: "Receivable",
					is_group: 0
				}
			};
		});
	},

	// -------------------------------------------------------
	// Refresh — build context-aware toolbar buttons
	// -------------------------------------------------------

	refresh(frm) {
		frm.trigger("setup_status_badges");

		if (frm.doc.docstatus === 0) {
			frm.trigger("add_draft_buttons");
		}

		if (frm.doc.docstatus === 1) {
			frm.trigger("add_submitted_buttons");
		}
	},

	add_draft_buttons(frm) {
		// "Load Items from Invoice"
		if (frm.doc.sales_invoice && frm.doc.insurance_policy) {
			frm.add_custom_button(__("Load Items from Invoice"), function () {
				frappe.call({
					method: "ateam_healthcare.ateam_healthcare.doctype.insurance_claim.insurance_claim.get_invoice_items",
					args: { claim_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Loading items…"),
					callback: function (r) {
						if (r.message && r.message.length) {
							frm.clear_table("items");
							r.message.forEach(function (item) {
								let row = frm.add_child("items");
								Object.assign(row, item);
							});
							frm.refresh_field("items");
							frm.dirty();
							frappe.show_alert({ message: __("Items loaded. Review and save."), indicator: "green" });
						} else {
							frappe.msgprint(__("No items found on the linked Sales Invoice."));
						}
					}
				});
			}, __("Actions"));
		}

		// "Calculate Settlement" (only when items exist)
		if (frm.doc.items && frm.doc.items.length > 0) {
			frm.add_custom_button(__("Calculate Settlement"), function () {
				frm.trigger("show_settlement_dialog");
			}, __("Actions"));

			// e-Claim buttons
			frm.add_custom_button(__("Preview e-Claim JSON"), function () {
				frm.trigger("preview_eclaim_json");
			}, __("e-Claim"));

			frm.add_custom_button(__("Submit Pre-Authorization"), function () {
				frappe.confirm(
					__("Submit Pre-Authorization request to Alpha Insurance? (Simulation Mode)"),
					function () {
						frappe.call({
							method: "ateam_healthcare.ateam_healthcare.api.eclaim.submit_to_gateway",
							args: { claim_name: frm.doc.name, mode: "pre_auth" },
							freeze: true,
							freeze_message: __("Submitting Pre-Auth…"),
							callback: function (r) {
								if (r.message) {
									frm.reload_doc();
									frappe.show_alert({ message: __("Pre-Authorization submitted successfully."), indicator: "green" });
									frm.trigger("show_gateway_response", r.message);
								}
							}
						});
					}
				);
			}, __("e-Claim"));
		}
	},

	add_submitted_buttons(frm) {
		// "Submit Final Claim" — only if pre-auth approved and GL not posted
		if (frm.doc.pre_auth_status === "Approved") {
			frm.add_custom_button(__("Submit Final Claim"), function () {
				frappe.confirm(
					__("Submit Final Claim to Alpha Insurance gateway? (Simulation Mode)"),
					function () {
						frappe.call({
							method: "ateam_healthcare.ateam_healthcare.api.eclaim.submit_to_gateway",
							args: { claim_name: frm.doc.name, mode: "final" },
							freeze: true,
							freeze_message: __("Submitting Final Claim…"),
							callback: function (r) {
								if (r.message) {
									frm.reload_doc();
									frappe.show_alert({ message: __("Final Claim accepted by insurer."), indicator: "green" });
								}
							}
						});
					}
				);
			}, __("e-Claim"));
		}

		// View Journal Entry shortcut
		if (frm.doc.journal_entry) {
			frm.add_custom_button(__("View Journal Entry"), function () {
				frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
			}, __("View"));
		}

		// View linked Sales Invoice
		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("View Sales Invoice"), function () {
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
			}, __("View"));
		}
	},

	// -------------------------------------------------------
	// Field Events
	// -------------------------------------------------------

	patient(frm) {
		if (!frm.doc.patient) return;

		// Fetch patient receivable account
		frappe.db.get_value("Customer", frm.doc.patient, "custom_patient_receivable_account")
			.then(function (r) {
				if (r && r.message && r.message.custom_patient_receivable_account) {
					frm.set_value("patient_receivable_account", r.message.custom_patient_receivable_account);
				}
			});

		// Refresh policy filter
		frm.set_query("insurance_policy", function () {
			return { filters: { patient: frm.doc.patient, status: "Active" } };
		});
		frm.set_query("sales_invoice", function () {
			return { filters: { customer: frm.doc.patient, docstatus: 1 } };
		});
	},

	insurance_policy(frm) {
		if (!frm.doc.insurance_policy) return;

		frappe.db.get_doc("Insurance Policy", frm.doc.insurance_policy).then(function (policy) {
			frm.set_value("co_pay_percentage", policy.co_pay_percentage);
			frm.set_value("deductible_cap", policy.coverage_cap);
			if (policy.insurance_receivable_account) {
				frm.set_value("insurance_receivable_account", policy.insurance_receivable_account);
			}
		});
	},

	// -------------------------------------------------------
	// Settlement Dialog
	// -------------------------------------------------------

	show_settlement_dialog(frm) {
		frappe.call({
			method: "ateam_healthcare.ateam_healthcare.doctype.insurance_claim.insurance_claim.get_settlement_breakdown",
			args: { claim_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Calculating…"),
			callback: function (r) {
				if (!r.message) return;
				const d = r.message;

				const fmt = (v) => format_currency(v, frappe.boot.sysdefaults.currency || "OMR");

				const revenue_rows = d.revenue_lines.map(l =>
					`<tr>
						<td style="padding:6px 10px;">${l.account}</td>
						<td style="padding:6px 10px; text-align:right; color:#1B5E20; font-weight:600;">Cr ${fmt(l.amount)}</td>
					</tr>`
				).join("");

				const html = `
<div style="font-family: var(--font-stack, sans-serif); padding: 4px;">

	<!-- Calculation table -->
	<table style="width:100%; border-collapse:collapse; margin-bottom:18px; font-size:13px;">
		<thead>
			<tr style="background:#E3F2FD;">
				<th style="padding:8px 10px; text-align:left; font-weight:600;">Description</th>
				<th style="padding:8px 10px; text-align:right; font-weight:600;">Amount (OMR)</th>
			</tr>
		</thead>
		<tbody>
			<tr style="border-bottom:1px solid #eee;"><td style="padding:6px 10px;">Total Invoice Amount</td><td style="padding:6px 10px; text-align:right;">${fmt(d.invoice_amount)}</td></tr>
			<tr style="border-bottom:1px solid #eee;"><td style="padding:6px 10px;">Insurable Amount (excl. disallowed)</td><td style="padding:6px 10px; text-align:right;">${fmt(d.total_insurable)}</td></tr>
			<tr style="border-bottom:1px solid #eee; color:#B71C1C;"><td style="padding:6px 10px;">Disallowed (Non-Reimbursable)</td><td style="padding:6px 10px; text-align:right;">- ${fmt(d.disallowed_amount)}</td></tr>
			<tr style="border-bottom:1px solid #eee;"><td style="padding:6px 10px;">Deductible Cap</td><td style="padding:6px 10px; text-align:right;">${fmt(d.deductible_cap)}</td></tr>
			<tr style="border-bottom:1px solid #eee;"><td style="padding:6px 10px;">Approved Amount (capped)</td><td style="padding:6px 10px; text-align:right;">${fmt(d.approved_amount)}</td></tr>
			<tr style="border-bottom:1px solid #eee; color:#E65100;"><td style="padding:6px 10px;">Uncovered Amount (above cap) → patient</td><td style="padding:6px 10px; text-align:right;">${fmt(d.uncovered_amount)}</td></tr>
			<tr style="border-bottom:1px solid #eee;"><td style="padding:6px 10px;">Co-Pay (${d.co_pay_percentage}% of Approved)</td><td style="padding:6px 10px; text-align:right;">${fmt(d.co_pay_amount)}</td></tr>
		</tbody>
	</table>

	<!-- GL Summary cards -->
	<div style="display:flex; gap:14px; margin-bottom:18px;">
		<div style="flex:1; background:linear-gradient(135deg,#E8F5E9,#C8E6C9); border-radius:10px; padding:16px; text-align:center; border:1px solid #A5D6A7;">
			<div style="font-size:11px; color:#388E3C; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Dr Insurance Receivables</div>
			<div style="font-size:26px; font-weight:700; color:#1B5E20;">${fmt(d.insurance_payable)}</div>
			<div style="font-size:11px; color:#555; margin-top:4px;">${d.insurance_account}</div>
		</div>
		<div style="flex:1; background:linear-gradient(135deg,#FFF3E0,#FFE0B2); border-radius:10px; padding:16px; text-align:center; border:1px solid #FFCC80;">
			<div style="font-size:11px; color:#E65100; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Dr Patient Receivables</div>
			<div style="font-size:26px; font-weight:700; color:#BF360C;">${fmt(d.patient_payable)}</div>
			<div style="font-size:11px; color:#555; margin-top:4px;">${d.patient_account}</div>
		</div>
	</div>

	<!-- Revenue credits -->
	<div style="background:#F1F8E9; border-radius:8px; padding:14px; border:1px solid #DCEDC8;">
		<div style="font-size:12px; font-weight:600; color:#33691E; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">Credit — Revenue Accounts</div>
		<table style="width:100%; font-size:13px; border-collapse:collapse;">${revenue_rows}</table>
	</div>

	<!-- Balance check -->
	<div style="margin-top:12px; font-size:12px; color:#666; text-align:right;">
		Balance: Dr ${fmt(d.patient_payable + d.insurance_payable)} = Cr ${fmt(d.invoice_amount)}
		${Math.abs((d.patient_payable + d.insurance_payable) - d.invoice_amount) < 0.01
			? ' <span style="color:#2E7D32;">✓ Balanced</span>'
			: ' <span style="color:#C62828;">✗ Imbalanced</span>'}
	</div>
</div>`;

				let dialog = new frappe.ui.Dialog({
					title: __("Settlement Breakdown — Alpha Insurance"),
					fields: [{ fieldtype: "HTML", fieldname: "breakdown_html", options: html }],
					size: "large",
					primary_action_label: __("Close"),
					primary_action() { dialog.hide(); }
				});
				dialog.show();
			}
		});
	},

	// -------------------------------------------------------
	// e-Claim JSON Preview
	// -------------------------------------------------------

	preview_eclaim_json(frm) {
		frappe.call({
			method: "ateam_healthcare.ateam_healthcare.api.eclaim.build_eclaim_payload",
			args: { claim_name: frm.doc.name },
			callback: function (r) {
				if (!r.message) return;
				let dialog = new frappe.ui.Dialog({
					title: __("Alpha Insurance — e-Claim JSON Payload"),
					fields: [{
						fieldtype: "Code",
						fieldname: "json_code",
						options: "JSON",
						read_only: 1,
						default: JSON.stringify(r.message, null, 2)
					}],
					size: "extra-large",
					primary_action_label: __("Close"),
					primary_action() { dialog.hide(); }
				});
				dialog.show();
			}
		});
	},

	// -------------------------------------------------------
	// Status badge colours
	// -------------------------------------------------------

	setup_status_badges(frm) {
		const pre_auth_colors = { "Approved": "green", "Rejected": "red", "Pending": "orange" };
		const gl_colors = { "Posted": "green", "Pending": "orange" };

		frm.set_indicator_formatter("pre_auth_status", function (doc) {
			return pre_auth_colors[doc.pre_auth_status] || "grey";
		});
		frm.set_indicator_formatter("gl_entry_status", function (doc) {
			return gl_colors[doc.gl_entry_status] || "grey";
		});
	}
});
