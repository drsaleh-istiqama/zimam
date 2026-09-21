# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""طلب حساب مستخدم — آلية إنشاء المستخدم وتوزيع الصلاحية له (v0.12، بطلب د. صالح 2026-09-20):

1. **الطلب**: مشرف الوحدة / مدير الذراع / مدير المالية يرفع طلبًا باسم الموظف وبريده والشركة وملف الصلاحيات (الصفة الوظيفية)؛
   يرى كلٌّ طلباته هو فقط. مسؤول الصلاحيات ومدير النظام يرون كل الطلبات ويُخطَرون بالجديد.
2. **الاعتماد والتنفيذ** (`provision`): مسؤول الصلاحيات (أو مدير النظام) يعتمد الطلب فيُنشأ حساب المستخدم ببريده،
   ويُربط بملف الصلاحيات وتُضاف أدواره (+ الأدوار الإضافية إن وُجدت)، ويُقيَّد بشركته/قسمه (User Permission) إن طُلب،
   ويُربط بسجل الموظف، وتصله رسالة ترحيب برابط تعيين كلمة المرور (لا كلمات مرور تُكتب أو تُرسل من هنا).
   إن كان الحساب موجودًا يُفعَّل وتُستكمل أدواره فقط.
3. **الإيقاف / إعادة التفعيل** (`suspend` / `reactivate`): إنهاء خدمة أو نقل ⟵ يُعطَّل الحساب مع بقاء سجلاته؛ وعكسه.

فصل المهام: من يطلب لا ينفّذ (إلا مدير النظام)؛ ولا يُمنح دور «System Manager» إلا من يحمله هو نفسه."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, validate_email_address

from zimam.setup.permissions import ERP_ROLE_SCOPE, R_ACCESS, R_SYS, ROLE_DESCRIPTIONS, apply_role_profile, ensure_user_permission
from zimam.utils import notify_roles

PRIVILEGED = {"System Manager", "Administrator"}


def _can_process():
	return bool({R_ACCESS, R_SYS} & set(frappe.get_roles()))


def _require_processor():
	if not _can_process():
		frappe.throw(_("اعتماد طلبات الحسابات وتنفيذها لمسؤول الصلاحيات أو مدير النظام فقط"), frappe.PermissionError)


