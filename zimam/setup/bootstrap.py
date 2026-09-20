# -*- coding: utf-8 -*-
"""تهيئة مؤسسة على زِمام من ملف تعريف — تُشغَّل مرة بعد إكمال معالج الإعداد:

    bench --site <site> execute zimam.setup.bootstrap.run --kwargs '{"profile": "<اسم الملف في profiles/>"}'
    bench --site <site> execute zimam.setup.bootstrap.run --kwargs '{"profile": "/path/to/custom.json", "with_optional_arms": true}'

ملفات التعريف في zimam/setup/profiles/*.json (انظر template.json). آمنة للتكرار: كل عنصر يُنشأ إن لم يوجد.

ما يُنشأ من الملف: الشركة الأم والأذرع التابعة (بشركة لكل ذراع) · مراكز التكلفة · الحزم المفعّلة (Domain Settings)
· مجموعة الأصناف وأصناف الخدمات · حسابات الإيراد · أنواع الخدمات · الأسهم الوقفية · العميل الداخلي والموردون الداخليون
للفوترة البينية · إعدادات زِمام · وإعدادات الحزمة التراثية إن كانت مفعّلة.
"""
import json
import os

import frappe
from frappe import _

ITEM_GROUP = "خدمات زِمام"
ARM_ROLE_LABEL = {"press": "مطبعة", "restoration": "ترميم", "waqf": "استثمار وقفي", "other": "أخرى"}


_LOG = []


def log(msg):
	print("[zimam bootstrap] " + msg)
	_LOG.append(msg)


@frappe.whitelist()
def list_profiles():
	"""أسماء ملفات التعريف المتاحة في zimam/setup/profiles (لمدير النظام)."""
	frappe.only_for("System Manager")
	folder = os.path.join(os.path.dirname(__file__), "profiles")
	return sorted(f[:-5] for f in os.listdir(folder) if f.endswith(".json") and f != "template.json") + ["template"]


@frappe.whitelist()
def run_profile(profile, with_optional_arms=0):
	"""تشغيل التهيئة من واجهة «إعدادات زِمام» (زر) — لمدير النظام فقط؛ يُرجع سجل ما أُنشئ."""
	frappe.only_for("System Manager")
	_LOG.clear()
	run(profile=profile, with_optional_arms=bool(int(with_optional_arms or 0)))
	return list(_LOG)


def load_profile(profile):
	path = profile if profile.endswith(".json") else os.path.join(os.path.dirname(__file__), "profiles", profile + ".json")
	if not os.path.exists(path):
		frappe.throw(_("ملف التعريف غير موجود: {0}").format(path))
	with open(path, encoding="utf-8") as fh:
		return json.load(fh), os.path.basename(path)[:-5]


# ---------------------------------------------------------------------------
def ensure_company(name, abbr, country, currency, parent=None, arm_type=None, arm_role=None, is_group=False):
	"""ERPNext يشترط أن تكون الشركة الأم «شركة مجموعة» (is_group) قبل ربط شركات تابعة بها."""
	if frappe.db.exists("Company", name):
		doc = frappe.get_doc("Company", name)
		changed = False
		if is_group and not doc.is_group:
			doc.is_group, changed = 1, True
		if parent and not doc.parent_company:
			doc.parent_company, changed = parent, True
		if arm_type and not doc.get("zimam_arm_type"):
			doc.zimam_arm_type, changed = arm_type, True
		if arm_role and not doc.get("zimam_arm_role"):
			doc.zimam_arm_role, changed = arm_role, True
		if changed:
			doc.save(ignore_permissions=True)
		log(f"الشركة موجودة: {name}")
		return doc
	doc = frappe.get_doc({
		"doctype": "Company", "company_name": name, "abbr": abbr, "default_currency": currency, "country": country,
		"chart_of_accounts": "Standard", "parent_company": parent, "zimam_arm_type": arm_type, "zimam_arm_role": arm_role,
		"is_group": 1 if is_group else 0,
	}).insert(ignore_permissions=True)
	log(f"أُنشئت الشركة: {name} ({abbr})")
	return doc


def root_cost_center(company):
	return frappe.db.get_value("Cost Center", {"company": company, "is_group": 1, "parent_cost_center": ["in", ["", None]]}, "name")


def ensure_cost_centers(company, names):
	parent = root_cost_center(company)
	if not parent:
		frappe.throw(_("لا مركز تكلفة جذري للشركة {0}").format(company))
	for cc in names:
		if not frappe.db.exists("Cost Center", {"cost_center_name": cc, "company": company}):
			frappe.get_doc({"doctype": "Cost Center", "cost_center_name": cc, "parent_cost_center": parent, "company": company, "is_group": 0}).insert(ignore_permissions=True)
			log(f"مركز تكلفة: {cc}")


