# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""سجل تقديرات الطباعة: كل عروض الأسعار بحالتها وقيمتها وهامشها وقناة إرسالها وموعد متابعتها — للمتابعة اليومية في المطبعة."""
import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions, values = ["e.docstatus < 2"], {}
	if filters.get("from_date"):
		conditions.append("e.estimate_date >= %(from_date)s"); values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("e.estimate_date <= %(to_date)s"); values["to_date"] = filters.to_date
	for key in ("company", "status", "customer", "product_type", "template", "sent_via"):
		if filters.get(key):
			conditions.append(f"e.{key} = %({key})s"); values[key] = filters.get(key)
	if filters.get("follow_up_due"):
		conditions.append("e.status = 'مُرسل' and e.follow_up_date is not null and e.follow_up_date <= %(today)s"); values["today"] = today()
	if filters.get("open_only"):
		conditions.append("e.status in ('مسودة', 'مُرسل')")
	rows = frappe.db.sql(f"""
		select e.name, e.estimate_date, e.date_hijri, coalesce(nullif(e.customer_name, ''), e.prospect_name) as party, e.contact_phone, e.title,
			e.product_type, e.quantity, e.unit_price, e.total_cost, e.net_total, e.grand_total,
			coalesce(nullif(e.margin_applied, 0), e.margin_percent) as margin, e.status, e.sent_via, e.sent_on, e.valid_until, e.follow_up_date,
			e.alternative_of, e.option_label, e.quotation, e.print_job, e.rejection_reason, e.owner
		from `tabPrint Estimate` e where {' and '.join(conditions)} order by e.estimate_date desc, e.name desc""", values, as_dict=True)
	columns = [
		{"label": _("التقدير"), "fieldname": "name", "fieldtype": "Link", "options": "Print Estimate", "width": 130},
		{"label": _("التاريخ"), "fieldname": "estimate_date", "fieldtype": "Date", "width": 95},
		{"label": _("العميل / طالب العرض"), "fieldname": "party", "fieldtype": "Data", "width": 160},
		{"label": _("الهاتف"), "fieldname": "contact_phone", "fieldtype": "Data", "width": 100},
		{"label": _("العمل"), "fieldname": "title", "fieldtype": "Data", "width": 180},
		{"label": _("المنتج"), "fieldname": "product_type", "fieldtype": "Data", "width": 100},
		{"label": _("الكمية"), "fieldname": "quantity", "fieldtype": "Int", "width": 70},
		{"label": _("للوحدة"), "fieldname": "unit_price", "fieldtype": "Currency", "width": 85},
		{"label": _("التكلفة"), "fieldname": "total_cost", "fieldtype": "Currency", "width": 95},
		{"label": _("قبل الضريبة"), "fieldname": "net_total", "fieldtype": "Currency", "width": 100},
		{"label": _("الإجمالي"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 100},
		{"label": _("الهامش %"), "fieldname": "margin", "fieldtype": "Percent", "width": 80},
		{"label": _("الحالة"), "fieldname": "status", "fieldtype": "Data", "width": 105},
		{"label": _("أُرسل عبر"), "fieldname": "sent_via", "fieldtype": "Data", "width": 90},
		{"label": _("صالح حتى"), "fieldname": "valid_until", "fieldtype": "Date", "width": 95},
		{"label": _("المتابعة"), "fieldname": "follow_up_date", "fieldtype": "Date", "width": 95},
		{"label": _("خيار بديل لـ"), "fieldname": "alternative_of", "fieldtype": "Link", "options": "Print Estimate", "width": 120},
		{"label": _("عرض السعر"), "fieldname": "quotation", "fieldtype": "Link", "options": "Quotation", "width": 120},
		{"label": _("أمر الطباعة"), "fieldname": "print_job", "fieldtype": "Link", "options": "Print Job", "width": 120},
		{"label": _("سبب الرفض"), "fieldname": "rejection_reason", "fieldtype": "Data", "width": 160},
		{"label": _("أعدّه"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 130},
	]
	return columns, rows
