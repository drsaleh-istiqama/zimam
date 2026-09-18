# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
"""تقييم وعرض تكلفة ترميم: يسعّر أوعية (مخطوطات/وثائق/كتب) بندًا بندًا من كتالوج «نظام التقييم الموحد»
(أصناف خدمة + قائمة أسعار)، ثم يولّد عرض سعر ERPNext قياسيًا (بضريبة وشروط دفع وصلاحية) وطلبات ترميم لكل وعاء."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, flt, getdate, nowdate

from zimam.utils import get_heritage_settings, get_settings, hijri_str


class RestorationAssessment(Document):
	def validate(self):
		hs = get_heritage_settings()
		if not self.company:
			self.company = hs.restoration_company or get_settings().parent_company
		if self.assessment_type == "تقييم داخلي لخزانة" and self.billing_type == "فاتورة عميل":
			self.billing_type = "فوترة بينية للمؤسسة"
		if self.assessment_type == "عرض سعر لعميل" and not self.customer:
			frappe.throw(_("حدد العميل"))
		if not self.price_list:
			self.price_list = hs.restoration_price_list
		if self.validity_days is None or self.validity_days == 0:
			self.validity_days = hs.default_validity_days or 30
		if self.advance_percent is None:
			self.advance_percent = hs.default_advance_percent or 0
		if self.warranty_months is None:
			self.warranty_months = hs.default_warranty_months or 12
		if self.tax_rate is None:
			self.tax_rate = flt(hs.default_tax_rate)
		if not self.date_hijri or (not self.is_new() and self.has_value_changed("assessment_date")):
			self.date_hijri = hijri_str(self.assessment_date)
		self.valid_until = add_days(getdate(self.assessment_date), int(self.validity_days))
		self.compute_totals()
		if not self.terms:
			self.terms = self.default_terms()

	def compute_totals(self):
		net, pages, objects = 0.0, 0, set()
		for row in self.items:
			if not row.rate and row.service_item and self.price_list:
				row.rate = get_rate(row.service_item, self.price_list)
			row.amount = flt(row.qty) * flt(row.rate)
			net += row.amount
			pages += int(row.pages or 0)
			objects.add(row.object_code or row.cabinet_item or row.title)
		self.net_total = net
		self.total_pages = pages
		self.total_objects = len(objects)
		tax = net * flt(self.tax_rate) / 100.0
		self.tax_amount = float(round(tax)) if self.round_tax else round(tax, 3)
		self.grand_total = flt(self.net_total) + flt(self.tax_amount)

	def default_terms(self):
		parts = []
		if self.warranty_months:
			parts.append(_("الضمان: {0} شهرًا من تاريخ تسليم العمل.").format(self.warranty_months))
		if self.validity_days:
			parts.append(_("فترة سريان عرض الأسعار: {0} يومًا من تاريخه.").format(self.validity_days))
		if flt(self.advance_percent):
			parts.append(_("الدفعة المقدمة: {0}% من إجمالي التكاليف قبل بدء العمل.").format(int(flt(self.advance_percent))))
		parts.append(_("تُحفظ المواد الورقية في مكان بارد وجاف."))
		return "\n".join(parts)

	def on_submit(self):
		if self.status == "مسودة":
			self.db_set("status", "مُرسل")

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
		if self.billing_type == "فوترة بينية للمؤسسة":
			customer = get_settings().internal_customer
			if not customer:
				frappe.throw(_("حدد «العميل الداخلي الذي يمثّل المؤسسة» في إعدادات زِمام"))
			return customer
		if self.billing_type == "بلا فوترة":
			frappe.throw(_("التقييم بلا فوترة — لا يُنشأ له عرض سعر"))
		return self.customer


@frappe.whitelist()
def get_rate(item, price_list=None):
	"""سعر الخدمة من قائمة أسعار الترميم، وإلا السعر القياسي للصنف."""
	price_list = price_list or get_heritage_settings().restoration_price_list
	if price_list:
		rate = frappe.db.get_value("Item Price", {"item_code": item, "price_list": price_list, "selling": 1}, "price_list_rate")
		if rate is not None:
			return flt(rate)
	return flt(frappe.db.get_value("Item", item, "standard_rate"))


@frappe.whitelist()
def make_quotation(name):
	"""عرض سعر ERPNext (مسودة) من التقييم: البنود بمرجع رمز الوعاء وعدد صفحاته، الضريبة من القالب،
	شروط الدفع (المقدم) والشروط والأحكام من إعدادات الحزمة التراثية، وتاريخ الصلاحية من التقييم."""
	doc = frappe.get_doc("Restoration Assessment", name)
	if doc.docstatus != 1:
		frappe.throw(_("رحّل التقييم أولًا"))
	if doc.quotation:
		return doc.quotation
	hs = get_heritage_settings()
	q = frappe.new_doc("Quotation")
	q.quotation_to = "Customer"
	q.party_name = doc.billing_customer()
	q.company = doc.company
	q.transaction_date = doc.assessment_date
	q.valid_till = doc.valid_until
	q.zimam_ref_doctype = doc.doctype
	q.zimam_ref_name = doc.name
	if doc.price_list:
		q.selling_price_list = doc.price_list
	for row in doc.items:
		desc = row.title
		if row.object_code:
			desc = f"{row.object_code} — {desc}"
		if row.pages:
			desc += f" ({row.pages} " + _("صفحة") + ")"
		q.append("items", {
			"item_code": row.service_item, "qty": flt(row.qty) or 1, "rate": flt(row.rate), "description": desc,
			"zimam_object_code": row.object_code, "zimam_pages": row.pages,
		})
	template = hs.restoration_taxes_template
	if template:
		from erpnext.controllers.accounts_controller import get_taxes_and_charges
		q.taxes_and_charges = template
		for t in get_taxes_and_charges("Sales Taxes and Charges Template", template):
			q.append("taxes", t)
	if hs.restoration_payment_terms:
		q.payment_terms_template = hs.restoration_payment_terms
	if hs.restoration_terms:
		q.tc_name = hs.restoration_terms
		q.terms = frappe.db.get_value("Terms and Conditions", hs.restoration_terms, "terms")
	elif doc.terms:
		q.terms = doc.terms
	q.set_missing_values()
	q.insert(ignore_permissions=True)
	doc.db_set("quotation", q.name)
	return q.name


@frappe.whitelist()
def make_restoration_jobs(name):
	"""طلب ترميم (مسودة) لكل وعاء في التقييم، بسعره المتفق ومدة ضمانه ومرجع التقييم."""
	doc = frappe.get_doc("Restoration Assessment", name)
	if doc.docstatus != 1:
		frappe.throw(_("رحّل التقييم أولًا"))
	if doc.jobs_created:
		frappe.throw(_("أُنشئت طلبات الترميم لهذا التقييم من قبل"))
	groups = {}
	for row in doc.items:
		key = row.object_code or row.cabinet_item or row.title
		g = groups.setdefault(key, {"row": row, "price": 0.0})
		g["price"] += flt(row.amount)
	created = []
	for key, g in groups.items():
		row = g["row"]
		internal = bool(row.cabinet_item)
		rj = frappe.get_doc({
			"doctype": "Restoration Job", "company": doc.company,
			"source_type": "داخلي - خزانة" if internal else "عميل خارجي",
			"cabinet_item": row.cabinet_item if internal else None,
			"customer": None if internal else doc.customer,
			"object_description": (f"{row.object_code} — " if row.object_code else "") + row.title,
			"object_type": row.object_type, "received_date": nowdate(),
			"billing_type": doc.billing_type, "price": g["price"], "assessment": doc.name,
			"warranty_months": doc.warranty_months,
			"notes": _("من التقييم {0}").format(doc.name),
		})
		rj.insert(ignore_permissions=True)
		created.append(rj.name)
	doc.db_set("jobs_created", 1)
	return created


def quotation_status_sync(quotation, status):
	"""يستدعيه integrations.selling عند ترحيل/إلغاء عرض السعر."""
	ra = frappe.db.get_value("Restoration Assessment", {"quotation": quotation}, "name")
	if ra:
		frappe.db.set_value("Restoration Assessment", ra, "status", status, update_modified=False)
