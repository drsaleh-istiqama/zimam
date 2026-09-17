# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""أمر طباعة في ذراع المطبعة: مواصفات + بنود تكلفة + هامش ⟵ سعر، ثم عرض سعر ⟵ أمر بيع ⟵ فاتورة عبر مستندات ERPNext القياسية."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from zimam.utils import compute_amounts, get_settings, make_service_invoice


class PrintJob(Document):
	def validate(self):
		settings = get_settings()
		if not self.company:
			self.company = settings.press_company or settings.parent_company
		if flt(self.quantity) <= 0:
			frappe.throw(_("الكمية يجب أن تكون أكبر من صفر"))
		self.total_cost = compute_amounts(self.cost_items)
		if not self.quoted_price:
			self.quoted_price = flt(self.total_cost) * (1 + flt(self.margin_percent) / 100.0)
		self.unit_price = flt(self.quoted_price) / flt(self.quantity) if self.quantity else 0
		if self.docstatus == 0 and self.status == "طلب" and self.quoted_price:
			self.status = "مُسعَّر"

	def on_cancel(self):
		self.db_set("status", "ملغى")

	@frappe.whitelist()
	def make_quotation(self):
		self.check_permission("write")
		if self.quotation:
			frappe.throw(_("يوجد عرض سعر مرتبط: {0}").format(self.quotation))
		item = get_settings().print_service_item
		if not item:
			frappe.throw(_("صنف خدمة الطباعة غير محدد في إعدادات زِمام"))
		q = frappe.new_doc("Quotation")
		q.company = self.company
		q.quotation_to = "Customer"
		q.party_name = self.customer
		q.zimam_print_job = self.name
		q.append("items", {"item_code": item, "qty": 1, "rate": flt(self.quoted_price), "description": self.item_description()})
		q.set_missing_values()
		q.insert(ignore_permissions=True)
		self.db_set("quotation", q.name)
		return q.name

	@frappe.whitelist()
	def make_sales_invoice(self):
		self.check_permission("write")
		if self.sales_invoice:
			frappe.throw(_("توجد فاتورة مرتبطة: {0}").format(self.sales_invoice))
		name = make_service_invoice(company=self.company, customer=self.customer, item_code=get_settings().print_service_item,
			rate=flt(self.quoted_price), description=self.item_description(), ref_doctype=self.doctype, ref_name=self.name)
		self.db_set("sales_invoice", name)
		return name

	def item_description(self):
		parts = [self.job_title, self.product_type, _("الكمية: {0}").format(self.quantity)]
		if self.size:
			parts.append(_("المقاس: {0}").format(self.size))
		if self.pages:
			parts.append(_("الصفحات: {0}").format(self.pages))
		if self.paper:
			parts.append(_("الورق: {0}").format(self.paper))
		parts.append(_("الألوان: {0}").format(self.color))
		if self.binding and self.binding != "بلا":
			parts.append(_("التجليد: {0}").format(self.binding))
		return " — ".join(str(p) for p in parts if p)
