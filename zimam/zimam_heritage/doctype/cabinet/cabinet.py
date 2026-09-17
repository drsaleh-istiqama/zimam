# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document


class Cabinet(Document):
	def validate(self):
		if self.status == "مُعادة" and self.ownership_type == "إهداء":
			frappe.throw(_("الخزانة المُهداة ملك للمؤسسة ولا تُعاد؛ غيّر نوع الملكية أولًا إن كان ذلك خطأ"))

	def on_trash(self):
		if frappe.db.count("Cabinet Item", {"cabinet": self.name}):
			frappe.throw(_("احذف مقتنيات الخزانة أولًا"))
