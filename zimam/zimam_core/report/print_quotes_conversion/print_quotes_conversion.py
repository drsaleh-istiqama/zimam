# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""تحويل عروض الطباعة: كم عرضًا أُرسل وكم قُبل ورُفض وانتهى، ونسبة القبول وقيمة المقبول ومتوسط الهامش — مجمَّعًا
بحسب نوع المنتج أو الشهر أو العميل أو قناة الإرسال أو مُعدّ التقدير؛ لمعايرة الأسعار (أين نخسر العروض؟) ومتابعة الأداء."""
import frappe
from frappe import _

GROUPS = {
	"نوع المنتج": ("e.product_type", _("نوع المنتج"), "Data", None),
	"الشهر": ("date_format(e.estimate_date, '%%Y-%%m')", _("الشهر"), "Data", None),
	"العميل": ("coalesce(nullif(e.customer_name, ''), e.prospect_name)", _("العميل"), "Data", None),
	"قناة الإرسال": ("coalesce(nullif(e.sent_via, ''), 'غير محدد')", _("قناة الإرسال"), "Data", None),
	"مُعدّ التقدير": ("e.owner", _("مُعدّ التقدير"), "Link", "User"),
	"قالب المنتج": ("coalesce(e.template, 'بلا قالب')", _("قالب المنتج"), "Data", None),
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group = filters.get("group_by") if filters.get("group_by") in GROUPS else "نوع المنتج"
	expr, label, ftype, options = GROUPS[group]
	conditions, values = ["e.docstatus = 1"], {}
	if filters.get("from_date"):
		conditions.append("e.estimate_date >= %(from_date)s"); values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("e.estimate_date <= %(to_date)s"); values["to_date"] = filters.to_date
	if filters.get("company"):
		conditions.append("e.company = %(company)s"); values["company"] = filters.company
	if not filters.get("include_alternatives"):
		conditions.append("(e.alternative_of is null or e.alternative_of = '')")
	rows = frappe.db.sql(f"""
		select {expr} as grp,
			count(*) as total,
			sum(e.status = 'مُرسل') as open_count,
			sum(e.status = 'مقبول') as accepted,
			sum(e.status = 'مرفوض') as rejected,
			sum(e.status = 'منتهي الصلاحية') as expired,
			sum(e.net_total) as quoted_value,
			sum(case when e.status = 'مقبول' then e.net_total else 0 end) as accepted_value,
			avg(coalesce(nullif(e.margin_applied, 0), e.margin_percent)) as avg_margin,
			avg(e.unit_price) as avg_unit_price,
			avg(case when e.sent_on is not null then timestampdiff(hour, e.creation, e.sent_on) end) as avg_hours_to_send
		from `tabPrint Estimate` e where {' and '.join(conditions)}
		group by grp order by accepted_value desc, total desc""", values, as_dict=True)
	for r in rows:
		decided = (r.accepted or 0) + (r.rejected or 0) + (r.expired or 0)
		r["acceptance_percent"] = round(100.0 * (r.accepted or 0) / decided, 1) if decided else None
		r["avg_margin"] = round(r.avg_margin or 0, 1)
		r["avg_hours_to_send"] = round(r.avg_hours_to_send, 1) if r.avg_hours_to_send is not None else None
	columns = [
		{"label": label, "fieldname": "grp", "fieldtype": ftype, "options": options, "width": 180},
		{"label": _("العروض"), "fieldname": "total", "fieldtype": "Int", "width": 70},
		{"label": _("بانتظار الرد"), "fieldname": "open_count", "fieldtype": "Int", "width": 90},
		{"label": _("مقبول"), "fieldname": "accepted", "fieldtype": "Int", "width": 70},
		{"label": _("مرفوض"), "fieldname": "rejected", "fieldtype": "Int", "width": 70},
		{"label": _("منتهٍ"), "fieldname": "expired", "fieldtype": "Int", "width": 70},
		{"label": _("نسبة القبول %"), "fieldname": "acceptance_percent", "fieldtype": "Percent", "width": 100},
		{"label": _("قيمة العروض"), "fieldname": "quoted_value", "fieldtype": "Currency", "width": 110},
		{"label": _("قيمة المقبول"), "fieldname": "accepted_value", "fieldtype": "Currency", "width": 110},
		{"label": _("متوسط الهامش %"), "fieldname": "avg_margin", "fieldtype": "Percent", "width": 105},
		{"label": _("متوسط سعر الوحدة"), "fieldname": "avg_unit_price", "fieldtype": "Currency", "width": 115},
		{"label": _("ساعات حتى الإرسال"), "fieldname": "avg_hours_to_send", "fieldtype": "Float", "width": 110},
	]
	chart = None
	if rows:
		top = rows[:12]
		chart = {
			"data": {"labels": [str(r.grp) for r in top], "datasets": [
				{"name": _("مقبول"), "values": [r.accepted or 0 for r in top]},
				{"name": _("مرفوض"), "values": [r.rejected or 0 for r in top]},
				{"name": _("بانتظار الرد"), "values": [r.open_count or 0 for r in top]},
			]},
			"type": "bar", "barOptions": {"stacked": 1}, "colors": ["#2F7A4F", "#B23A2E", "#7B3F61"],
		}
	return columns, rows, None, chart
