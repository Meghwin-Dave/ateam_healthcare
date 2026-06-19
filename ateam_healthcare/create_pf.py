import frappe

def execute():
    frappe.init(site="healthcare.local")
    frappe.connect()

    html = """<style>
    .print-format { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .header { border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 20px; }
    .logo { max-height: 80px; }
    .hospital-info { text-align: right; font-size: 12px; color: #555; }
    .title { font-size: 28px; font-weight: bold; color: #2c3e50; margin: 0; }
    .info-table { width: 100%; margin-bottom: 20px; font-size: 13px; }
    .info-table td { padding: 4px; }
    .info-label { font-weight: bold; color: #555; width: 120px; }
    .items-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }
    .items-table th { background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; padding: 10px; text-align: left; font-weight: bold; color: #2c3e50; }
    .items-table td { border-bottom: 1px solid #dee2e6; padding: 10px; }
    .totals-table { width: 40%; float: right; font-size: 13px; }
    .totals-table td { padding: 6px; }
    .total-row td { font-size: 16px; font-weight: bold; border-top: 2px solid #2c3e50; color: #2c3e50; }
    .footer { text-align: center; margin-top: 50px; font-size: 11px; color: #777; border-top: 1px solid #eee; padding-top: 10px; }
    .badge { background-color: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 1px solid #ccc; display: inline-block; }
</style>

<div class="print-format">
    <div class="header">
        <table style="width: 100%; border: none;">
            <tr>
                <td style="width: 50%; border: none;">
                    {% if frappe.db.get_value("Company", doc.company, "company_logo") %}
                        <img src="{{ frappe.db.get_value("Company", doc.company, "company_logo") }}" class="logo">
                    {% else %}
                        <h2 style="color: #2c3e50; margin: 0;">{{ doc.company }}</h2>
                    {% endif %}
                </td>
                <td class="hospital-info" style="border: none;">
                    <strong>{{ doc.company }}</strong><br>
                    {% set company_address = frappe.db.get_value("Dynamic Link", {"link_doctype": "Company", "link_name": doc.company, "parenttype": "Address"}, "parent") %}
                    {% if company_address %}
                        {% set addr = frappe.get_doc("Address", company_address) %}
                        {{ addr.address_line1 }}<br>
                        {% if addr.address_line2 %}{{ addr.address_line2 }}<br>{% endif %}
                        {{ addr.city }}, {{ addr.state }} {{ addr.pincode }}<br>
                        {% if addr.phone %}Phone: {{ addr.phone }}{% endif %}
                    {% endif %}
                </td>
            </tr>
        </table>
    </div>

    <div style="margin-bottom: 30px;">
        <h1 class="title">Sales Invoice</h1>
        <div style="color: #777; font-size: 14px;">#{{ doc.name }}</div>
    </div>

    <table class="info-table" style="border: none;">
        <tr>
            <td style="width: 50%; vertical-align: top; border: none;">
                <table style="width: 100%; border: none;">
                    <tr><td class="info-label" style="border: none;">Patient:</td><td style="border: none;">{{ doc.customer_name }}</td></tr>
                    {% if doc.custom_insurance_policy %}
                    <tr><td class="info-label" style="border: none;">Insurance Policy:</td><td style="border: none;"><span class="badge">{{ doc.custom_insurance_policy }}</span></td></tr>
                    {% endif %}
                    {% if doc.custom_procedure_request %}
                    <tr><td class="info-label" style="border: none;">Procedure Ref:</td><td style="border: none;">{{ doc.custom_procedure_request }}</td></tr>
                    {% endif %}
                </table>
            </td>
            <td style="width: 50%; vertical-align: top; border: none;">
                <table style="width: 100%; border: none;">
                    <tr><td class="info-label" style="border: none;">Date:</td><td style="border: none;">{{ doc.get_formatted("posting_date") }}</td></tr>
                    <tr><td class="info-label" style="border: none;">Due Date:</td><td style="border: none;">{{ doc.get_formatted("due_date") }}</td></tr>
                    <tr><td class="info-label" style="border: none;">Status:</td><td style="border: none;"><strong>{{ doc.status }}</strong></td></tr>
                </table>
            </td>
        </tr>
    </table>

    <table class="items-table">
        <thead>
            <tr>
                <th>Sr</th>
                <th>Item / Procedure</th>
                <th style="text-align: right;">Qty</th>
                <th style="text-align: right;">Rate</th>
                <th style="text-align: right;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.items %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>
                    <strong>{{ row.item_name }}</strong><br>
                    {% if row.description and row.description != row.item_name %}
                        <span style="color: #777; font-size: 11px;">{{ row.description }}</span>
                    {% endif %}
                </td>
                <td style="text-align: right;">{{ row.qty }}</td>
                <td style="text-align: right;">{{ row.get_formatted("rate") }}</td>
                <td style="text-align: right;">{{ row.get_formatted("amount") }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div style="overflow: hidden;">
        <table class="totals-table" style="border: none;">
            <tr>
                <td style="border: none;">Subtotal</td>
                <td style="text-align: right; border: none;">{{ doc.get_formatted("base_net_total") }}</td>
            </tr>
            {% for tax in doc.taxes %}
            <tr>
                <td style="border: none;">{{ tax.description }}</td>
                <td style="text-align: right; border: none;">{{ tax.get_formatted("tax_amount") }}</td>
            </tr>
            {% endfor %}
            {% if doc.discount_amount %}
            <tr>
                <td style="border: none;">Discount</td>
                <td style="text-align: right; border: none;">-{{ doc.get_formatted("discount_amount") }}</td>
            </tr>
            {% endif %}
            <tr class="total-row">
                <td style="border: none; border-top: 2px solid #2c3e50;">Grand Total</td>
                <td style="text-align: right; border: none; border-top: 2px solid #2c3e50;">{{ doc.get_formatted("grand_total") }}</td>
            </tr>
            {% if doc.outstanding_amount > 0 and doc.outstanding_amount != doc.grand_total %}
            <tr>
                <td style="color: #d9534f; font-weight: bold; border: none;">Amount Due</td>
                <td style="text-align: right; color: #d9534f; font-weight: bold; border: none;">{{ doc.get_formatted("outstanding_amount") }}</td>
            </tr>
            {% endif %}
        </table>
    </div>

    <div class="footer">
        <p>Thank you for choosing {{ doc.company }}. Wishing you a speedy recovery!</p>
    </div>
</div>
"""

    if not frappe.db.exists("Print Format", "Ateam Medical Invoice"):
        doc = frappe.new_doc("Print Format")
        doc.name = "Ateam Medical Invoice"
        doc.doc_type = "Sales Invoice"
        doc.standard = "Yes"
        doc.module = "Ateam Healthcare"
        doc.custom_format = 1
        doc.print_format_builder = 0
        doc.html = html
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Print Format")
    else:
        doc = frappe.get_doc("Print Format", "Ateam Medical Invoice")
        doc.html = html
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated Print Format")
        
execute()
