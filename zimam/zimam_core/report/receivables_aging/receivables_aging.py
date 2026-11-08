# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""أعمار الديون (0.16.0): فواتير المبيعات غير المحصَّلة موزعة على فئات التأخر، مع آخر متابعة تحصيل ووعد السداد.

يمرّ بصلاحيات المستخدم (get_list). المبالغ بعملة الفاتورة (outstanding_amount) فاختر الشركة/العميل عند تعدد العملات.
فئة التأخر تُحسب من تاريخ الاستحقاق (أو تاريخ الفاتورة إن غاب) إلى «كما في تاريخ».
"""
import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, nowdate

BUCKETS = [("b0", "غير مستحق بعد", None, 0), ("b1", "1–30 يومًا", 1, 30), ("b2", "31–60 يومًا", 31, 60), ("b3", "61–90 يومًا", 61, 90), ("b4", "أكثر من 90 يومًا", 91, None)]


def bucket_of(days_overdue):
	"""مفتاح الفئة لعدد أيام التأخر (≤0 غير مستحق)."""
	for key, _label, lo, hi in BUCKETS:
		if lo is None and days_overdue <= hi:
			return key
		if lo is not None and days_overdue >= lo and (hi is None or days_overdue <= hi):
			return key
	return "b4"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	as_of = getdate(filters.get("as_of_date") or nowdate())
	f = [["Sales Invoice", "docstatus", "=", 1], ["Sales Invoice", "is_return", "=", 0], ["Sales Invoice", "outstanding_amount", ">", 0],
		["Sales Invoice", "posting_date", "<=", as_of]]
	for key in ("company", "customer"):
		if filters.get(key):
			f.append(["Sales Invoice", key, "=", filters.get(key)])
	rows = frappe.get_list("Sales Invoice", filters=f, limit_page_length=0, order_by="due_date asc, name asc",
		fields=["name", "customer", "customer_name", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency", "company"])

	followups = {}
	if rows:
		for fu in frappe.get_all("Collection Followup", filters={"sales_invoice": ["in", [r.name for r in rows]]},
				fields=["sales_invoice", "contact_date", "outcome", "promised_date", "promised_amount", "assigned_to"], order_by="contact_date asc, creation asc"):
			cur = followups.setdefault(fu.sales_invoice, {"count": 0})
			cur.update(last_date=fu.contact_date, last_outcome=fu.outcome, promised_date=fu.promised_date, promised_amount=fu.promised_amount, assigned_to=fu.assigned_to)
			cur["count"] += 1

	out = []
	totals = {k: 0.0 for k, *_x in BUCKETS}
	for r in rows:
		days = date_diff(as_of, getdate(r.due_date or r.posting_date))
		key = bucket_of(days)
		fu = followups.get(r.name, {})
		if filters.get("without_followup") and fu:
			continue
		if filters.get("bucket") and filters.bucket != key:
			continue
		if filters.get("min_overdue_days") and days < int(filters.min_overdue_days):
			continue
		row = {"invoice": r.name, "customer": r.customer, "customer_name": r.customer_name, "due_date": r.due_date, "days_overdue": max(days, 0),
			"grand_total": r.grand_total, "outstanding": flt(r.outstanding_amount), "currency": r.currency, "company": r.company,
			"followups": fu.get("count", 0), "last_followup": fu.get("last_date"), "last_outcome": fu.get("last_outcome"),
			"promised_date": fu.get("promised_date"), "promised_amount": fu.get("promised_amount"), "assigned_to": fu.get("assigned_to")}
		for k, *_x in BUCKETS:
			row[k] = flt(r.outstanding_amount) if k == key else 0
			totals[k] += row[k]
		out.append(row)

	columns = [
		{"label": _("الفاتورة"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
		{"label": _("العميل"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": _("الاستحقاق"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("أيام التأخر"), "fieldname": "days_overdue", "fieldtype": "Int", "width": 90},
		{"label": _("إجمالي الفاتورة"), "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("المتبقي"), "fieldname": "outstanding", "fieldtype": "Currency", "options": "currency", "width": 120},
	] + [{"label": _(label), "fieldname": key, "fieldtype": "Currency", "options": "currency", "width": 110} for key, label, _lo, _hi in BUCKETS] + [
		{"label": _("عدد المتابعات"), "fieldname": "followups", "fieldtype": "Int", "width": 90},
		{"label": _("آخر متابعة"), "fieldname": "last_followup", "fieldtype": "Date", "width": 100},
		{"label": _("نتيجتها"), "fieldname": "last_outcome", "fieldtype": "Data", "width": 120},
		{"label": _("موعد السداد الموعود"), "fieldname": "promised_date", "fieldtype": "Date", "width": 120},
		{"label": _("المبلغ الموعود"), "fieldname": "promised_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
		{"label": _("المسؤول"), "fieldname": "assigned_to", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("الشركة"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
		{"label": _("العملة"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 70},
	]
	if out:
		out.append({"invoice": _("الإجمالي"), "outstanding": sum(r["outstanding"] for r in out), **totals})
	return columns, out