def ensure_warehouse(name, company):
	existing = frappe.db.get_value("Warehouse", {"warehouse_name": name, "company": company}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": name, "company": company}).insert(ignore_permissions=True)
	log(f"مستودع: {doc.name}")
	return doc.name


def ensure_item_group():
	if not frappe.db.exists("Item Group", ITEM_GROUP):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": ITEM_GROUP, "parent_item_group": "All Item Groups", "is_group": 0}).insert(ignore_permissions=True)


def ensure_item(code, name, is_stock=0, has_serial=0, uom="Nos", sales=1):
	if frappe.db.exists("Item", code):
		return code
	frappe.get_doc({
		"doctype": "Item", "item_code": code, "item_name": name, "description": name, "item_group": ITEM_GROUP,
		"stock_uom": uom, "is_stock_item": is_stock, "has_serial_no": has_serial,
		"serial_no_series": "ZS-.#####" if has_serial else None, "is_sales_item": sales, "is_purchase_item": 0,
	}).insert(ignore_permissions=True)
	log(f"صنف: {code} — {name}")
	return code


def income_parent(company):
	for candidate in ("Direct Income", "Income"):
		acc = frappe.db.get_value("Account", {"company": company, "account_name": candidate, "is_group": 1}, "name")
		if acc:
			return acc
	return frappe.db.get_value("Account", {"company": company, "root_type": "Income", "is_group": 1}, "name")


def ensure_income_account(name, company):
	existing = frappe.db.get_value("Account", {"account_name": name, "company": company}, "name")
	if existing:
		return existing
	parent = income_parent(company)
	if not parent:
		frappe.throw(_("لا حساب إيراد أب في {0}").format(company))
	doc = frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent, "company": company, "is_group": 0, "account_type": "Income Account"}).insert(ignore_permissions=True)
	log(f"حساب: {doc.name}")
	return doc.name


def default_customer_group():
	return frappe.db.get_single_value("Selling Settings", "customer_group") or frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups"


def default_territory():
	return frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"


def ensure_internal_customer(represents, allowed):
	existing = frappe.db.get_value("Customer", {"is_internal_customer": 1, "represents_company": represents}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Customer", "customer_name": represents, "customer_type": "Company", "customer_group": default_customer_group(),
		"territory": default_territory(), "is_internal_customer": 1, "represents_company": represents,
		"companies": [{"company": c} for c in allowed],
	}).insert(ignore_permissions=True)
	log(f"عميل داخلي يمثّل {represents}")
	return doc.name


def ensure_internal_supplier(represents, allowed):
	existing = frappe.db.get_value("Supplier", {"is_internal_supplier": 1, "represents_company": represents}, "name")
	if existing:
		return existing
	group = frappe.db.get_single_value("Buying Settings", "supplier_group") or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"
	doc = frappe.get_doc({
		"doctype": "Supplier", "supplier_name": represents, "supplier_type": "Company", "supplier_group": group,
		"is_internal_supplier": 1, "represents_company": represents, "companies": [{"company": c} for c in allowed],
	}).insert(ignore_permissions=True)
	log(f"مورد داخلي يمثّل {represents}")
	return doc.name


def ensure_service_types(rows, company, default_item):
	for r in rows:
		if frappe.db.exists("Service Type", r["name"]):
			continue
		frappe.get_doc({
			"doctype": "Service Type", "service_name": r["name"], "company": company, "is_free": 1 if r.get("free") else 0,
			"default_fees": r.get("fees", 0), "service_item": None if r.get("free") else default_item,
			"description": r.get("description"), "is_active": 1, "publish_on_website": 1 if r.get("public") else 0,
		}).insert(ignore_permissions=True)
		log(f"نوع خدمة: {r['name']}")


def ensure_waqf_shares(rows):
	for name, amount in rows:
		if not frappe.db.exists("Waqf Share Type", name):
			frappe.get_doc({"doctype": "Waqf Share Type", "share_name": name, "amount": amount, "is_active": 1}).insert(ignore_permissions=True)
			log(f"سهم وقفي: {name} = {amount}")


def activate_domains(domains):
	ds = frappe.get_single("Domain Settings")
	existing = {d.domain for d in ds.active_domains}
	changed = False
	for dom in domains:
		if dom not in existing:
			ds.append("active_domains", {"domain": dom})
			changed = True
	if changed:
		ds.save(ignore_permissions=True)
		log(f"الحزم المفعّلة: {', '.join(domains)}")


RESTORATION_ITEM_GROUP = "خدمات الترميم"


