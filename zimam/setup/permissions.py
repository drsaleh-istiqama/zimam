# -*- coding: utf-8 -*-
"""مصفوفة الصلاحيات في زِمام — المصدر الواحد لكل ما يخص «من يفعل ماذا» (v0.12.0، بطلب د. صالح 2026-09-20).

ثلاث طبقات، كلها تُقرأ من هذا الملف:

1. **الأدوار** (تُنشأ في setup/install.py): عشرة أدوار عامة + أدوار سلسلة الاعتماد + «مسؤول الصلاحيات».
   وصف كل دور هنا (ROLE_DESCRIPTIONS) يظهر في مصفوفة الصلاحيات المولَّدة.
2. **ملفات الصلاحيات** (Frappe «Role Profile» — ROLE_PROFILES): حزمة أدوار لكل صفة وظيفية — دور زِمام + أدوار ERPNext
   القياسية التي تلزمه (Accounts User للمحاسب، Sales User للاستقبال…). إنشاء مستخدم = اختيار ملف صلاحيات واحد؛
   لا تُوزَّع الأدوار فرادى إلا استثناءً (جدول «أدوار إضافية» في طلب الحساب).
3. **صلاحيات مستندات ERPNext القياسية** (STANDARD_PERMS ⟵ Custom DocPerm): ما تمنحه زِمام صراحةً لأدوارها على قيود
   اليومية والفواتير والموظفين… — غالبًا «عرض» للأدوار المشرفة (مدير المؤسسة، معتمد الصرف، أمين الصندوق)؛ أما الإضافة
   والتعديل على المستندات القياسية فتأتي من أدوار ERPNext المضمومة في ملف الصلاحيات.

صلاحيات مستندات زِمام نفسها (27+ نوعًا) تعيش في تعريف كل نوع (tools/gen_doctypes.py ⟵ JSON) وتُقرأ منها عند توليد المصفوفة.

مستويات الصلاحية المعتمدة (بطلب د. صالح: أمام كل صلاحية مستواها — حذف/إضافة/تعديل/عرض):
    عرض     read
    إضافة   read + create
    تعديل   read + write
    إضافة وتعديل  read + create + write
    كامل    read + create + write + delete   (+ اعتماد/إلغاء/تعديل بعد الاعتماد للمستندات المعتمَدة)
    (سجلاته فقط) = if_owner: يرى ويعدّل ما أنشأه هو فقط.

الملف لا يستورد frappe في رأسه كي تقرأه أدوات التوليد الساكنة (tools/build_permissions_matrix.py، tools/validate.py).
"""

# ---------------------------------------------------------------------------
# الأدوار
# ---------------------------------------------------------------------------
R_UNIT = "موظف وحدة"
R_UNIT_SUP = "مشرف وحدة"
R_RECEPTION = "موظف استقبال وخدمة"
R_EXTERNAL = "مستفيد خارجي"
R_PARTNER = "شريك خارجي"
R_TECH_SUP = "مشرف فني"
R_ACCOUNTANT = "محاسب مالي"
R_DESIGNER = "مخرج فني ومصمم"
R_ARM_MGR = "مدير ذراع"
R_INST_MGR = "مدير المؤسسة"
R_FIN_MGR = "مدير مالي"
R_APPROVER = "معتمد الصرف"
R_CASHIER = "أمين صندوق"
R_ACCESS = "مسؤول الصلاحيات"
R_SYS = "System Manager"
R_EMPLOYEE = "Employee"

# أدوار زِمام بترتيب عرضها في المصفوفة
ZIMAM_ROLES = [R_INST_MGR, R_ARM_MGR, R_FIN_MGR, R_ACCOUNTANT, R_APPROVER, R_CASHIER, R_UNIT_SUP, R_UNIT,
	R_RECEPTION, R_TECH_SUP, R_DESIGNER, R_ACCESS, R_EXTERNAL, R_PARTNER]

