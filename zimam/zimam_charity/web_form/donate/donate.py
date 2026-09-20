# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""نموذج التبرع العام على الموقع: يُنشئ إيصال تبرع مسودةً بمصدر «الموقع الإلكتروني» ليراجعه المحاسب عند ورود التحويل ثم يرحّله."""
import frappe


def get_context(context):
	s = frappe.get_cached_doc("Charity Settings")
	context.categories = frappe.get_all("Donation Category", filters={"publish_on_website": 1, "is_active": 1, "is_group": 0}, fields=["name", "category_code"], order_by="category_code")
	context.default_category = s.website_donation_category
	context.projects = frappe.get_all("Project", filters={"zimam_publish_on_website": 1, "status": "Open"}, fields=["name", "project_name"]) if frappe.get_meta("Project").has_field("zimam_publish_on_website") else []