class UserAccountRequest(Document):
	def validate(self):
		self.email = (self.email or "").strip().lower()
		validate_email_address(self.email, throw=True)
		self.full_name = (self.full_name or "").strip()
		if not self.requested_by:
			self.requested_by = frappe.session.user
		if self.is_new():
			self.status = "طلب جديد"
		if self.role_profile:
			self.role_profile_summary = profile_summary(self.role_profile)
		# لا يُمنح دور مدير النظام إلا ممن يحمله
		asked = {r.role for r in self.extra_roles or []}
		if asked & PRIVILEGED and "System Manager" not in frappe.get_roles():
			frappe.throw(_("لا يجوز طلب دور «System Manager» إلا لمن يحمله"))
		if self.employee and not self.company:
			self.company = frappe.db.get_value("Employee", self.employee, "company")
		if self.status == "طلب جديد" and frappe.db.exists("User", self.email):
			enabled = frappe.db.get_value("User", self.email, "enabled")
			self.processing_note = _("تنبيه: يوجد حساب بهذا البريد ({0}) — عند الاعتماد يُفعَّل وتُستكمل أدواره فقط").format(
				_("مفعَّل") if enabled else _("موقوف"))

	def after_insert(self):
		notify_roles([R_ACCESS, R_SYS], _("طلب حساب مستخدم جديد {0}: {1}").format(self.name, self.full_name),
			_("البريد {0} · الشركة {1} · ملف الصلاحيات {2} · مقدم الطلب {3}").format(self.email, self.company, self.role_profile, self.requested_by),
			self.doctype, self.name)

	# ------------------------------------------------------------------
	def _stamp(self, status, note=None):
		self.db_set({"status": status, "processed_by": frappe.session.user, "processed_on": now_datetime(),
			"processing_note": note or self.processing_note})
		if self.requested_by and self.requested_by != frappe.session.user:
			frappe.get_doc({"doctype": "Notification Log", "for_user": self.requested_by, "type": "Alert",
				"subject": _("طلب الحساب {0} ({1}): {2}").format(self.name, self.full_name, status), "email_content": note or "",
				"document_type": self.doctype, "document_name": self.name}).insert(ignore_permissions=True)

	def _roles(self):
		roles = [r.role for r in self.extra_roles or [] if frappe.db.exists("Role", r.role)]
		if not frappe.db.exists("Role Profile", self.role_profile):
			frappe.throw(_("ملف الصلاحيات {0} غير موجود على هذا الموقع — شغّل التهيئة أولًا").format(self.role_profile))
		return roles

	@frappe.whitelist()
	def provision(self, note=None, send_welcome_email=1):
		"""اعتماد الطلب وإنشاء الحساب (أو تفعيله واستكمال أدواره) وتوزيع الصلاحية."""
		_require_processor()
		if self.status != "طلب جديد":
			frappe.throw(_("الطلب ليس في حالة «طلب جديد»"))
		extra = self._roles()
		first, _sep, last = self.full_name.partition(" ")
		created = False
		if frappe.db.exists("User", self.email):
			user = frappe.get_doc("User", self.email)
			user.enabled = 1
		else:
			user = frappe.get_doc({"doctype": "User", "email": self.email, "first_name": first or self.email.split("@")[0],
				"last_name": last or None, "mobile_no": self.mobile_no, "language": "ar", "enabled": 1,
				"send_welcome_email": 1 if int(send_welcome_email or 0) else 0})
			user.flags.no_welcome_mail = not int(send_welcome_email or 0)
			created = True
		existing = {r.role for r in user.get("roles") or []}
		for r in extra:
			if r not in existing:
				user.append("roles", {"role": r})
		apply_role_profile(user, self.role_profile)
		user.flags.ignore_permissions = True
		if created:
			user.insert()
		else:
			user.save()
		# القيود: الشركة والقسم
		restrictions = []
		if self.restrict_to_company and self.company:
			ensure_user_permission(user.name, "Company", self.company)
			restrictions.append(_("الشركة {0}").format(self.company))
		if self.restrict_to_department and self.department:
			ensure_user_permission(user.name, "Department", self.department)
			restrictions.append(_("القسم {0}").format(self.department))
		# ربط سجل الموظف بحساب الدخول (الخدمة الذاتية)
		if self.employee and frappe.db.exists("Employee", self.employee) and not frappe.db.get_value("Employee", self.employee, "user_id"):
			frappe.db.set_value("Employee", self.employee, "user_id", user.name)
		summary = _("{0} الحساب {1} بملف الصلاحيات «{2}»").format(_("أُنشئ") if created else _("فُعِّل وحُدِّث"), user.name, self.role_profile)
		if extra:
			summary += _(" + أدوار إضافية: {0}").format("، ".join(extra))
		if restrictions:
			summary += _(" · مقيَّد بـ: {0}").format("، ".join(restrictions))
		if created and int(send_welcome_email or 0):
			summary += _(" · أُرسلت رسالة الترحيب برابط تعيين كلمة المرور")
		if note:
			summary += "\n" + note
		self.db_set("user", user.name)
		self._stamp("معتمد ومنفَّذ", summary)
		return user.name

	@frappe.whitelist()
	def reject(self, note):
		_require_processor()
		if self.status != "طلب جديد":
			frappe.throw(_("الطلب ليس في حالة «طلب جديد»"))
		if not note:
			frappe.throw(_("اكتب سبب الرفض"))
		self._stamp("مرفوض", note)

	@frappe.whitelist()
	def suspend(self, note):
		"""إيقاف الحساب (إنهاء خدمة/نقل) — يبقى الحساب وسجلاته، ويُمنع الدخول."""
		_require_processor()
		if self.status != "معتمد ومنفَّذ" or not self.user:
			frappe.throw(_("لا حساب منفَّذ لإيقافه"))
		if self.user == frappe.session.user:
			frappe.throw(_("لا يمكنك إيقاف حسابك أنت"))
		frappe.db.set_value("User", self.user, "enabled", 0)
		self._stamp("موقوف", note or _("أُوقف الحساب"))

	@frappe.whitelist()
	def reactivate(self, note=None):
		_require_processor()
		if self.status != "موقوف" or not self.user:
			frappe.throw(_("الطلب ليس موقوفًا"))
		frappe.db.set_value("User", self.user, "enabled", 1)
		self._stamp("معتمد ومنفَّذ", note or _("أُعيد تفعيل الحساب"))


@frappe.whitelist()
def profile_summary(role_profile):
	"""ملخص مقروء لملف الصلاحيات: أدواره وما يمنحه كل دور — يظهر في الطلب قبل الاعتماد."""
	if not role_profile or not frappe.db.exists("Role Profile", role_profile):
		return ""
	roles = frappe.get_all("Has Role", filters={"parent": role_profile, "parenttype": "Role Profile"}, pluck="role")
	lines = []
	for r in roles:
		desc = ROLE_DESCRIPTIONS.get(r) or ERP_ROLE_SCOPE.get(r) or ""
		lines.append(f"• {r}" + (f": {desc}" if desc else ""))
	desk = any(frappe.db.get_value("Role", r, "desk_access") for r in roles)
	lines.append(_("نوع الحساب: {0}").format(_("مستخدم نظام (سطح المكتب)") if desk else _("مستخدم موقع (بوابة خارجية فقط)")))
	return "\n".join(lines)


@frappe.whitelist()
def role_profiles_catalog():
	"""قائمة ملفات الصلاحيات المتاحة بوصفها (لحوار الاختيار والمصفوفة)."""
	from zimam.setup.permissions import ROLE_PROFILES
	out = []
	for name, desc, roles in ROLE_PROFILES:
		if frappe.db.exists("Role Profile", name):
			out.append({"name": name, "description": desc, "roles": roles})
	return out


@frappe.whitelist()
def effective_permissions(user):
	"""«ماذا يستطيع هذا الحساب فعلًا؟» — انظر zimam.setup.permissions.effective_permissions."""
	from zimam.setup.permissions import effective_permissions as _eff
	return _eff(user)