# (الدور: الوصف الوظيفي المختصر) — يظهر في المصفوفة وفي ملخص ملف الصلاحيات داخل طلب الحساب
ROLE_DESCRIPTIONS = {
	R_INST_MGR: "الرئيس التنفيذي / مدير المؤسسة: اطلاع على كل شيء في كل الشركات، ولوحات المؤشرات — لا يُدخل ولا يعدّل (فصل المهام)؛ اعتماد الصرف بدور «معتمد الصرف»",
	R_ARM_MGR: "مدير ذراع تابع (المطبعة، بيت الترميم، الاستثمار الوقفي): يدير أوامر الطباعة وتقديرات الأسعار وكتالوج المطبعة والبيع والشراء والمخزون ضمن شركته",
	R_FIN_MGR: "مدير المالية: مراجعة سندات الصرف واعتمادها، الصناديق وتصنيفات المصروف، وكل أعمال المحاسبة (Accounts Manager)",
	R_ACCOUNTANT: "المحاسب: تسجيل سندات الصرف وطلبات الصرف، الفوترة والقيود (Accounts User)، الوقفيات والعقارات الوقفية",
	R_APPROVER: "معتمد الصرف (مدير المؤسسة / الرئيس التنفيذي): اعتماد سندات الصرف فوق حد الاعتماد أو رفضها — اطلاع على المالية",
	R_CASHIER: "أمين الصندوق: تسجيل دفع السندات الجاهزة وإلغاؤها؛ اطلاع على القيود وحركات البنك",
	R_UNIT_SUP: "مشرف وحدة (رئيس قسم): يدير أعمال وحدته — الخدمات والفعاليات والإعلام والقانونية والمشاريع — ويعتمد ما يرفعه موظفوه",
	R_UNIT: "موظف وحدة: ينفّذ أعمال وحدته (إدخال وتعديل) ويرفع طلبات الصرف؛ لا يحذف",
	R_RECEPTION: "موظف الاستقبال والخدمة: طلبات الخدمة والمواعيد والمستفيدون والعملاء والتبرعات والعضويات؛ اطلاع على الكتالوجات",
	R_TECH_SUP: "المشرف الفني (الحزمة التراثية): أوامر المعالجة والرقمنة والمقتنيات وحركات المخزون",
	R_DESIGNER: "المخرج الفني والمصمم: أوامر الطباعة وتقديرات الأسعار والفعاليات والإعلام؛ اطلاع على عروض الأسعار والأصناف",
	R_ACCESS: "مسؤول الصلاحيات: يعتمد طلبات حسابات المستخدمين وينشئ الحسابات ويوقفها ويوزّع ملفات الصلاحيات — لا يملك صلاحيات مالية",
	R_EXTERNAL: "مستفيد خارجي (بوابة الموقع): يرفع طلبات خدمة ويتابع طلباته هو فقط",
	R_PARTNER: "شريك خارجي (بوابة الموقع): اطلاع على ما يُشارَك معه فقط",
	R_SYS: "مدير النظام: كل الصلاحيات — للتقني المسؤول عن الموقع فقط",
	R_EMPLOYEE: "موظف (Frappe HR): الخدمة الذاتية — إجازاته وحضوره وقسائم راتبه ومطالباته",
}

# أدوار ERPNext/Frappe القياسية التي تُضم في ملفات الصلاحيات، مع ما يمنحه كل دور (للمصفوفة والملخص)
ERP_ROLE_SCOPE = {
	"Accounts User": "إضافة وتعديل واعتماد قيود اليومية وقيود الدفع وفواتير البيع والشراء؛ لا حذف ولا إلغاء",
	"Accounts Manager": "كل صلاحيات المحاسبة بما فيها الإلغاء والحذف وشجرة الحسابات والفترات المالية والموازنات",
	"Sales User": "العملاء وعروض الأسعار وأوامر البيع (إضافة وتعديل واعتماد)",
	"Sales Manager": "كل صلاحيات البيع بما فيها الإلغاء والحذف والأسعار",
	"Purchase User": "الموردون وأوامر الشراء وفواتير الشراء (إضافة وتعديل واعتماد)",
	"Purchase Manager": "كل صلاحيات الشراء بما فيها الإلغاء والحذف",
	"Stock User": "الأصناف وحركات المخزون والمستودعات (إضافة وتعديل واعتماد)",
	"Stock Manager": "كل صلاحيات المخزون بما فيها الإلغاء والحذف",
	"Item Manager": "إنشاء الأصناف وتعديلها وحذفها",
	"Projects User": "المشاريع والمهام وسجلات الساعات (إضافة وتعديل)",
	"Projects Manager": "كل صلاحيات المشاريع بما فيها الحذف",
	"HR User": "الموظفون والإجازات والحضور والتوظيف (إضافة وتعديل)",
	"HR Manager": "كل صلاحيات الموارد البشرية بما فيها الحذف وهياكل الرواتب",
	"Payroll Manager": "قيود الرواتب وقسائم الرواتب",
	"Leave Approver": "اعتماد طلبات الإجازة",
	"Expense Approver": "اعتماد مطالبات المصروفات",
	"Employee": "الخدمة الذاتية للموظف: طلباته وإجازاته وقسائمه",
	"Report Manager": "بناء التقارير وحفظها ومشاركتها",
	"System Manager": "إدارة النظام كاملة",
}

