# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

from zimam.utils import get_settings


class InstitutionEvent(Document):
	def validate(self):
		if not self.company:
			self.company = get_settings().parent_company
		if self.end_datetime and get_datetime(self.end_datetime) < get_datetime(self.start_datetime):
			frappe.throw(_("نهاية الفعالية لا تسبق بدايتها"))
		self.registrations_count = len(self.registrations or [])
		self.attendees_count = sum(1 for r in self.registrations or [] if r.attended)
