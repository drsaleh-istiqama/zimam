# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""سجل سندات الصرف (كما في شاشة «المصروفات» في وقاف): بالمرحلة والتصنيف والصندوق والفرع والمشروع وطريقة الدفع."""
import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions, values = ["v.docstatus < 2"], {}
	if filters.get("from_date"):
		conditions.append("v.voucher_date >= %(from_date)s"); values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("v.voucher_date <= %(to_date)s"); values["to_date"] = filters.to_date
	for key in ("workflow_state", "expense_classification", "fund", "branch", "project", "payment_method", "company", "beneficiary_type"):
		if filters.get(key):
			conditions.append(f"v.{key} = %({key})s"); values[key] = filters.get(key)
	if filters.get("pending_only"):
		conditions.append("v.workflow_state in ('مراجعة المالية', 'بانتظار اعتماد الرئيس التنفيذي', 'جاهز للدفع')")
	rows = frappe.db.sql(f"""
		select v.name, v.voucher_date, v.date_hijri, v.beneficiary_name, v.beneficiary_type, v.branch, v.payment_method, v.amount,
			v.expense_classification, v.classification_name, v.project, v.fund, v.workflow_state, v.due_date, v.paid_on, v.description, v.owner,
			v.finance_reviewed_by, v.approved_by, v.paid_by, v.journal_entry
		from `tabPayment Voucher` v where {' and '.join(conditions)} order by v.voucher_date desc, v.name desc""", values, as_dict=True)
	columns = [
		{"label": _("السند"), "fieldname": "name", "fieldtype": "Link", "options": "Payment Voucher", "width": 140},
		{"label": _("التاريخ"), "fieldname": "voucher_date", "fieldtype": "Date", "width": 100},
		{"label": _("المستفيد"), "fieldname": "beneficiary_name", "fieldtype": "Data", "width": 170},
		{"label": _("الفرع"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 80},
		{"label": _("طريقة الدفع"), "fieldname": "payment_method", "fieldtype": "Data", "width": 100},
		{"label": _("المبلغ"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("التصنيف"), "fieldname": "expense_classification", "fieldtype": "Link", "options": "Expense Classification", "width": 90},
		{"label": _("اسم التصنيف"), "fieldname": "classification_name", "fieldtype": "Data", "width": 140},
		{"label": _("المشروع"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 130},
		{"label": _("الصندوق"), "fieldname": "fund", "fieldtype": "Link", "options": "Treasury Fund", "width": 110},
		{"label": _("المرحلة"), "fieldname": "workflow_state", "fieldtype": "Data", "width": 170},
		{"label": _("الاستحقاق"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("دُفع في"), "fieldname": "paid_on", "fieldtype": "Date", "width": 100},
		{"label": _("سجّله"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("اعتمده"), "fieldname": "approved_by", "fieldtype": "Link", "options": "User", "width": 130},
		{"label": _("البيان"), "fieldname": "description", "fieldtype": "Data", "width": 240},
		{"label": _("القيد"), "fieldname": "journal_entry", "fieldtype": "Link", "options": "Journal Entry", "width": 120},
	]
	return columns, rows