# ---------------------------------------------------------------------------
# ملفات الصلاحيات (Role Profile) — (الاسم, الوصف, الأدوار)
# ---------------------------------------------------------------------------
PROFILE_PREFIX = "زِمام — "
ROLE_PROFILES = [
	(PROFILE_PREFIX + "مدير المؤسسة", "الرئيس التنفيذي: اطلاع على كل شيء + اعتماد الصرف", [R_INST_MGR, R_APPROVER, R_EMPLOYEE]),
	(PROFILE_PREFIX + "مدير ذراع", "مدير المطبعة / بيت الترميم / الاستثمار — يُقيَّد بشركته", [R_ARM_MGR, "Sales User", "Purchase User", "Stock User", "Projects User", R_EMPLOYEE]),
	(PROFILE_PREFIX + "مدير مالي", "مدير المالية: المراجعة والاعتماد وكل المحاسبة", [R_FIN_MGR, "Accounts Manager", R_EMPLOYEE]),
	(PROFILE_PREFIX + "محاسب مالي", "المحاسب: التسجيل والفوترة والقيود", [R_ACCOUNTANT, "Accounts User", R_EMPLOYEE]),
	(PROFILE_PREFIX + "معتمد الصرف", "معتمد الصرف فوق الحد (حين يُفوَّض غير مدير المؤسسة)", [R_APPROVER, R_EMPLOYEE]),
	(PROFILE_PREFIX + "أمين صندوق", "أمين الصندوق: تسجيل الدفع", [R_CASHIER, R_EMPLOYEE]),
	(PROFILE_PREFIX + "مشرف وحدة", "رئيس قسم: يدير وحدته ومشاريعها", [R_UNIT_SUP, "Projects User", R_EMPLOYEE]),
	(PROFILE_PREFIX + "موظف وحدة", "موظف تنفيذي في وحدة", [R_UNIT, R_EMPLOYEE]),
	(PROFILE_PREFIX + "موظف استقبال وخدمة", "الاستقبال والخدمة والعملاء", [R_RECEPTION, "Sales User", R_EMPLOYEE]),
	(PROFILE_PREFIX + "مشرف فني", "المشرف الفني على المعالجة والرقمنة والمخزون", [R_TECH_SUP, "Stock User", R_EMPLOYEE]),
	(PROFILE_PREFIX + "مخرج فني ومصمم", "التصميم والإخراج وأوامر الطباعة", [R_DESIGNER, R_EMPLOYEE]),
	(PROFILE_PREFIX + "موارد بشرية", "مسؤول الموارد البشرية: الموظفون والإجازات والحضور", ["HR User", "Leave Approver", "Expense Approver", R_EMPLOYEE]),
	(PROFILE_PREFIX + "مدير الموارد البشرية والرواتب", "مدير الموارد البشرية: كل الموارد البشرية والرواتب", ["HR Manager", "HR User", "Payroll Manager", "Leave Approver", "Expense Approver", R_EMPLOYEE]),
	(PROFILE_PREFIX + "مسؤول الصلاحيات", "إنشاء الحسابات وتوزيع ملفات الصلاحيات وإيقافها", [R_ACCESS, R_EMPLOYEE]),
	(PROFILE_PREFIX + "مدير النظام", "التقني المسؤول عن الموقع: كل الصلاحيات", [R_SYS, R_ACCESS, R_EMPLOYEE]),
	(PROFILE_PREFIX + "مستفيد خارجي", "بوابة الموقع: باحث أو مستفيد يرفع طلباته", [R_EXTERNAL]),
	(PROFILE_PREFIX + "شريك خارجي", "بوابة الموقع: شريك يطّلع على ما يُشارَك معه", [R_PARTNER]),
]

