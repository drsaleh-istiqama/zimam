# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""الإيرادات بحسب الفئة (شجرةً): الإجمالي والرسوم الإدارية والصافي وعدد الإيصالات لكل فئة، مع مجموع الفئة الأم."""
import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions, values = ["d.docstatus = 1"], {}
	if filters.get("from_date"):
		conditions.append("d.donation_date >= %(from_date)s"); values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("d.donation_date <= %(to_date)s"); values["to_date"] = filters.to_date
	if filters.get("channel"):
		conditions.append("d.channel = %(channel)s"); values["channel"] = filters.channel
	if filters.get("fund"):
		conditions.append("d.fund = %(fund)s"); values["fund"] = filters.fund
	agg = frappe.db.sql(f"""
		select a.donation_category as category, sum(a.amount) as amount, sum(a.admin_fee_amount) as fee, sum(a.net_amount) as net, count(distinct d.name) as receipts
		from `tabDonation Allocation` a join `tabDonation` d on d.name = a.parent
		where {' and '.join(conditions)} group by a.donation_category""", values, as_dict=True)
	by_cat = {r.category: r for r in agg}
	cats = frappe.get_all("Donation Category", fields=["name", "category_name", "category_code", "is_group", "parent_donation_category", "lft", "rgt", "is_restricted"], order_by="lft")
	rows = []
	for c in cats:
		if c.is_group:
			children = [x for x in cats if x.lft > c.lft and x.rgt < c.rgt and not x.is_group]
			amount = sum(flt(by_cat.get(x.name, {}).get("amount")) for x in children)
			fee = sum(flt(by_cat.get(x.name, {}).get("fee")) for x in children)
			net = sum(flt(by_cat.get(x.name, {}).get("net")) for x in children)
			receipts = sum(int(by_cat.get(x.name, {}).get("receipts") or 0) for x in children)
		else:
			r = by_cat.get(c.name, {})
			amount, fee, net, receipts = flt(r.get("amount")), flt(r.get("fee")), flt(r.get("net")), int(r.get("receipts") or 0)
		if not amount and filters.get("hide_empty"):
			continue
		rows.append({"category": c.name, "category_code": c.category_code, "is_group": c.is_group, "parent": c.parent_donation_category,
			"indent": 0 if not c.parent_donation_category else 1, "restricted": "مقيد" if c.is_restricted else "",
			"amount": amount, "fee": fee, "net": net, "receipts": receipts})
	columns = [
		{"label": _("الفئة"), "fieldname": "category", "fieldtype": "Link", "options": "Donation Category", "width": 240},
		{"label": _("الرمز"), "fieldname": "category_code", "fieldtype": "Data", "width": 80},
		{"label": _("القيد"), "fieldname": "restricted", "fieldtype": "Data", "width": 70},
		{"label": _("الإيصالات"), "fieldname": "receipts", "fieldtype": "Int", "width": 90},
		{"label": _("الإجمالي"), "fieldname": "amount", "fieldtype": "Currency", "width": 130},
		{"label": _("الرسوم الإدارية"), "fieldname": "fee", "fieldtype": "Currency", "width": 120},
		{"label": _("الصافي"), "fieldname": "net", "fieldtype": "Currency", "width": 130},
	]
	total = {"category": _("الإجمالي"), "amount": sum(r["amount"] for r in rows if not r["is_group"]), "fee": sum(r["fee"] for r in rows if not r["is_group"]),
		"net": sum(r["net"] for r in rows if not r["is_group"]), "receipts": sum(r["receipts"] for r in rows if not r["is_group"]), "is_group": 1, "indent": 0}
	chart = {"data": {"labels": [r["category"] for r in rows if r["is_group"] and r["amount"]], "datasets": [{"name": _("الإجمالي"), "values": [r["amount"] for r in rows if r["is_group"] and r["amount"]]}]}, "type": "donut"}
	return columns, rows + [total], None, chart
