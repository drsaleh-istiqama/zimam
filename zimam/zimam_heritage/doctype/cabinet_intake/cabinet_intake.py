# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
# For license information, please see license.txt
"""استلام خزانة: عند الترحيل يُنشأ سجل «خزانة» وقيد استلام مخزون بقيمة صفرية برقم تسلسلي = رمز الخزانة.
الخزانة مادة خام تدخل بقيمة صفرية وبنوع ملكية صريح؛ لا تُستهلك ولا تُباع، والمُسعَّر مخرجات معالجتها."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate

from zimam.utils import get_heritage_settings, notify_roles


class CabinetIntake(Document):
	def validate(self):
		if self.ownership_type == "أمانة مؤقتة" and not self.return_due_date:
			frappe.throw(_("حدد تاريخ الإعادة المتوقع للأمانة المؤقتة"))
		if self.return_due_date and getdate(self.return_due_date) < getdate(self.intake_date):
			frappe.throw(_("تاريخ الإعادة لا يسبق تاريخ الاستلام"))
		if self.docstatus == 0:
			self.status = "مسودة"

	def on_submit(self):
		cabinet = self.make_cabinet()
		self.db_set("cabinet", cabinet.name)
		stock_entry = self.make_stock_receipt(cabinet)
		if stock_entry:
			self.db_set("stock_entry", stock_entry)
			serial = frappe.db.get_value("Serial No", {"serial_no": cabinet.name}, "name")
			if serial:
				cabinet.db_set("serial_no", serial)
		self.db_set("status", "مستلمة")

	def on_cancel(self):
		if self.cabinet and frappe.db.count("Cabinet Item", {"cabinet": self.cabinet}):
			frappe.throw(_("لا يمكن إلغاء الاستلام: الخزانة {0} تحوي مقتنيات مسجلة").format(self.cabinet))
		if self.stock_entry:
			se = frappe.get_doc("Stock Entry", self.stock_entry)
			if se.docstatus == 1:
				se.cancel()
		if self.cabinet:
			frappe.db.set_value("Cabinet", self.cabinet, "status", "ملغاة")
		self.db_set("status", "ملغاة")

	def make_cabinet(self):
		cabinet = frappe.get_doc({
			"doctype": "Cabinet", "cabinet_name": self.cabinet_name, "depositor": self.depositor, "intake": self.name,
			"ownership_type": self.ownership_type, "origin_wilayat": self.origin_wilayat, "origin_place": self.origin_place,
			"storage_warehouse": get_heritage_settings().incoming_cabinets_warehouse, "condition": self.condition,
			"cover_image": self.intake_photo, "status": "واردة", "notes": self.terms,
		})
		cabinet.insert(ignore_permissions=True)
		return cabinet

	def make_stock_receipt(self, cabinet):
		hs = get_heritage_settings()
		if not hs.incoming_cabinet_item or not hs.incoming_cabinets_warehouse:
			frappe.msgprint(_("لم يُنشأ قيد مخزون: صنف «خزانة واردة» أو مستودع الخزائن غير محدد في إعدادات الحزمة التراثية"), indicator="orange", alert=True)
			return None
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.purpose = "Material Receipt"
		se.company = self.company
		se.posting_date = self.intake_date
		se.remarks = _("استلام الخزانة {0} من {1} — نوع الملكية: {2}").format(cabinet.name, self.depositor_name, self.ownership_type)
		se.append("items", {
			"item_code": hs.incoming_cabinet_item, "qty": 1, "t_warehouse": hs.incoming_cabinets_warehouse,
			"basic_rate": 0, "allow_zero_valuation_rate": 1, "use_serial_batch_fields": 1, "serial_no": cabinet.name,
		})
		se.insert(ignore_permissions=True)
		se.submit()
		return se.name


def send_return_due_reminders():
	"""مهمة يومية: تنبيه قبل موعد إعادة الأمانات المؤقتة بأسبوع وعند تجاوزه."""
	today = getdate(nowdate())
	due = frappe.get_all("Cabinet Intake",
		filters={"docstatus": 1, "ownership_type": "أمانة مؤقتة", "status": ["not in", ["مُعادة", "ملغاة"]], "return_due_date": ["<=", add_days(today, 7)]},
		fields=["name", "cabinet_name", "depositor_name", "return_due_date", "cabinet"])
	for row in due:
		overdue = getdate(row.return_due_date) < today
		subject = _("أمانة مؤقتة {0}: {1}").format("متأخرة الإعادة" if overdue else "يحلّ موعد إعادتها", row.cabinet_name)
		message = _("الخزانة {0} ({1}) للمودع {2} موعد إعادتها {3}.").format(row.cabinet or row.name, row.cabinet_name, row.depositor_name, frappe.format(row.return_due_date, "Date"))
		notify_roles(["مشرف وحدة", "مدير المؤسسة"], subject, message, "Cabinet Intake", row.name)
