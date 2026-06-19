# Copyright (c) 2026, Meghwin Dave and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class InsuranceClaim(Document):

	# -------------------------------------------------------
	# Standard Frappe Lifecycle Hooks
	# -------------------------------------------------------

	def validate(self):
		self.validate_policy_active()
		self.fetch_account_defaults()
		self.calculate_settlement()

	def on_submit(self):
		self.validate_accounts_before_gl()
		self.post_gl_entries()
		self.update_sales_invoice_eclaim_status("Submitted")

	def on_cancel(self):
		self.cancel_gl_entries()
		self.update_sales_invoice_eclaim_status("Cancelled")

	# -------------------------------------------------------
	# Validation Helpers
	# -------------------------------------------------------

	def validate_policy_active(self):
		"""Ensure the linked Insurance Policy is Active."""
		if not self.insurance_policy:
			return
		status = frappe.get_value("Insurance Policy", self.insurance_policy, "status")
		if status != "Active":
			frappe.throw(
				_("Insurance Policy {0} is not Active. Current status: <b>{1}</b>").format(
					self.insurance_policy, status
				),
				title=_("Invalid Policy")
			)

	def fetch_account_defaults(self):
		"""Auto-fetch receivable accounts if not already set."""
		if self.insurance_policy and not self.insurance_receivable_account:
			self.insurance_receivable_account = frappe.get_value(
				"Insurance Policy", self.insurance_policy, "insurance_receivable_account"
			)
		if self.patient and not self.patient_receivable_account:
			self.patient_receivable_account = frappe.get_value(
				"Customer", self.patient, "custom_patient_receivable_account"
			)

	def validate_accounts_before_gl(self):
		"""Check all required accounts are set before posting GL."""
		if not self.patient_receivable_account:
			frappe.throw(
				_("Patient Receivable Account is missing. "
				  "Please set <b>Patient Receivable Account</b> on the Customer <b>{0}</b>.").format(self.patient),
				title=_("Missing Account")
			)
		if not self.insurance_receivable_account:
			frappe.throw(
				_("Insurance Receivable Account is missing. "
				  "Please set it on Insurance Policy <b>{0}</b>.").format(self.insurance_policy),
				title=_("Missing Account")
			)
		for item in self.items:
			if not item.income_account:
				frappe.throw(
					_("Income Account is missing for item <b>{0}</b>. "
					  "Please set <b>Insurance Revenue Account</b> on the Item master.").format(item.item_code),
					title=_("Missing Income Account")
				)

	# -------------------------------------------------------
	# Settlement Calculation Engine
	# -------------------------------------------------------

	def calculate_settlement(self):
		"""
		Core settlement algorithm:

		1. Split items into insurable vs disallowed.
		2. Apply deductible cap to insurable amount → approved_amount.
		3. Compute co-pay from approved_amount.
		4. Insurance pays: approved_amount - co_pay_amount.
		5. Patient pays: co_pay_amount + uncovered(above cap) + disallowed.
		"""
		if not self.items:
			return

		total_insurable = 0.0
		total_disallowed = 0.0

		for item in self.items:
			if item.is_disallowed:
				total_disallowed += flt(item.amount)
			else:
				total_insurable += flt(item.amount)

		self.invoice_amount = total_insurable + total_disallowed
		self.disallowed_amount = total_disallowed

		# Apply deductible cap
		deductible_cap = flt(self.deductible_cap)
		approved_amount = min(total_insurable, deductible_cap) if deductible_cap > 0 else total_insurable
		self.approved_amount = flt(approved_amount, 3)

		# Portion of insurable amount the insurance will NOT cover (above cap)
		uncovered_amount = total_insurable - approved_amount
		self.uncovered_amount = flt(uncovered_amount, 3)

		# Co-pay
		co_pay_rate = flt(self.co_pay_percentage) / 100
		self.co_pay_amount = flt(approved_amount * co_pay_rate, 3)

		# Final payables
		self.insurance_payable = flt(approved_amount - self.co_pay_amount, 3)
		self.patient_payable = flt(self.co_pay_amount + uncovered_amount + total_disallowed, 3)

	# -------------------------------------------------------
	# GL Posting
	# -------------------------------------------------------

	def post_gl_entries(self):
		"""
		Create a balanced Journal Entry with 4 legs:
		  Dr Patient Receivables   → patient_payable
		  Dr Insurance Receivables → insurance_payable
		  Cr Item Income Account   → per-item revenue (grouped by account)
		"""
		if self.gl_entry_status == "Posted":
			frappe.throw(_("GL Entries already posted for this claim."))

		# Group items by their income_account for revenue credit lines
		revenue_lines = {}
		for item in self.items:
			account = item.income_account
			revenue_lines[account] = revenue_lines.get(account, 0.0) + flt(item.amount)

		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)

		jv_accounts = []

		# Debit: Patient Receivables
		jv_accounts.append({
			"account": self.patient_receivable_account,
			"party_type": "Customer",
			"party": self.patient,
			"debit_in_account_currency": flt(self.patient_payable, 3),
			"credit_in_account_currency": 0,
			"reference_type": "Sales Invoice",
			"reference_name": self.sales_invoice or None,
			"user_remark": _("Patient Co-Pay + Uncovered + Disallowed — Claim {0}").format(self.name)
		})

		# Debit: Insurance Receivables
		jv_accounts.append({
			"account": self.insurance_receivable_account,
			"debit_in_account_currency": flt(self.insurance_payable, 3),
			"credit_in_account_currency": 0,
			"reference_type": "Insurance Claim",
			"reference_name": self.name,
			"user_remark": _("Insurance Payable — Claim {0}").format(self.name)
		})

		# Credit: Revenue accounts (one line per unique income account)
		for account, amount in revenue_lines.items():
			jv_accounts.append({
				"account": account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": flt(amount, 3),
				"reference_type": "Insurance Claim",
				"reference_name": self.name
			})

		jv = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"posting_date": self.claim_date or today(),
			"company": company,
			"user_remark": _(
				"Alpha Insurance Settlement | Claim: {0} | Invoice: {1} | Patient: {2}"
			).format(self.name, self.sales_invoice or "N/A", self.patient),
			"accounts": jv_accounts
		})

		jv.insert(ignore_permissions=True)
		jv.submit()

		self.db_set("journal_entry", jv.name)
		self.db_set("gl_entry_status", "Posted")

		frappe.msgprint(
			_("Journal Entry <b>{0}</b> posted successfully.").format(jv.name),
			indicator="green",
			alert=True
		)

	def cancel_gl_entries(self):
		"""Cancel the linked Journal Entry when claim is cancelled."""
		if self.journal_entry:
			jv = frappe.get_doc("Journal Entry", self.journal_entry)
			if jv.docstatus == 1:
				jv.cancel()
			self.db_set("gl_entry_status", "Pending")
			self.db_set("journal_entry", None)

	def update_sales_invoice_eclaim_status(self, status):
		"""Sync e-claim status back to the linked Sales Invoice."""
		if self.sales_invoice:
			frappe.db.set_value(
				"Sales Invoice", self.sales_invoice, "custom_eclaim_status", status
			)


