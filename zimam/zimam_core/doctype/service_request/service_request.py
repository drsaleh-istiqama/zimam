# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""طلب خدمة عام: نوع الخدمة من كتالوج «Service Type» (الرسوم والصنف والشركة)، ومرجع ديناميكي إلى أي مستند
(مقتنى في الحزمة التراثية، مقرر في التعليمية…) دون أن تربط النواة بحزمة بعينها."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from zimam.utils import ensure_customer_for, get_settings, make_service_invoice


class ServiceRequest(Document):
	def validate(self):
		st = frappe.get_cached_doc("Service Type", self.service_type)
		if st.is_free:
			self.is_free, self.fees = 1, 0
		elif not self.fees and self.is_new():
			self.fees = flt(st.default_fees)
		if self.status == "مرفوض" and not self.rejection_reason:
			frappe.throw(_("اذكر سبب الرفض"))
		if self.status == "مكتمل" and not self.completed_on:
			self.completed_on = nowdate()
		if self.status == "مكتمل" and not self.is_free and flt(self.fees) > 0 and not self.sales_invoice:
			frappe.msgprint(_("الطلب مكتمل برسوم ولم تُنشأ فاتورة بعد — استخدم زر «فاتورة»"), indicator="orange", alert=True)

	@frappe.whitelist()
	def make_invoice(self):
		self.check_permission("write")
		if self.sales_invoice:
			frappe.throw(_("توجد فاتورة مرتبطة: {0}").format(self.sales_invoice))
		if self.is_free or flt(self.fees) <= 0:
			frappe.throw(_("الخدمة مجانية أو بلا رسوم"))
		st = frappe.get_cached_doc("Service Type", self.service_type)
		settings = get_settings()
		customer = self.customer or ensure_customer_for(self.requester_name, self.email, self.phone)
		if not self.customer:
			self.db_set("customer", customer)
		name = make_service_invoice(
			company=st.company or settings.service_company or settings.parent_company,
			customer=customer,
			item_code=st.service_item or settings.default_service_item,
			rate=flt(self.fees),
			description=_("{0} — {1}").format(self.service_type, self.reference_note or self.reference_name or ""),
			ref_doctype=self.doctype,
			ref_name=self.name,
		)
		self.db_set("sales_invoice", name)
		return name
