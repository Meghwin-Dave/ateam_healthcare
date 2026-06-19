# Copyright (c) 2026, Meghwin Dave and contributors
# For license information, please see license.txt
"""
Alpha Insurance e-Claim Gateway Module (Mock Simulation)

Provides:
  - build_eclaim_payload(): Constructs the Alpha Insurance JSON payload
  - submit_to_gateway(): Simulates submitting Pre-Auth or Final Claim
"""

import json
import frappe
from frappe import _
from frappe.utils import flt, today, now_datetime, add_days


# -------------------------------------------------------
# Alpha Insurance JSON Schema Builder
# -------------------------------------------------------

@frappe.whitelist()
def build_eclaim_payload(claim_name):
	"""
	Build the Alpha Insurance compliant e-Claim JSON payload.

	Schema matches Alpha's automated e-Claim gateway expectations so that
	the 'Total Claim Amount' always matches their algorithmic calculation.
	"""
	claim = frappe.get_doc("Insurance Claim", claim_name)
	policy = frappe.get_doc("Insurance Policy", claim.insurance_policy)
	patient = frappe.get_doc("Customer", claim.patient)
	ins_company = frappe.get_doc("Insurance Company", policy.insurance_company)
	plan_name = frappe.get_value("Insurance Plan", policy.insurance_plan, "plan_name") or policy.insurance_plan

	procedure_items = []
	disallowed_items = []

	for item in claim.items:
		base = {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"billed_amount": flt(item.amount, 3),
			"is_claimable": not bool(item.is_disallowed)
		}
		if item.is_disallowed:
			base["reason_disallowed"] = item.disallowed_reason or "Non-reimbursable item"
			base["patient_liability"] = flt(item.amount, 3)
			disallowed_items.append(base)
		else:
			# Proportional cap per item (for multi-item claims)
			base["approved_amount"] = flt(
				min(item.amount, flt(claim.deductible_cap)), 3
			)
			base["income_account"] = item.income_account or ""
			procedure_items.append(base)

	payload = {
		"schema_version": "ALPHA-ECLAIM-v2.1",
		"claim_header": {
			"submission_type": "FINAL_CLAIM",
			"transaction_date": str(claim.claim_date or today()),
			"transaction_timestamp": str(now_datetime()),
			"provider_id": "LIFECARE-001",
			"provider_name": frappe.defaults.get_user_default("Company") or "Lifecare Hospital",
			"claim_number": claim.name,
			"claim_reference": claim.claim_number,
			"pre_auth_number": claim.pre_auth_number or None
		},
		"patient": {
			"patient_id": claim.patient,
			"patient_name": patient.customer_name,
			"national_id": patient.get("custom_national_id") or "",
			"date_of_birth": str(patient.get("custom_date_of_birth") or ""),
			"policy_number": policy.policy_number,
			"insurance_plan": plan_name,
			"insurance_company": ins_company.company_name,
			"corporate_code": ins_company.company_code
		},
		"claim_details": {
			"linked_invoice": claim.sales_invoice or "",
			"procedure_items": procedure_items,
			"disallowed_items": disallowed_items,
			"financial_summary": {
				"total_billed_omr": flt(claim.invoice_amount, 3),
				"total_insurable_omr": flt(
					(claim.invoice_amount or 0) - (claim.disallowed_amount or 0), 3
				),
				"disallowed_amount_omr": flt(claim.disallowed_amount, 3),
				"deductible_cap_omr": flt(claim.deductible_cap, 3),
				"approved_amount_omr": flt(claim.approved_amount, 3),
				"uncovered_above_cap_omr": flt(claim.uncovered_amount, 3),
				"co_pay_percentage": flt(claim.co_pay_percentage, 2),
				"co_pay_amount_omr": flt(claim.co_pay_amount, 3),
				"total_claim_amount_omr": flt(claim.insurance_payable, 3),
				"patient_liability_omr": flt(claim.patient_payable, 3)
			}
		}
	}

	return payload


# -------------------------------------------------------
# Mock Gateway Submission
# -------------------------------------------------------

@frappe.whitelist()
def submit_to_gateway(claim_name, mode="pre_auth"):
	"""
	Simulate submitting a claim to the Alpha Insurance e-Claim gateway.

	Mode:
	  pre_auth  — Pre-Authorization request before procedure
	  final     — Final claim settlement after discharge

	Returns the mock gateway response dict.
	"""
	claim = frappe.get_doc("Insurance Claim", claim_name)

	if not claim.items:
		frappe.throw(_("No items in claim. Please load items before submitting."))

	# Build the payload
	payload = build_eclaim_payload(claim_name)
	payload["claim_header"]["submission_type"] = (
		"PRE_AUTHORIZATION" if mode == "pre_auth" else "FINAL_CLAIM"
	)

	json_payload = json.dumps(payload, indent=2, default=str)

	# ---- MOCK GATEWAY LOGIC ----
	mock_response = _build_mock_response(claim, mode)
	# ----------------------------

	# Persist payload and response on the claim
	claim.db_set("eclaim_json", json_payload)
	claim.db_set("eclaim_response", json.dumps(mock_response, indent=2, default=str))

	if mode == "pre_auth":
		claim.db_set("pre_auth_status", mock_response.get("pre_auth_status", "Pending"))
		if mock_response.get("pre_auth_number"):
			claim.db_set("pre_auth_number", mock_response["pre_auth_number"])

	frappe.db.commit()
	return mock_response


def _build_mock_response(claim, mode):
	"""Build a realistic-looking mock Alpha Insurance gateway response."""
	txn_id_prefix = "ALPHA-PA" if mode == "pre_auth" else "ALPHA-FC"
	txn_id = f"{txn_id_prefix}-{frappe.generate_hash(length=8).upper()}"

	if mode == "pre_auth":
		return {
			"status": "SUCCESS",
			"transaction_id": txn_id,
			"pre_auth_number": f"PA-{frappe.generate_hash(length=6).upper()}",
			"pre_auth_status": "Approved",
			"approved_amount_omr": flt(claim.insurance_payable, 3),
			"validity_date": str(add_days(today(), 30)),
			"message": (
				"Pre-authorization approved. Approved amount: OMR {0}. "
				"Valid for 30 days. Please quote Pre-Auth number on final claim."
			).format(flt(claim.insurance_payable, 3)),
			"gateway": "Alpha Insurance e-Claim Gateway v2.1 (SIMULATION)",
			"timestamp": str(now_datetime())
		}
	else:
		return {
			"status": "SUCCESS",
			"transaction_id": txn_id,
			"claim_status": "Accepted",
			"settlement_amount_omr": flt(claim.insurance_payable, 3),
			"patient_liability_omr": flt(claim.patient_payable, 3),
			"expected_payment_date": str(add_days(today(), 14)),
			"payment_reference": f"PAY-{frappe.generate_hash(length=10).upper()}",
			"message": (
				"Final claim accepted. Settlement amount OMR {0} will be "
				"credited to provider account within 14 working days. "
				"Patient is liable for OMR {1}."
			).format(flt(claim.insurance_payable, 3), flt(claim.patient_payable, 3)),
			"gateway": "Alpha Insurance e-Claim Gateway v2.1 (SIMULATION)",
			"timestamp": str(now_datetime())
		}