# -------------------------------------------------------
# Whitelisted server methods (called from JS)
# -------------------------------------------------------

@frappe.whitelist()
def get_invoice_items(claim_name):
	"""
	Load items from the linked Sales Invoice into the Insurance Claim.
	Automatically flags items as disallowed based on:
	  1. Insurance Plan's disallowed_items table
	  2. Item master's custom_is_insurance_excluded flag
	"""
	claim = frappe.get_doc("Insurance Claim", claim_name)

	if not claim.sales_invoice:
		frappe.throw(_("Please link a Sales Invoice first."))
	if not claim.insurance_policy:
		frappe.throw(_("Please select an Insurance Policy first."))

	# Fetch the plan's disallowed item codes
	plan_name = frappe.get_value("Insurance Policy", claim.insurance_policy, "insurance_plan")
	disallowed_codes = set()
	if plan_name:
		plan_disallowed = frappe.get_all(
			"Insurance Plan Disallowed Item",
			filters={"parent": plan_name},
			fields=["item_code"]
		)
		disallowed_codes = {d.item_code for d in plan_disallowed}

	# Fetch Sales Invoice items
	si = frappe.get_doc("Sales Invoice", claim.sales_invoice)
	items = []

	for si_item in si.items:
		# Check if disallowed by plan or by item master flag
		is_excluded_on_master = frappe.get_value(
			"Item", si_item.item_code, "custom_is_insurance_excluded"
		) or 0

		is_disallowed = 1 if (
			si_item.item_code in disallowed_codes or is_excluded_on_master
		) else 0

		disallowed_reason = ""
		if si_item.item_code in disallowed_codes:
			disallowed_reason = "Listed in Insurance Plan disallowed items"
		elif is_excluded_on_master:
			disallowed_reason = "Marked as excluded on Item master"

		income_account = frappe.get_value(
			"Item", si_item.item_code, "custom_insurance_revenue_account"
		) or ""

		items.append({
			"item_code": si_item.item_code,
			"item_name": si_item.item_name,
			"rate": flt(si_item.rate, 3),
			"amount": flt(si_item.amount, 3),
			"income_account": income_account,
			"is_disallowed": is_disallowed,
			"disallowed_reason": disallowed_reason
		})

	return items


@frappe.whitelist()
def get_settlement_breakdown(claim_name):
	"""Return detailed settlement breakdown for the settlement dialog."""
	claim = frappe.get_doc("Insurance Claim", claim_name)

	if not claim.items:
		frappe.throw(_("No items in claim. Please load items from the invoice first."))

	# Recalculate in memory (does not save)
	claim.calculate_settlement()

	# Build revenue credit lines for GL preview
	revenue_lines = {}
	for item in claim.items:
		account = item.income_account or _("(Income Account not set for {0})").format(item.item_code)
		revenue_lines[account] = revenue_lines.get(account, 0.0) + flt(item.amount)

	return {
		"invoice_amount": flt(claim.invoice_amount, 3),
		"total_insurable": flt(claim.invoice_amount - claim.disallowed_amount, 3),
		"disallowed_amount": flt(claim.disallowed_amount, 3),
		"deductible_cap": flt(claim.deductible_cap, 3),
		"approved_amount": flt(claim.approved_amount, 3),
		"uncovered_amount": flt(claim.uncovered_amount, 3),
		"co_pay_percentage": flt(claim.co_pay_percentage, 2),
		"co_pay_amount": flt(claim.co_pay_amount, 3),
		"insurance_payable": flt(claim.insurance_payable, 3),
		"patient_payable": flt(claim.patient_payable, 3),
		"patient_account": claim.patient_receivable_account or "(Not Set)",
		"insurance_account": claim.insurance_receivable_account or "(Not Set)",
		"revenue_lines": [
			{"account": k, "amount": flt(v, 3)} for k, v in revenue_lines.items()
		]
	}
