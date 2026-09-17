# -*- coding: utf-8 -*-
"""حقن معلومات العلامة في جلسة سطح المكتب (boot_session) — تقرأها zimam_branding.js."""
import frappe


def boot_session(bootinfo):
	try:
		text = frappe.db.get_single_value("Zimam Settings", "powered_by_text")
		url = frappe.db.get_single_value("Zimam Settings", "powered_by_url")
	except Exception:
		text, url = None, None
	bootinfo.zimam = {"powered_by_text": text or "", "powered_by_url": url or ""}


def website_context(context):
	"""ذيل الموقع العام: «يعمل من خلال منصة زِمام» ما لم تعطّله المؤسسة."""
	try:
		text = frappe.db.get_single_value("Zimam Settings", "powered_by_text")
	except Exception:
		text = None
	if text and not context.get("footer_powered"):
		context["footer_powered"] = text
	return context
