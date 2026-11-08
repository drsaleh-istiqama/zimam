# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""متابعة تحصيل (0.16.0): سجل تواصل مع العميل بشأن فاتورة مبيعات مستحقة، وملخص يومي للمتأخرات ووعود السداد.

لا مستند مطالبة رسمي (Dunning) هنا عمدًا: قرار د. صالح المعلَّق هو هل تكفي المتابعة الداخلية في البداية.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, nowdate

from zimam.utils import get_settings, hijri_str, notify_roles

REMINDER_ROLES = ["محاسب مالي", "مدير مالي"]


class CollectionFollowup(Document):
	def validate(self):
		inv = frappe.db.get_value("Sales Invoice", self.sales_invoice, ["docstatus", "is_return", "outstanding_amount"], as_dict=True)
		if not inv or inv.docstatus != 1:
			frappe.throw(_("المتابعة تُسجَّل على فاتورة مبيعات معتمدة فقط"))
		if inv.is_return:
			frappe.throw(_("الفاتورة {0} إشعار دائن (مرتجع) ولا يُتابَع تحصيله").format(self.sales_invoice))
		if self.is_new():
			self.outstanding_at_contact = flt(inv.outstanding_amount)
		if self.contact_date:
			self.date_hijri = hijri_str(self.contact_date)
		problem = validate_promise(self.outcome, self.contact_date, self.promised_date, self.promised_amount, self.outstanding_at_contact)
		if problem:
			frappe.throw(_(problem))


PROMISE_OUTCOMES = ("وعد بالسداد", "سداد جزئي", "طلب جدولة / تأجيل")


def validate_promise(outcome, contact_date, promised_date, promised_amount, outstanding):
	"""يُرجع نص المشكلة أو None. الوعد يحتاج موعدًا لاحقًا لتاريخ التواصل، والمبلغ الموعود لا يتجاوز المتبقي."""
	if outcome in PROMISE_OUTCOMES and not promised_date:
		return "اكتب موعد السداد الموعود"
	if promised_date and contact_date and getdate(promised_date) < getdate(contact_date):
		return "موعد السداد الموعود سابق لتاريخ التواصل"
	if flt(promised_amount) and flt(outstanding) and flt(promised_amount) > flt(outstanding) + 0.0005:
		return "المبلغ الموعود أكبر من المتبقي على الفاتورة"
	return None


def build_summary(overdue, promises_due, followed_up):
	"""يصوغ الملخص اليومي. overdue: [{outstanding_amount, name}]، promises_due: عدد الوعود الحالّة، followed_up: مجموعة أسماء فواتير لها متابعة.
	يُرجع (العنوان, النص) أو None إن لم يكن هناك ما يُنبَّه به."""
	if not overdue and not promises_due:
		return None
	total = sum(flt(r["outstanding_amount"]) for r in overdue)
	no_follow = sum(1 for r in overdue if r["name"] not in followed_up)
	parts = []
	if overdue:
		parts.append(_("{0} فاتورة متأخرة بإجمالي {1} (منها {2} بلا أي متابعة)").format(len(overdue), "%.3f" % total, no_follow))
	if promises_due:
		parts.append(_("{0} وعد سداد حلّ موعده ولم تُسدَّد فاتورته").format(promises_due))
	return _("تحصيل الديون: ") + _("، ").join(parts), _("افتح تقرير «أعمار الديون» لتفاصيل الفواتير وسجّل متابعة لكل منها.")


def send_overdue_reminders():
	"""مهمة يومية: ملخص واحد للمحاسب ومدير المالية بالفواتير المتأخرة ووعود السداد الحالّة (لا رسالة لكل فاتورة)."""
	enabled = get_settings().get("notify_overdue_receivables")
	if enabled is not None and not cint(enabled):  # حقل جديد لم يُحفظ بعد في الإعدادات القائمة = مفعَّل (افتراضه 1)
		return
	today = nowdate()
	cutoff = add_days(today, -cint(get_settings().overdue_grace_days))
	overdue = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "outstanding_amount": [">", 0], "due_date": ["<", cutoff]},
		fields=["name", "outstanding_amount"])
	latest = {}
	for f in frappe.get_all("Collection Followup", fields=["sales_invoice", "promised_date"], order_by="contact_date asc, creation asc"):
		latest[f.sales_invoice] = f.promised_date  # آخر متابعة لكل فاتورة تكسب
	promised = [inv for inv, d in latest.items() if d and getdate(d) <= getdate(today)]
	promises_due = 0
	if promised:
		promises_due = frappe.db.count("Sales Invoice", {"name": ["in", promised], "docstatus": 1, "outstanding_amount": [">", 0]})
	summary = build_summary(overdue, promises_due, set(latest))
	if summary:
		notify_roles(REMINDER_ROLES, summary[0], summary[1], "Report", "Receivables Aging")