def ensure_restoration_catalog(company, h):
	"""كتالوج «نظام التقييم الموحد» لذراع الترميم: مجموعة أصناف + أصناف خدمة + قائمة أسعار بيع + أسعار،
	وقالب ضريبة مبيعات وشروط دفع (مقدم) وشروط وأحكام؛ ثم تُربط كلها في إعدادات الحزمة التراثية."""
	pricing = h.get("restoration_pricing") or {}
	catalog = pricing.get("catalog") or []
	if not catalog:
		return {}
	if not frappe.db.exists("Item Group", RESTORATION_ITEM_GROUP):
		frappe.get_doc({"doctype": "Item Group", "item_group_name": RESTORATION_ITEM_GROUP, "parent_item_group": "All Item Groups", "is_group": 0}).insert(ignore_permissions=True)
	price_list = pricing.get("price_list") or "أسعار الترميم"
	if not frappe.db.exists("Price List", price_list):
		currency = frappe.db.get_value("Company", company, "default_currency")
		frappe.get_doc({"doctype": "Price List", "price_list_name": price_list, "selling": 1, "buying": 0, "enabled": 1, "currency": currency}).insert(ignore_permissions=True)
		log(f"قائمة أسعار: {price_list}")
	n_items = n_prices = 0
	for row in catalog:
		code = row["code"]
		if not frappe.db.exists("Item", code):
			frappe.get_doc({
				"doctype": "Item", "item_code": code, "item_name": row["name"], "description": f"{row['name']} — لكل {row.get('unit', 'وحدة')}",
				"item_group": RESTORATION_ITEM_GROUP, "stock_uom": "Nos", "is_stock_item": 0, "is_sales_item": 1, "is_purchase_item": 0,
				"standard_rate": row["rate"],
			}).insert(ignore_permissions=True)
			n_items += 1
		if not frappe.db.exists("Item Price", {"item_code": code, "price_list": price_list}):
			frappe.get_doc({"doctype": "Item Price", "item_code": code, "price_list": price_list, "price_list_rate": row["rate"], "selling": 1}).insert(ignore_permissions=True)
			n_prices += 1
	log(f"كتالوج الترميم: {n_items} صنفًا جديدًا، {n_prices} سعرًا في «{price_list}»")

	out = {"price_list": price_list}
	tax_rate = pricing.get("tax_rate", 5)
	if tax_rate:
		out["taxes_template"] = ensure_sales_tax_template(company, pricing.get("tax_account") or "ضريبة القيمة المضافة", tax_rate)
	advance = pricing.get("advance_percent", 50)
	if advance:
		out["payment_terms"] = ensure_payment_terms(advance)
	terms = pricing.get("terms")
	if terms:
		out["terms"] = ensure_terms(pricing.get("terms_title") or "شروط خدمات الترميم", terms)
	out.update(tax_rate=tax_rate, advance=advance, validity=pricing.get("validity_days", 30), warranty=pricing.get("warranty_months", 12))
	return out


def ensure_press_catalog(company, press):
	"""كتالوج المطبعة لمحرّك تقدير التسعير: خامات الورق، آلات الطباعة، خدمات التشطيب، قوالب المنتجات،
	وإعدادات المطبعة (الافتراضيات + قالب ضريبة + شروط دفع + شروط وأحكام + صنف التصميم). آمن للتكرار: لا يُعدَّل موجود."""
	if not press:
		return
	n = {"paper": 0, "machine": 0, "finishing": 0, "template": 0}
	for p in press.get("papers", []):
		if not frappe.db.exists("Paper Stock", p["name"]):
			frappe.get_doc({"doctype": "Paper Stock", "stock_name": p["name"], "category": p.get("category", "أخرى"), "gsm": p.get("gsm"),
				"finish": p.get("finish", "غير مصقول"), "sheet_width_mm": p["w"], "sheet_height_mm": p["h"], "caliper_mm": p.get("caliper"),
				"pricing_basis": p.get("basis", "لكل فرخ"), "cost": p["cost"], "is_active": 1}).insert(ignore_permissions=True)
			n["paper"] += 1
	for m in press.get("machines", []):
		if not frappe.db.exists("Print Machine", m["name"]):
			frappe.get_doc({"doctype": "Print Machine", "machine_name": m["name"], "machine_type": m["type"], "is_active": 1,
				"max_sheet_width_mm": m["max_w"], "max_sheet_height_mm": m["max_h"], "gripper_margin_mm": m.get("gripper", 0), "duplex": m.get("duplex", 1),
				"click_cost_color": m.get("click_color"), "click_cost_mono": m.get("click_mono"), "waste_sheets": m.get("waste_sheets", 0),
				"plate_cost": m.get("plate"), "makeready_cost": m.get("makeready"), "run_cost_per_1000": m.get("run_per_1000"),
				"cost_per_sqm": m.get("cost_per_sqm"), "min_charge": m.get("min"), "setup_cost": m.get("setup"), "speed_per_hour": m.get("speed")}).insert(ignore_permissions=True)
			n["machine"] += 1
	for f in press.get("finishing", []):
		if not frappe.db.exists("Finishing Service", f["name"]):
			frappe.get_doc({"doctype": "Finishing Service", "service_name": f["name"], "category": f.get("category", "أخرى"), "is_active": 1,
				"basis": f["basis"], "rate": f["rate"], "setup_cost": f.get("setup", 0), "min_charge": f.get("min", 0)}).insert(ignore_permissions=True)
			n["finishing"] += 1
	for t in press.get("templates", []):
		if frappe.db.exists("Print Product Template", t["name"]):
			continue
		cover, inner = t.get("cover", {}), t.get("inner", {})
		doc = frappe.get_doc({"doctype": "Print Product Template", "template_name": t["name"], "product_type": t["product_type"], "is_active": 1,
			"structure": t.get("structure", "قطعة واحدة"), "size_preset": t.get("size", "مخصص"), "finished_width_mm": t.get("w"), "finished_height_mm": t.get("h"),
			"bleed_mm": t.get("bleed", 3), "binding": t.get("binding", "بلا"), "default_pages": t.get("pages"),
			"cover_paper": cover.get("paper"), "cover_machine": cover.get("machine"), "cover_color": cover.get("color", "ملون"), "cover_sides": cover.get("sides", "وجهان"),
			"inner_paper": inner.get("paper"), "inner_machine": inner.get("machine"), "inner_color": inner.get("color", "أحادي"), "inner_sides": inner.get("sides", "وجهان"),
			"margin_percent": t.get("margin"), "design_hours": t.get("design_hours"), "tiers": t.get("tiers"), "description": t.get("description")})
		for fin in t.get("finishing", []):
			doc.append("finishing", {"finishing_service": fin[0], "applies_to": fin[1] if len(fin) > 1 else "الكل", "qty_per_copy": fin[2] if len(fin) > 2 else 1})
		doc.insert(ignore_permissions=True)
		n["template"] += 1
	log(f"كتالوج المطبعة: {n['paper']} خامة، {n['machine']} آلة، {n['finishing']} خدمة تشطيب، {n['template']} قالب منتج (جديد)")

	s = press.get("settings", {})
	ps = frappe.get_single("Press Settings")
	values = {k: s[k] for k in ("default_margin_percent", "default_tax_rate", "default_validity_days", "default_advance_percent", "default_rush_percent",
		"default_design_rate", "default_round_to", "min_job_price", "default_tiers", "default_waste_percent", "default_bleed_mm") if k in s}
	values["design_service_item"] = ensure_item("SRV-DESIGN", "خدمة تصميم")
	if s.get("default_tax_rate"):
		values["taxes_template"] = ensure_sales_tax_template(company, s.get("tax_account") or "ضريبة القيمة المضافة", s["default_tax_rate"])
	if s.get("default_advance_percent"):
		values["payment_terms"] = ensure_payment_terms(s["default_advance_percent"])
	if s.get("terms"):
		values["terms"] = ensure_terms(s.get("terms_title") or "شروط خدمات الطباعة", s["terms"])
	ps.update(values)
	ps.save(ignore_permissions=True)
	log("إعدادات المطبعة جاهزة")


