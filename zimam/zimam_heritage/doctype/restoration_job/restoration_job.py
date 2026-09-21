# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
"""طلب ترميم في ذراع الترميم (شركة تابعة): داخلي لمقتنى من خزائن المؤسسة أو لعميل خارجي.
الفوترة: فاتورة عميل خارجي · فوترة بينية للمؤسسة عبر العميل الداخلي · أو بلا فوترة (كلفة داخلية)."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt, nowdate

from zimam.utils import (cancel_linked, compute_amounts, compute_labor, get_heritage_settings, get_settings,
	make_material_issue, make_service_invoice)


class RestorationJob(Document):
	def validate(self):
		hs = get_heritage_settings()
		if not self.company:
			self.company = hs.restoration_company or get_settings().parent_company
		if self.source_type == "عميل خارجي" and not self.customer:
			frappe.throw(_("حدد العميل الخارجي"))
		if self.source_type == "داخلي - خزانة" and not self.cabinet_item:
			frappe.throw(_("حدد المقتنى"))
		if self.source_type == "داخلي - خزانة" and self.billing_type == "فاتورة عميل":
			self.billing_type = "فوترة بينية للمؤسسة"
		_hours, self.total_labor = compute_labor(self.treatments, flt(hs.default_labor_rate))
		self.total_materials = compute_amounts(self.materials)
		self.total_cost = flt(flt(self.total_labor) + flt(self.total_materials), 3)
		if self.billing_type != "بلا فوترة" and not self.price:
			self.price = self.total_cost
		if not self.materials_warehouse and self.materials:
			self.materials_warehouse = hs.restoration_materials_warehouse
		self.set_warranty()
		self.sync_item_status()

	def on_update_after_submit(self):
		self.set_warranty()
		self.sync_item_status()

	def set_warranty(self):
		"""الضمان يبدأ من تاريخ التسليم؛ يُعبَّأ تاريخ التسليم تلقائيًا عند الحالة «مُسلَّم»."""
		if self.status == "مُسلَّم" and not self.delivered_on:
			self.delivered_on = nowdate()
		if self.delivered_on and self.warranty_months:
			self.warranty_until = add_months(self.delivered_on, int(self.warranty_months))
		elif not self.delivered_on:
			self.warranty_until = None

	def on_submit(self):
		se = make_material_issue(self.company, self.materials_warehouse, self.materials, None, _("مواد ترميم {0}").format(self.name))
		if se:
			self.db_set("stock_entry", se)
		if self.billing_type != "بلا فوترة":
			self.db_set("sales_invoice", self.make_invoice())

	def on_cancel(self):
		cancel_linked("Stock Entry", self.stock_entry)
		if self.sales_invoice:
			si = frappe.get_doc("Sales Invoice", self.sales_invoice)
			if si.docstatus == 1:
				frappe.throw(_("ألغِ الفاتورة {0} أولًا").format(self.sales_invoice))
			if si.docstatus == 0:
				si.delete()
			self.db_set("sales_invoice", None)
		self.db_set("status", "ملغى")

	def make_invoice(self):
		if self.billing_type == "فوترة بينية للمؤسسة":
			customer = get_settings().internal_customer
			if not customer:
				frappe.throw(_("حدد «العميل الداخلي الذي يمثّل المؤسسة» في إعدادات زِمام"))
		else:
			customer = self.customer
		return make_service_invoice(company=self.company, customer=customer, item_code=get_heritage_settings().restoration_service_item,
			rate=self.price, description=_("ترميم: {0}").format(self.object_description), ref_doctype=self.doctype, ref_name=self.name)

	def sync_item_status(self):
		if self.source_type != "داخلي - خزانة" or not self.cabinet_item:
			return
		if self.status in ("مكتمل", "مُسلَّم"):
			status = "مُرمَّم"
		elif self.status == "ملغى":
			status = "بانتظار الترميم"
		else:
			status = "قيد الترميم"
		frappe.db.set_value("Cabinet Item", self.cabinet_item, {"restoration_status": status, "needs_restoration": 0 if status == "مُرمَّم" else 1}, update_modified=False)
