# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""تقدير وعرض سعر طباعة: يحسب التكلفة فوريًا من كتالوج المطبعة (ورق، آلات، تشطيب) بمحرّك `print_estimating`،
ويعرض شرائح كمية، ثم يولّد عرض سعر ERPNext قياسيًا (لتقدير واحد أو عدة تقديرات في عرض مجمّع) وأمر طباعة ببنود التكلفة.

منذ 0.11: هامش بحسب الكمية، خدمات مسنَدة لجهة خارجية، خيارات بديلة، إرسال عبر واتساب/البريد مع ختم الإرسال وتاريخ المتابعة،
انتهاء الصلاحية آليًا، وكتالوج لصفحة «التسعير السريع» مع إنشاء التقدير منها."""
import json
import re
from urllib.parse import quote

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate, today

from zimam.utils import ensure_customer_for, get_settings, hijri_str
from zimam.zimam_core import print_estimating as pe

HEADER_FIELDS = ("paper_cost", "print_cost", "finishing_cost", "extras_cost", "total_cost", "unit_cost", "rush_amount",
	"discount_amount", "net_total", "unit_price", "tax_amount", "grand_total", "total_sheets", "total_impressions",
	"production_hours", "spine_mm", "margin_applied", "lead_days")
COMPONENT_FIELDS = ("ups", "run_w", "run_h", "sheets", "impressions", "paper_cost", "print_cost", "amount", "hours", "warning",
	"piece_width_mm", "piece_height_mm", "pages")
FINISHING_FIELDS = ("basis", "qty", "rate", "setup_cost", "amount", "outsourced")
TIER_FIELDS = ("total_cost", "price", "unit_price", "grand_total", "margin_applied")
DEFAULTS = {
	"margin_percent": "default_margin_percent", "tax_rate": "default_tax_rate", "validity_days": "default_validity_days",
	"advance_percent": "default_advance_percent", "rush_percent": "default_rush_percent", "design_rate": "default_design_rate",
	"round_to": "default_round_to", "waste_percent": "default_waste_percent", "bleed_mm": "default_bleed_mm",
	"pricing_mode": "default_pricing_mode",
}
SETTING_KEYS = ("default_margin_percent", "default_tax_rate", "default_validity_days", "default_advance_percent", "default_rush_percent",
	"default_design_rate", "default_round_to", "min_job_price", "default_tiers", "default_waste_percent", "default_bleed_mm",
	"default_pricing_mode", "margin_tiers", "follow_up_days", "whatsapp_template")
BINDING_TO_JOB = {"بلا": "بلا", "تدبيس سلك": "تدبيس", "غراء (تجليد حراري)": "غراء", "خياطة وغراء": "خياطة", "سلك حلزوني": "سلك", "غلاف صلب": "غلاف صلب"}
OPEN_STATUSES = ("مسودة", "مُرسل")


def get_press_settings():
	return frappe.get_cached_doc("Press Settings")


def settings_dict():
	return get_press_settings().as_dict()


def load_masters(d):
	"""قواميس الورق/الآلات/التشطيب المستخدمة في المستند فقط."""
	masters = {"paper": {}, "machine": {}, "finishing": {}}
	for c in d.get("components") or []:
		for key, dt in (("paper", "Paper Stock"), ("machine", "Print Machine")):
			n = c.get(key)
			if n and n not in masters[key] and frappe.db.exists(dt, n):
				masters[key][n] = frappe.get_cached_doc(dt, n).as_dict()
	for f in d.get("finishing") or []:
		n = f.get("finishing_service")
		if n and n not in masters["finishing"] and frappe.db.exists("Finishing Service", n):
			masters["finishing"][n] = frappe.get_cached_doc("Finishing Service", n).as_dict()
	return masters


def apply_result(doc, result):
	for f in HEADER_FIELDS:
		doc.set(f, result.get(f))
	doc.finished_width_mm, doc.finished_height_mm = result["finished_width_mm"], result["finished_height_mm"]
	if not doc.estimated_days:
		doc.estimated_days = result.get("estimated_days")
	for row, r in zip(doc.components or [], result.get("components") or []):
		for f in COMPONENT_FIELDS:
			row.set(f, r.get(f))
	for row, r in zip(doc.finishing or [], result.get("finishing") or []):
		for f in FINISHING_FIELDS:
			row.set(f, r.get(f))
	for row, r in zip(doc.extras or [], result.get("extras") or []):
		row.amount = r.get("amount")
	for row, r in zip(doc.tiers or [], result.get("tiers") or []):
		for f in TIER_FIELDS:
			row.set(f, r.get(f))


def press_company_name(company):
	return frappe.db.get_value("Company", company, "company_name") or company or ""


def normalize_phone(phone, default_cc="968"):
	"""رقم واتساب دولي بلا رموز: 9xxxxxxx ⟵ 968…؛ 00968… ⟵ 968…؛ +968… ⟵ 968…"""
	digits = re.sub(r"\D", "", str(phone or ""))
	if digits.startswith("00"):
		digits = digits[2:]
	if len(digits) == 8:
		digits = default_cc + digits
	return digits


class PrintEstimate(Document):
	def validate(self):
		zs = get_settings()
		if not self.company:
			self.company = zs.press_company or zs.parent_company
		if not self.customer and not self.prospect_name:
			frappe.throw(_("حدد العميل أو اكتب اسم طالب العرض"))
		if self.alternative_of and self.alternative_of == self.name:
			frappe.throw(_("لا يكون التقدير خيارًا بديلًا لنفسه"))
		self.apply_defaults(only_missing=True)
		if self.size_preset in pe.SIZE_PRESETS and self.size_preset != "مخصص" and (self.has_value_changed("size_preset") or not self.finished_width_mm):
			self.finished_width_mm, self.finished_height_mm = pe.SIZE_PRESETS[self.size_preset]
		if not self.estimate_date:
			self.estimate_date = nowdate()
		if not self.date_hijri or (not self.is_new() and self.has_value_changed("estimate_date")):
			self.date_hijri = hijri_str(self.estimate_date)
		self.valid_until = add_days(getdate(self.estimate_date), cint(self.validity_days))
		if not self.tiers:
			self.fill_tiers()
		self.recalculate()
		if not self.terms:
			self.terms = self.default_terms()
		if not self.description:
			self.description = self.spec_summary()
		if self.docstatus == 0 and self.status not in ("مسودة", "ملغى"):
			self.status = "مسودة"

	def apply_defaults(self, only_missing=True):
		ps = get_press_settings()
		for field, src in DEFAULTS.items():
			if not only_missing or self.get(field) in (None, "", 0, 0.0):
				self.set(field, ps.get(src))
		if self.template and self.get("margin_percent") in (None, 0, 0.0):
			m = frappe.db.get_value("Print Product Template", self.template, "margin_percent")
			if m:
				self.margin_percent = m

	def fill_tiers(self):
		text = frappe.db.get_value("Print Product Template", self.template, "tiers") if self.template else None
		qtys = pe.parse_tiers(text or get_press_settings().default_tiers)
		if self.quantity and cint(self.quantity) not in qtys:
			qtys = sorted(qtys + [cint(self.quantity)])
		self.set("tiers", [])
		for q in qtys:
			self.append("tiers", {"qty": q})

	@frappe.whitelist()
	def recalculate(self):
		"""يُستدعى من النموذج (بلا حفظ) ومن validate: يحسب كل شيء بمحرّك التقدير ويكتب النتائج في المستند."""
		d = self.as_dict()
		result = pe.compute(d, load_masters(d), settings_dict())
		apply_result(self, result)
		return {"total_cost": self.total_cost, "net_total": self.net_total, "grand_total": self.grand_total, "margin_applied": self.margin_applied}

	@frappe.whitelist()
	def apply_template(self):
		"""يعبّئ المواصفات والمكوّنات والتشطيب وشرائح الكمية من قالب المنتج، ثم يعيد الحساب (بلا حفظ)."""
		if not self.template:
			frappe.throw(_("اختر قالب المنتج أولًا"))
		t = frappe.get_doc("Print Product Template", self.template)
		self.product_type = t.product_type
		self.structure = t.structure
		self.size_preset = t.size_preset or "مخصص"
		if t.finished_width_mm and t.finished_height_mm:
			self.finished_width_mm, self.finished_height_mm = t.finished_width_mm, t.finished_height_mm
		elif self.size_preset in pe.SIZE_PRESETS:
			self.finished_width_mm, self.finished_height_mm = pe.SIZE_PRESETS[self.size_preset]
		if t.bleed_mm:
			self.bleed_mm = t.bleed_mm
		self.binding = t.binding or "بلا"
		if t.structure == "غلاف + داخلي" and not self.pages:
			self.pages = t.default_pages
		if t.margin_percent:
			self.margin_percent = t.margin_percent
		if t.design_hours and not self.design_hours:
			self.design_hours = t.design_hours
		if t.description and not self.description:
			self.description = t.description
		if not self.title:
			self.title = t.template_name
		self.set("components", [])
		if t.structure == "قطعة واحدة":
			self.append("components", {"component": pe.SINGLE, "paper": t.cover_paper, "machine": t.cover_machine, "color": t.cover_color, "sides": t.cover_sides, "auto_size": 1})
		else:
			self.append("components", {"component": pe.COVER, "paper": t.cover_paper, "machine": t.cover_machine, "color": t.cover_color, "sides": t.cover_sides, "auto_size": 1})
			self.append("components", {"component": pe.INNER, "paper": t.inner_paper, "machine": t.inner_machine, "color": t.inner_color, "sides": t.inner_sides, "pages": self.pages, "auto_size": 1})
		self.set("finishing", [])
		for f in t.finishing:
			self.append("finishing", {"finishing_service": f.finishing_service, "applies_to": f.applies_to, "qty_per_copy": f.qty_per_copy or 1, "auto_qty": 1})
		self.fill_tiers()
		self.apply_defaults(only_missing=True)
		self.recalculate()

	def spec_summary(self):
		parts = [self.product_type]
		if self.finished_width_mm and self.finished_height_mm:
			parts.append(_("المقاس {0}×{1} مم").format(frappe.format(self.finished_width_mm, {"fieldtype": "Float"}).rstrip("0").rstrip("."),
				frappe.format(self.finished_height_mm, {"fieldtype": "Float"}).rstrip("0").rstrip(".")))
		if self.structure == "غلاف + داخلي" and self.pages:
			parts.append(_("{0} صفحة داخلية").format(self.pages))
		for c in self.components:
			label = {"غلاف": _("الغلاف"), "داخلي": _("الداخلي"), "قطعة واحدة": _("الورق"), "إدراج/ملحق": _("الملحق")}.get(c.component, c.component)
			parts.append(f"{label}: {c.paper} — {c.color} {c.sides}")
		if self.binding and self.binding != "بلا":
			parts.append(_("التجليد: {0}").format(self.binding))
		fin = [f.finishing_service for f in self.finishing]
		if fin:
			parts.append(_("التشطيب: {0}").format("، ".join(fin)))
		return " · ".join(str(p) for p in parts if p)

	def default_terms(self):
		ps = get_press_settings()
		if ps.terms:
			text = frappe.db.get_value("Terms and Conditions", ps.terms, "terms")
			if text:
				return text
		parts = []
		if self.validity_days:
			parts.append(_("فترة سريان عرض الأسعار: {0} يومًا من تاريخه.").format(self.validity_days))
		if flt(self.advance_percent):
			parts.append(_("الدفعة المقدمة: {0}% قبل بدء العمل.").format(int(flt(self.advance_percent))))
		parts.append(_("يبدأ التنفيذ بعد اعتماد التصميم النهائي كتابيًا."))
		return "\n".join(parts)

	def on_submit(self):
		values = {}
		if self.status == "مسودة":
			values["status"] = "مُرسل"
		if not self.follow_up_date:
			values["follow_up_date"] = add_days(getdate(self.estimate_date or today()), cint(get_press_settings().follow_up_days) or 3)
		if values:
			self.db_set(values)

	def on_cancel(self):
		if self.quotation:
			q = frappe.get_doc("Quotation", self.quotation)
			if q.docstatus == 1:
				frappe.throw(_("ألغِ عرض السعر {0} أولًا").format(self.quotation))
			if q.docstatus == 0:
				q.delete()
			self.db_set("quotation", None)
		self.db_set("status", "ملغى")

	def billing_customer(self):
		if self.customer:
			return self.customer
		return ensure_customer_for(self.prospect_name, phone=self.contact_phone)

	def summary(self, company_name=None):
		"""الملخص النصي للعرض (المحرّك نفسه في Python وJavaScript) من قيم المستند المحفوظة."""
		d = self.as_dict()
		return pe.summary_text(d, d, settings_dict(), company_name if company_name is not None else press_company_name(self.company))

	def message_text(self):
		"""نص رسالة واتساب/البريد من قالب إعدادات المطبعة."""
		ps = get_press_settings()
		tpl = ps.whatsapp_template or "{summary}"
		company = press_company_name(self.company)
		values = {"customer": self.customer_name or self.prospect_name or "", "company": company, "summary": self.summary(company),
			"title": self.title or "", "grand_total": frappe.format(self.grand_total, {"fieldtype": "Currency"}), "name": self.name}
		out = tpl
		for k, v in values.items():
			out = out.replace("{" + k + "}", str(v))
		return out


# ---------------------------------------------------------------------------
# واجهات النموذج وصفحة التسعير السريع
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_defaults():
	"""افتراضيات المطبعة للنموذج الجديد (قبل الحفظ)."""
	ps = get_press_settings()
	out = {f: ps.get(src) for f, src in DEFAULTS.items()}
	out["tiers"] = pe.parse_tiers(ps.default_tiers)
	out["size_presets"] = pe.SIZE_PRESETS
	out["margin_tiers"] = ps.margin_tiers
	return out


@frappe.whitelist()
def get_catalog():
	"""الكتالوج كاملًا لصفحة «التسعير السريع» (تحسب في المتصفح بالمحرّك نفسه): الخامات النشطة والآلات والتشطيب
	والقوالب بتشطيبها وإعدادات المطبعة والمقاسات الجاهزة."""
	if not frappe.has_permission("Print Estimate", "read"):
		frappe.throw(_("لا تملك صلاحية قراءة تقديرات الطباعة"), frappe.PermissionError)
	zs = get_settings()
	company = zs.press_company or zs.parent_company
	templates = frappe.get_all("Print Product Template", filters={"is_active": 1}, fields=["*"], order_by="product_type, template_name")
	for t in templates:
		t["finishing"] = frappe.get_all("Print Template Finishing", filters={"parent": t.name, "parenttype": "Print Product Template"},
			fields=["finishing_service", "applies_to", "qty_per_copy"], order_by="idx")
	ps = settings_dict()
	return {
		"papers": frappe.get_all("Paper Stock", filters={"is_active": 1}, fields=["*"], order_by="category, gsm, stock_name"),
		"machines": frappe.get_all("Print Machine", filters={"is_active": 1}, fields=["*"], order_by="machine_type, machine_name"),
		"finishing": frappe.get_all("Finishing Service", filters={"is_active": 1}, fields=["*"], order_by="category, service_name"),
		"templates": templates,
		"settings": {k: ps.get(k) for k in SETTING_KEYS},
		"size_presets": pe.SIZE_PRESETS,
		"company": company, "company_name": press_company_name(company),
		"currency": frappe.db.get_value("Company", company, "default_currency") if company else None,
	}


@frappe.whitelist()
def create_from_quick(data):
	"""ينشئ تقدير طباعة (مسودة) من بيانات صفحة التسعير السريع، ويعيد اسمه — validate يعيد الحساب على الخادم."""
	d = json.loads(data) if isinstance(data, str) else dict(data)
	doc = frappe.new_doc("Print Estimate")
	head = {k: v for k, v in d.items() if k not in ("components", "finishing", "extras", "tiers")}
	doc.update(head)
	for c in d.get("components") or []:
		doc.append("components", {k: c.get(k) for k in ("component", "paper", "machine", "color", "sides", "pages", "auto_size", "piece_width_mm", "piece_height_mm")})
	for f in d.get("finishing") or []:
		doc.append("finishing", {k: f.get(k) for k in ("finishing_service", "applies_to", "qty_per_copy", "auto_qty", "qty")})
	for e in d.get("extras") or []:
		doc.append("extras", {"component": e.get("component") or "أخرى", "description": e.get("description"), "qty": e.get("qty") or 1, "rate": e.get("rate")})
	for t in d.get("tiers") or []:
		if cint(t.get("qty")):
			doc.append("tiers", {"qty": cint(t.get("qty"))})
	if not doc.title:
		doc.title = doc.template or doc.product_type or _("تقدير طباعة")
	doc.insert()
	return doc.name


@frappe.whitelist()
def make_alternative(name, option_label=None):
	"""نسخة من التقدير كخيار بديل (ورق آخر/تشطيب آخر…) مرتبطة بالأصل؛ تظهر في عرض أسعار الأصل ضمن «خيارات بديلة»."""
	src = frappe.get_doc("Print Estimate", name)
	new = frappe.copy_doc(src)
	new.alternative_of = src.alternative_of or src.name
	new.option_label = option_label or _("خيار بديل لـ {0}").format(src.title)
	new.status = "مسودة"
	for f in ("quotation", "print_job", "sales_order", "sent_via", "sent_on", "follow_up_date", "rejection_reason", "date_hijri"):
		new.set(f, None)
	new.estimate_date = nowdate()
	new.insert()
	return new.name


@frappe.whitelist()
def whatsapp_link(name):
	"""نص الرسالة ورابط wa.me (يفتحه الموظف بنفسه — لا يُرسل شيء نيابةً عنه)."""
	doc = frappe.get_doc("Print Estimate", name)
	text = doc.message_text()
	phone = normalize_phone(doc.contact_phone or (frappe.db.get_value("Customer", doc.customer, "mobile_no") if doc.customer else ""))
	url = f"https://wa.me/{phone}?text={quote(text)}" if phone else f"https://wa.me/?text={quote(text)}"
	return {"url": url, "text": text, "phone": phone, "summary": doc.summary()}


@frappe.whitelist()
def mark_sent(name, via):
	"""ختم الإرسال (واتساب/بريد/طباعة/يدويًا) على تقدير مرحَّل: الحالة مُرسل، وقت الإرسال، وتاريخ المتابعة إن لم يُحدَّد."""
	doc = frappe.get_doc("Print Estimate", name)
	if doc.docstatus != 1:
		frappe.throw(_("رحّل التقدير أولًا"))
	values = {"sent_via": via, "sent_on": now_datetime()}
	if doc.status in OPEN_STATUSES:
		values["status"] = "مُرسل"
	if not doc.follow_up_date:
		values["follow_up_date"] = add_days(getdate(today()), cint(get_press_settings().follow_up_days) or 3)
	doc.db_set(values)
	return values


def _quotation_lines(q, doc, zs, ps):
	item = zs.print_service_item
	design_cost = flt(doc.design_hours) * flt(doc.design_rate)
	price = flt(doc.net_total)
	design_item = ps.design_service_item
	if design_cost and design_item:
		# سطر التصميم بتكلفته (بلا هامش) والباقي على سطر الطباعة
		q.append("items", {"item_code": design_item, "qty": 1, "rate": pe.r3(design_cost), "description": _("تصميم: {0} ساعة — {1}").format(doc.design_hours, doc.title)})
		price = pe.r3(price - design_cost)
	qty = cint(doc.quantity) or 1
	unit = pe.r3(price / qty)
	desc = f"{doc.title} — {doc.description or ''}"
	if doc.option_label:
		desc = f"{doc.option_label}: {desc}"
	if abs(unit * qty - price) < 0.0005:
		q.append("items", {"item_code": item, "qty": qty, "rate": unit, "description": desc})
	else:
		q.append("items", {"item_code": item, "qty": 1, "rate": price, "description": desc + " — " + _("الكمية: {0}").format(qty)})


@frappe.whitelist()
def make_quotation(name=None, names=None):
	"""عرض سعر ERPNext (مسودة) من تقدير واحد أو عدة تقديرات مرحَّلة لعميل واحد (عرض مجمّع: سطر لكل منتج):
	سطر خدمة الطباعة بالكمية وسعر الوحدة (أو سطر واحد بالإجمالي إن لم يقبل القسمة بدقة البيسة) وسطر للتصميم إن وُجد؛
	الضريبة وشروط الدفع والشروط من إعدادات المطبعة؛ والصلاحية أقرب صلاحية بين التقديرات."""
	if names and isinstance(names, str):
		names = json.loads(names)
	names = [n for n in (names or []) if n] or ([name] if name else [])
	if not names:
		frappe.throw(_("اختر تقديرًا واحدًا على الأقل"))
	docs = [frappe.get_doc("Print Estimate", n) for n in names]
	for doc in docs:
		if doc.docstatus != 1:
			frappe.throw(_("رحّل التقدير {0} أولًا").format(doc.name))
		if doc.quotation:
			if len(docs) == 1:
				return doc.quotation
			frappe.throw(_("التقدير {0} له عرض سعر بالفعل: {1}").format(doc.name, doc.quotation))
	zs, ps = get_settings(), get_press_settings()
	if not zs.print_service_item:
		frappe.throw(_("صنف خدمة الطباعة غير محدد في إعدادات زِمام"))
	customer = docs[0].billing_customer()
	for doc in docs:
		if doc.billing_customer() != customer:
			frappe.throw(_("التقديرات المختارة لعملاء مختلفين — العرض المجمّع لعميل واحد"))
		if not doc.customer:
			doc.db_set("customer", customer)
	first = docs[0]
	q = frappe.new_doc("Quotation")
	q.quotation_to = "Customer"
	q.party_name = customer
	q.company = first.company
	q.transaction_date = first.estimate_date
	q.valid_till = min(getdate(d.valid_until) for d in docs if d.valid_until) if any(d.valid_until for d in docs) else None
	q.zimam_ref_doctype = first.doctype
	q.zimam_ref_name = first.name
	for doc in docs:
		_quotation_lines(q, doc, zs, ps)
	if ps.taxes_template:
		from erpnext.controllers.accounts_controller import get_taxes_and_charges
		q.taxes_and_charges = ps.taxes_template
		for t in get_taxes_and_charges("Sales Taxes and Charges Template", ps.taxes_template):
			q.append("taxes", t)
	if ps.payment_terms:
		q.payment_terms_template = ps.payment_terms
	if ps.terms:
		q.tc_name = ps.terms
		q.terms = frappe.db.get_value("Terms and Conditions", ps.terms, "terms")
	elif first.terms:
		q.terms = first.terms
	q.set_missing_values()
	q.insert(ignore_permissions=True)
	for doc in docs:
		doc.db_set("quotation", q.name)
	return q.name


@frappe.whitelist()
def make_print_job(name):
	"""أمر طباعة (مسودة) من التقدير: المواصفات وبنود التكلفة (ورق/طباعة/تشطيب/تصميم/إضافي) والسعر المعروض والهامش."""
	doc = frappe.get_doc("Print Estimate", name)
	if doc.docstatus != 1:
		frappe.throw(_("رحّل التقدير أولًا"))
	if doc.print_job:
		return doc.print_job
	customer = doc.billing_customer()
	if not doc.customer:
		doc.db_set("customer", customer)
	papers = "، ".join(f"{c.paper} ({c.component})" if len(doc.components) > 1 else c.paper for c in doc.components)
	colors = {c.color for c in doc.components}
	pj = frappe.new_doc("Print Job")
	pj.update({
		"company": doc.company, "customer": customer, "job_title": doc.title, "product_type": doc.product_type if doc.product_type in
			("كتاب", "كتيب", "مجلة", "بطاقات", "ملصق", "لوحة", "صورة مخطوطة", "هدية") else "أخرى",
		"quantity": doc.quantity, "size": f"{doc.finished_width_mm:g}×{doc.finished_height_mm:g} مم" if doc.finished_width_mm else doc.size_preset,
		"pages": doc.pages, "paper": papers, "color": "ملون" if colors == {"ملون"} else ("أبيض وأسود" if colors == {"أحادي"} else "مختلط"),
		"binding": BINDING_TO_JOB.get(doc.binding, "بلا"), "finishing": "، ".join(f.finishing_service for f in doc.finishing),
		"artwork": doc.artwork, "margin_percent": doc.margin_applied or doc.margin_percent, "quoted_price": doc.net_total,
		"due_date": doc.delivery_date, "estimate": doc.name, "quotation": doc.quotation,
		"notes": _("من التقدير {0}").format(doc.name) + (("\n" + _("طلبات العميل: {0}").format(doc.customer_notes)) if doc.customer_notes else ""),
	})
	for c in doc.components:
		pj.append("cost_items", {"component": "ورق", "description": f"{c.component}: {c.paper} — {c.sheets} " + _("فرخ"), "qty": 1, "rate": c.paper_cost})
		pj.append("cost_items", {"component": "طباعة/حبر", "description": f"{c.component}: {c.machine} — {c.impressions} " + _("مرور"), "qty": 1, "rate": c.print_cost})
	for f in doc.finishing:
		comp = "تجليد" if f.finishing_service and frappe.db.get_value("Finishing Service", f.finishing_service, "category") == "تجليد" else "تشطيب"
		label = f"{f.finishing_service} ({f.basis} × {f.qty:g})" + (" — " + _("لدى جهة خارجية") if f.outsourced else "")
		pj.append("cost_items", {"component": comp, "description": label, "qty": 1, "rate": f.amount})
	for e in doc.extras:
		pj.append("cost_items", {"component": e.component, "description": e.description, "qty": e.qty, "rate": e.rate})
	if flt(doc.design_hours):
		pj.append("cost_items", {"component": "تصميم", "description": _("{0} ساعة تصميم").format(doc.design_hours), "qty": doc.design_hours, "rate": doc.design_rate})
	pj.insert(ignore_permissions=True)
	doc.db_set("print_job", pj.name)
	return pj.name


def quotation_status_sync(quotation, status):
	pe_name = frappe.db.get_value("Print Estimate", {"quotation": quotation}, "name")
	if pe_name:
		frappe.db.set_value("Print Estimate", pe_name, "status", status, update_modified=False)


def expire_estimates():
	"""مهمة يومية: التقديرات المُرسلة التي تجاوزت «صالح حتى» تصير «منتهي الصلاحية» (التي لها عرض سعر ERPNext يزامنها عرض السعر أيضًا)."""
	frappe.db.sql("""update `tabPrint Estimate` set status = 'منتهي الصلاحية'
		where docstatus = 1 and status = 'مُرسل' and valid_until is not null and valid_until < %s""", (today(),))
	frappe.db.commit()