def root_company(company):
	"""ERPNext يشترط إنشاء الحسابات في الشركة الجذر (الأم) لتُنسخ تلقائيًا إلى الشركات التابعة."""
	seen = set()
	while company and company not in seen:
		seen.add(company)
		parent = frappe.db.get_value("Company", company, "parent_company")
		if not parent:
			return company
		company = parent
	return company


def ensure_tax_account(company, name):
	existing = frappe.db.get_value("Account", {"account_name": name, "company": company}, "name")
	if existing:
		return existing
	root = root_company(company)
	if not frappe.db.get_value("Account", {"account_name": name, "company": root}, "name"):
		parent = frappe.db.get_value("Account", {"company": root, "account_name": "Duties and Taxes", "is_group": 1}, "name") \
			or frappe.db.get_value("Account", {"company": root, "root_type": "Liability", "is_group": 1}, "name")
		doc = frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent, "company": root, "is_group": 0, "account_type": "Tax"}).insert(ignore_permissions=True)
		log(f"حساب ضريبة في الشركة الجذر: {doc.name}")
	# النسخة في الشركة التابعة تُنشأ تلقائيًا؛ وإلا نستخدم حساب الجذر
	return frappe.db.get_value("Account", {"account_name": name, "company": company}, "name") \
		or frappe.db.get_value("Account", {"account_name": name, "company": root}, "name")


def ensure_sales_tax_template(company, account_name, rate):
	title = f"ضريبة القيمة المضافة {rate}%"
	existing = frappe.db.get_value("Sales Taxes and Charges Template", {"title": title, "company": company}, "name")
	if existing:
		return existing
	account = ensure_tax_account(company, account_name)
	doc = frappe.get_doc({
		"doctype": "Sales Taxes and Charges Template", "title": title, "company": company, "is_default": 0,
		"taxes": [{"charge_type": "On Net Total", "account_head": account, "description": title, "rate": rate}],
	}).insert(ignore_permissions=True)
	log(f"قالب ضريبة: {doc.name}")
	return doc.name


def ensure_payment_terms(advance_percent):
	name = f"مقدم {int(advance_percent)}% والباقي عند التسليم"
	if frappe.db.exists("Payment Terms Template", name):
		return name
	def term(tname, portion, due_days):
		if not frappe.db.exists("Payment Term", tname):
			frappe.get_doc({"doctype": "Payment Term", "payment_term_name": tname, "invoice_portion": portion, "due_date_based_on": "Day(s) after invoice date", "credit_days": due_days}).insert(ignore_permissions=True)
		return tname
	t1 = term(f"دفعة مقدمة {int(advance_percent)}%", advance_percent, 0)
	t2 = term(f"الباقي {int(100 - advance_percent)}% عند التسليم", 100 - advance_percent, 30)
	frappe.get_doc({"doctype": "Payment Terms Template", "template_name": name,
		"terms": [{"payment_term": t1, "invoice_portion": advance_percent, "due_date_based_on": "Day(s) after invoice date", "credit_days": 0},
			{"payment_term": t2, "invoice_portion": 100 - advance_percent, "due_date_based_on": "Day(s) after invoice date", "credit_days": 30}]}).insert(ignore_permissions=True)
	log(f"قالب شروط دفع: {name}")
	return name


