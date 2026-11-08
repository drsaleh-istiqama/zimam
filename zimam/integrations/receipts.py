# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""سند القبض في زِمام (0.14.0): طبقة عربية فوق «قيد دفع» (Payment Entry) من نوع «استلام» — دون مستند موازٍ ودون تكرار قيد.

الحقول المخصصة (setup/install.py): Payment Entry.zimam_fund (الصندوق) · zimam_date_hijri (التاريخ الهجري المحسوب).
الأحداث (hooks.py): Payment Entry.before_validate.

القواعد:
- الصندوق (اختياري): إن اختير فحساب الاستلام هو حساب الصندوق وشركتهما واحدة، فتظهر المقبوضات في «أرصدة الصناديق» لأنها تُحسب من الأستاذ.
- فصل المهام: من لا يحمل دورًا محاسبيًا (أمين الصندوق مثلًا) يحفظ سندات القبض فقط، ولا يحفظ سند دفع؛ والاعتماد (submit) للمحاسب.
"""
import frappe
from frappe import _

from zimam.utils import hijri_str

ACCOUNTING_ROLES = {"Accounts User", "Accounts Manager", "System Manager"}


def payment_entry_before_validate(doc, method=None):
	if doc.get("posting_date"):
		doc.zimam_date_hijri = hijri_str(doc.posting_date)

	if doc.payment_type != "Receive":
		# أمين الصندوق وأمثاله: لا يحفظون إلا سندات القبض (سند الدفع يمر بسلسلة سند الصرف)
		if not (set(frappe.get_roles()) & ACCOUNTING_ROLES):
			frappe.throw(_("صلاحيتك تتيح حفظ سندات القبض فقط. سند الدفع يُسجَّل بسند صرف يمر بسلسلة الاعتماد."))
		doc.zimam_fund = None
		return

	fund = doc.get("zimam_fund")
	if not fund:
		return
	account, company = frappe.db.get_value("Treasury Fund", fund, ["account", "company"]) or (None, None)
	if not account:
		frappe.throw(_("الصندوق {0} بلا حساب أستاذ").format(fund))
	if doc.company and company and doc.company != company:
		frappe.throw(_("الصندوق {0} تابع للشركة {1} لا {2}").format(fund, company, doc.company))
	if not doc.paid_to:
		doc.paid_to = account
		doc.paid_to_account_currency = frappe.db.get_value("Account", account, "account_currency")
	elif doc.paid_to != account:
		frappe.throw(_("حساب الاستلام ({0}) ليس حساب الصندوق {1} ({2}). اختر الصندوق من جديد أو أفرغه.").format(doc.paid_to, fund, account))
