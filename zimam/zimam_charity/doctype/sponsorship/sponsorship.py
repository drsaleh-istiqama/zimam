# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""كفالة: التزام دوري من كافل لمكفول. الاستحقاق يُقيَّد يوم حلوله لا قبله (مهمة يومية)، و«متأخر» يُشتق من التاريخ ولا يُخزَّن،
والسداد يأتي من إيصال تبرع يحمل رقم الكفالة فيُسدِّد أقدم الاستحقاقات."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, flt, getdate, nowdate

STEP_MONTHS = {"شهري": 1, "ربع سنوي": 3, "نصف سنوي": 6, "سنوي": 12}


class Sponsorship(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("قيمة القسط يجب أن تكون أكبر من صفر"))
		if not self.donation_category:
			self.donation_category = frappe.db.get_single_value("Charity Settings", "sponsorship_category")
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("نهاية الكفالة قبل بدايتها"))
		if not self.next_due_date:
			self.next_due_date = self.start_date
		if self.status == "نشطة" and self.end_date and getdate(self.end_date) < getdate(nowdate()):
			self.status = "منتهية"

	def refresh_totals(self):
		paid = flt(frappe.db.sql("select coalesce(sum(amount),0) from `tabSponsorship Due` where sponsorship=%s and status='مدفوع'", self.name)[0][0])
		unpaid = flt(frappe.db.sql("select coalesce(sum(amount),0) from `tabSponsorship Due` where sponsorship=%s and status='مستحق'", self.name)[0][0])
		frappe.db.set_value("Sponsorship", self.name, {"paid_total": paid, "due_unpaid": unpaid}, update_modified=False)

	def create_due(self, due_date):
		if frappe.db.exists("Sponsorship Due", {"sponsorship": self.name, "due_date": due_date}):
			return None
		due = frappe.get_doc({"doctype": "Sponsorship Due", "sponsorship": self.name, "sponsor": self.sponsor, "sponsor_name": self.sponsor_name,
			"beneficiary_name": self.beneficiary_name, "due_date": due_date, "amount": flt(self.amount), "status": "مستحق"})
		due.insert(ignore_permissions=True)
		return due.name


def generate_dues():
	"""مهمة يومية: لكل كفالة نشطة يُنشأ استحقاق حين يحلّ موعده (أو قبله بأيام من الإعدادات)، ويتقدم الموعد التالي."""
	ahead = int(frappe.db.get_single_value("Charity Settings", "dues_generation_days_ahead") or 0)
	horizon = add_days(nowdate(), ahead)
	for name in frappe.get_all("Sponsorship", filters={"status": "نشطة"}, pluck="name"):
		sp = frappe.get_doc("Sponsorship", name)
		step = STEP_MONTHS.get(sp.frequency, 1)
		nxt = getdate(sp.next_due_date or sp.start_date)
		created = 0
		while nxt <= getdate(horizon) and created < 36:
			if sp.end_date and nxt > getdate(sp.end_date):
				frappe.db.set_value("Sponsorship", name, "status", "منتهية", update_modified=False)
				break
			sp.create_due(nxt)
			created += 1
			nxt = getdate(add_months(nxt, step))
		if created:
			frappe.db.set_value("Sponsorship", name, "next_due_date", nxt, update_modified=False)
			sp.refresh_totals()
	frappe.db.commit()


@frappe.whitelist()
def generate_dues_now():
	frappe.only_for(["System Manager", "محاسب مالي", "مدير مالي"])
	generate_dues()
	return True
