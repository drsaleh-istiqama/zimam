# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""المالية المشتركة في النواة: قيد اليومية من سطور، حساب الصندوق، أرصدة الصندوق الثلاثة (مرحَّل/دفتري/فعلي)، وتحديث المصروف على المشروع."""
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate


def fund_account(fund):
	acc, company = frappe.db.get_value("Treasury Fund", fund, ["account", "company"])
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
	"""أرصدة صندوق: المرحَّل (رصيد الأستاذ)، الالتزامات (سندات جاهزة للدفع)، الدفتري، فرق كشف البنك."""
	doc = frappe.get_doc("Treasury Fund", fund) if isinstance(fund, str) else fund
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
	frappe.has_permission("Treasury Fund", "read", throw=True)
	vals = fund_balances(fund)
	frappe.db.set_value("Treasury Fund", fund, vals, update_modified=False)
	return vals


def update_project_spent(project):
	"""المصروف بسندات الصرف المدفوعة على المشروع (حقل zimam_spent المخصص إن وُجد)."""
	if not project or not frappe.db.exists("Project", project) or not frappe.get_meta("Project").has_field("zimam_spent"):
		return
	spent = flt(frappe.db.sql("""select coalesce(sum(amount), 0) from `tabPayment Voucher`
		where docstatus=1 and workflow_state='مدفوع' and project=%s""", project)[0][0])
	frappe.db.set_value("Project", project, "zimam_spent", spent, update_modified=False)


@frappe.whitelist()
def get_hijri(date):
	from zimam.utils import hijri_str
	return hijri_str(date)
