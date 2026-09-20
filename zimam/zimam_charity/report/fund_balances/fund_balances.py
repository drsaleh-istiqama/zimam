# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""أرصدة الصناديق (بطاقات الصناديق في وقاف): المرحَّل (الأستاذ) · الالتزامات المعتمدة غير المدفوعة · الدفتري · الفعلي حسب الكشف · الفرق."""
import frappe
from frappe import _
from frappe.utils import flt

from zimam.zimam_charity.utils import fund_balances


def execute(filters=None):
	filters = frappe._dict(filters or {})
	f = {"is_active": 1}
	if filters.get("company"):
		f["company"] = filters.company
	if filters.get("include_inactive"):
		f.pop("is_active")
	rows, totals = [], {"posted": 0, "committed": 0, "book": 0, "statement": 0}
	for fund in frappe.get_all("Charity Fund", filters=f, fields=["name", "fund_name", "fund_type", "account", "statement_balance", "statement_date", "purpose"], order_by="fund_type, name"):
		b = fund_balances(fund.name)
		rows.append({"fund": fund.name, "fund_name": fund.fund_name, "fund_type": fund.fund_type, "account": fund.account, "purpose": fund.purpose,
			"posted": b["posted_balance"], "committed": b["committed_amount"], "book": b["book_balance"],
			"statement": flt(fund.statement_balance), "statement_date": fund.statement_date, "difference": b["statement_difference"]})
		for k in ("posted", "committed", "book", "statement"):
			totals[k] += flt(rows[-1][k])
	rows.append({"fund": _("الإجمالي"), **totals, "difference": totals["statement"] - totals["posted"]})
	columns = [
		{"label": _("الصندوق"), "fieldname": "fund", "fieldtype": "Link", "options": "Charity Fund", "width": 130},
		{"label": _("الاسم"), "fieldname": "fund_name", "fieldtype": "Data", "width": 220},
		{"label": _("النوع"), "fieldname": "fund_type", "fieldtype": "Data", "width": 110},
		{"label": _("الغرض"), "fieldname": "purpose", "fieldtype": "Data", "width": 160},
		{"label": _("المرحَّل"), "fieldname": "posted", "fieldtype": "Currency", "width": 130},
		{"label": _("التزامات معتمدة"), "fieldname": "committed", "fieldtype": "Currency", "width": 130},
		{"label": _("الدفتري"), "fieldname": "book", "fieldtype": "Currency", "width": 130},
		{"label": _("الفعلي (الكشف)"), "fieldname": "statement", "fieldtype": "Currency", "width": 130},
		{"label": _("تاريخ الكشف"), "fieldname": "statement_date", "fieldtype": "Date", "width": 100},
		{"label": _("الفرق"), "fieldname": "difference", "fieldtype": "Currency", "width": 120},
	]
	return columns, rows
