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

# أدوار المالية الإضافية (النواة — سلسلة اعتماد سند الصرف لكل مؤسسة)
PACKAGE_ROLES = [
	# المحاسب المالي (تسجيل) ← مدير مالي ← معتمد الصرف (مدير المؤسسة / الرئيس التنفيذي) ← أمين صندوق
	("مدير مالي", 1),
	("معتمد الصرف", 1),
	("أمين صندوق", 1),
	# حسابات المستخدمين وتوزيع ملفات الصلاحيات (v0.12) — بلا صلاحيات مالية
	("مسؤول الصلاحيات", 1),
]

DOMAINS = ["Heritage", "Education", "Training", "Charity"]
# الوحدات المقيدة بنطاق: تُخفى وحدة الحزمة (Module Def) حين لا يكون نطاقها مفعَّلًا
MODULE_DOMAINS = {"Zimam Heritage": "Heritage", "Zimam Charity": "Charity"}

CUSTOM_FIELDS = {
	"Project": [
		dict(fieldname="zimam_charity_section", label="المشروع الخيري (زِمام)", fieldtype="Section Break", insert_after="notes", collapsible=1),
		dict(fieldname="zimam_country", label="الدولة / الموقع", fieldtype="Data", insert_after="zimam_charity_section", in_standard_filter=1),
		dict(fieldname="zimam_donation_category", label="فئة التبرع", fieldtype="Link", options="Donation Category", insert_after="zimam_country"),
		dict(fieldname="zimam_target_amount", label="المبلغ المستهدف", fieldtype="Currency", insert_after="zimam_donation_category"),
		dict(fieldname="zimam_beneficiaries", label="عدد المستفيدين المتوقع", fieldtype="Int", insert_after="zimam_target_amount"),
		dict(fieldname="zimam_charity_cb", fieldtype="Column Break", insert_after="zimam_beneficiaries"),
		dict(fieldname="zimam_collected", label="المحصَّل من التبرعات", fieldtype="Currency", insert_after="zimam_charity_cb", read_only=1, no_copy=1),
		dict(fieldname="zimam_spent", label="المصروف بسندات الصرف", fieldtype="Currency", insert_after="zimam_collected", read_only=1, no_copy=1),
		dict(fieldname="zimam_publish_on_website", label="يظهر في نموذج التبرع على الموقع", fieldtype="Check", insert_after="zimam_spent"),
	],
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
		dict(fieldname="zimam_ref_section", label="مرجع زِمام", fieldtype="Section Break", insert_after="terms", collapsible=1),
		dict(fieldname="zimam_ref_doctype", label="نوع المستند المصدر", fieldtype="Link", options="DocType",
			insert_after="zimam_ref_section", read_only=1, no_copy=1),
		dict(fieldname="zimam_ref_name", label="المستند المصدر", fieldtype="Dynamic Link", options="zimam_ref_doctype",
			insert_after="zimam_ref_doctype", read_only=1, no_copy=1),
	],
	"Quotation Item": [
		dict(fieldname="zimam_object_code", label="رمز الوعاء", fieldtype="Data", insert_after="description", in_list_view=0),
		dict(fieldname="zimam_pages", label="الصفحات/الوثائق", fieldtype="Int", insert_after="zimam_object_code"),
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
	for role_name, desk in ROLES + PACKAGE_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": desk, "is_custom": 1}).insert(ignore_permissions=True)


def sync_permissions():
	"""ملفات الصلاحيات (Role Profile) + صلاحيات أدوار زِمام على مستندات ERPNext القياسية — من setup/permissions.py (v0.12)."""
	try:
		from zimam.setup.permissions import sync_role_profiles, sync_standard_permissions
		sync_role_profiles()
		sync_standard_permissions()
	except Exception:
		frappe.log_error(title="zimam: permissions sync failed")


def create_domains():
	for domain in DOMAINS:
		if not frappe.db.exists("Domain", domain):
			frappe.get_doc({"doctype": "Domain", "domain": domain}).insert(ignore_permissions=True)
	# وحدة الحزمة تُقيَّد بنطاقها فتختفي من سطح المكتب والبحث حين لا يكون مفعَّلًا
	for module, domain in MODULE_DOMAINS.items():
		if frappe.db.exists("Module Def", module) and frappe.db.get_value("Module Def", module, "restrict_to_domain") != domain:
			frappe.db.set_value("Module Def", module, "restrict_to_domain", domain, update_modified=False)


def active_domains():
	try:
		return {d.domain for d in frappe.get_single("Domain Settings").active_domains}
	except Exception:
		return set()


def sync_finance_workflow():
	"""سير اعتماد سند الصرف (النواة) — يُنشأ/يُحدَّث عند كل ترحيل بعد إكمال معالج الإعداد."""
	if not frappe.db.get_single_value("System Settings", "setup_complete"):
		return
	try:
		from zimam.zimam_core.workflow import ensure_payment_voucher_workflow
		ensure_payment_voucher_workflow()
	except Exception:
		frappe.log_error(title="zimam: payment voucher workflow sync failed")


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
	"""الواجهة الرسمية: شاشة الدخول صفحةً رئيسية، شعار زِمام الرسمي (PNG) في الدخول وسطح المكتب. تُستبدل قيم زِمام
	القديمة (svg / zimam-home) بالجديدة، ولا تُمسّ قيم خصّصتها المؤسسة بنفسها."""
	ws = frappe.get_single("Website Settings")
	institution = None
	if frappe.db.exists("DocType", "Zimam Settings"):
		company = frappe.db.get_single_value("Zimam Settings", "parent_company")
		if company:
			institution = frappe.db.get_value("Company", company, "company_name")
	changed = False
	if (ws.home_page or "") in ("", "zimam-home"):
		if ws.home_page != "login":
			ws.home_page, changed = "login", True
	if institution and (not ws.app_name or ws.app_name in ("Frappe", "ERPNext")):
		ws.app_name, changed = institution, True
	if (ws.app_logo or "") in ("", "/assets/zimam/images/zimam-logo.svg"):
		ws.app_logo, changed = "/assets/zimam/images/zimam-mark.png", True
	if (ws.splash_image or "") in ("", "/assets/zimam/images/zimam-logo.svg"):
		ws.splash_image, changed = "/assets/zimam/images/zimam-logo.png", True
	if not ws.footer_powered:
		ws.footer_powered, changed = "يعمل هذا الموقع من خلال منصة زِمام", True
	if changed:
		ws.save(ignore_permissions=True)

def prune_sidebars_for_domains():
	"""الشريط الجانبي الموحد يضم أنواع الحزم القطاعية؛ نحذف بعد كل ترحيل بنود الأنواع المقيدة بنطاق غير مفعَّل
	(والمجموعات التي تفرغ) فيصلح الشريط للمؤسسات التي لا تشغّل الحزمة التراثية. تُعاد المزامنة من JSON في الترحيل التالي ثم يُعاد الحذف."""
	if not frappe.db.exists("DocType", "Workspace Sidebar"):
		return
	active = {d.domain for d in frappe.get_single("Domain Settings").active_domains}
	for name in frappe.get_all("Workspace Sidebar", filters={"app": "zimam", "standard": 1}, pluck="name"):
		try:
			doc = frappe.get_doc("Workspace Sidebar", name)
		except Exception:
			continue
		keep, changed = [], False
		for row in doc.items:
			domain = None
			if row.type == "Link" and row.link_type == "DocType":
				domain = frappe.db.get_value("DocType", row.link_to, "restrict_to_domain") if frappe.db.exists("DocType", row.link_to) else None
			elif row.type == "Link" and row.link_type == "Report":
				ref = frappe.db.get_value("Report", row.link_to, "ref_doctype") if frappe.db.exists("Report", row.link_to) else None
				domain = frappe.db.get_value("DocType", ref, "restrict_to_domain") if ref else None
			elif row.type == "Link" and row.link_type == "Dashboard":
				module = frappe.db.get_value("Dashboard", row.link_to, "module") if frappe.db.exists("Dashboard", row.link_to) else None
				domain = MODULE_DOMAINS.get(module)
			if domain and domain not in active:
				changed = True
				continue
			keep.append(row)
		# مجموعات بلا أبناء
		pruned = []
		for i, row in enumerate(keep):
			if row.type == "Section Break" and row.indent:
				has_child = i + 1 < len(keep) and keep[i + 1].type == "Link" and keep[i + 1].child
				if not has_child:
					changed = True
					continue
			pruned.append(row)
		if changed:
			doc.items = []
			for row in pruned:
				doc.append("items", {k: row.get(k) for k in ("label", "link_type", "link_to", "icon", "type", "child", "indent", "collapsible", "keep_closed", "show_arrow", "url", "navigate_to_tab", "filters", "route_options")})
			doc.flags.ignore_permissions = True
			doc.save()

def after_install():
	create_roles()
	create_domains()
	create_fields()
	sync_permissions()
	sync_dashboards()
	sync_desktop_icons()
	ensure_website_defaults()
	sync_finance_workflow()
	prune_sidebars_for_domains()
	frappe.clear_cache()
	frappe.db.commit()
	frappe.msgprint("تم تثبيت زِمام. الخطوة التالية: bench --site <site> execute zimam.setup.bootstrap.run --kwargs '{\"profile\": \"<profile>\"}'")


def after_migrate():
	create_roles()
	create_domains()
	create_fields()
	sync_permissions()
	sync_dashboards()
	sync_desktop_icons()
	ensure_website_defaults()
	sync_finance_workflow()
	prune_sidebars_for_domains()
	frappe.clear_cache()
	frappe.db.commit()
