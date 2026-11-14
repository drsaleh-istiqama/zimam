# -*- coding: utf-8 -*-
"""طبقة الطباعة (0.14.1، بطلب مريم دويماز لذاكرة عُمان): ترويسة الورق الرسمي، النماذج الافتراضية، وحفظ PDF تلقائي.

- ترويسة «Company Letterhead - Grey» الافتراضية في ERPNext تُطبع فوق سندات المؤسسة؛ نُنشئ بدلها ترويسة باسم المؤسسة
  (من `print.letterhead_title` في ملف التعريف، وإلا اسم الشركة الأم) ونجعلها الافتراضية. خلفية الورق الرسمي: ضع الصورة في
  `public/images/letterheads/<اسم الملف>` وأشر إليها في `print.letterhead_image`؛ بلا صورة تُطبع ترويسة نصية باسم المؤسسة.
- النموذج الافتراضي لقيد الدفع وفاتورة المبيعات هو نموذج زِمام (Property Setter) بدل Monochrome/Standard.
- عند اعتماد قيد الدفع أو الفاتورة يُحفظ PDF بنموذج زِمام مرفقًا خاصًا بالمستند (`attach_pdf`)؛ لا يفشل الاعتماد أبدًا بسببه.
"""
import frappe

DEFAULT_FORMATS = {"Payment Entry": "Receipt Voucher Form", "Sales Invoice": "Sales Invoice Form"}
GREY = "Company Letterhead - Grey"


def _parent_company_name():
	company = frappe.db.get_single_value("Zimam Settings", "parent_company") if frappe.db.exists("DocType", "Zimam Settings") else None
	return frappe.db.get_value("Company", company, "company_name") if company else None


def ensure_letterhead(title=None, image=None, footer_image=None):
	"""يُنشئ ترويسة المؤسسة ويجعلها الافتراضية؛ لا يمسّ ترويسة أنشأها المستخدم بنفسه (يُحدَّث ما أنشأناه فقط)."""
	title = title or _parent_company_name()
	if not title:
		return None
	name = title
	if frappe.db.exists("Letter Head", name):
		doc = frappe.get_doc("Letter Head", name)
		if not (doc.get("content") or "").startswith("<!--zimam-->"):
			return name  # أنشأها المستخدم يدويًا
	else:
		doc = frappe.new_doc("Letter Head")
		doc.letter_head_name = name
	base = "/assets/zimam/images/letterheads/"
	if image:
		doc.source = "HTML"
		doc.content = '<!--zimam--><img src="' + base + image + '" style="width:100%; display:block;">'
		if footer_image:
			doc.footer_source = "HTML"
			doc.footer = '<img src="' + base + footer_image + '" style="width:100%; display:block;">'
	else:
		doc.source = "HTML"
		doc.content = (
			'<!--zimam--><div dir="rtl" style="text-align:center; border-bottom:2px solid #7B3F61; padding-bottom:6px;">'
			'<div style="font-size:20pt; font-weight:bold; color:#7B3F61;">' + frappe.utils.escape_html(title) + "</div></div>"
		)
	doc.disabled = 0
	doc.is_default = 1
	doc.flags.ignore_permissions = True
	doc.save()
	if frappe.db.exists("Letter Head", GREY):
		frappe.db.set_value("Letter Head", GREY, "is_default", 0)
	return name


def ensure_default_formats():
	for doctype, fmt in DEFAULT_FORMATS.items():
		if not frappe.db.exists("Print Format", fmt):
			continue
		frappe.make_property_setter(
			{"doctype": doctype, "doctype_or_field": "DocType", "property": "default_print_format", "value": fmt, "property_type": "Data"}
		)


def sync(profile_print=None):
	profile_print = profile_print or {}
	ensure_letterhead(
		profile_print.get("letterhead_title"), profile_print.get("letterhead_image"), profile_print.get("letterhead_footer_image")
	)
	ensure_default_formats()


def attach_pdf(doc, method=None):
	"""PDF بنموذج زِمام مرفقًا بالمستند عند الاعتماد. الفشل يُسجَّل ولا يمنع الاعتماد."""
	fmt = DEFAULT_FORMATS.get(doc.doctype)
	if not fmt or not frappe.db.exists("Print Format", fmt):
		return
	try:
		fname = f"{doc.name}.pdf"
		if frappe.db.exists("File", {"attached_to_doctype": doc.doctype, "attached_to_name": doc.name, "file_name": fname}):
			return
		out = frappe.attach_print(doc.doctype, doc.name, file_name=doc.name, print_format=fmt)
		frappe.get_doc(
			{"doctype": "File", "file_name": out["fname"], "content": out["fcontent"], "attached_to_doctype": doc.doctype,
			 "attached_to_name": doc.name, "is_private": 1}
		).save(ignore_permissions=True)
	except Exception:
		frappe.log_error(title=f"zimam: auto PDF failed {doc.doctype} {doc.name}")