# ---------------------------------------------------------------------------
# صلاحيات مستندات ERPNext/HRMS القياسية لأدوار زِمام (Custom DocPerm — permlevel 0)
# ---------------------------------------------------------------------------
# مستويات الصلاحية ⟵ أنواع الصلاحية في Frappe
LEVELS = {
	"عرض": ("read",),
	"إضافة": ("read", "create"),
	"تعديل": ("read", "write"),
	"إضافة وتعديل": ("read", "create", "write"),
	"كامل": ("read", "create", "write", "delete"),
}
LEVEL_ORDER = ["عرض", "إضافة", "تعديل", "إضافة وتعديل", "كامل"]
SUBMIT_PTYPES = ("submit", "cancel", "amend")
AUX_PTYPES = ("report", "export", "print", "email", "share")

RO, RW, FULL = "عرض", "إضافة وتعديل", "كامل"
STANDARD_PERMS = {
	# المالية
	"Journal Entry": {R_INST_MGR: RO, R_APPROVER: RO, R_CASHIER: RO, R_ARM_MGR: RO},
	"Payment Entry": {R_INST_MGR: RO, R_APPROVER: RO, R_CASHIER: RO, R_ARM_MGR: RO},
	"Sales Invoice": {R_INST_MGR: RO, R_FIN_MGR: RO, R_APPROVER: RO, R_ARM_MGR: RO, R_DESIGNER: RO, R_RECEPTION: RO, R_UNIT_SUP: RO},
	"Purchase Invoice": {R_INST_MGR: RO, R_FIN_MGR: RO, R_APPROVER: RO, R_ARM_MGR: RO},
	"Expense Claim": {R_INST_MGR: RO, R_FIN_MGR: RO, R_APPROVER: RO, R_ACCOUNTANT: RO},
	"Budget": {R_INST_MGR: RO, R_FIN_MGR: RO, R_APPROVER: RO, R_ARM_MGR: RO},
	"Bank Transaction": {R_INST_MGR: RO, R_CASHIER: RO},
	"Account": {R_INST_MGR: RO, R_APPROVER: RO, R_CASHIER: RO},
	"Cost Center": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO, R_ARM_MGR: RO, R_UNIT_SUP: RO},
	"Mode of Payment": {R_ACCOUNTANT: RO, R_CASHIER: RO, R_RECEPTION: RO},
	# البيع والشراء والمخزون
	"Quotation": {R_INST_MGR: RO, R_FIN_MGR: RO, R_DESIGNER: RO, R_ACCOUNTANT: RO},
	"Sales Order": {R_INST_MGR: RO, R_FIN_MGR: RO, R_DESIGNER: RO, R_ACCOUNTANT: RO, R_TECH_SUP: RO},
	"Purchase Order": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO},
	"Customer": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO, R_DESIGNER: RO, R_UNIT: RO, R_UNIT_SUP: RO},
	"Supplier": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO, R_CASHIER: RO},
	"Item": {R_INST_MGR: RO, R_ACCOUNTANT: RO, R_DESIGNER: RO, R_RECEPTION: RO, R_UNIT: RO, R_UNIT_SUP: RO},
	"Stock Entry": {R_INST_MGR: RO, R_ACCOUNTANT: RO, R_UNIT_SUP: RO},
	"Warehouse": {R_INST_MGR: RO, R_TECH_SUP: RO, R_UNIT_SUP: RO},
	# المشاريع والتواصل
	"Project": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO, R_APPROVER: RO, R_UNIT: RO, R_RECEPTION: RO, R_DESIGNER: RO},
	"Task": {R_INST_MGR: RO, R_UNIT: RW, R_RECEPTION: RO, R_DESIGNER: RW, R_TECH_SUP: RW},
	"Contact": {R_UNIT: RW, R_UNIT_SUP: RW, R_RECEPTION: RW, R_DESIGNER: RO, R_ARM_MGR: RW},
	"Contract": {R_INST_MGR: RO, R_FIN_MGR: RO, R_UNIT_SUP: RW, R_ARM_MGR: RW},
	# الموارد البشرية (اطلاع محدود؛ الإدخال بأدوار HR)
	"Employee": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO, R_UNIT_SUP: RO, R_ARM_MGR: RO, R_ACCESS: RO},
	"Department": {R_INST_MGR: RO, R_UNIT_SUP: RO, R_ARM_MGR: RO, R_ACCESS: RO},
	"Leave Application": {R_INST_MGR: RO, R_UNIT_SUP: RO, R_ARM_MGR: RO},
	"Attendance": {R_INST_MGR: RO, R_UNIT_SUP: RO, R_ARM_MGR: RO},
	# النظام والشركات
	"Company": {R_INST_MGR: RO, R_FIN_MGR: RO, R_ACCOUNTANT: RO, R_ARM_MGR: RO, R_ACCESS: RO},
	"User": {R_INST_MGR: RO, R_ACCESS: RO},
	"Role Profile": {R_INST_MGR: RO, R_ACCESS: RO, R_UNIT_SUP: RO, R_ARM_MGR: RO, R_FIN_MGR: RO},
	"User Permission": {R_ACCESS: RO},
	"File": {R_UNIT: RW, R_UNIT_SUP: RW, R_RECEPTION: RW, R_DESIGNER: RW, R_TECH_SUP: RW, R_ACCOUNTANT: RW, R_ARM_MGR: RW, R_INST_MGR: RO},
}

