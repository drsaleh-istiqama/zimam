# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from zimam.utils import get_settings

STATUS_MAP = {"مجدول": "قيد الرقمنة", "قيد التصوير": "قيد الرقمنة", "قيد المعالجة": "قيد الرقمنة", "مكتمل": "مرقمن", "ملغى": "غير مرقمن"}


class DigitizationJob(Document):
	def validate(self):
		if not self.company:
			self.company = get_settings().parent_company
		if self.started_on and self.completed_on and getdate(self.completed_on) < getdate(self.started_on):
			frappe.throw(_("تاريخ الاكتمال لا يسبق تاريخ البدء"))
		if self.status == "مكتمل" and self.qc_status == "يحتاج إعادة":
			frappe.throw(_("لا يكتمل أمر الرقمنة وفحص الجودة «يحتاج إعادة»"))

	def on_update(self):
		frappe.db.set_value("Cabinet Item", self.cabinet_item, "digitization_status", STATUS_MAP.get(self.status, "قيد الرقمنة"), update_modified=False)
		if self.status == "مكتمل" and self.storage_path:
			item = frappe.get_doc("Cabinet Item", self.cabinet_item)
			if not item.notes or self.storage_path not in item.notes:
				item.db_set("notes", ((item.notes or "") + "\n" + _("مسار النسخة الرقمية: {0}").format(self.storage_path)).strip(), update_modified=False)
