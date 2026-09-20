# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""أدوات مشتركة للحزمة الخيرية: الإعدادات، نسبة الرسوم لكل فئة، القيود، أرصدة الصناديق، تحديث المشاريع."""
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate


def get_charity_settings():
	return frappe.get_cached_doc("Charity Settings")


def charity_company():
	s = get_charity_settings()
	if s.company:
		return s.company
	parent = frappe.db.get_single_value("Zimam Settings", "parent_company")
	if not parent:
		frappe.throw(_("حدد الشركة في إعدادات الحزمة الخيرية أو المؤسسة الأم في إعدادات زِمام"))
	return parent


def fee_percent_for(category, row_percent=None):
	"""نسبة الرسوم الإدارية لسطر تخصيص: قيمة السطر إن وُجدت، وإلا نسبة الفئة، وإلا الافتراضية — وصفر إن كانت الفئة لا تقبل رسومًا."""
	if row_percent not in (None, ""):
		return flt(row_percent)
	if not category:
		return flt(get_charity_settings().default_admin_fee_percent)
	apply_fee, pct = frappe.db.get_value("Donation Category", category, ["apply_admin_fee", "admin_fee_percent"]) or (1, None)
	if not apply_fee:
		return 0.0
	if pct not in (None, 0, ""):
		return flt(pct)
	return flt(get_charity_settings().default_admin_fee_percent)


def category_income_account(category, company):
	acc = frappe.db.get_value("Donation Category", category, "income_account") if category else None
	if acc and frappe.db.get_value("Account", acc, "company") == company:
		return acc
	default = get_charity_settings().default_donation_income_account
	if default and frappe.db.get_value("Account", default, "company") == company:
		return default
	return acc or default


def fund_account(fund):
	acc, company = frappe.db.get_value("Charity Fund", fund, ["account", "company"])
	if not acc:
		frappe.throw(_("الصندوق {0} بلا حساب أستاذ").format(fund))
	return acc, company


def make_journal_entry(company, posting_date, rows, remark, reference_no=None, reference_date=None, voucher_type="Journal Entry"):
	"""قيد يومية من سطور {account, debit, credit, cost_center, project}؛ يُرحَّل ويُرجع اسمه."""
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = voucher_type
	je.company = company
	je.posting_date = posting_date or nowdate()
	je.user_remark = remark
	if reference_no:
		je.cheque_no = reference_no
		je.cheque_date = reference_date or je.posting_date
	for r in rows:
		if not flt(r.get("debit")) and not flt(r.get("credit")):
			continue
		je.append("accounts", {
			"account": r["account"],
			"debit_in_account_currency": flt(r.get("debit")),
			"credit_in_account_currency": flt(r.get("credit")),
			"cost_center": r.get("cost_center"),
			"project": r.get("project"),
		})
	je.insert(ignore_permissions=True)
	je.submit()
	return je.name


def fund_balances(fund):
	"""أرصدة صندوق كما في وقاف: المرحَّل (رصيد الأستاذ)، الالتزامات (سندات جاهزة للدفع)، الدفتري، فرق الكشف."""
	doc = frappe.get_doc("Charity Fund", fund) if isinstance(fund, str) else fund
	posted = 0.0
	if doc.account:
		from erpnext.accounts.utils import get_balance_on
		posted = flt(get_balance_on(account=doc.account, company=doc.company))
	committed = flt(frappe.db.sql("""select coalesce(sum(amount), 0) from `tabPayment Voucher`
		where fund=%s and docstatus=1 and workflow_state='جاهز للدفع'""", doc.name)[0][0])
	book = posted - committed
	diff = flt(doc.statement_balance) - posted if doc.statement_date else 0.0
	return {"posted_balance": posted, "committed_amount": committed, "book_balance": book,
		"statement_difference": diff, "balances_as_of": now_datetime()}


@frappe.whitelist()
def refresh_fund_balances(fund):
	frappe.has_permission("Charity Fund", "read", throw=True)
	vals = fund_balances(fund)
	frappe.db.set_value("Charity Fund", fund, vals, update_modified=False)
	return vals


def update_project_totals(project):
	if not project or not frappe.db.exists("Project", project):
		return
	meta = frappe.get_meta("Project")
	if not meta.has_field("zimam_collected"):
		return
	collected = flt(frappe.db.sql("""select coalesce(sum(a.net_amount), 0) from `tabDonation Allocation` a
		join `tabDonation` d on d.name = a.parent where d.docstatus=1 and a.project=%s""", project)[0][0])
	collected += flt(frappe.db.sql("""select coalesce(sum(d.net_amount), 0) from `tabDonation` d
		where d.docstatus=1 and d.project=%s and not exists (select 1 from `tabDonation Allocation` a where a.parent=d.name and a.project=%s)""",
		(project, project))[0][0])
	spent = flt(frappe.db.sql("""select coalesce(sum(amount), 0) from `tabPayment Voucher`
		where docstatus=1 and workflow_state='مدفوع' and project=%s""", project)[0][0])
	frappe.db.set_value("Project", project, {"zimam_collected": collected, "zimam_spent": spent}, update_modified=False)


def update_donor_stats(donor):
	if not donor or not frappe.db.exists("Donor", donor):
		return
	row = frappe.db.sql("""select coalesce(sum(amount), 0), count(name), min(donation_date), max(donation_date)
		from `tabDonation` where donor=%s and docstatus=1""", donor)[0]
	frappe.db.set_value("Donor", donor, {"total_donated": flt(row[0]), "donations_count": int(row[1] or 0),
		"first_donation_date": row[2], "last_donation_date": row[3]}, update_modified=False)


@frappe.whitelist()
def get_hijri(date):
	from zimam.utils import hijri_str
	return hijri_str(date)


def notify_stage(roles, subject, message, doctype, name):
	try:
		from zimam.utils import notify_roles
		notify_roles(roles, subject, message, doctype, name)
	except Exception:
		frappe.log_error(title="zimam charity: notify failed")
