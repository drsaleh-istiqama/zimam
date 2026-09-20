# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""فئات التبرع شجرةً (فئة رئيسية ⟵ فئات فرعية برموز مثل 06 ⟵ 06.09) — كما في فلاتر «الفئة/الفئة الفرعية» في وقاف."""
import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class DonationCategory(NestedSet):
	nsm_parent_field = "parent_donation_category"

	def validate(self):
		if self.parent_donation_category == self.name:
			frappe.throw(_("الفئة لا تكون أمًّا لنفسها"))
		if self.parent_donation_category and not frappe.db.get_value("Donation Category", self.parent_donation_category, "is_group"):
			frappe.throw(_("الفئة الأم {0} ليست فئة رئيسية").format(self.parent_donation_category))
		if self.is_restricted and self.apply_admin_fee and self.restriction_type == "زكاة":
			frappe.msgprint(_("تنبيه: الزكاة أموال مقيدة لا تُقتطع منها رسوم إدارية عادة"), alert=True)

	def on_update(self):
		super().on_update()

	def on_trash(self):
		if frappe.db.exists("Donation Allocation", {"donation_category": self.name}):
			frappe.throw(_("لا تُحذف فئة عليها إيصالات"))
		super().on_trash()


@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **kwargs):
	filters = {"parent_donation_category": parent or ""} if not is_root else {"parent_donation_category": ["in", ["", None]]}
	return frappe.get_all("Donation Category", filters=filters, fields=["name as value", "category_name as title", "is_group as expandable", "category_code"], order_by="category_code, name")
