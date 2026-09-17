# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from zimam.utils import get_settings


class WaqfCampaign(Document):
	def validate(self):
		if not self.company:
			self.company = get_settings().parent_company
		if self.start_date and self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("تاريخ النهاية لا يسبق تاريخ البداية"))
		if self.income_account and frappe.db.get_value("Account", self.income_account, "company") != self.company:
			frappe.throw(_("حساب الإيراد لا يتبع الشركة {0}").format(self.company))
		target = flt(self.target_amount)
		self.progress = min(flt(self.raised_amount) / target * 100.0, 100) if target else 0
