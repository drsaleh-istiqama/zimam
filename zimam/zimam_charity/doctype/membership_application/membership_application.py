# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class MembershipApplication(Document):
	@frappe.whitelist()
	def accept(self):
		frappe.has_permission("Member", "create", throw=True)
		if self.member:
			return self.member
		member = frappe.get_doc({"doctype": "Member", "member_name": self.applicant_name, "membership_type": self.membership_type,
			"phone": self.phone, "email": self.email, "national_id": self.national_id, "join_date": nowdate(), "status": "نشط"}).insert(ignore_permissions=True)
		self.db_set({"status": "مقبول", "member": member.name, "reviewed_by": frappe.session.user, "reviewed_on": nowdate()})
		return member.name

	@frappe.whitelist()
	def reject(self, note=None):
		self.db_set({"status": "مرفوض", "review_note": note or self.review_note, "reviewed_by": frappe.session.user, "reviewed_on": nowdate()})
		return self.status
