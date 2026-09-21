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


def zimam_home_route():
	"""مسار مساحة زِمام: v16 يستخدم /desk، وما قبله /app."""
	try:
		major = int(str(frappe.__version__).split(".")[0])
	except Exception:
		major = 15
	return "/desk/zimam" if major >= 16 else "/app/zimam"


def on_session_creation(login_manager):
	"""بعد الدخول (كلمة مرور، رابط بريد، تعيين كلمة مرور) يفتح مستخدم النظام على مساحة زِمام مباشرة لا على شاشة أيقونات سطح المكتب —
	بقرار د. صالح 2026-09-21. مستخدم الموقع (بوابة خارجية) يبقى على مساره الافتراضي."""
	try:
		user = frappe.session.user
		if user in ("Guest", "Administrator") or frappe.db.get_value("User", user, "user_type") != "System User":
			return
		frappe.local.response["home_page"] = zimam_home_route()
	except Exception:
		frappe.log_error(title="zimam: on_session_creation failed")
