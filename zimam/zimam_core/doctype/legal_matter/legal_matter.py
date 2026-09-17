# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, nowdate

from zimam.utils import notify_roles


class LegalMatter(Document):
	def validate(self):
		if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("تاريخ الانتهاء لا يسبق تاريخ البدء"))
		if self.status == "ساري" and self.end_date and getdate(self.end_date) < getdate(nowdate()):
			self.status = "منتهٍ"


def send_expiry_reminders():
	"""مهمة يومية: تنبيه المسؤول ومدير المؤسسة قبل انتهاء العقد/الالتزام (مرة كل 7 أيام)."""
	today = getdate(nowdate())
	matters = frappe.get_all("Legal Matter", filters={"status": "ساري", "end_date": ["is", "set"]},
		fields=["name", "title", "matter_type", "counterparty", "end_date", "renewal_reminder_days", "responsible", "reminder_sent_on"])
	for m in matters:
		days = cint(m.renewal_reminder_days) or 30
		if getdate(m.end_date) > add_days(today, days):
			continue
		if m.reminder_sent_on and getdate(m.reminder_sent_on) > add_days(today, -7):
			continue
		remaining = (getdate(m.end_date) - today).days
		subject = _("تنبيه قانوني: {0} ينتهي خلال {1} يومًا").format(m.title, remaining)
		message = _("{0} ({1}) مع {2} ينتهي بتاريخ {3}. راجع التجديد أو الإغلاق.").format(
			m.title, m.matter_type, m.counterparty or "-", frappe.format(m.end_date, "Date"))
		recipients = notify_roles(["مدير المؤسسة"], subject, message, "Legal Matter", m.name)
		if m.responsible and m.responsible not in recipients:
			frappe.get_doc({"doctype": "Notification Log", "for_user": m.responsible, "type": "Alert", "subject": subject,
				"email_content": message, "document_type": "Legal Matter", "document_name": m.name}).insert(ignore_permissions=True)
			frappe.sendmail(recipients=[m.responsible], subject=subject, message=message,
				reference_doctype="Legal Matter", reference_name=m.name, now=False)
		frappe.db.set_value("Legal Matter", m.name, "reminder_sent_on", today, update_modified=False)
