# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
"""الرقم المدني في ملف الموظف (0.18.0).

الحقل `zimam_civil_id` حقل مخصَّص على Employee (setup/install.py). هنا التحقق عند الحفظ:
- تُحوَّل الأرقام الهندية/الفارسية (٠١٢…) إلى لاتينية وتُحذف المسافات والشرطات، فيُخزَّن دائمًا بصيغة واحدة قابلة للبحث.
- أرقام فقط وبطول معقول (6–12) — لا نفرض 8 خانات صارمة لأن بعض الوثائق أقدم أو أجنبية.
- لا يتكرر بين موظفين غير مغادرين؛ تكراره مع سجل موظف «Left» مسموح (إعادة التعيين) ويُنبَّه إليه.
الحقل اختياري: الفارغ لا يُرفض، فلا يتعطل حفظ الموظفين القائمين قبل تعبئته.
"""
import frappe
from frappe import _

DIGITS = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
DIGITS.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})
MIN_LEN, MAX_LEN = 6, 12


def normalize_civil_id(value):
	"""«٩٨ ٧٦-٥٤٣٢١» ⟵ «98765432 1» → 987654321؛ الفارغ يرجع فارغًا."""
	if value is None:
		return ""
	s = str(value).translate(DIGITS)
	return "".join(ch for ch in s if ch not in " \t-_.‏‎‪‫‬")


def employee_validate(doc, method=None):
	raw = doc.get("zimam_civil_id")
	civil = normalize_civil_id(raw)
	if not civil:
		doc.zimam_civil_id = ""
		return
	if not civil.isdigit():
		frappe.throw(_("الرقم المدني يتكوّن من أرقام فقط."), title=_("الرقم المدني غير صحيح"))
	if not MIN_LEN <= len(civil) <= MAX_LEN:
		frappe.throw(_("الرقم المدني ({0}) يجب أن يكون بين {1} و{2} خانة.").format(civil, MIN_LEN, MAX_LEN), title=_("الرقم المدني غير صحيح"))
	doc.zimam_civil_id = civil

	same = frappe.get_all("Employee", filters={"zimam_civil_id": civil, "name": ["!=", doc.name or ""]}, fields=["name", "employee_name", "status"])
	active = [e for e in same if e.get("status") != "Left"]
	if active:
		frappe.throw(_("الرقم المدني {0} مسجَّل لموظف آخر: {1} ({2}).").format(civil, active[0].get("employee_name") or active[0].name, active[0].name),
			title=_("رقم مدني مكرَّر"))
	if same:
		frappe.msgprint(_("الرقم المدني {0} مسجَّل لسجل موظف سابق: {1}. تأكد أنها إعادة تعيين لا تكرار.").format(civil, same[0].name), indicator="orange")
