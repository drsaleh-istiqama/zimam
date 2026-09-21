# -*- coding: utf-8 -*-
"""أدوات مشتركة لزِمام."""
import frappe
from frappe import _
from frappe.utils import flt, getdate

HIJRI_MONTHS = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
	"رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]


def get_settings():
	return frappe.get_cached_doc("Zimam Settings")


def get_heritage_settings():
	return frappe.get_cached_doc("Heritage Settings")


def parent_company():
	company = get_settings().parent_company
	if not company:
		frappe.throw(_("حدد المؤسسة (الشركة الأم) في إعدادات زِمام"))
	return company


# ---------------------------------------------------------------------------
# التاريخ الهجري (حساب جدولي — قد يفرق يومًا عن أم القرى؛ يكفي للشهادات مع مراجعة بشرية)
# ---------------------------------------------------------------------------
def gregorian_to_hijri(date):
	d = getdate(date)
	year, month, day = d.year, d.month, d.day
	if month < 3:
		year -= 1
		month += 12
	a = year // 100
	b = 2 - a + a // 4
	jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524
	l = jd - 1948440 + 10632
	n = (l - 1) // 10631
	l = l - 10631 * n + 354
	j = ((10985 - l) // 5316) * ((50 * l) // 17719) + (l // 5670) * ((43 * l) // 15238)
	l = l - ((30 - j) // 15) * ((17719 * j) // 50) - (j // 16) * ((15238 * j) // 43) + 29
	hm = (24 * l) // 709
	hd = l - (709 * hm) // 24
	hy = 30 * n + j - 30
	return hy, hm, hd


def hijri_str(date):
	hy, hm, hd = gregorian_to_hijri(date)
	return f"{hd} {HIJRI_MONTHS[hm - 1]} {hy}هـ"


# ---------------------------------------------------------------------------
def compute_amounts(rows, qty_field="qty", rate_field="rate", amount_field="amount"):
	total = 0.0
	for row in rows or []:
		row.set(amount_field, flt(flt(row.get(qty_field)) * flt(row.get(rate_field)), 3))
		total += flt(row.get(amount_field))
	return flt(total, 3)


def compute_labor(rows, default_rate, hours_field="hours", rate_field="rate", amount_field="amount"):
	total, hours = 0.0, 0.0
	for row in rows or []:
		if not row.get(rate_field):
			row.set(rate_field, default_rate)
		row.set(amount_field, flt(flt(row.get(hours_field)) * flt(row.get(rate_field)), 3))
		total += flt(row.get(amount_field))
		hours += flt(row.get(hours_field))
	return flt(hours, 2), flt(total, 3)


# ---------------------------------------------------------------------------
def make_material_issue(company, warehouse, rows, cost_center=None, remarks=None):
	rows = [r for r in (rows or []) if r.get("item") and flt(r.get("qty")) > 0]
	if not rows:
		return None
	if not warehouse:
		frappe.throw(_("حدد مستودع صرف المواد قبل الترحيل"))
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Issue"
	se.purpose = "Material Issue"
	se.company = company
	se.remarks = remarks
	for r in rows:
		se.append("items", {"item_code": r.item, "qty": flt(r.qty), "uom": r.get("uom"), "s_warehouse": warehouse, "cost_center": cost_center})
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name


def cancel_linked(doctype, name):
	if not name:
		return
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus == 1:
		doc.cancel()


SERVICE_ITEMS = {"print": ("print_service_item", "SRV-PRINT", "خدمة طباعة"), "general": ("default_service_item", "SRV-GENERAL", "خدمة عامة")}


def service_item(kind="general"):
	"""صنف الخدمة من إعدادات زِمام؛ إن لم يُحدَّد يُنشأ الصنف الافتراضي (خدمة غير مخزنية) ويُحفظ في الإعدادات — فلا يتوقف
	عرض السعر أو الفاتورة على إعداد نسيه أحد (وجدنا ذلك في الفحص الحي 2026-09-21)."""
	field, code, label = SERVICE_ITEMS[kind]
	zs = frappe.get_cached_doc("Zimam Settings")
	item = zs.get(field)
	if item and frappe.db.exists("Item", item):
		return item
	if not frappe.db.exists("Item", code):
		group = "خدمات زِمام"
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups", "is_group": 0}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": label, "description": label, "item_group": group,
			"stock_uom": "Nos", "is_stock_item": 0, "is_sales_item": 1, "is_purchase_item": 0}).insert(ignore_permissions=True)
	frappe.db.set_single_value("Zimam Settings", field, code)
	frappe.clear_cache(doctype="Zimam Settings")
	return code


