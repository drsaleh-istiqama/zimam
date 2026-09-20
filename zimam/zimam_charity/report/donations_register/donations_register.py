# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""سجل الإيرادات (كما في شاشة «الإيرادات» في وقاف): كل إيصال بفلاتر التاريخ والفئة والقناة والصندوق والمتبرع والمشروع والمصدر."""
import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions, values = ["d.docstatus = 1"], {}
	if filters.get("from_date"):
		conditions.append("d.donation_date >= %(from_date)s"); values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("d.donation_date <= %(to_date)s"); values["to_date"] = filters.to_date
	for key in ("channel", "fund", "donor", "member", "project", "source", "company"):
		if filters.get(key):
			conditions.append(f"d.{key} = %({key})s"); values[key] = filters.get(key)
	if filters.get("donation_category"):
		conditions.append("""exists (select 1 from `tabDonation Allocation` a join `tabDonation Category` c on c.name = a.donation_category
			join `tabDonation Category` p on p.name = %(donation_category)s
			where a.parent = d.name and c.lft >= p.lft and c.rgt <= p.rgt)""")
		values["donation_category"] = filters.donation_category
	rows = frappe.db.sql(f"""
		select d.name, d.donation_date, d.date_hijri, d.donor, d.donor_name, d.member, d.channel, d.fund, d.amount, d.admin_fee_amount, d.net_amount,
			d.donation_category, d.project, d.purpose, d.reference_no, d.source, d.status, d.owner, d.modified
		from `tabDonation` d where {' and '.join(conditions)} order by d.donation_date desc, d.name desc""", values, as_dict=True)
	columns = [
		{"label": _("المرجع"), "fieldname": "name", "fieldtype": "Link", "options": "Donation", "width": 150},
		{"label": _("التاريخ"), "fieldname": "donation_date", "fieldtype": "Date", "width": 100},
		{"label": _("هجري"), "fieldname": "date_hijri", "fieldtype": "Data", "width": 120},
		{"label": _("المتبرع"), "fieldname": "donor_name", "fieldtype": "Data", "width": 160},
		{"label": _("العضو"), "fieldname": "member", "fieldtype": "Link", "options": "Member", "width": 100},
		{"label": _("القناة"), "fieldname": "channel", "fieldtype": "Data", "width": 90},
		{"label": _("الصندوق"), "fieldname": "fund", "fieldtype": "Link", "options": "Treasury Fund", "width": 120},
		{"label": _("المبلغ"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("الرسوم"), "fieldname": "admin_fee_amount", "fieldtype": "Currency", "width": 100},
		{"label": _("الصافي"), "fieldname": "net_amount", "fieldtype": "Currency", "width": 110},
		{"label": _("الفئة"), "fieldname": "donation_category", "fieldtype": "Link", "options": "Donation Category", "width": 160},
		{"label": _("المشروع"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
		{"label": _("وذلك عن"), "fieldname": "purpose", "fieldtype": "Data", "width": 180},
		{"label": _("المرجع البنكي"), "fieldname": "reference_no", "fieldtype": "Data", "width": 120},
		{"label": _("مُسجَّل عبر"), "fieldname": "source", "fieldtype": "Data", "width": 110},
		{"label": _("سجّله"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 140},
	]
	return columns, rows
