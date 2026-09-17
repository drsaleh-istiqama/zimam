# -*- coding: utf-8 -*-
"""إعداد زِمام بعد التثبيت وبعد كل ترحيل — كل الدوال آمنة للتكرار (idempotent).

- الأدوار العشرة العامة (تعميم لمصفوفة الأدوار في عقد ذاكرة عُمان 2025 لتصلح لأي مؤسسة).
- النطاقات (Domains) للحزم القطاعية: Heritage الآن، وEducation/Training/Charity محجوزة.
- حقول مخصصة على مستندات ERPNext القياسية (لا تعديل على النواة).
"""
import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# (اسم الدور, وصول لسطح المكتب)
ROLES = [
	("موظف وحدة", 1),
	("مشرف وحدة", 1),
	("موظف استقبال وخدمة", 1),
	("مستفيد خارجي", 0),
	("شريك خارجي", 0),
	("مشرف فني", 1),
	("محاسب مالي", 1),
	("مخرج فني ومصمم", 1),
	("مدير ذراع", 1),
	("مدير المؤسسة", 1),
]

DOMAINS = ["Heritage", "Education", "Training", "Charity"]

CUSTOM_FIELDS = {
	"Company": [
		dict(fieldname="zimam_arm_type", label="الصفة في منظومة زِمام", fieldtype="Select",
			options="\nالمؤسسة (الشركة الأم)\nذراع استثماري تابع", insert_after="parent_company"),
		dict(fieldname="zimam_arm_role", label="دور الذراع", fieldtype="Select",
			options="\nمطبعة\nترميم\nاستثمار وقفي\nأخرى", insert_after="zimam_arm_type",
			depends_on="eval:doc.zimam_arm_type=='ذراع استثماري تابع'"),
	],
	"Sales Invoice": [
		dict(fieldname="zimam_ref_section", label="مرجع زِمام", fieldtype="Section Break", insert_after="remarks", collapsible=1),
		dict(fieldname="zimam_ref_doctype", label="نوع المستند المصدر", fieldtype="Link", options="DocType",
			insert_after="zimam_ref_section", read_only=1, no_copy=1),
		dict(fieldname="zimam_ref_name", label="المستند المصدر", fieldtype="Dynamic Link", options="zimam_ref_doctype",
			insert_after="zimam_ref_doctype", read_only=1, no_copy=1),
	],
	"Quotation": [
		dict(fieldname="zimam_print_job", label="أمر الطباعة", fieldtype="Link", options="Print Job",
			insert_after="order_type", read_only=1, no_copy=1),
	],
	"Sales Order": [
		dict(fieldname="zimam_print_job", label="أمر الطباعة", fieldtype="Link", options="Print Job",
			insert_after="order_type", read_only=1, no_copy=1),
	],
	"Item": [
		dict(fieldname="zimam_source_doctype", label="نوع المصدر (زِمام)", fieldtype="Link", options="DocType",
			insert_after="description", read_only=1, no_copy=1),
		dict(fieldname="zimam_source_name", label="المصدر (زِمام)", fieldtype="Dynamic Link", options="zimam_source_doctype",
			insert_after="zimam_source_doctype", read_only=1, no_copy=1),
	],
}


def create_roles():
	for role_name, desk in ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": desk, "is_custom": 1}).insert(ignore_permissions=True)


def create_domains():
	for domain in DOMAINS:
		if not frappe.db.exists("Domain", domain):
			frappe.get_doc({"doctype": "Domain", "domain": domain}).insert(ignore_permissions=True)


def create_fields():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=frappe.flags.in_patch, update=True)


def sync_dashboards():
	"""Frappe لا يزامن مستندات Dashboard من مجلد التطبيق تلقائيًا (بخلاف Number Card وDashboard Chart) — نستوردها هنا."""
	import glob
	from frappe.modules.import_file import import_file_by_path

	base = os.path.dirname(os.path.dirname(__file__))
	for path in sorted(glob.glob(os.path.join(base, "*", "dashboard", "*", "*.json"))):
		try:
			import_file_by_path(path, force=True, ignore_version=True)
		except Exception:
			frappe.log_error(title="zimam: dashboard sync failed", message=path)


def sync_desktop_icons():
	"""v16: أيقونات سطح المكتب تُشتق من المساحات العامة وتطبيقات add_to_apps_screen — نعيد توليدها بعد التثبيت/الترحيل."""
	try:
		create = frappe.get_attr("frappe.desk.doctype.desktop_icon.desktop_icon.create_desktop_icons")
	except Exception:
		return
	try:
		create()
	except Exception:
		frappe.log_error(title="zimam: desktop icons sync failed")



def ensure_website_defaults():
	"""الواجهة الرسمية: تُملأ إعدادات الموقع الفارغة/الافتراضية فقط (لا تُستبدل تخصيصات المؤسسة)."""
	ws = frappe.get_single("Website Settings")
	institution = None
	if frappe.db.exists("DocType", "Zimam Settings"):
		company = frappe.db.get_single_value("Zimam Settings", "parent_company")
		if company:
			institution = frappe.db.get_value("Company", company, "company_name")
	changed = False
	if not ws.home_page:
		ws.home_page, changed = "zimam-home", True
	if institution and (not ws.app_name or ws.app_name in ("Frappe", "ERPNext")):
		ws.app_name, changed = institution, True
	if not ws.app_logo:
		ws.app_logo, changed = "/assets/zimam/images/zimam-logo.svg", True
	if not ws.splash_image:
		ws.splash_image, changed = "/assets/zimam/images/zimam-logo.svg", True
	if not ws.footer_powered:
		ws.footer_powered, changed = "يعمل هذا الموقع من خلال منصة زِمام", True
	if changed:
		ws.save(ignore_permissions=True)

def after_install():
	create_roles()
	create_domains()
	create_fields()
	sync_dashboards()
	sync_desktop_icons()
	ensure_website_defaults()
	frappe.clear_cache()
	frappe.db.commit()
	frappe.msgprint("تم تثبيت زِمام. الخطوة التالية: bench --site <site> execute zimam.setup.bootstrap.run --kwargs '{\"profile\": \"<profile>\"}'")


def after_migrate():
	create_roles()
	create_domains()
	create_fields()
	sync_dashboards()
	sync_desktop_icons()
	ensure_website_defaults()
	frappe.clear_cache()
	frappe.db.commit()
