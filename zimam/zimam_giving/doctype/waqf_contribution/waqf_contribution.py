# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""مساهمة وقفية: المبلغ من الأسهم أو حرّ؛ عند «مدفوع» يُنشأ قيد يومية (مدين حساب طريقة الدفع / دائن إيراد الحملة
أو حساب إيرادات الوقف) وتصدر الشهادة بالتاريخ الهجري أولًا."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from zimam.utils import cancel_linked, get_settings, hijri_str


class WaqfContribution(Document):
	def validate(self):
		if self.share_type:
			self.share_amount = flt(frappe.db.get_value("Waqf Share Type", self.share_type, "amount"))
			if not self.shares or self.shares < 1:
				self.shares = 1
			self.amount = flt(flt(self.share_amount) * int(self.shares), 3)
		if flt(self.amount) <= 0:
			frappe.throw(_("المبلغ يجب أن يكون أكبر من صفر"))
		if not self.company:
			self.company = frappe.db.get_value("Waqf Campaign", self.campaign, "company") or get_settings().parent_company
		if self.payment_status == "مدفوع":
			if not self.mode_of_payment:
				frappe.throw(_("حدد طريقة الدفع للمساهمة المدفوعة"))
			if not self.paid_on:
				self.paid_on = nowdate()

	def on_submit(self):
		if self.payment_status == "مدفوع":
			self.post_payment()
		self.update_campaign()

	def on_update_after_submit(self):
		if self.payment_status == "مدفوع" and not self.journal_entry:
			if not self.mode_of_payment:
				frappe.throw(_("حدد طريقة الدفع"))
			if not self.paid_on:
				self.db_set("paid_on", nowdate())
			self.post_payment()
		self.update_campaign()

	def on_cancel(self):
		cancel_linked("Journal Entry", self.journal_entry)
		self.db_set({"payment_status": "ملغى", "certificate_issued": 0})
		self.update_campaign()

	def post_payment(self):
		je = self.make_journal_entry()
		cert_date = self.paid_on or nowdate()
		self.db_set({"journal_entry": je, "certificate_issued": 1, "certificate_date": cert_date, "certificate_date_hijri": hijri_str(cert_date)})

	def make_journal_entry(self):
		settings = get_settings()
		campaign = frappe.get_doc("Waqf Campaign", self.campaign)
		income_account = campaign.income_account or settings.waqf_income_account
		if not income_account:
			frappe.throw(_("حدد حساب إيراد الحملة أو حساب إيرادات الوقف في إعدادات زِمام"))
		cost_center = campaign.cost_center or settings.waqf_cost_center
		debit_account = frappe.db.get_value("Mode of Payment Account", {"parent": self.mode_of_payment, "company": self.company}, "default_account") \
			or frappe.db.get_value("Company", self.company, "default_cash_account")
		if not debit_account:
			frappe.throw(_("لا حساب افتراضي لطريقة الدفع {0} في الشركة {1}").format(self.mode_of_payment, self.company))
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.posting_date = self.paid_on or nowdate()
		je.user_remark = _("مساهمة وقفية {0} — {1} — حملة {2}").format(self.name, self.contributor_name, campaign.campaign_name)
		je.cheque_no = self.payment_reference
		je.cheque_date = self.paid_on if self.payment_reference else None
		je.append("accounts", {"account": debit_account, "debit_in_account_currency": flt(self.amount), "cost_center": cost_center})
		je.append("accounts", {"account": income_account, "credit_in_account_currency": flt(self.amount), "cost_center": cost_center})
		je.insert(ignore_permissions=True)
		je.submit()
		return je.name

	def update_campaign(self):
		raised = frappe.db.sql("""select coalesce(sum(amount),0) from `tabWaqf Contribution`
			where campaign=%s and docstatus=1 and payment_status='مدفوع'""", self.campaign)[0][0]
		target = flt(frappe.db.get_value("Waqf Campaign", self.campaign, "target_amount"))
		progress = (flt(raised) / target * 100.0) if target else 0
		frappe.db.set_value("Waqf Campaign", self.campaign, {"raised_amount": raised, "progress": min(progress, 100)}, update_modified=False)
