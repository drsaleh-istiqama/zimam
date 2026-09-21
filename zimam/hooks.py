# -*- coding: utf-8 -*-
app_name = "zimam"
app_title = "زِمام"
app_publisher = "جدوى للدراسات والتطوير"
app_description = "زِمام — نظام إدارة المؤسسات المالي والإداري فوق ERPNext: الأذرع الاستثمارية، العطاء الوقفي، الخدمات، الفعاليات، الشؤون القانونية، والحزم القطاعية (التراثية والخيرية)"
app_email = "info@jadwa.om"
app_license = "MIT"

# التطبيقات المطلوبة (صيغة Frappe Cloud / v15+)
required_apps = ["frappe/erpnext"]

# الظهور في شاشة التطبيقات وسطح المكتب (v15/v16)
app_logo_url = "/assets/zimam/images/zimam-mark.png"
app_home = "/desk/zimam"  # v16: مسار سطح المكتب /desk (يُعاد توجيه /app إليه)
add_to_apps_screen = [
	{
		"name": "zimam",
		"logo": "/assets/zimam/images/zimam-mark.png",
		"title": "زِمام",
		"route": "/desk/zimam",
	}
]

# ---------------------------------------------------------------------------
# التثبيت والترحيل — دوال آمنة للتكرار
# ---------------------------------------------------------------------------
after_install = "zimam.setup.install.after_install"
after_migrate = "zimam.setup.install.after_migrate"

# ---------------------------------------------------------------------------
# أحداث مستندات ERPNext القياسية
# ---------------------------------------------------------------------------
doctype_js = {"User": "public/js/user_zimam.js"}  # زر «تخصيص حزمة زِمام» في شاشة المستخدم

doc_events = {
	"Sales Invoice": {
		"on_submit": "zimam.integrations.selling.sales_invoice_on_submit",
		"on_cancel": "zimam.integrations.selling.sales_invoice_on_cancel",
	},
	"Quotation": {
		"on_submit": "zimam.integrations.selling.quotation_on_submit",
		"on_update_after_submit": "zimam.integrations.selling.quotation_on_update_after_submit",
		"on_cancel": "zimam.integrations.selling.quotation_on_cancel",
	},
	"Sales Order": {
		"on_submit": "zimam.integrations.selling.sales_order_on_submit",
	},
}

# ---------------------------------------------------------------------------
# المهام المجدولة
# ---------------------------------------------------------------------------
scheduler_events = {
	"daily": [
		"zimam.zimam_core.doctype.legal_matter.legal_matter.send_expiry_reminders",
		"zimam.zimam_heritage.doctype.cabinet_intake.cabinet_intake.send_return_due_reminders",
		# الحزمة الخيرية: استحقاقات الكفالات تُقيَّد يوم حلولها لا قبله (أو قبلها بأيام محددة في الإعدادات)
		"zimam.zimam_charity.doctype.sponsorship.sponsorship.generate_dues",
		# المطبعة: عروض الأسعار المُرسلة التي تجاوزت «صالح حتى» تصير منتهية الصلاحية
		"zimam.zimam_core.doctype.print_estimate.print_estimate.expire_estimates",
	],
}

# ---------------------------------------------------------------------------
# العلامة: «يعمل هذا النظام من خلال منصة زِمام» — كل مؤسسة تبقي اسمها وشعارها
# ---------------------------------------------------------------------------
from zimam import __version__ as _v  # noqa: E402

app_include_js = [f"/assets/zimam/js/zimam_branding.js?v={_v}"]  # رقم الإصدار يمنع المتصفح من خدمة نسخة قديمة بعد النشر
app_include_css = ["/assets/zimam/css/zimam-desk.css"]
web_include_css = ["/assets/zimam/css/zimam-web.css"]

# الصفحة الرسمية (صفحة الهبوط) وشاشة الدخول
home_page = "login"  # الواجهة الرسمية = شاشة الدخول فقط (بقرار د. صالح 2026-09-20)؛ صفحة التعريف تبقى على /zimam-home
boot_session = "zimam.setup.boot.boot_session"
# بعد الدخول: مساحة زِمام مباشرة (لا شاشة أيقونات سطح المكتب) — بقرار د. صالح 2026-09-21
on_session_creation = "zimam.setup.boot.on_session_creation"
website_context = {"footer_powered": "يعمل هذا الموقع من خلال منصة زِمام", "splash_image": "/assets/zimam/images/zimam-logo.png"}
update_website_context = ["zimam.setup.boot.website_context"]

# لا نعدّل نواة ERPNext إطلاقًا؛ الحقول الإضافية Custom Field في setup/install.py
