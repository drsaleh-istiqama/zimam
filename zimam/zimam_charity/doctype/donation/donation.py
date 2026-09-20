# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""إيصال تبرع (كما في وقاف): مبلغ إجمالي يُخصَّص على فئات، تُقتطع رسوم إدارية بحسب الفئة، ويُرحَّل قيد يومية عند الاعتماد:
مدين حساب الصندوق بالإجمالي / دائن حساب إيراد كل فئة بالصافي / دائن حساب الرسوم الإدارية بالرسوم.
التصحيح بعد الترحيل = إلغاء + تعديل (amend) فيبقى الإيصال الأصلي في السجل ويُنشأ إيصال مصحَّح برقمه-1."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from zimam.utils import cancel_linked, hijri_str
from zimam.zimam_core.finance import fund_account, make_journal_entry
from zimam.zimam_charity.utils import (category_income_account, charity_company, fee_percent_for, get_charity_settings,
	update_donor_stats, update_project_totals)


class Donation(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("المبلغ يجب أن يكون أكبر من صفر"))
		if not self.company:
			self.company = charity_company()
		if not self.fund:
			self.fund = get_charity_settings().default_fund or frappe.db.get_single_value("Zimam Settings", "default_fund")
		if not self.donor_name and self.donor:
			self.donor_name = frappe.db.get_value("Donor", self.donor, "donor_name")
		if self.is_anonymous and not self.donor_name:
			self.donor_name = _("فاعل خير")
		if not self.donor_name:
			frappe.throw(_("اكتب اسم المتبرع أو اختر بطاقة متبرع"))
		if self.donation_date and not self.date_hijri:
			self.date_hijri = hijri_str(self.donation_date)
		if self.sponsorship and not self.donation_category:
			self.donation_category = frappe.db.get_value("Sponsorship", self.sponsorship, "donation_category") or get_charity_settings().sponsorship_category
		self.ensure_allocations()
		self.compute()

	def ensure_allocations(self):
		if not self.allocations:
			if not self.donation_category:
				frappe.throw(_("اختر الفئة أو أضف سطرًا واحدًا على الأقل في التخصيصات"))
			self.append("allocations", {"donation_category": self.donation_category, "project": self.project, "amount": flt(self.amount)})
		if not self.donation_category:
			self.donation_category = self.allocations[0].donation_category
		if not self.project and self.allocations[0].project:
			self.project = self.allocations[0].project
		for a in self.allocations:
			if frappe.db.get_value("Donation Category", a.donation_category, "is_group"):
				frappe.throw(_("الفئة {0} رئيسية — اختر فئة فرعية").format(a.donation_category))

	def compute(self):
		total_fee, total, settings = 0.0, 0.0, get_charity_settings()
		for a in self.allocations:
			pct = fee_percent_for(a.donation_category, a.admin_fee_percent)
			a.admin_fee_percent = pct
			a.admin_fee_amount = flt(flt(a.amount) * pct / 100.0, 3)
			a.net_amount = flt(a.amount) - a.admin_fee_amount
			if not a.income_account:
				a.income_account = category_income_account(a.donation_category, self.company)
			if not a.cost_center:
				a.cost_center = frappe.db.get_value("Donation Category", a.donation_category, "cost_center") or settings.default_cost_center
			total_fee += a.admin_fee_amount
			total += flt(a.amount)
		if abs(total - flt(self.amount)) > 0.0005:
			frappe.throw(_("مجموع التخصيصات ({0}) لا يساوي المبلغ الإجمالي ({1})").format(total, self.amount))
		self.admin_fee_amount = flt(total_fee, 3)
		self.net_amount = flt(self.amount) - self.admin_fee_amount

	def on_submit(self):
		self.db_set({"journal_entry": self.make_journal_entry(), "status": "مُرحَّل"})
		self.after_change()
		self.settle_sponsorship()
		if self.member:
			from zimam.zimam_charity.doctype.member.member import on_membership_fee_paid
			on_membership_fee_paid(self)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Journal Entry")
		cancel_linked("Journal Entry", self.journal_entry)
		self.db_set({"status": "ملغى"})
		for due in frappe.get_all("Sponsorship Due", filters={"donation": self.name}, pluck="name"):
			frappe.db.set_value("Sponsorship Due", due, {"status": "مستحق", "donation": None, "paid_on": None})
		self.after_change()

	def after_change(self):
		update_donor_stats(self.donor)
		projects = {self.project} | {a.project for a in self.allocations}
		for p in projects:
			update_project_totals(p)
		if self.sponsorship:
			frappe.get_doc("Sponsorship", self.sponsorship).refresh_totals()

	def make_journal_entry(self):
		debit_account, fund_company = fund_account(self.fund)
		if fund_company != self.company:
			frappe.throw(_("الصندوق {0} يتبع شركة أخرى ({1})").format(self.fund, fund_company))
		settings = get_charity_settings()
		rows = [{"account": debit_account, "debit": flt(self.amount), "cost_center": settings.default_cost_center}]
		for a in self.allocations:
			if not a.income_account:
				frappe.throw(_("حدد حساب الإيراد للفئة {0} (في الفئة أو في إعدادات الحزمة الخيرية)").format(a.donation_category))
			rows.append({"account": a.income_account, "credit": flt(a.net_amount), "cost_center": a.cost_center, "project": a.project})
		if flt(self.admin_fee_amount) > 0:
			if not settings.admin_fee_income_account:
				frappe.throw(_("حدد حساب إيرادات الرسوم الإدارية في إعدادات الحزمة الخيرية"))
			rows.append({"account": settings.admin_fee_income_account, "credit": flt(self.admin_fee_amount), "cost_center": settings.default_cost_center})
		remark = _("إيصال تبرع {0} — {1} — {2}").format(self.name, self.donor_name, self.purpose or self.donation_category)
		return make_journal_entry(self.company, self.donation_date, rows, remark, self.reference_no, self.reference_date,
			voucher_type="Bank Entry" if self.channel in ("بنك", "بطاقة", "ثواني", "OMPay", "الموقع الإلكتروني") else "Cash Entry" if self.channel == "نقد" else "Journal Entry")

	def settle_sponsorship(self):
		"""سداد كفالة: يُسدَّد أقدم الاستحقاقات غير المسددة حتى يستنفد المبلغ (لا يُنشأ استحقاق مسبق)."""
		if not self.sponsorship:
			return
		remaining = flt(self.amount)
		dues = frappe.get_all("Sponsorship Due", filters={"sponsorship": self.sponsorship, "status": "مستحق"},
			fields=["name", "amount"], order_by="due_date asc")
		for d in dues:
			if remaining < flt(d.amount) - 0.0005:
				break
			frappe.db.set_value("Sponsorship Due", d.name, {"status": "مدفوع", "donation": self.name, "paid_on": self.donation_date or nowdate()})
			remaining -= flt(d.amount)
		frappe.get_doc("Sponsorship", self.sponsorship).refresh_totals()

	@frappe.whitelist()
	def recalculate(self):
		"""إعادة حساب الرسوم والصافي في النموذج بلا حفظ."""
		self.ensure_allocations()
		self.compute()
		return {"admin_fee_amount": self.admin_fee_amount, "net_amount": self.net_amount}


@frappe.whitelist()
def get_defaults():
	s = get_charity_settings()
	return {"company": s.company or frappe.db.get_single_value("Zimam Settings", "parent_company"), "fund": s.default_fund,
		"date_hijri": hijri_str(getdate(nowdate()))}