def make_service_invoice(company, customer, item_code, rate, description, ref_doctype, ref_name,
		qty=1, cost_center=None, income_account=None, submit=False):
	"""فاتورة مبيعات (مسودة افتراضيًا) لخدمة واحدة مع مرجع إلى مستند زِمام."""
	if not customer:
		frappe.throw(_("حدد العميل قبل إنشاء الفاتورة"))
	if not item_code:
		item_code = service_item("general")
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.customer = customer
	si.zimam_ref_doctype = ref_doctype
	si.zimam_ref_name = ref_name
	row = {"item_code": item_code, "qty": qty, "rate": flt(rate), "description": description}
	if cost_center:
		row["cost_center"] = cost_center
	if income_account:
		row["income_account"] = income_account
	si.append("items", row)
	si.set_missing_values()
	si.insert(ignore_permissions=True)
	if submit:
		si.submit()
	return si.name


def ensure_customer_for(name, email=None, phone=None):
	existing = frappe.db.get_value("Customer", {"customer_name": name}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Customer", "customer_name": name, "customer_type": "Individual",
		"customer_group": leaf_of("Customer Group", frappe.db.get_single_value("Selling Settings", "customer_group"), "Individual"),
		"territory": leaf_of("Territory", frappe.db.get_single_value("Selling Settings", "territory"), "Oman"),
		"email_id": email, "mobile_no": phone,
	}).insert(ignore_permissions=True)
	return doc.name


def leaf_of(doctype, preferred=None, fallback=None):
	"""عقدة غير مجموعة من شجرة (مجموعة العملاء/الإقليم): ERPNext يرفض إسناد مجموعة (is_group) للعميل — الإعداد الافتراضي
	«All Customer Groups»/«All Territories» مجموعتان فيفشل إنشاء العميل من طلب الخدمة. نأخذ المفضَّل إن كان ورقة، ثم البديل، ثم أول ورقة."""
	for cand in (preferred, fallback):
		if cand and frappe.db.exists(doctype, cand) and not frappe.db.get_value(doctype, cand, "is_group"):
			return cand
	leaf = frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="name")
	if leaf:
		return leaf
	# لا ورقة إطلاقًا: ننشئ واحدة تحت الجذر
	root = frappe.db.get_value(doctype, {"is_group": 1, "parent_" + doctype.lower().replace(" ", "_"): ["in", ["", None]]}, "name") or frappe.db.get_value(doctype, {"is_group": 1}, "name")
	name_field = "customer_group_name" if doctype == "Customer Group" else "territory_name"
	parent_field = "parent_customer_group" if doctype == "Customer Group" else "parent_territory"
	doc = frappe.get_doc({"doctype": doctype, name_field: fallback or "عام", parent_field: root, "is_group": 0}).insert(ignore_permissions=True)
	return doc.name


def notify_roles(roles, subject, message, reference_doctype=None, reference_name=None):
	"""إشعار داخلي + بريد لكل مستخدم يحمل أحد الأدوار. يُرجع قائمة المستلمين."""
	users = set()
	for role in roles:
		users.update(frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"))
	users -= {"Administrator", "Guest"}
	enabled = set(frappe.get_all("User", filters={"enabled": 1, "name": ["in", list(users)]}, pluck="name")) if users else set()
	for user in enabled:
		frappe.get_doc({
			"doctype": "Notification Log", "for_user": user, "type": "Alert", "subject": subject,
			"email_content": message, "document_type": reference_doctype, "document_name": reference_name,
		}).insert(ignore_permissions=True)
	if enabled:
		frappe.sendmail(recipients=list(enabled), subject=subject, message=message,
			reference_doctype=reference_doctype, reference_name=reference_name, now=False)
	return list(enabled)