def ensure_terms(title, text):
	if frappe.db.exists("Terms and Conditions", title):
		return title
	frappe.get_doc({"doctype": "Terms and Conditions", "title": title, "selling": 1, "buying": 0, "terms": text}).insert(ignore_permissions=True)
	log(f"شروط وأحكام: {title}")
	return title


# ---------------------------------------------------------------------------
def run(profile="template", with_optional_arms=False):
	if not frappe.db.get_single_value("System Settings", "setup_complete"):
		frappe.throw(_("أكمل معالج الإعداد (Setup Wizard) أولًا."))
	p, profile_name = load_profile(profile)
	inst = p["institution"]
	parent = inst["name"]
	country, currency = inst["country"], inst["currency"]

	arms = list(p.get("arms", [])) + (list(p.get("optional_arms", [])) if with_optional_arms else [])
	ensure_company(parent, inst["abbr"], country, currency, arm_type="المؤسسة (الشركة الأم)", is_group=bool(arms))
	by_role = {}
	for a in arms:
		ensure_company(a["name"], a["abbr"], country, currency, parent=parent, arm_type="ذراع استثماري تابع", arm_role=ARM_ROLE_LABEL[a["role"]])
		by_role.setdefault(a["role"], a["name"])

	ensure_cost_centers(parent, p.get("cost_centers", []))
	activate_domains(p.get("domains", []))
	ensure_item_group()
	service_item = ensure_item("SRV-GENERAL", "خدمة مؤسسية")
	print_item = ensure_item("SRV-PRINT", "خدمة طباعة") if "press" in by_role else None

	accounts = p.get("income_accounts", {})
	for name in accounts.get("parent", []):
		ensure_income_account(name, parent)
	for role, names in accounts.items():
		if role != "parent" and role in by_role:
			for name in names:
				ensure_income_account(name, by_role[role])
	waqf_income = ensure_income_account(p.get("waqf_income_account", "إيرادات الوقف"), parent)

	ensure_service_types(p.get("service_types", []), parent, service_item)
	ensure_waqf_shares([(r["name"], r["amount"]) for r in p.get("waqf_shares", [])])

	internal_customer = None
	if arms:
		internal_customer = ensure_internal_customer(parent, [a["name"] for a in arms])
		for a in arms:
			ensure_internal_supplier(a["name"], [parent])

	waqf_cc_name = p.get("waqf_cost_center")
	waqf_cc = frappe.db.get_value("Cost Center", {"cost_center_name": waqf_cc_name, "company": parent}, "name") if waqf_cc_name else None
	cert = p.get("certificate", {})

	settings = frappe.get_single("Zimam Settings")
	settings.update({
		"parent_company": parent, "institution_type": inst["type"], "institution_profile": profile_name,
		"internal_customer": internal_customer, "press_company": by_role.get("press"), "print_service_item": print_item,
		"default_service_item": service_item, "service_company": parent, "waqf_income_account": waqf_income,
		"waqf_cost_center": waqf_cc, "certificate_signatory": cert.get("signatory") or settings.certificate_signatory,
		"certificate_title": cert.get("title") or settings.certificate_title, "certificate_footer": cert.get("footer") or settings.certificate_footer,
	})
	settings.save(ignore_permissions=True)

	if p.get("press"):
		ensure_press_catalog(by_role.get("press", parent), p["press"])

	if "Heritage" in p.get("domains", []):
		h = p.get("heritage", {})
		# ERPNext v15+: قيود الرقم التسلسلي على سطر المستند تتطلب تفعيل هذا الخيار في إعدادات المخزون
		# Stock Settings مستند مفرد (Single) بلا جدول — لا يصلح معه has_column؛ نفحص الحقل عبر الـmeta
		stock_meta = frappe.get_meta("Stock Settings")
		for flag in ("enable_serial_and_batch_no_for_item", "use_serial_batch_fields"):
			if stock_meta.has_field(flag) and not frappe.db.get_single_value("Stock Settings", flag):
				frappe.db.set_single_value("Stock Settings", flag, 1)
				log(f"إعدادات المخزون: تفعيل {flag}")
		wh = h.get("warehouses", {})
		lab = by_role.get("restoration", parent)
		hs = frappe.get_single("Heritage Settings")
		hs.update({
			"restoration_company": lab,
			"default_labor_rate": h.get("labor_rate", 3),
			"incoming_cabinet_item": ensure_item("CABINET-IN", "خزانة واردة", is_stock=1, has_serial=1, sales=0),
			"incoming_cabinets_warehouse": ensure_warehouse(wh.get("cabinets", "خزائن واردة"), parent),
			"restoration_materials_warehouse": ensure_warehouse(wh.get("materials", "مواد الترميم"), lab),
			"restoration_service_item": ensure_item("SRV-RESTORATION", "خدمة ترميم"),
			"digital_copy_item": ensure_item("DIGITAL-COPY", "نسخة رقمية من مقتنى"),
		})
		cat = ensure_restoration_catalog(lab, h)
		if cat:
			hs.update({
				"restoration_price_list": cat.get("price_list"), "restoration_taxes_template": cat.get("taxes_template"),
				"default_tax_rate": cat.get("tax_rate"), "default_validity_days": cat.get("validity"),
				"default_advance_percent": cat.get("advance"), "default_warranty_months": cat.get("warranty"),
				"restoration_payment_terms": cat.get("payment_terms"), "restoration_terms": cat.get("terms"),
			})
		hs.save(ignore_permissions=True)
		log("إعدادات الحزمة التراثية جاهزة")

	ensure_finance(parent, p.get("finance") or {})
	if "Charity" in p.get("domains", []):
		ensure_charity(parent, p.get("charity") or {})

	setup_website(parent)
	setup_login_policy(p.get("login_policy"))
	ensure_users(p.get("users"))
	frappe.db.commit()
	log(f"اكتملت تهيئة «{parent}» من ملف التعريف {profile_name}. راجع إعدادات زِمام وأدوار المستخدمين.")


