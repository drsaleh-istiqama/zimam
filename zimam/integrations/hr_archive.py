# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""أرشيف الموظفين السابقين (0.15.0).

لا مستند جديد: الموظف الذي غادر يبقى سجلُّه في Employee بحالة «Left» (ERPNext/HRMS)، وزِمام يضيف:
- تقرير «أرشيف الموظفين السابقين» (zimam_core/report/former_employees_archive) وبند «إنهاء خدمة» في الشريط الجانبي.
- حفظ السجل: لا يُحذف سجل موظف سابق إلا بمدير النظام (على بقية الأدوار يُرفض الحذف).
- تنبيه مسؤول الصلاحيات حين تتحول الحالة إلى «Left» ولحسابه مستخدم مفعَّل، ليوقف الحساب (الخطوة التي يطلبها دليل الموارد البشرية يدويًا).
"""
import frappe
from frappe import _

from zimam.utils import notify_roles

ACCESS_ROLE = "مسؤول الصلاحيات"


def employee_on_trash(doc, method=None):
	if doc.get("status") == "Left" and "System Manager" not in frappe.get_roles():
		frappe.throw(_("سجل الموظف السابق {0} محفوظ في الأرشيف ولا يُحذف. للضرورة القصوى يحذفه مدير النظام.").format(doc.name))


def employee_on_update(doc, method=None):
	"""عند التحول إلى «Left»: إن كان له مستخدم مفعَّل نُبِّه مسؤول الصلاحيات (لا يُوقَف الحساب آليًّا — قرار بشري)."""
	if doc.get("status") != "Left" or not doc.has_value_changed("status") or not doc.get("user_id"):
		return
	try:
		if not frappe.db.get_value("User", doc.user_id, "enabled"):
			return
		notify_roles([ACCESS_ROLE], _("إيقاف حساب موظف غادر: {0}").format(doc.employee_name or doc.name),
			_("غادر الموظف {0} ({1}). حسابه {2} ما زال مفعَّلًا — أوقفه من شاشة المستخدم ثم أرشف تعيينه.").format(
				doc.employee_name or doc.name, doc.name, doc.user_id), "Employee", doc.name)
	except Exception:
		# التنبيه لا يوقف حفظ الموظف أبدًا
		frappe.log_error(title="zimam: former-employee notice failed")
