# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
"""أمر معالجة خزانة: المراحل بساعات عمل ومواد مستهلكة ⟵ التكلفة الفعلية لكل خزانة (خام ⟵ منتج محاسبيًا)."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from zimam.utils import cancel_linked, compute_amounts, get_heritage_settings, make_material_issue

STAGE_TO_CABINET_STATUS = {"فرز": "قيد الفرز", "ترميم": "قيد المعالجة", "فهرسة": "قيد المعالجة", "رقمنة": "قيد المعالجة"}


class ProcessingOrder(Document):
	def validate(self):
		if not self.stages:
			frappe.throw(_("أضف مرحلة واحدة على الأقل"))
		hs = get_heritage_settings()
		if not self.labor_rate:
			self.labor_rate = flt(hs.default_labor_rate)
		self.labor_hours = sum(flt(s.hours) for s in self.stages)
		self.total_labor_cost = flt(self.labor_hours) * flt(self.labor_rate)
		self.total_material_cost = compute_amounts(self.materials)
		self.total_cost = flt(flt(self.total_labor_cost) + flt(self.total_material_cost), 3)
		if not self.materials_warehouse and self.materials:
			self.materials_warehouse = hs.restoration_materials_warehouse
		self.sync_status()

	def sync_status(self):
		if self.status == "ملغى":
			return
		statuses = [s.status for s in self.stages]
		if all(s == "مكتملة" for s in statuses):
			self.status = "مكتمل"
		elif any(s in ("جارية", "مكتملة") for s in statuses):
			self.status = "قيد التنفيذ"
		else:
			self.status = "مفتوح"

	def on_update_after_submit(self):
		self.validate()
		self.db_update()
		self.update_cabinet()

	def on_submit(self):
		se = make_material_issue(self.company, self.materials_warehouse, self.materials, self.cost_center, _("مواد معالجة الخزانة {0}").format(self.cabinet))
		if se:
			self.db_set("stock_entry", se)
		self.update_cabinet()

	def on_cancel(self):
		cancel_linked("Stock Entry", self.stock_entry)
		self.db_set("status", "ملغى")

	def update_cabinet(self):
		if self.status == "مكتمل":
			new_status = "مفهرسة"
		else:
			running = [s.stage for s in self.stages if s.status == "جارية"]
			new_status = STAGE_TO_CABINET_STATUS.get(running[0], "قيد المعالجة") if running else "قيد المعالجة"
		frappe.db.set_value("Cabinet", self.cabinet, "status", new_status, update_modified=False)