# ---------------------------------------------------------------------------
# الصرف والاعتماد (النواة، 0.10.0 — لكل مؤسسة): الصناديق بحساب أستاذ لكل صندوق (بنك/نقد)، تصنيفات المصروف بحساب
# مصروف لكل تصنيف، الفروع والأقسام، إعدادات سلسلة الاعتماد في إعدادات زِمام، وسير اعتماد سند الصرف. آمنة للتكرار.
# ---------------------------------------------------------------------------
def _account_group(company, candidates, root_type):
	for c in candidates:
		acc = frappe.db.get_value("Account", {"company": company, "account_name": c, "is_group": 1}, "name")
		if acc:
			return acc
	return frappe.db.get_value("Account", {"company": company, "root_type": root_type, "is_group": 1}, "name")


def ensure_account(company, name, parent, account_type=None, is_group=0):
	existing = frappe.db.get_value("Account", {"account_name": name, "company": company}, "name")
	if existing:
		return existing
	root = root_company(company)
	target = company if root == company else root
	if not frappe.db.get_value("Account", {"account_name": name, "company": target}, "name"):
		parent_acc = parent if frappe.db.get_value("Account", parent, "company") == target else frappe.db.get_value("Account", {"account_name": frappe.db.get_value("Account", parent, "account_name"), "company": target}, "name")
		doc = frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent_acc, "company": target, "is_group": is_group, "account_type": account_type}).insert(ignore_permissions=True)
		log(f"حساب: {doc.name}")
	return frappe.db.get_value("Account", {"account_name": name, "company": company}, "name") or frappe.db.get_value("Account", {"account_name": name, "company": target}, "name")


def ensure_finance(company, fin):
	default_cc = frappe.db.get_value("Cost Center", {"cost_center_name": fin.get("default_cost_center"), "company": company}, "name") if fin.get("default_cost_center") else None

	# تصنيفات المصروف بحساب لكل تصنيف
	exp_parent = _account_group(company, ["Indirect Expenses", "Expenses"], "Expense")
	n_cl = 0
	for c in fin.get("expense_classifications", []):
		if frappe.db.exists("Expense Classification", c["code"]):
			continue
		acc = ensure_account(company, f"{c['code']} {c['name']}", exp_parent, account_type="Expense Account")
		frappe.get_doc({"doctype": "Expense Classification", "classification_code": c["code"], "classification_name": c["name"],
			"expense_account": acc, "cost_center": default_cc, "is_active": 1, "description": c.get("description")}).insert(ignore_permissions=True)
		n_cl += 1
	log(f"تصنيفات المصروف: {n_cl} جديد")

	# الصناديق بحساب أستاذ لكل صندوق (بنك/نقد)
	bank_parent = _account_group(company, ["Bank Accounts"], "Asset")
	cash_parent = _account_group(company, ["Cash In Hand"], "Asset")
	n_f = 0
	for f in fin.get("funds", []):
		if frappe.db.exists("Treasury Fund", f["code"]):
			continue
		is_cash = f.get("type") == "صندوق نقدي"
		acc = ensure_account(company, f["name"], cash_parent if is_cash else bank_parent, account_type="Cash" if is_cash else "Bank")
		cc = frappe.db.get_value("Cost Center", {"cost_center_name": f.get("cost_center"), "company": company}, "name") if f.get("cost_center") else None
		frappe.get_doc({"doctype": "Treasury Fund", "fund_code": f["code"], "fund_name": f["name"], "fund_type": f.get("type", "حساب بنكي"), "company": company,
			"account": acc, "purpose": f.get("purpose"), "cost_center": cc, "is_restricted": 1 if f.get("restricted") else 0, "is_active": 1}).insert(ignore_permissions=True)
		n_f += 1
	log(f"الصناديق: {n_f} جديد")

	# الفروع والأقسام
	for b in fin.get("branches", []):
		if not frappe.db.exists("Branch", b):
			frappe.get_doc({"doctype": "Branch", "branch": b}).insert(ignore_permissions=True)
	for dname in fin.get("departments", []):
		if not frappe.db.exists("Department", {"department_name": dname, "company": company}):
			frappe.get_doc({"doctype": "Department", "department_name": dname, "company": company}).insert(ignore_permissions=True)

	# إعدادات سلسلة الاعتماد في إعدادات زِمام
	zs = frappe.get_single("Zimam Settings")
	values = {"ceo_approval_threshold": fin.get("ceo_approval_threshold", zs.ceo_approval_threshold or 0),
		"allow_self_approval": 1 if fin.get("allow_self_approval") else 0, "notify_on_stage_change": 1,
		"default_expense_cost_center": default_cc or zs.default_expense_cost_center,
		"default_fund": fin.get("default_fund") if frappe.db.exists("Treasury Fund", fin.get("default_fund") or "") else zs.default_fund}
	if fin.get("voucher_note"):
		values["voucher_note"] = fin["voucher_note"]
	zs.update(values)
	zs.save(ignore_permissions=True)

	from zimam.zimam_core.workflow import ensure_payment_voucher_workflow
	ensure_payment_voucher_workflow()
	log("الصرف والاعتماد جاهزان: سير اعتماد سند الصرف (محاسب ← مدير مالي ← معتمد الصرف ← أمين صندوق)")


