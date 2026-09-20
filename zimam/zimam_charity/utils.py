# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""أدوات الحزمة الخيرية: الإعدادات، نسبة الرسوم لكل فئة، حساب إيراد الفئة، تحديث المحصَّل على المشروع وإحصاء المتبرع.
(قيود اليومية والصناديق في zimam.zimam_core.finance)"""
import frappe
from frappe import _
from frappe.utils import flt

from zimam.zimam_core.finance import get_hijri, update_project_spent  # noqa: F401 — يُستدعى من الواجهة بالمسار القديم


def get_charity_settings():
	return frappe.get_cached_doc("Charity Settings")


def charity_company():
	s = get_charity_settings()
	if s.company:
		return s.company
	parent = frappe.db.get_single_value("Zimam Settings", "parent_company")
	if not parent:
		frappe.throw(_("حدد الشركة في إعدادات الحزمة الخيرية أو المؤسسة الأم في إعدادات زِمام"))
	return parent


def fee_percent_for(category, row_percent=None):
	"""نسبة الرسوم الإدارية لسطر تخصيص: قيمة السطر إن وُجدت، وإلا نسبة الفئة، وإلا الافتراضية — وصفر إن كانت الفئة لا تقبل رسومًا."""
	if row_percent not in (None, ""):
		return flt(row_percent)
	if not category:
		return flt(get_charity_settings().default_admin_fee_percent)
	apply_fee, pct = frappe.db.get_value("Donation Category", category, ["apply_admin_fee", "admin_fee_percent"]) or (1, None)
	if not apply_fee:
		return 0.0
	if pct not in (None, 0, ""):
		return flt(pct)
	return flt(get_charity_settings().default_admin_fee_percent)


def category_income_account(category, company):
	acc = frappe.db.get_value("Donation Category", category, "income_account") if category else None
	if acc and frappe.db.get_value("Account", acc, "company") == company:
		return acc
	default = get_charity_settings().default_donation_income_account
	if default and frappe.db.get_value("Account", default, "company") == company:
		return default
	return acc or default


def update_project_totals(project):
	"""المحصَّل من التبرعات (صافيًا) + المصروف بسندات الصرف على المشروع."""
	if not project or not frappe.db.exists("Project", project) or not frappe.get_meta("Project").has_field("zimam_collected"):
		return
	collected = flt(frappe.db.sql("""select coalesce(sum(a.net_amount), 0) from `tabDonation Allocation` a
		join `tabDonation` d on d.name = a.parent where d.docstatus=1 and a.project=%s""", project)[0][0])
	collected += flt(frappe.db.sql("""select coalesce(sum(d.net_amount), 0) from `tabDonation` d
		where d.docstatus=1 and d.project=%s and not exists (select 1 from `tabDonation Allocation` a where a.parent=d.name and a.project=%s)""",
		(project, project))[0][0])
	frappe.db.set_value("Project", project, "zimam_collected", collected, update_modified=False)
	update_project_spent(project)


def update_donor_stats(donor):
	if not donor or not frappe.db.exists("Donor", donor):
		return
	row = frappe.db.sql("""select coalesce(sum(amount), 0), count(name), min(donation_date), max(donation_date)
		from `tabDonation` where donor=%s and docstatus=1""", donor)[0]
	frappe.db.set_value("Donor", donor, {"total_donated": flt(row[0]), "donations_count": int(row[1] or 0),
		"first_donation_date": row[2], "last_donation_date": row[3]}, update_modified=False)
