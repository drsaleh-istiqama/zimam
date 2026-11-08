# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""الإشعارات المالية (0.17.0) فوق notify_roles (إشعار داخلي + بريد). كانت الإشعارات قائمة لسلسلة الصرف وحدها.

أحداث (hooks.py):
- فاتورة مبيعات معتمدة ........ ← المحاسب
- سند قبض جديد (مسودة) ........ ← المحاسب ليعتمده (يُستثنى مُنشئه)
- سند قبض معتمد ............... ← مدير المالية (يُستثنى معتمِده)
مهمة يومية (send_finance_alerts): فواتير يحلّ استحقاقها قريبًا · صناديق نزل رصيدها الدفتري عن حدّها (ملخص واحد لكل نوع).
يُعطَّل الكل من «إعدادات زِمام ⟵ التحصيل والإشعارات المالية»؛ وفشل الإشعار لا يمنع حفظ ولا اعتماد أي مستند أبدًا.
المتأخرات ووعود السداد تتولاها مهمة التحصيل (collection_followup.send_overdue_reminders).
"""
import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, nowdate

from zimam.utils import get_settings, notify_roles

ACCOUNTANT, FIN_MGR = "محاسب مالي", "مدير مالي"


def events_enabled():
	"""الحقل الجديد غير المحفوظ بعد في الإعدادات القائمة يُعدّ مفعَّلًا (افتراضه 1)."""
	v = get_settings().get("notify_finance_events")
	return v is None or bool(cint(v))


def _run(fn, doc):
	"""الإشعار لا يوقف الحفظ/الاعتماد: أي خطأ يُسجَّل ويُبتلع."""
	try:
		if events_enabled():
			fn(doc)
	except Exception:
		frappe.log_error(title="zimam: finance notice failed")


def money(v, currency=None):
	return "%.3f %s" % (flt(v), currency or "")


def _invoice_submitted(doc):
	if doc.get("is_return"):
		return
	notify_roles([ACCOUNTANT], _("صدرت فاتورة مبيعات {0}").format(doc.name),
		_("فاتورة {0} للعميل {1} بمبلغ {2}، استحقاقها {3}.").format(doc.name, doc.customer_name or doc.customer, money(doc.get("rounded_total") or doc.grand_total, doc.currency), doc.due_date or "—"),
		"Sales Invoice", doc.name, exclude=frappe.session.user)


def _receipt_created(doc):
	if doc.payment_type != "Receive":
		return
	notify_roles([ACCOUNTANT], _("سند قبض بانتظار الاعتماد {0}").format(doc.name),
		_("سجّل {0} سند قبض {1} من {2} بمبلغ {3}. راجعه واعتمده.").format(frappe.session.user, doc.name, doc.party_name or doc.party or "—", money(doc.received_amount, doc.paid_to_account_currency)),
		"Payment Entry", doc.name, exclude=frappe.session.user)


def _receipt_submitted(doc):
	if doc.payment_type != "Receive":
		return
	notify_roles([FIN_MGR], _("قبض معتمد {0}").format(doc.name),
		_("اعتُمد سند القبض {0} من {1} بمبلغ {2} في {3}.").format(doc.name, doc.party_name or doc.party or "—", money(doc.received_amount, doc.paid_to_account_currency), doc.get("zimam_fund") or doc.paid_to),
		"Payment Entry", doc.name, exclude=frappe.session.user)


def sales_invoice_on_submit(doc, method=None):
	_run(_invoice_submitted, doc)


def payment_entry_after_insert(doc, method=None):
	_run(_receipt_created, doc)


def payment_entry_on_submit(doc, method=None):
	_run(_receipt_submitted, doc)


# ---------------------------------------------------------------------------
# المهمة اليومية
# ---------------------------------------------------------------------------
def due_soon_message(invoices, days):
	"""invoices: [{name, outstanding_amount}] → (العنوان, النص) أو None."""
	if not invoices:
		return None
	total = sum(flt(i["outstanding_amount"]) for i in invoices)
	return (_("فواتير يحلّ استحقاقها خلال {0} أيام").format(days),
		_("{0} فاتورة بإجمالي متبقٍ {1} يحلّ استحقاقها قريبًا — تواصل مع عملائها قبل الموعد (تقرير «أعمار الديون»).").format(len(invoices), "%.3f" % total))


def low_funds(funds):
	"""funds: [{name, label, book_balance, threshold}] → المنخفضة بترتيب الأشد."""
	low = [f for f in funds if flt(f["threshold"]) > 0 and flt(f["book_balance"]) < flt(f["threshold"])]
	return sorted(low, key=lambda f: flt(f["book_balance"]) - flt(f["threshold"]))


def low_funds_message(low):
	if not low:
		return None
	lines = _("؛ ").join(_("{0}: الدفتري {1} دون الحد {2}").format(f["label"], "%.3f" % flt(f["book_balance"]), "%.3f" % flt(f["threshold"])) for f in low)
	return _("انخفاض رصيد {0} صندوق").format(len(low)), lines


def send_finance_alerts():
	"""مهمة يومية: استحقاق قريب + صناديق منخفضة (ملخص واحد لكل نوع)."""
	if not events_enabled():
		return
	days = cint(get_settings().get("due_soon_days") if get_settings().get("due_soon_days") is not None else 3)
	if days > 0:
		today = nowdate()
		upcoming = frappe.get_all("Sales Invoice", filters={"docstatus": 1, "is_return": 0, "outstanding_amount": [">", 0],
			"due_date": ["between", [today, add_days(today, days)]]}, fields=["name", "outstanding_amount"])
		msg = due_soon_message(upcoming, days)
		if msg:
			notify_roles([ACCOUNTANT, FIN_MGR], msg[0], msg[1], "Report", "Receivables Aging")
	from zimam.zimam_core.finance import fund_balances
	funds = []
	for f in frappe.get_all("Treasury Fund", filters={"is_active": 1, "low_balance_alert": [">", 0]}, fields=["name", "fund_name", "low_balance_alert"]):
		funds.append({"name": f.name, "label": f.fund_name or f.name, "book_balance": fund_balances(f.name)["book_balance"], "threshold": f.low_balance_alert})
	msg = low_funds_message(low_funds(funds))
	if msg:
		notify_roles([FIN_MGR], msg[0], msg[1], "Report", "Fund Balances")
