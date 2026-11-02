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
	hide_other_systems(bootinfo)
	bootinfo.zimam["scan_allowed"], bootinfo.zimam["scan_enabled"] = scan_flags()


APP = "zimam"


def scan_flags():
	"""(مسموح، مفعّل): الزر يظهر لمن يملك صلاحية المسح، ويعمل حين يكون المساعد مفعّلًا. المفتاح لا يُرسَل إلى المتصفح أبدًا."""
	try:
		if frappe.session.user == "Guest" or not frappe.has_permission("Scanned Document", "create"):
			return False, False
		return True, bool(frappe.db.get_single_value("Zimam Settings", "ai_enabled"))
	except Exception:
		return False, False


def hide_other_systems(bootinfo):
	"""شاشة التطبيقات ومبدّل التطبيقات يعرضان زِمام وحدها: المحاسبة والموارد البشرية وبقية وحدات ERPNext/HRMS تبقى داخل زِمام
	(بنود الشريط الجانبي) حسب صلاحيات كل مستخدم، فلا يرى المستخدم «أنظمة» متعددة (طلب د. صالح 2026-11-02).
	ترشيح وقت الإقلاع فقط: لا يمس التثبيت ولا الصلاحيات ولا مسارات الشاشات — ويُلغى بإعداد «إظهار أنظمة ERPNext الأخرى».
	يتحمّل اختلاف بنية bootinfo بين إصدارات v16."""
	try:
		if frappe.db.get_single_value("Zimam Settings", "show_other_systems"):
			return
		apps = bootinfo.get("app_data")
		if apps:
			for a in apps:
				if a.get("app_name") != APP:
					a["on_apps_screen"] = False
		icons = bootinfo.get("desktop_icons")
		if icons:
			bootinfo["desktop_icons"] = [i for i in icons if _keep_icon(i)]
	except Exception:
		frappe.log_error(title="zimam: hide_other_systems failed")


def _keep_icon(icon):
	"""أيقونة سطح المكتب تبقى إن كانت لتطبيق زِمام، أو لا تتبع تطبيقًا بعينه (مجلدات وروابط مخصّصة)."""
	app = icon.get("app")
	if icon.get("icon_type") == "App":
		return app == APP
	return not app or app == APP


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