# ---------------------------------------------------------------------------
# دوال مساعدة ساكنة (بلا Frappe)
# ---------------------------------------------------------------------------
def level_of(perm, submittable=False):
	"""تصف صفَّ صلاحية (DocPerm/Custom DocPerm كقاموس) بمستوى عربي: عرض / إضافة / تعديل / إضافة وتعديل / كامل (+ اعتماد) (سجلاته فقط)."""
	g = lambda k: int(perm.get(k) or 0)  # noqa: E731
	if not g("read") and not g("write") and not g("create"):
		return ""
	if g("delete"):
		level = "كامل"
	elif g("create") and g("write"):
		level = "إضافة وتعديل"
	elif g("write"):
		level = "تعديل"
	elif g("create"):
		level = "إضافة"
	else:
		level = "عرض"
	extras = []
	if submittable and g("submit"):
		extras.append("اعتماد")
	if submittable and g("cancel"):
		extras.append("إلغاء")
	if g("if_owner"):
		extras.append("سجلاته فقط")
	return level + (" (" + "، ".join(extras) + ")" if extras else "")


def level_flags(perm, submittable=False):
	"""العلامات الأربع المطلوبة أمام كل صلاحية: عرض/إضافة/تعديل/حذف (+ اعتماد للمعتمَد)."""
	g = lambda k: int(perm.get(k) or 0)  # noqa: E731
	flags = {"عرض": bool(g("read") or g("write") or g("create")), "إضافة": bool(g("create")), "تعديل": bool(g("write")), "حذف": bool(g("delete"))}
	if submittable:
		flags["اعتماد"] = bool(g("submit"))
		flags["إلغاء"] = bool(g("cancel"))
	flags["سجلاته فقط"] = bool(g("if_owner"))
	return flags


def profile_roles(name):
	for n, _d, roles in ROLE_PROFILES:
		if n == name:
			return list(roles)
	return []


def profile_names():
	return [n for n, _d, _r in ROLE_PROFILES]


