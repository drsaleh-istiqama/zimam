# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""أرشيف الموظفين السابقين (0.15.0): كل من حالته «Left» بتاريخ انتهاء الخدمة ومدتها وسبب المغادرة وإنهاء الخدمة المرتبط وهل حسابه ما زال مفعَّلًا.

يمرّ بصلاحيات المستخدم (get_list) فلا يرى المقيَّد بشركة موظفي شركة أخرى. لا رواتب هنا عمدًا.
"""
import frappe
from frappe import _
from frappe.utils import date_diff, getdate


def service_text(joined, left):
	"""مدة الخدمة نصًّا: «٣ سنة و٢ شهر» دون تقريب مضلِّل (تعتمد الأيام)."""
	if not joined or not left:
		return ""
	days = date_diff(getdate(left), getdate(joined))
	if days < 0:
		return ""
	years, rest = divmod(days, 365)
	months = rest // 30
	parts = []
	if years:
		parts.append(_("{0} سنة").format(years))
	if months:
		parts.append(_("{0} شهر").format(months))
	return _(" و").join(parts) if parts else _("{0} يوم").format(days)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	f = [["Employee", "status", "=", "Left"]]
	if filters.get("from_date"):
		f.append(["Employee", "relieving_date", ">=", filters.from_date])
	if filters.get("to_date"):
		f.append(["Employee", "relieving_date", "<=", filters.to_date])
	for key in ("company", "department", "designation", "branch"):
		if filters.get(key):
			f.append(["Employee", key, "=", filters.get(key)])
	if filters.get("reason"):
		f.append(["Employee", "reason_for_leaving", "like", f"%{filters.reason}%"])

	rows = frappe.get_list("Employee", filters=f, limit_page_length=0, order_by="relieving_date desc, name desc",
		fields=["name", "employee_name", "company", "department", "designation", "branch", "date_of_joining", "relieving_date",
			"resignation_letter_date", "reason_for_leaving", "user_id"])

	# إنهاء الخدمة المرتبط (إن كان HRMS مثبتًا) وحالة حساب المستخدم
	separation = {}
	if rows and frappe.db.exists("DocType", "Employee Separation"):
		for s in frappe.get_all("Employee Separation", filters={"employee": ["in", [r.name for r in rows]], "docstatus": ["<", 2]},
				fields=["name", "employee"], order_by="creation asc"):
			separation[s.employee] = s.name
	users = {}
	user_ids = [r.user_id for r in rows if r.user_id]
	if user_ids:
		users = {u.name: u.enabled for u in frappe.get_all("User", filters={"name": ["in", user_ids]}, fields=["name", "enabled"])}
	for r in rows:
		r["service"] = service_text(r.date_of_joining, r.relieving_date)
		r["separation"] = separation.get(r.name)
		r["account"] = "" if not r.user_id else (_("ما زال مفعَّلًا — يلزم إيقافه") if users.get(r.user_id) else _("موقوف"))

	columns = [
		{"label": _("الموظف"), "fieldname": "name", "fieldtype": "Link", "options": "Employee", "width": 110},
		{"label": _("الاسم"), "fieldname": "employee_name", "fieldtype": "Data", "width": 190},
		{"label": _("الشركة"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
		{"label": _("القسم"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
		{"label": _("المسمى الوظيفي"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 140},
		{"label": _("الفرع"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 100},
		{"label": _("تاريخ التعيين"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 100},
		{"label": _("تاريخ انتهاء الخدمة"), "fieldname": "relieving_date", "fieldtype": "Date", "width": 120},
		{"label": _("مدة الخدمة"), "fieldname": "service", "fieldtype": "Data", "width": 120},
		{"label": _("تاريخ خطاب الاستقالة"), "fieldname": "resignation_letter_date", "fieldtype": "Date", "width": 130},
		{"label": _("سبب المغادرة"), "fieldname": "reason_for_leaving", "fieldtype": "Data", "width": 200},
		{"label": _("إنهاء الخدمة"), "fieldname": "separation", "fieldtype": "Link", "options": "Employee Separation", "width": 150},
		{"label": _("حساب النظام"), "fieldname": "account", "fieldtype": "Data", "width": 170},
	]
	return columns, rows
