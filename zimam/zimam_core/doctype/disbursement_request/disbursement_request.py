# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""طلب صرف من موظف (كما في «طلبات الدفع» في وقاف): يرفعه أي موظف، ويرقّمه المحاسب ويحوّله إلى سند صرف يدخل سلسلة الاعتماد،
أو يعيده إلى مقدمه بملاحظة، أو يرفضه."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from zimam.utils import notify_roles


class DisbursementRequest(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("المبلغ يجب أن يكون أكبر من صفر"))
		if not self.requester_user:
			self.requester_user = frappe.session.user
		if not self.requested_by:
			emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
			if emp:
				self.requested_by = emp
		if self.is_new() and self.status not in ("للمراجعة",):
			self.status = "للمراجعة"

	def after_insert(self):
		notify_roles(["محاسب مالي"], _("طلب صرف جديد {0}: {1}").format(self.name, self.title),
			_("المبلغ {0} · المستلم {1} · الأولوية {2}").format(self.amount, self.recipient_name, self.priority), self.doctype, self.name)

	def _stamp(self, status, note=None):
		self.db_set({"status": status, "reviewed_by": frappe.session.user, "reviewed_on": now_datetime(), "review_note": note or self.review_note})
		if self.requester_user and self.requester_user != frappe.session.user:
			frappe.get_doc({"doctype": "Notification Log", "for_user": self.requester_user, "type": "Alert",
				"subject": _("طلب الصرف {0}: {1}").format(self.name, status), "email_content": note or "",
				"document_type": self.doctype, "document_name": self.name}).insert(ignore_permissions=True)

	@frappe.whitelist()
	def make_voucher(self, expense_classification=None, fund=None, payment_method="تحويل بنكي"):
		"""تحويل الطلب إلى سند صرف (مسودة) — المحاسب يكمل الترميز ثم يحيله لمراجعة المالية."""
		frappe.has_permission("Payment Voucher", "create", throw=True)
		if self.payment_voucher and frappe.db.exists("Payment Voucher", self.payment_voucher):
			return self.payment_voucher
		pv = frappe.new_doc("Payment Voucher")
		fund = fund or frappe.db.get_single_value("Zimam Settings", "default_fund")
		# شركة السند = شركة الصندوق (لا الشركة الافتراضية للمستخدم — كانت تعطي «zimam (Demo)» فيفشل الدفع، فحص 2026-09-21)
		company = (frappe.db.get_value("Treasury Fund", fund, "company") if fund else None) or frappe.db.get_single_value("Zimam Settings", "parent_company")
		pv.update({
			"company": company,
			"beneficiary_type": "مستفيد", "beneficiary_name": self.recipient_name, "amount": flt(self.amount),
			"expense_classification": expense_classification, "project": self.project, "fund": fund, "payment_method": payment_method,
			"description": _("{0} — طلب صرف {1}").format(self.title, self.name), "disbursement_request": self.name,
			"due_date": self.needed_by, "supporting_document": self.attachment,
		})
		pv.flags.ignore_mandatory = not (expense_classification and fund)
		pv.insert(ignore_permissions=True)
		self.db_set({"payment_voucher": pv.name})
		self._stamp("محوّلة", _("حُوِّل إلى سند الصرف {0}").format(pv.name))
		return pv.name

	@frappe.whitelist()
	def return_to_requester(self, note):
		if not note:
			frappe.throw(_("اكتب ملاحظة الإعادة"))
		self._stamp("مُعادة", note)
		return self.status

	@frappe.whitelist()
	def reject(self, note=None):
		self._stamp("مرفوضة", note)
		return self.status

	@frappe.whitelist()
	def resubmit(self):
		if self.status != "مُعادة":
			frappe.throw(_("لا يُعاد تقديم إلا الطلبات المُعادة"))
		self.db_set({"status": "للمراجعة"})
		return self.status