# ---------------------------------------------------------------------------
# المزامنة على الموقع (تحتاج Frappe) — كلها آمنة للتكرار
# ---------------------------------------------------------------------------
def sync_role_profiles():
	"""ينشئ/يحدّث ملفات الصلاحيات (Role Profile) من ROLE_PROFILES — الأدوار غير الموجودة على الموقع (مثل أدوار HRMS حين لا يُثبَّت) تُتخطّى."""
	import frappe

	changed = []
	for name, _desc, roles in ROLE_PROFILES:
		roles = [r for r in roles if frappe.db.exists("Role", r)]
		if frappe.db.exists("Role Profile", name):
			doc = frappe.get_doc("Role Profile", name)
			if {r.role for r in doc.roles} == set(roles):
				continue
			doc.roles = []
		else:
			doc = frappe.new_doc("Role Profile")
			doc.role_profile = name
		for r in roles:
			doc.append("roles", {"role": r})
		doc.flags.ignore_permissions = True
		doc.save()
		changed.append(name)
	return changed


def sync_standard_permissions():
	"""يطبّق STANDARD_PERMS على مستندات ERPNext القياسية عبر Custom DocPerm (الآلية نفسها التي يستخدمها «مدير الصلاحيات» في الواجهة).
	لا يمسّ صلاحيات أدوار ERPNext القياسية؛ يضيف/يصحّح صفوف أدوار زِمام فقط."""
	import frappe
	from frappe.permissions import add_permission, update_permission_property

	changed = []
	for doctype, grants in STANDARD_PERMS.items():
		if not frappe.db.exists("DocType", doctype):
			continue  # HRMS غير مثبَّت مثلًا
		submittable = bool(frappe.get_meta(doctype).is_submittable)
		for role, level in grants.items():
			if not frappe.db.exists("Role", role):
				continue
			wanted = set(LEVELS[level]) | set(AUX_PTYPES)
			if level == FULL and submittable:
				wanted |= set(SUBMIT_PTYPES)
			try:
				add_permission(doctype, role, 0)
				filters = {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}
				current = frappe.db.get_value("Custom DocPerm", filters,
					["read", "write", "create", "delete", "submit", "cancel", "amend"] + list(AUX_PTYPES), as_dict=True) or {}
				for ptype in ("write", "create", "delete", "submit", "cancel", "amend") + AUX_PTYPES:
					want = 1 if ptype in wanted else 0
					if int(current.get(ptype) or 0) != want:
						update_permission_property(doctype, role, 0, ptype, want, validate=False)
						changed.append(f"{doctype}/{role}/{ptype}={want}")
			except Exception:
				frappe.log_error(title=f"zimam: standard permission sync failed — {doctype}/{role}")
	if changed:
		frappe.clear_cache()
	return changed


def ensure_user_permission(user, allow, for_value, apply_to_all=1):
	"""قيد مستخدم (User Permission): يرى مستندات الشركة/القسم المحدد فقط. آمن للتكرار."""
	import frappe

	if not (user and allow and for_value):
		return None
	existing = frappe.db.get_value("User Permission", {"user": user, "allow": allow, "for_value": for_value}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": "User Permission", "user": user, "allow": allow, "for_value": for_value,
		"apply_to_all_doctypes": 1 if apply_to_all else 0})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def apply_role_profile(user_doc, profile_name):
	"""يربط المستخدم بملف الصلاحيات (v15: role_profile_name، v16: جدول role_profiles) ويضيف أدواره صراحةً — فلا يعتمد على آلية الملء التلقائي وحدها."""
	import frappe

	if not profile_name or not frappe.db.exists("Role Profile", profile_name):
		return []
	meta = user_doc.meta
	if meta.has_field("role_profiles"):
		if profile_name not in {r.role_profile for r in (user_doc.get("role_profiles") or [])}:
			user_doc.append("role_profiles", {"role_profile": profile_name})
	elif meta.has_field("role_profile_name"):
		user_doc.role_profile_name = profile_name
	roles = frappe.get_all("Has Role", filters={"parent": profile_name, "parenttype": "Role Profile"}, pluck="role")
	existing = {r.role for r in user_doc.get("roles") or []}
	added = []
	for r in roles:
		if r not in existing and frappe.db.exists("Role", r):
			user_doc.append("roles", {"role": r})
			added.append(r)
	return added
