# -*- coding: utf-8 -*-
"""صفحة الهبوط الرسمية لزِمام: تعرض اسم المؤسسة من إعدادات زِمام وتذيّل «يعمل من خلال منصة زِمام»."""
import frappe
from frappe import _

no_cache = 1


def get_context(context):
	settings = frappe.get_cached_doc("Zimam Settings") if frappe.db.exists("DocType", "Zimam Settings") else None
	company = settings.parent_company if settings and settings.parent_company else None
	institution = frappe.db.get_value("Company", company, "company_name") if company else None
	context.institution = institution or frappe.db.get_single_value("Website Settings", "app_name") or "زِمام"
	context.powered_by = (settings and settings.powered_by_text) or "يعمل هذا النظام من خلال منصة زِمام"
	context.powered_by_url = (settings and settings.powered_by_url) or "https://jadwa.om"
	context.version = frappe.get_attr("zimam.__version__")
	context.headline = _("نظام الإدارة المالية والإدارية لـ{0}").format(context.institution)
	context.lead = _("محاسبة مزدوجة القيد، أذرع استثمارية مستقلة بقوائم موحدة، عطاء وقفي بشهادات فورية، موارد بشرية، وحزم قطاعية تناسب طبيعة نشاط المؤسسة.")
	context.stats = [
		{"value": frappe.db.count("Company"), "label": _("شركة / ذراع")},
		{"value": frappe.db.count("User", {"enabled": 1, "user_type": "System User"}), "label": _("مستخدم")},
		{"value": frappe.db.count("Waqf Campaign") if frappe.db.exists("DocType", "Waqf Campaign") else 0, "label": _("حملة وقفية")},
		{"value": frappe.db.count("Service Type") if frappe.db.exists("DocType", "Service Type") else 0, "label": _("خدمة")},
	]
	context.features = [
		{"icon": "🧾", "title": _("المالية والمحاسبة"), "text": _("شجرة حسابات، قيود، موازنات، وعشرة تقارير قياسية: ميزان المراجعة والدخل والمركز المالي والتدفقات والذمم.")},
		{"icon": "🏛️", "title": _("الأذرع الاستثمارية"), "text": _("مطبعة أو معمل أو عقارات: كل ذراع شركة مستقلة بدفاترها، وفوترة بينية، وقوائم موحدة للمؤسسة الأم.")},
		{"icon": "🕌", "title": _("العطاء الوقفي"), "text": _("حملات وأسهم ومساهمات بقيد آلي وشهادة مساهمة بالتاريخ الهجري أولًا، وعقارات وقفية بعقود إيجار.")},
		{"icon": "👥", "title": _("الموارد البشرية"), "text": _("إجازات وحضور وتقييم أداء ورواتب، وعشرة أدوار جاهزة من موظف الوحدة إلى مدير المؤسسة.")},
		{"icon": "📜", "title": _("الحزم القطاعية"), "text": _("الحزمة التراثية للخزائن والترميم والرقمنة، وحزم تعليمية وتدريبية وخيرية تُفعَّل بحسب نشاط المؤسسة.")},
		{"icon": "📊", "title": _("لوحة المدير"), "text": _("مؤشرات لحظية للخدمات والوقف والفواتير والفعاليات والشؤون القانونية في لوحة واحدة.")},
	]
	return context
