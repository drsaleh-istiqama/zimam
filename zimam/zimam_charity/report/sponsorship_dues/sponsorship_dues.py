# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""استحقاقات الكفالات: «متأخر» يُشتق من التاريخ عند التشغيل ولا يُخزَّن."""
import frappe
from frappe import _
from frappe.utils import date_diff, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	f = {}
	if filters.get("sponsor"):
		f["sponsor"] = filters.sponsor
	if filters.get("sponsorship"):
		f["sponsorship"] = filters.sponsorship
	if filters.get("status"):
		f["status"] = filters.status
	rows = frappe.get_all("Sponsorship Due", filters=f, fields=["name", "sponsorship", "sponsor", "sponsor_name", "beneficiary_name", "due_date", "amount", "status", "donation", "paid_on"], order_by="due_date")
	today = nowdate()
	out = []
	for r in rows:
		late = date_diff(today, r.due_date) if r.status == "مستحق" else 0
		if filters.get("overdue_only") and late <= 0:
			continue
		r["days_late"] = late if late > 0 else 0
		r["state"] = _("متأخر") if late > 0 else r.status
		out.append(r)
	columns = [
		{"label": _("الاستحقاق"), "fieldname": "name", "fieldtype": "Link", "options": "Sponsorship Due", "width": 150},
		{"label": _("الكفالة"), "fieldname": "sponsorship", "fieldtype": "Link", "options": "Sponsorship", "width": 130},
		{"label": _("الكافل"), "fieldname": "sponsor_name", "fieldtype": "Data", "width": 160},
		{"label": _("المكفول"), "fieldname": "beneficiary_name", "fieldtype": "Data", "width": 160},
		{"label": _("تاريخ الاستحقاق"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
		{"label": _("المبلغ"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("الحالة"), "fieldname": "state", "fieldtype": "Data", "width": 90},
		{"label": _("أيام التأخر"), "fieldname": "days_late", "fieldtype": "Int", "width": 90},
		{"label": _("إيصال السداد"), "fieldname": "donation", "fieldtype": "Link", "options": "Donation", "width": 140},
		{"label": _("سُدِّد في"), "fieldname": "paid_on", "fieldtype": "Date", "width": 100},
	]
	return columns, out
