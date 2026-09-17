# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document

from zimam.utils import get_heritage_settings


class CabinetItem(Document):
	def validate(self):
		if self.needs_restoration and self.restoration_status == "لا يحتاج":
			self.restoration_status = "بانتظار الترميم"
		if not self.needs_restoration and self.restoration_status == "بانتظار الترميم":
			self.restoration_status = "لا يحتاج"
		if self.is_sellable_digital and not self.digital_price:
			frappe.throw(_("حدد سعر النسخة الرقمية"))

	def on_update(self):
		self.update_cabinet_count()
		if self.is_sellable_digital and not self.digital_item:
			self.make_store_item()

	def on_trash(self):
		self.update_cabinet_count(exclude_self=True)

	def update_cabinet_count(self, exclude_self=False):
		filters = {"cabinet": self.cabinet}
		if exclude_self:
			filters["name"] = ["!=", self.name]
		frappe.db.set_value("Cabinet", self.cabinet, "item_count", frappe.db.count("Cabinet Item", filters), update_modified=False)

	def make_store_item(self):
		"""صنف متجر (غير مخزني) للنسخة الرقمية، ليُباع عبر المتجر أو الفواتير."""
		template = get_heritage_settings().digital_copy_item
		item_group = frappe.db.get_value("Item", template, "item_group") if template else None
		if not item_group:
			frappe.msgprint(_("لم يُنشأ صنف المتجر: صنف «النسخة الرقمية» غير محدد في إعدادات الحزمة التراثية"), indicator="orange", alert=True)
			return
		code = f"DC-{self.name}"
		if not frappe.db.exists("Item", code):
			frappe.get_doc({
				"doctype": "Item", "item_code": code, "item_name": _("نسخة رقمية: {0}").format(self.title)[:140],
				"description": self.summary or self.title, "item_group": item_group, "stock_uom": "Nos", "is_stock_item": 0,
				"is_sales_item": 1, "is_purchase_item": 0, "standard_rate": self.digital_price, "image": self.cover_image,
				"zimam_source_doctype": "Cabinet Item", "zimam_source_name": self.name,
			}).insert(ignore_permissions=True)
		self.db_set("digital_item", code, update_modified=False)