# ---------------------------------------------------------------------------
# الحزمة الخيرية (0.10.0): فئات التبرع شجرةً بحساب إيراد لكل فئة، المشاريع الخيرية، وإعدادات الحزمة. آمنة للتكرار.
# ---------------------------------------------------------------------------
def ensure_charity(company, ch):
	income_parent_acc = income_parent(company)
	donations_group = ensure_account(company, "إيرادات التبرعات بحسب الفئة", income_parent_acc, is_group=1)
	default_cc = frappe.db.get_value("Cost Center", {"cost_center_name": ch.get("default_cost_center"), "company": company}, "name") if ch.get("default_cost_center") else None

	# الفئات شجرةً
	n_cat = 0
	for g in ch.get("categories", []):
		if not frappe.db.exists("Donation Category", g["name"]):
			frappe.get_doc({"doctype": "Donation Category", "category_name": g["name"], "category_code": g.get("code"), "is_group": 1,
				"apply_admin_fee": 0 if g.get("fee") == 0 else 1, "admin_fee_percent": g.get("fee") if g.get("fee") else None,
				"is_restricted": 1 if g.get("restricted") else 0, "restriction_type": g.get("restricted") or "", "is_active": 1}).insert(ignore_permissions=True)
			n_cat += 1
		for c in g.get("children", []):
			if frappe.db.exists("Donation Category", c["name"]):
				continue
			fee = c.get("fee", g.get("fee"))
			restricted = c.get("restricted") or g.get("restricted")
			acc = ensure_account(company, c["name"], donations_group, account_type="Income Account")
			frappe.get_doc({"doctype": "Donation Category", "category_name": c["name"], "category_code": c.get("code"), "is_group": 0,
				"parent_donation_category": g["name"], "apply_admin_fee": 0 if fee == 0 else 1, "admin_fee_percent": fee if fee else None,
				"is_restricted": 1 if restricted else 0, "restriction_type": restricted or "", "income_account": acc, "cost_center": default_cc,
				"is_active": 1, "publish_on_website": 1 if c.get("website") else 0}).insert(ignore_permissions=True)
			n_cat += 1
	log(f"فئات التبرع: {n_cat} فئة جديدة")

	# المشاريع الخيرية (Project القياسي بحقول زِمام)
	n_p = 0
	for pr in ch.get("projects", []):
		if frappe.db.exists("Project", {"project_name": pr["name"]}):
			continue
		doc = frappe.get_doc({"doctype": "Project", "project_name": pr["name"], "company": company, "status": "Open",
			"zimam_country": pr.get("country"), "zimam_donation_category": pr.get("category"), "zimam_target_amount": pr.get("target"),
			"zimam_publish_on_website": 1 if pr.get("website", True) else 0})
		doc.insert(ignore_permissions=True)
		n_p += 1
	log(f"المشاريع الخيرية: {n_p} جديد")

	# الإعدادات
	cs = frappe.get_single("Charity Settings")
	fund = ch.get("default_fund") if frappe.db.exists("Treasury Fund", ch.get("default_fund") or "") else frappe.db.get_single_value("Zimam Settings", "default_fund")
	values = {"company": company, "default_admin_fee_percent": ch.get("default_admin_fee_percent", cs.default_admin_fee_percent),
		"default_cost_center": default_cc, "default_fund": fund, "website_fund": fund,
		"sponsorship_category": ch.get("sponsorship_category") if frappe.db.exists("Donation Category", ch.get("sponsorship_category") or "") else None,
		"website_donation_category": ch.get("website_donation_category") if frappe.db.exists("Donation Category", ch.get("website_donation_category") or "") else None}
	if ch.get("admin_fee_income_account"):
		values["admin_fee_income_account"] = ensure_income_account(ch["admin_fee_income_account"], company)
	if ch.get("default_donation_income_account"):
		values["default_donation_income_account"] = ensure_income_account(ch["default_donation_income_account"], company)
	for k in ("receipt_signatory", "receipt_title", "receipt_footer", "receipt_note"):
		if ch.get(k):
			values[k] = ch[k]
	cs.update(values)
	cs.save(ignore_permissions=True)
	log("إعدادات الحزمة الخيرية جاهزة")


