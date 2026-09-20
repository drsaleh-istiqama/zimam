# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""سند صرف بسلسلة اعتماد (Workflow «سند صرف — سلسلة الاعتماد»): المحاسب يسجّل ← مدير المالية ← الرئيس التنفيذي
(إن بلغ المبلغ الحد) ← أمين الصندوق يسجّل الدفع فيُرحَّل القيد: مدين حساب المصروف / دائن حساب الصندوق.
الاعتماد النهائي = الترحيل (docstatus 1)؛ الدفع = تحديث بعد الترحيل؛ الرفض يعيد السند مسودةً قابلة للتصحيح."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate

from zimam.utils import cancel_linked, hijri_str
from zimam.zimam_charity.utils import charity_company, fund_account, get_charity_settings, make_journal_entry, update_project_totals

# الإشعارات وصندوق «الإجراءات» لأصحاب المرحلة التالية يتولاهما Frappe نفسه (Workflow Action + بريد) حين يكون send_email_alert مفعَّلًا في سير العمل


class PaymentVoucher(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("المبلغ يجب أن يكون أكبر من صفر"))
		if not self.company:
			self.company = charity_company()
		if self.voucher_date and not self.date_hijri:
			self.date_hijri = hijri_str(self.voucher_date)
		if self.beneficiary_type == "موظف" and self.employee and not self.beneficiary_name:
			self.beneficiary_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		if not self.beneficiary_name:
			frappe.throw(_("اكتب اسم المستفيد"))
		if not self.expense_account:
			self.expense_account = frappe.db.get_value("Expense Classification", self.expense_classification, "expense_account")
		if not self.cost_center:
			self.cost_center = frappe.db.get_value("Expense Classification", self.expense_classification, "cost_center") or get_charity_settings().default_cost_center
		threshold = flt(get_charity_settings().ceo_approval_threshold)
		self.requires_ceo_approval = 1 if (threshold <= 0 or flt(self.amount) >= threshold) else 0
		if not self.workflow_state:
			self.workflow_state = "مسودة"
		total = sum(flt(a.amount) for a in self.allocations)
		if self.allocations and abs(total - flt(self.amount)) > 0.0005:
			frappe.throw(_("مجموع الأوعية المموِّلة ({0}) لا يساوي مبلغ السند ({1})").format(total, self.amount))
		self.stamp_stage()

	def stamp_stage(self):
		"""توقيع كل مرحلة باسم من نفّذها ووقتها (يُقارن بالحالة المحفوظة)."""
		before = self.get_doc_before_save() if not self.is_new() else None
		old = before.workflow_state if before else None
		if old == self.workflow_state:
			return
		user, now = frappe.session.user, now_datetime()
		if self.workflow_state == "بانتظار اعتماد الرئيس التنفيذي" or (self.workflow_state == "جاهز للدفع" and old == "مراجعة المالية"):
			self.finance_reviewed_by, self.finance_reviewed_on = user, now
		if self.workflow_state == "جاهز للدفع":
			self.approved_by, self.approved_on = user, now
		if self.workflow_state == "مدفوع":
			self.paid_by = user
			if not self.paid_on:
				self.paid_on = nowdate()
		if self.workflow_state in ("مسودة", "مراجعة المالية") and old in ("مرفوض", None):
			self.rejection_reason = None if old == "مرفوض" else self.rejection_reason
		self.flags.stage_changed = (old, self.workflow_state)

	def on_update_after_submit(self):
		if self.workflow_state == "مدفوع" and not self.journal_entry:
			self.db_set("journal_entry", self.make_journal_entry())
			update_project_totals(self.project)

	def on_submit(self):
		# الترحيل لا يقع إلا عبر انتقال «اعتماد» في سير العمل (docstatus 1 = جاهز للدفع)
		if self.workflow_state not in ("جاهز للدفع", "مدفوع"):
			self.db_set("workflow_state", "جاهز للدفع")

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Journal Entry")
		cancel_linked("Journal Entry", self.journal_entry)
		self.db_set("workflow_state", "ملغى")
		update_project_totals(self.project)

	def make_journal_entry(self):
		credit_account, fund_company = fund_account(self.fund)
		if fund_company != self.company:
			frappe.throw(_("الصندوق {0} يتبع شركة أخرى ({1})").format(self.fund, fund_company))
		if not self.expense_account:
			frappe.throw(_("حدد حساب المصروف (في التصنيف {0} أو في السند)").format(self.expense_classification))
		rows = []
		if self.allocations:
			for a in self.allocations:
				rows.append({"account": self.expense_account, "debit": flt(a.amount), "cost_center": a.cost_center or self.cost_center, "project": a.project or self.project})
		else:
			rows.append({"account": self.expense_account, "debit": flt(self.amount), "cost_center": self.cost_center, "project": self.project})
		rows.append({"account": credit_account, "credit": flt(self.amount), "cost_center": self.cost_center})
		remark = _("سند صرف {0} — {1} — {2}").format(self.name, self.beneficiary_name, self.description)
		return make_journal_entry(self.company, self.paid_on or nowdate(), rows, remark, self.cheque_no or self.payment_reference, self.cheque_date,
			voucher_type="Cash Entry" if self.payment_method == "نقد" else "Bank Entry")


@frappe.whitelist()
def get_defaults():
	s = get_charity_settings()
	return {"company": s.company or frappe.db.get_single_value("Zimam Settings", "parent_company"), "fund": s.default_fund,
		"threshold": flt(s.ceo_approval_threshold)}
