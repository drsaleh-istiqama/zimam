# -*- coding: utf-8 -*-
"""ربط مستندات البيع القياسية (عرض سعر، أمر بيع، فاتورة) بمستندات زِمام المصدر.

الحقول المخصصة (setup/install.py): Sales Invoice.zimam_ref_doctype/zimam_ref_name · Quotation/Sales Order.zimam_print_job
"""
import frappe

INVOICE_BACKREF = {
	"Restoration Job": "sales_invoice",
	"Print Job": "sales_invoice",
	"Service Request": "sales_invoice",
}


def sales_invoice_on_submit(doc, method=None):
	ref_dt, ref_dn = doc.get("zimam_ref_doctype"), doc.get("zimam_ref_name")
	if ref_dt in INVOICE_BACKREF and ref_dn and frappe.db.exists(ref_dt, ref_dn):
		frappe.db.set_value(ref_dt, ref_dn, INVOICE_BACKREF[ref_dt], doc.name, update_modified=False)


def sales_invoice_on_cancel(doc, method=None):
	ref_dt, ref_dn = doc.get("zimam_ref_doctype"), doc.get("zimam_ref_name")
	if ref_dt in INVOICE_BACKREF and ref_dn and frappe.db.exists(ref_dt, ref_dn):
		field = INVOICE_BACKREF[ref_dt]
		if frappe.db.get_value(ref_dt, ref_dn, field) == doc.name:
			frappe.db.set_value(ref_dt, ref_dn, field, None, update_modified=False)


def quotation_on_submit(doc, method=None):
	pj = doc.get("zimam_print_job")
	if pj and frappe.db.exists("Print Job", pj):
		frappe.db.set_value("Print Job", pj, {"quotation": doc.name, "status": "مُسعَّر"}, update_modified=False)
	_assessment_sync(doc, "مُرسل")


def quotation_on_update_after_submit(doc, method=None):
	status = {"Ordered": "مقبول", "Lost": "مرفوض", "Expired": "منتهي الصلاحية"}.get(doc.status)
	if status:
		_assessment_sync(doc, status)


def quotation_on_cancel(doc, method=None):
	_assessment_sync(doc, "مسودة", clear=True)


STATUS_SYNC_DOCTYPES = ("Restoration Assessment", "Print Estimate")


def _assessment_sync(doc, status, clear=False):
	"""يزامن حالة المستند المصدر (تقييم ترميم / تقدير طباعة) مع عرض السعر: مُرسل/مقبول/مرفوض/منتهي، ويفكّ الربط عند الإلغاء."""
	ref_dt, ref_dn = doc.get("zimam_ref_doctype"), doc.get("zimam_ref_name")
	if ref_dt not in STATUS_SYNC_DOCTYPES or not ref_dn:
		return
	if not frappe.db.exists(ref_dt, ref_dn):
		return
	values = {"status": status}
	if clear:
		values["quotation"] = None
	frappe.db.set_value(ref_dt, ref_dn, values, update_modified=False)


def sales_order_on_submit(doc, method=None):
	pj = doc.get("zimam_print_job")
	if pj and frappe.db.exists("Print Job", pj):
		frappe.db.set_value("Print Job", pj, {"sales_order": doc.name, "status": "معتمد"}, update_modified=False)
