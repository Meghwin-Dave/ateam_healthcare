# Ateam Healthcare

> **A custom Frappe/ERPNext app for Lifecare Hospital's Healthcare Information System (HIS)**
>
> Solves the *Disputed Co-Pay & Multi-Tier Insurance Settlement* problem — automatically splitting patient and insurer receivables, posting balanced GL entries, and generating compliant e-Claim JSON payloads for Alpha Insurance's automated gateway.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture & DocType Map](#architecture--doctype-map)
- [Settlement Calculation Engine](#settlement-calculation-engine)
- [GL Accounting Flow](#gl-accounting-flow)
- [Installation](#installation)
- [Configuration (Master Data Setup)](#configuration-master-data-setup)
- [User Workflow](#user-workflow)
- [e-Claim JSON Schema](#e-claim-json-schema)
- [Custom Fields Added](#custom-fields-added)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Lifecare Hospital's accounting team faced a critical revenue leak: for high-volume surgical procedures billed to **Alpha Insurance**, the native ERPNext Healthcare and Accounts modules could not automatically handle:

1. **Patient Co-Pay** — patient pays a % of the approved amount
2. **Deductible Cap** — insurer covers a maximum fixed amount regardless of procedure cost
3. **Disallowed Items** — non-medical consumables are 100% non-reimbursable and must be billed entirely to the patient

This caused rejected e-Claims (the `total_claim_amount` didn't match Alpha's algorithmic expectation) and a growing backlog of **Unbilled/Disputed Receivables** in the General Ledger.

**Ateam Healthcare** solves this by introducing a full Insurance Claim lifecycle with an embedded settlement engine, automatic Journal Entry posting, and a mock e-Claim gateway.

---

## Key Features

| Feature | Details |
|---|---|
| 🧮 **Settlement Engine** | Auto-calculates co-pay, uncovered amounts, and insurance payable from policy terms |
| 📒 **GL Auto-Posting** | Creates a balanced 4-leg Journal Entry on claim submission |
| 🔗 **Configurable Accounts** | Patient AR on Customer, Insurance AR on Policy, Revenue account on Item master |
| 🚫 **Disallowed Items** | Two-tier exclusion: plan-level table + item-level flag |
| 📤 **e-Claim JSON Builder** | Generates Alpha Insurance compliant JSON payload |
| 🔄 **Mock Gateway** | Pre-Auth and Final Claim simulation with realistic responses |
| 🧾 **Sales Invoice Integration** | "Create Insurance Claim" button on submitted invoices |
| ✅ **Validation** | Blocks submission if accounts are missing; status badges; field filters |

---

## Architecture & DocType Map

```
Insurance Company
      │
      ├──▶ Insurance Plan  ──▶ Disallowed Items [ Insurance Plan Disallowed Item ]
      │          │
      │    coverage_cap, co_pay_%
      │          │
      └──▶ Insurance Policy  ──▶ insurance_receivable_account (→ Account)
                 │
                 │  linked via custom field
                 ▼
          Sales Invoice  ──▶  custom_insurance_policy
                 │
                 │  "Create Insurance Claim" button
                 ▼
          Insurance Claim  ══════════════════════════════════════╗
            │  patient → Customer.custom_patient_receivable_account ║
            │  insurance_policy → Policy.insurance_receivable_account ║
            │                                                      ║
            │── Items [ Insurance Claim Item ]                     ║
            │     │  item_code → Item.custom_insurance_revenue_account ║
            │     │  is_disallowed (auto-flagged)                  ║
            │     └  income_account (fetched from Item master)     ║
            │                                                      ║
            │── Settlement Calculation (on validate)               ║
            │     co_pay_amount, insurance_payable, patient_payable ║
            │                                                      ║
            │── on_submit → Journal Entry (4 legs)  ◀═════════════╝
            │
            └── e-Claim JSON → Mock Gateway (Pre-Auth / Final Claim)
```

---

## Settlement Calculation Engine

**Scenario**: SURG-001 @ OMR 1,500 + CONS-999 @ OMR 50, Alpha Corporate Plan (Co-Pay 10%, Cap OMR 1,200)

```
Step 1 – Classify items
  Insurable items:    SURG-001   OMR 1,500
  Disallowed items:   CONS-999   OMR    50  ← 100% patient

Step 2 – Apply deductible cap
  Total insurable:               OMR 1,500
  Deductible cap:                OMR 1,200
  Approved amount:   min(1500, 1200) = OMR 1,200
  Uncovered (above cap):         OMR   300  ← patient pays

Step 3 – Co-pay split
  Co-pay (10% × 1200):          OMR   120  ← patient pays
  Insurance payable (90% × 1200): OMR 1,080

Step 4 – Total patient liability
  Co-pay + Uncovered + Disallowed = 120 + 300 + 50 = OMR 470
```

**Result:**

| Receivable | Amount (OMR) |
|---|---|
| Dr Patient Receivables (John Doe) | **470.000** |
| Dr Insurance Receivables (Alpha) | **1,080.000** |
| Cr Healthcare Service Revenue | 1,500.000 |
| Cr Consumables Revenue | 50.000 |

---

## GL Accounting Flow

```
Sales Invoice Submitted
        │
        ▼
Insurance Claim Created (Draft)
        │
   [Load Items from Invoice]
   [Calculate Settlement]
   [Submit Pre-Authorization] ──▶ Mock Gateway ──▶ PA-XXXXXX Approved
        │
   [Submit Claim]
        │
        ▼
Journal Entry Auto-Created & Submitted
  ┌────────────────────────────────────────────────────────────┐
  │ Account                    │  Debit     │  Credit          │
  ├────────────────────────────┼────────────┼──────────────────┤
  │ Patient Receivables        │  470.000   │                  │
  │ Insurance Receivables      │ 1080.000   │                  │
  │ Healthcare Service Revenue │            │  1500.000        │
  │ Consumables Revenue        │            │    50.000        │
  ├────────────────────────────┼────────────┼──────────────────┤
  │ TOTAL                      │ 1550.000   │  1550.000 ✅     │
  └────────────────────────────┴────────────┴──────────────────┘
        │
   [Submit Final Claim] ──▶ Mock Gateway ──▶ Payment confirmed in 14 days
```

---

## Installation

### Prerequisites

- Frappe Bench (v15+)
- ERPNext installed on the site
- Site created and configured

### Install via bench

```bash
cd /path/to/your/bench

# Get the app
bench get-app https://github.com/Meghwin-Dave/ateam_healthcare.git --branch main

# Install on your site
bench --site your-site.local install-app ateam_healthcare

# Run migrations
bench --site your-site.local migrate

# Restart
bench restart
```

---

## Configuration (Master Data Setup)

Follow these steps in order before processing any claims.

### Step 1 — Chart of Accounts

Create these accounts under **Accounting → Chart of Accounts**:

| Account Name | Type | Use |
|---|---|---|
| `Patient Receivables` | Receivable | Patient co-pay / uncovered / disallowed |
| `Insurance Receivables — Alpha` | Receivable | Insurance company's share |
| `Healthcare Service Revenue` | Income | Surgical/clinical procedures |
| `Consumables Revenue` | Income | Non-medical consumables |

### Step 2 — Item Master

For each item billed through insurance, set custom fields in the **Ateam Healthcare** section:

| Item | `Excluded from Insurance` | `Insurance Revenue Account` |
|---|---|---|
| SURG-001 (Surgical Package) | ❌ No | Healthcare Service Revenue |
| CONS-999 (Non-Medical Bundle) | ✅ **Yes** | Consumables Revenue |

### Step 3 — Insurance Company

Navigate to **Ateam Healthcare → Insurance Company → New**

Required: Company Name, Company Code, API URL (for live integration)

### Step 4 — Insurance Plan

Navigate to **Ateam Healthcare → Insurance Plan → New**

| Field | Example |
|---|---|
| Plan Name | Alpha Corporate Plan |
| Insurance Company | Alpha Insurance |
| Coverage Cap | 1,200 |
| Co-Pay Percentage | 10% |
| Disallowed Items table | Add CONS-999 |

### Step 5 — Customer (Patient)

On the Customer record, set in the **Ateam Details** section:

- **ATEAM Customer Type** = `Patient`
- **Patient Receivable Account** = `Patient Receivables`

### Step 6 — Insurance Policy

Navigate to **Ateam Healthcare → Insurance Policy → New**

| Field | Value |
|---|---|
| Patient | John Doe |
| Insurance Plan | Alpha Corporate Plan |
| Status | **Active** |
| Insurance Receivable Account | Insurance Receivables — Alpha |

---

## User Workflow

```
1. Submit Sales Invoice
         │
         ▼  [Healthcare → Create Insurance Claim]
2. Insurance Claim created (Draft, linked to invoice)
         │
         ▼  [Actions → Load Items from Invoice]
3. Items loaded, CONS-999 auto-flagged as Disallowed
         │
         ▼  [Actions → Calculate Settlement]
4. Settlement dialog shows split: OMR 470 patient / OMR 1,080 insurer
         │
         ▼  [e-Claim → Submit Pre-Authorization]
5. Mock gateway returns Pre-Auth Number, status = Approved
         │
         ▼  [Submit Claim]
6. Journal Entry created + submitted automatically
   GL Entry Status → Posted
         │
         ▼  [e-Claim → Submit Final Claim]
7. Final claim accepted, payment expected in 14 days
```

---

## e-Claim JSON Schema

The `build_eclaim_payload()` function generates a payload matching Alpha Insurance's `ALPHA-ECLAIM-v2.1` schema:

```json
{
  "schema_version": "ALPHA-ECLAIM-v2.1",
  "claim_header": {
    "submission_type": "FINAL_CLAIM | PRE_AUTHORIZATION",
    "provider_id": "LIFECARE-001",
    "claim_number": "IC-XXXX-XXXX",
    "pre_auth_number": "PA-XXXXXX"
  },
  "patient": {
    "patient_id": "CUST-XXXXX",
    "policy_number": "IP-XXXXX",
    "insurance_plan": "Alpha Corporate Plan"
  },
  "claim_details": {
    "procedure_items": [ ... ],
    "disallowed_items": [ ... ],
    "financial_summary": {
      "total_billed_omr": 1550.000,
      "total_claim_amount_omr": 1080.000,
      "patient_liability_omr": 470.000
    }
  }
}
```

The `total_claim_amount_omr` field is calculated using the same algorithm as Alpha's gateway, eliminating claim rejections due to amount mismatches.

---

## Custom Fields Added

| DocType | Field Name | Type | Purpose |
|---|---|---|---|
| Customer | `custom_patient_receivable_account` | Link → Account | AR account for patient's GL debit |
| Customer | `custom_ateam_customer_type` | Select | Patient / Corporate / Insurance |
| Customer | `custom_national_id` | Data | Patient ID |
| Customer | `custom_date_of_birth` | Date | Patient DOB |
| Customer | `custom_blood_group` | Select | Medical reference |
| Sales Invoice | `custom_insurance_policy` | Link → Insurance Policy | Links invoice to policy |
| Sales Invoice | `custom_procedure_request` | Link → Procedure Request | Clinical order reference |
| Sales Invoice | `custom_eclaim_status` | Data (read-only) | Mirrors claim status |
| Sales Invoice | `custom_requested_by` | Link → Employee | Requesting clinician |
| Sales Invoice | `custom_requested_on_` | Date | Request date |
| Item | `custom_is_insurance_excluded` | Check | Globally exclude from insurance |
| Item | `custom_insurance_revenue_account` | Link → Account | Revenue account for GL credit |

---

## API Reference

All methods are `@frappe.whitelist()` accessible from JavaScript and external calls.

### `ateam_healthcare.ateam_healthcare.doctype.insurance_claim.insurance_claim`

| Method | Args | Returns | Description |
|---|---|---|---|
| `get_invoice_items(claim_name)` | claim name | list of item dicts | Fetches SI items, auto-flags disallowed ones |
| `get_settlement_breakdown(claim_name)` | claim name | settlement dict | Full calculation breakdown for display |

### `ateam_healthcare.ateam_healthcare.api.eclaim`

| Method | Args | Returns | Description |
|---|---|---|---|
| `build_eclaim_payload(claim_name)` | claim name | JSON dict | Alpha Insurance compliant payload |
| `submit_to_gateway(claim_name, mode)` | name, `"pre_auth"` or `"final"` | response dict | Submit to mock gateway |

---

## Module Structure

```
ateam_healthcare/
├── ateam_healthcare/
│   ├── api/
│   │   └── eclaim.py                      # e-Claim gateway API
│   ├── doctype/
│   │   ├── insurance_claim/               # Core claim lifecycle + GL posting
│   │   ├── insurance_claim_item/          # Child: items with disallowed flag
│   │   ├── insurance_company/             # Insurer master
│   │   ├── insurance_plan/                # Plan with coverage terms
│   │   ├── insurance_plan_disallowed_item/# Child: plan-level exclusions
│   │   ├── insurance_policy/              # Patient-policy link + AR account
│   │   ├── medical_procedure/             # Procedure catalogue (child)
│   │   └── procedure_request_item/        # Procedure request child
│   ├── fixtures/
│   │   └── custom_field.json              # All custom fields (exported)
│   ├── public/
│   │   └── js/
│   │       └── sales_invoice.js           # SI button override
│   └── hooks.py                           # Frappe hook registrations
├── README.md
├── license.txt
└── pyproject.toml
```

---

## Contributing

This app uses `pre-commit` for code formatting and linting.

```bash
cd apps/ateam_healthcare
pre-commit install
```

Pre-commit tools configured:

- **ruff** — Python linting & formatting
- **eslint** — JavaScript linting
- **prettier** — JS/JSON/YAML formatting
- **pyupgrade** — Python syntax modernisation

### Development Setup

```bash
# Clone into bench
bench get-app https://github.com/Meghwin-Dave/ateam_healthcare.git

# Run tests
bench --site your-site.local run-tests --app ateam_healthcare

# Export fixtures after making UI changes
bench export-fixtures --app ateam_healthcare

# Build JS assets
bench build --app ateam_healthcare
```

---

## License

MIT — see [license.txt](license.txt)

---

*Built for Lifecare Hospital HIS · Frappe/ERPNext v15 · Ateam Healthcare v1.0*
