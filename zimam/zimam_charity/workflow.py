# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""سير اعتماد سند الصرف (كما في وقاف): المحاسب يسجّل ويحيل ← مدير المالية يراجع ← الرئيس التنفيذي يعتمد (فوق الحد)
← أمين الصندوق يدفع. يُنشأ Workflow قياسيًا في Frappe فتظهر أزرار الإجراء في النموذج وتُسجَّل الانتقالات في التعليقات.

آمن للتكرار: يُعاد بناء الحالات والانتقالات عند كل استدعاء (التغييرات في التعريف تصل إلى المواقع مع الترحيل)."""
import frappe

WORKFLOW_NAME = "سند صرف — سلسلة الاعتماد"
DOCTYPE = "Payment Voucher"

ACCOUNTANT, FIN_MGR, APPROVER, CASHIER, SYS = "محاسب مالي", "مدير مالي", "معتمد الصرف", "أمين صندوق", "System Manager"

# (الحالة, docstatus, من يجوز له التعديل في هذه الحالة, لون المؤشر)
STATES = [
	("مسودة", 0, ACCOUNTANT, "Gray"),
	("مراجعة المالية", 0, FIN_MGR, "Blue"),
	("بانتظار اعتماد الرئيس التنفيذي", 0, APPROVER, "Orange"),
	("جاهز للدفع", 1, CASHIER, "Purple"),
	("مدفوع", 1, CASHIER, "Green"),
	("مرفوض", 0, ACCOUNTANT, "Red"),
	("ملغى", 2, SYS, "Gray"),
]

# (من, الإجراء, إلى, الدور, الشرط, اعتماد ذاتي مسموح)
# قاعدة Frappe: من ينفّذ الانتقال يجب أن يحمل دور «يجوز له التعديل» في الحالة الحالية (المصدر) — لذا الإلغاء من «جاهز للدفع» لأمين الصندوق
TRANSITIONS = [
	("مسودة", "إحالة لمراجعة المالية", "مراجعة المالية", ACCOUNTANT, "", 1),
	("مراجعة المالية", "اعتماد المالية", "بانتظار اعتماد الرئيس التنفيذي", FIN_MGR, "doc.requires_ceo_approval == 1", 0),
	("مراجعة المالية", "اعتماد المالية", "جاهز للدفع", FIN_MGR, "doc.requires_ceo_approval != 1", 0),
	("مراجعة المالية", "رفض", "مرفوض", FIN_MGR, "", 1),
	("مراجعة المالية", "إعادة إلى المحاسب", "مسودة", FIN_MGR, "", 1),
	("بانتظار اعتماد الرئيس التنفيذي", "اعتماد", "جاهز للدفع", APPROVER, "", 0),
	("بانتظار اعتماد الرئيس التنفيذي", "رفض", "مرفوض", APPROVER, "", 1),
	("جاهز للدفع", "تسجيل الدفع", "مدفوع", CASHIER, "", 1),
	("جاهز للدفع", "إلغاء", "ملغى", CASHIER, "", 1),
	("مرفوض", "إعادة التقديم بعد التصحيح", "مراجعة المالية", ACCOUNTANT, "", 1),
]


def ensure_states():
	for state, _ds, _role, color in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": {"Gray": "", "Blue": "Primary", "Orange": "Warning", "Purple": "Info", "Green": "Success", "Red": "Danger"}.get(color, "")}).insert(ignore_permissions=True)
	for action in {t[1] for t in TRANSITIONS}:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)


def ensure_payment_voucher_workflow():
	ensure_states()
	allow_self = 1 if frappe.db.get_single_value("Charity Settings", "allow_self_approval") else 0
	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		wf = frappe.get_doc("Workflow", WORKFLOW_NAME)
	else:
		wf = frappe.new_doc("Workflow")
		wf.workflow_name = WORKFLOW_NAME
	wf.document_type = DOCTYPE
	wf.is_active = 1
	wf.override_status = 0
	wf.send_email_alert = 1 if frappe.db.get_single_value("Charity Settings", "notify_on_stage_change") else 0
	wf.workflow_state_field = "workflow_state"
	wf.states = []
	for state, ds, role, _color in STATES:
		wf.append("states", {"state": state, "doc_status": str(ds), "allow_edit": role})
	wf.transitions = []
	for src, action, dst, role, cond, self_ok in TRANSITIONS:
		wf.append("transitions", {"state": src, "action": action, "next_state": dst, "allowed": role, "condition": cond,
			"allow_self_approval": 1 if (self_ok or allow_self) else 0})
		# مدير النظام يستطيع كل إجراء (للإدارة والعرض)
		wf.append("transitions", {"state": src, "action": action, "next_state": dst, "allowed": SYS, "condition": cond, "allow_self_approval": 1})
	wf.flags.ignore_permissions = True
	wf.save()
	return wf.name
