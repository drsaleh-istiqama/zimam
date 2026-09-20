# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate, nowdate


class Member(Document):
	def validate(self):
		if not self.membership_number:
			self.membership_number = self.name

	def after_insert(self):
		if not self.donor:
			donor = frappe.get_doc({"doctype": "Donor", "donor_name": self.member_name, "donor_type": "فرد", "phone": self.phone,
				"email": self.email, "national_id": self.national_id, "member": self.name}).insert(ignore_permissions=True)
			self.db_set("donor", donor.name)

	@frappe.whitelist()
	def make_fee_donation(self, category=None):
		"""اشتراك العضوية = إيصال تبرع على فئة الاشتراكات؛ يُحدَّث «مسدَّد حتى» عند ترحيله."""
		if not category:
			category = frappe.db.get_value("Donation Category", {"category_name": "اشتراكات الأعضاء"}, "name")
		if not category:
			frappe.throw(_("أنشئ فئة «اشتراكات الأعضاء» أولًا"))
		don = frappe.get_doc({"doctype": "Donation", "donor": self.donor, "donor_name": self.member_name, "member": self.name,
			"amount": self.annual_fee, "donation_category": category, "channel": "نقد", "purpose": _("اشتراك عضوية {0}").format(self.name)})
		don.insert(ignore_permissions=True)
		return don.name


def on_membership_fee_paid(donation):
	"""تُستدعى من إيصال التبرع عند ترحيله إن كان لعضو على فئة الاشتراكات."""
	member = donation.member
	if not member:
		return
	cat_name = frappe.db.get_value("Donation Category", donation.donation_category, "category_name")
	if cat_name != "اشتراكات الأعضاء":
		return
	current = frappe.db.get_value("Member", member, "fee_paid_until")
	base = getdate(current) if current and getdate(current) > getdate(nowdate()) else getdate(donation.donation_date or nowdate())
	frappe.db.set_value("Member", member, "fee_paid_until", add_months(base, 12), update_modified=False)
