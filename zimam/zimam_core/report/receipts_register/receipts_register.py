# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""سجل سندات القبض (0.14.0): قيود الدفع من نوع «استلام» بالتاريخ والحالة والصندوق والطرف وطريقة القبض.

يمرّ بصلاحيات المستخدم (get_list) فلا يرى مستخدم مقيَّد بشركة قبض شركة أخرى. المبلغ بعملة الشركة (base_received_amount) ليصح الإجمالي.
"""
import frappe
from frappe import _

STATUS = {"مسودة": 0, "معتمد": 1, "ملغى": 2}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	f = [["Payment Entry", "payment_type", "=", "Receive"]]
	if filters.get("from_date"):
		f.append(["Payment Entry", "posting_date", ">=", filters.from_date])
	if filters.get("to_date"):
		f.append(["Payment Entry", "posting_date", "<=", filters.to_date])
	for key in ("company", "mode_of_payment", "party_type", "party", "project"):
		if filters.get(key):
			f.append(["Payment Entry", key, "=", filters.get(key)])
	if filters.get("status") in STATUS:
		f.append(["Payment Entry", "docstatus", "=", STATUS[filters.status]])
	else:
		f.append(["Payment Entry", "docstatus", "<", 2])  # الملغاة لا تظهر إلا باختيارها
	if filters.get("min_amount"):
		f.append(["Payment Entry", "base_received_amount", ">=", filters.min_amount])

	rows = frappe.get_list("Payment Entry", filters=f, limit_page_length=0, order_by="posting_date desc, name desc",
		fields=["name", "posting_date", "zimam_date_hijri", "party_type", "party", "party_name", "mode_of_payment", "base_received_amount",
			"paid_to", "zimam_fund", "reference_no", "reference_date", "docstatus", "company", "project", "remarks", "owner"])

	# الصندوق: المختار صراحةً، وإلا الصندوق الذي حسابه هو حساب الاستلام
	by_account = {x.account: x.name for x in frappe.get_all("Treasury Fund", fields=["name", "account"]) if x.account}
	if filters.get("fund"):
		rows = [r for r in rows if (r.zimam_fund or by_account.get(r.paid_to)) == filters.fund]
	for r in rows:
		r["fund"] = r.pop("zimam_fund") or by_account.get(r.paid_to)
		r["amount"] = r.pop("base_received_amount")
		r["status"] = {0: _("مسودة"), 1: _("معتمد"), 2: _("ملغى")}.get(r.pop("docstatus"))

	columns = [
		{"label": _("السند"), "fieldname": "name", "fieldtype": "Link", "options": "Payment Entry", "width": 150},
		{"label": _("التاريخ"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("التاريخ الهجري"), "fieldname": "zimam_date_hijri", "fieldtype": "Data", "width": 130},
		{"label": _("الحالة"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("الدافع"), "fieldname": "party_name", "fieldtype": "Data", "width": 190},
		{"label": _("نوع الطرف"), "fieldname": "party_type", "fieldtype": "Link", "options": "DocType", "width": 90},
		{"label": _("المبلغ"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": _("طريقة القبض"), "fieldname": "mode_of_payment", "fieldtype": "Link", "options": "Mode of Payment", "width": 120},
		{"label": _("الصندوق"), "fieldname": "fund", "fieldtype": "Link", "options": "Treasury Fund", "width": 120},
		{"label": _("حساب الاستلام"), "fieldname": "paid_to", "fieldtype": "Link", "options": "Account", "width": 200},
		{"label": _("المرجع"), "fieldname": "reference_no", "fieldtype": "Data", "width": 110},
		{"label": _("المشروع"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 130},
		{"label": _("الشركة"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": _("سجّله"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("البيان"), "fieldname": "remarks", "fieldtype": "Data", "width": 260},
	]
	total = sum((r.amount or 0) for r in rows if r.status != _("ملغى"))
	rows.append({"name": _("الإجمالي (دون الملغى)"), "amount": total})
	return columns, rows