# ---------------------------------------------------------------------------
# الدخول وكلمات المرور — سياسة موحّدة لكل مؤسسة على زِمام (0.7.1)
# ---------------------------------------------------------------------------
# افتراضيات Frappe صارمة على غير التقنيين: رابط إعادة التعيين يبطل بعد 20 دقيقة، و3 طلبات في الساعة فقط،
# ورابط الدخول بالبريد 10 دقائق. هنا: ساعتان للتعيين، 5 طلبات، رابط دخول 30 دقيقة، والدخول باسم المستخدم أيضًا.
DEFAULT_LOGIN_POLICY = {
	"login_with_email_link": 1,               # دخول برابط يُرسل إلى البريد بلا كلمة مرور
	"login_with_email_link_expiry": 30,       # دقائق
	"rate_limit_email_link_login": 5,         # طلبات في الساعة
	"reset_password_link_expiry_duration": 7200,  # ثانية = ساعتان
	"password_reset_limit": 5,                # طلبات إعادة تعيين في الساعة
	"allow_login_using_user_name": 1,
	"logout_on_password_reset": 1,
}


def setup_login_policy(policy=None):
	"""تطبيق سياسة الدخول على System Settings — تُكتب القيم المختلفة فقط (آمنة للتكرار)."""
	wanted = dict(DEFAULT_LOGIN_POLICY)
	wanted.update({k: v for k, v in (policy or {}).items() if not k.startswith("_")})
	ss = frappe.get_single("System Settings")
	changed = [k for k, v in wanted.items() if ss.meta.has_field(k) and (ss.get(k) or 0) != v]
	if not changed:
		return
	for k in changed:
		ss.set(k, wanted[k])
	ss.flags.ignore_mandatory = True
	ss.save(ignore_permissions=True)
	log("سياسة الدخول: " + "، ".join(f"{k}={wanted[k]}" for k in changed))


def ensure_users(rows):
	"""حسابات الدخول من ملف التعريف.

	- حساب جديد: يُنشأ «مستخدم نظام» بأدواره، ويُرسل له Frappe رسالة ترحيب تحمل رابط تعيين كلمة المرور
	  (صلاحيته حسب سياسة الدخول أعلاه) — لا تُكتب كلمة مرور في أي ملف.
	- حساب قائم: يُفعَّل إن كان معطَّلًا وتُستكمل أدواره الناقصة فقط؛ لا يُمسّ شيء آخر.
	- حساب Administrator لا يُرسل له Frappe بريد إعادة تعيين إطلاقًا؛ لذلك يجب أن يكون لكل مدير حسابه ببريده.
	"""
	for u in rows or []:
		email = (u.get("email") or "").strip().lower()
		if not email or "@" not in email:
			continue
		roles = [r for r in u.get("roles", []) if frappe.db.exists("Role", r)]
		for r in set(u.get("roles", [])) - set(roles):
			log(f"المستخدم {email}: الدور «{r}» غير موجود على هذا الموقع — تُخطّي")
		if frappe.db.exists("User", email):
			doc = frappe.get_doc("User", email)
			existing = {r.role for r in doc.roles}
			added = [r for r in roles if r not in existing]
			if not added and doc.enabled:
				log(f"المستخدم {email}: موجود بأدواره — لا تغيير")
				continue
			doc.enabled = 1
			for r in added:
				doc.append("roles", {"role": r})
			doc.save(ignore_permissions=True)
			log(f"المستخدم {email}: موجود — أُضيفت الأدوار {added}" if added else f"المستخدم {email}: أُعيد تفعيله")
			continue
		welcome = u.get("welcome_email", True)
		doc = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": u.get("first_name") or email.split("@")[0],
			"last_name": u.get("last_name"),
			"language": u.get("language") or "ar",
			"user_type": "System User",
			"enabled": 1,
			"send_welcome_email": 1 if welcome else 0,
			"roles": [{"role": r} for r in roles],
		})
		if u.get("time_zone"):
			doc.time_zone = u["time_zone"]
		doc.flags.no_welcome_mail = not welcome
		doc.insert(ignore_permissions=True)
		log(f"المستخدم {email}: أُنشئ" + (" وأُرسلت رسالة تعيين كلمة المرور إلى بريده" if welcome else " بلا رسالة ترحيب"))


def setup_website(institution):
	"""الصفحة الرسمية: صفحة هبوط زِمام صفحةً رئيسية، واسم المؤسسة وشعار زِمام في إعدادات الموقع وشاشة الدخول."""
	ws = frappe.get_single("Website Settings")
	changed = False
	if ws.home_page != "login":
		ws.home_page, changed = "login", True
	if not ws.app_name or ws.app_name in ("Frappe", "ERPNext"):
		ws.app_name, changed = institution, True
	if not ws.app_logo:
		ws.app_logo, changed = "/assets/zimam/images/zimam-mark.png", True
	if not ws.splash_image:
		ws.splash_image, changed = "/assets/zimam/images/zimam-logo.png", True
	if not ws.footer_powered:
		ws.footer_powered, changed = "يعمل هذا الموقع من خلال منصة زِمام", True
	if changed:
		ws.save(ignore_permissions=True)
		log("إعدادات الموقع: شاشة الدخول صفحةً رئيسية، الاسم، الشعار الرسمي")
