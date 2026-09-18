# -*- coding: utf-8 -*-
# Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
# For license information, please see license.txt
"""محرّك تقدير تكلفة الطباعة — Print Estimating Engine.

وحدة خالصة (بلا Frappe) حتى تُختبر محليًا وتُنقل حرفيًا إلى JavaScript في الحاسبة المستقلة.
المدخلات قواميس عادية (dict) والمخرجات قواميس؛ الربط بأنواع المستندات في `doctype/print_estimate/print_estimate.py`.

المنهج (كما في أنظمة Print MIS التجارية: Printlogic، Tharstern، Printsmith):
    مقاس نهائي + هوامش قصّ ⟵ التلقيم على فرخ التشغيل (ups) ⟵ الأفرخ الصافية والهدر ⟵ تكلفة الورق
    ⟵ المرورات/النقرات بحسب نوع الآلة (رقمية لكل نقرة · أوفست زنكات وتجهيز وتشغيل · واسعة التنسيق لكل م²)
    ⟵ التشطيب بأساسه (نسخة/فرخ/عمل/م²/ساعة/ألف) ⟵ بنود إضافية وتصميم ⟵ التكلفة
    ⟵ هامش + استعجال − خصم ⟵ تقريب وحدّ أدنى ⟵ ضريبة ⟵ الإجمالي، ثم يُعاد الحساب لكل شريحة كمية.
"""
from __future__ import annotations

import math

EDGE_MM = 5.0  # هامش جانبي غير مطبوع على كل حافة (غير حافة الماسك)

SINGLE = "قطعة واحدة"
COVER = "غلاف"
INNER = "داخلي"
INSERT = "إدراج/ملحق"

MACHINE_DIGITAL = "رقمية (لكل نقرة)"
MACHINE_OFFSET = "أوفست"
MACHINE_WIDE = "واسعة التنسيق (لكل م²)"

BASIS_PER_COPY = "لكل نسخة"
BASIS_PER_SHEET = "لكل فرخ"
BASIS_PER_JOB = "لكل عمل"
BASIS_PER_SQM = "لكل متر مربع"
BASIS_PER_HOUR = "لكل ساعة"
BASIS_PER_1000 = "لكل 1000"

PAPER_PER_SHEET = "لكل فرخ"
PAPER_PER_SQM = "لكل متر مربع"
PAPER_PER_LM = "لكل متر طولي"

BINDING_SPINE = {"غراء (تجليد حراري)", "خياطة وغراء", "غلاف صلب"}

SIZE_PRESETS = {
	"A6": (105, 148), "A5": (148, 210), "A4": (210, 297), "A3": (297, 420), "B5": (176, 250),
	"بطاقة أعمال 90×55": (90, 55), "DL 99×210": (99, 210), "20×20": (200, 200),
}


def flt(v, default=0.0):
	try:
		if v is None or v == "":
			return default
		return float(v)
	except (TypeError, ValueError):
		return default


def cint(v, default=0):
	try:
		if v is None or v == "":
			return default
		return int(float(v))
	except (TypeError, ValueError):
		return default


def r3(v):
	"""تقريب بدقة البيسة (3 منازل) كما يفعل ERPNext مع الريال العماني."""
	return round(flt(v) + 1e-9, 3)


# ---------------------------------------------------------------------------
# التلقيم (Imposition)
# ---------------------------------------------------------------------------
def imposition(piece_w, piece_h, sheet_w, sheet_h, bleed=0.0, gripper=0.0, edge=EDGE_MM):
	"""عدد القطع (ups) التي تسع على الفرخ في أفضل اتجاه، مع هوامش القصّ وحافة الماسك.

	يُرجع (ups, orientation) حيث orientation ∈ {"portrait", "landscape"}. صفر إن لم تسع قطعة واحدة.
	"""
	pw, ph = flt(piece_w) + 2 * flt(bleed), flt(piece_h) + 2 * flt(bleed)
	uw, uh = flt(sheet_w) - 2 * flt(edge), flt(sheet_h) - flt(gripper) - flt(edge)
	if pw <= 0 or ph <= 0 or uw <= 0 or uh <= 0:
		return 0, "portrait"
	a = int(uw // pw) * int(uh // ph)
	b = int(uw // ph) * int(uh // pw)
	return (a, "portrait") if a >= b else (b, "landscape")


def fits(w, h, max_w, max_h):
	return (flt(w) <= flt(max_w) and flt(h) <= flt(max_h)) or (flt(h) <= flt(max_w) and flt(w) <= flt(max_h))


def run_sheet(paper, machine):
	"""فرخ التشغيل: فرخ الورق كما يُشترى إن كان يسع الآلة، وإلا يُقصّ إلى أقصى مقاس تقبله الآلة.

	يُرجع (run_w, run_h, pieces_per_parent).
	"""
	pw, ph = flt(paper.get("sheet_width_mm")), flt(paper.get("sheet_height_mm"))
	mw, mh = flt(machine.get("max_sheet_width_mm")), flt(machine.get("max_sheet_height_mm"))
	if not mw or not mh or fits(pw, ph, mw, mh):
		return pw, ph, 1
	# القصّ من الفرخ الأم إلى فرخ الآلة (بلا هوامش قصّ ولا ماسك — القصّ بالمقص)
	ups, _ = imposition(mw, mh, pw, ph, bleed=0, gripper=0, edge=0)
	return mw, mh, max(ups, 1)


def paper_cost_per_run_sheet(paper, run_w, run_h, pieces_per_parent):
	basis = paper.get("pricing_basis") or PAPER_PER_SHEET
	cost = flt(paper.get("cost"))
	if basis == PAPER_PER_SQM:
		return cost * (flt(run_w) * flt(run_h)) / 1e6
	if basis == PAPER_PER_LM:
		# لفّة بعرض الفرخ: التكلفة لكل متر طولي من اللفّة
		return cost * flt(run_h) / 1000.0
	return cost / max(pieces_per_parent, 1)


def caliper_mm(paper):
	"""سماكة الورقة (مم): من الحقل إن وُجد، وإلا تقدير من الوزن (≈ 0.00125 مم لكل غم/م²)."""
	c = flt(paper.get("caliper_mm"))
	if c > 0:
		return c
	return flt(paper.get("gsm")) * 0.00125


def spine_mm(pages, inner_paper, binding):
	if binding not in BINDING_SPINE or not inner_paper:
		return 0.0
	leaves = math.ceil(cint(pages) / 2.0)
	return round(leaves * caliper_mm(inner_paper) + (1.0 if binding == "غلاف صلب" else 0.0), 1)


# ---------------------------------------------------------------------------
# مكوّن واحد (غلاف / داخلي / قطعة واحدة / إدراج)
# ---------------------------------------------------------------------------
def component_cost(comp, qty, paper, machine, waste_percent=5.0, bleed=3.0):
	"""تكلفة الورق والطباعة لمكوّن واحد بكمية qty.

	comp: component, pages, sides ("وجه"/"وجهان"), color ("ملون"/"أحادي"), piece_width_mm, piece_height_mm
	يُرجع قاموسًا بالقيم المحسوبة: ups, run_w, run_h, sheets, impressions, paper_cost, print_cost, amount, hours, area_sqm
	"""
	qty = max(cint(qty), 0)
	pages = max(cint(comp.get("pages")), 1)
	sides = 2 if (comp.get("sides") or "وجهان") == "وجهان" else 1
	color = (comp.get("color") or "ملون") == "ملون"
	pw, ph = flt(comp.get("piece_width_mm")), flt(comp.get("piece_height_mm"))
	mtype = machine.get("machine_type") or MACHINE_DIGITAL
	out = {"ups": 0, "run_w": 0, "run_h": 0, "sheets": 0, "impressions": 0, "paper_cost": 0.0, "print_cost": 0.0,
		"amount": 0.0, "hours": 0.0, "area_sqm": 0.0, "orientation": "portrait", "warning": ""}
	if qty == 0 or pw <= 0 or ph <= 0:
		return out

	if mtype == MACHINE_WIDE:
		# واسعة التنسيق: لا تلقيم — كل نسخة قطعة بمساحتها
		area = pw * ph / 1e6
		total_area = area * qty * (1 + flt(waste_percent) / 100.0)
		basis = paper.get("pricing_basis") or PAPER_PER_SQM
		if basis == PAPER_PER_SQM:
			paper_cost = flt(paper.get("cost")) * total_area
		elif basis == PAPER_PER_LM:
			# لفّة بعرض paper.sheet_width_mm: الطول المستهلك لكل نسخة = البعد الذي يُمرَّر على طول اللفّة
			roll_w = flt(paper.get("sheet_width_mm")) or max(pw, ph)
			across = min(pw, ph) if max(pw, ph) > roll_w else max(pw, ph)
			along = ph if across == pw else pw
			paper_cost = flt(paper.get("cost")) * (along / 1000.0) * qty * (1 + flt(waste_percent) / 100.0)
		else:
			sheet_area = flt(paper.get("sheet_width_mm")) * flt(paper.get("sheet_height_mm")) / 1e6
			paper_cost = flt(paper.get("cost")) * (total_area / sheet_area if sheet_area else 0)
		print_cost = max(flt(machine.get("cost_per_sqm")) * total_area * sides, flt(machine.get("min_charge")))
		print_cost += flt(machine.get("setup_cost"))
		speed = flt(machine.get("speed_per_hour"))
		hours = (total_area / speed) if speed else 0.0
		out.update(ups=1, run_w=pw, run_h=ph, sheets=qty, impressions=qty * sides, area_sqm=r3(total_area),
			paper_cost=r3(paper_cost), print_cost=r3(print_cost), amount=r3(paper_cost + print_cost), hours=round(hours + 0.25, 2))
		return out

	rw, rh, pieces_per_parent = run_sheet(paper, machine)
	ups, orientation = imposition(pw, ph, rw, rh, bleed=bleed, gripper=flt(machine.get("gripper_margin_mm")))
	if ups == 0:
		out["warning"] = "القطعة أكبر من فرخ التشغيل"
		return out
	duplex = sides == 2 and cint(machine.get("duplex", 1)) == 1
	leaves_per_copy = math.ceil(pages / 2.0) if sides == 2 else pages
	net_sheets = math.ceil(qty * leaves_per_copy / float(ups))
	waste = math.ceil(net_sheets * flt(waste_percent) / 100.0) + cint(machine.get("waste_sheets"))
	total_sheets = net_sheets + waste
	impressions = total_sheets * sides
	paper_cost = paper_cost_per_run_sheet(paper, rw, rh, pieces_per_parent) * total_sheets

	if mtype == MACHINE_OFFSET:
		colors = 4 if color else 1
		plates = colors * sides
		print_cost = plates * (flt(machine.get("plate_cost")) + flt(machine.get("makeready_cost")))
		print_cost += impressions * flt(machine.get("run_cost_per_1000")) / 1000.0
		print_cost += flt(machine.get("setup_cost"))
	else:  # رقمية
		click = flt(machine.get("click_cost_color")) if color else flt(machine.get("click_cost_mono"))
		print_cost = impressions * click + flt(machine.get("setup_cost"))
	if not duplex and sides == 2 and mtype != MACHINE_OFFSET:
		out["warning"] = "الآلة لا تطبع الوجهين آليًا — يُحسب مروران يدويان"
	speed = flt(machine.get("speed_per_hour"))
	hours = (impressions / speed if speed else 0.0) + 0.25
	out.update(ups=ups, run_w=rw, run_h=rh, orientation=orientation, sheets=total_sheets, impressions=impressions,
		paper_cost=r3(paper_cost), print_cost=r3(print_cost), amount=r3(paper_cost + print_cost), hours=round(hours, 2),
		area_sqm=r3(pw * ph / 1e6 * qty))
	return out


# ---------------------------------------------------------------------------
# التشطيب
# ---------------------------------------------------------------------------
def finishing_qty(row, service, qty, comps_out, comps_in, piece_area_sqm):
	"""الكمية الآلية لبند تشطيب بحسب أساسه: نسخة ⟵ الكمية × الكمية لكل نسخة · فرخ ⟵ أفرخ المكوّنات المعنية · عمل ⟵ 1
	· م² ⟵ مساحة القطعة × الكمية · ساعة ⟵ كما أُدخل · 1000 ⟵ الكمية/1000."""
	basis = row.get("basis") or service.get("basis") or BASIS_PER_COPY
	per_copy = flt(row.get("qty_per_copy"), 1.0) or 1.0
	applies = row.get("applies_to") or "الكل"
	if basis == BASIS_PER_COPY:
		return qty * per_copy
	if basis == BASIS_PER_SHEET:
		total = 0
		for c, o in zip(comps_in, comps_out):
			if applies == "الكل" or (applies == "الغلاف" and c.get("component") in (COVER, SINGLE)) \
				or (applies == "الداخلي" and c.get("component") in (INNER, INSERT)):
				total += cint(o.get("sheets"))
		return total * per_copy
	if basis == BASIS_PER_JOB:
		return 1
	if basis == BASIS_PER_SQM:
		return r3(piece_area_sqm * qty * per_copy)
	if basis == BASIS_PER_1000:
		return math.ceil(qty * per_copy / 1000.0)
	return flt(row.get("qty"), 1.0) or 1.0  # لكل ساعة: الساعات كما أُدخلت


def finishing_amount(row, service, q):
	rate = flt(row.get("rate")) if row.get("rate") not in (None, "") else flt(service.get("rate"))
	setup = flt(row.get("setup_cost")) if row.get("setup_cost") not in (None, "") else flt(service.get("setup_cost"))
	amount = q * rate + setup
	return r3(max(amount, flt(service.get("min_charge"))))


# ---------------------------------------------------------------------------
# التقدير الكامل
# ---------------------------------------------------------------------------
def round_to(value, step):
	step = flt(step)
	if step <= 0:
		return r3(value)
	return r3(math.ceil(flt(value) / step - 1e-9) * step)


def price_from_cost(total_cost, settings, doc):
	"""من التكلفة إلى السعر: هامش ⟵ استعجال ⟵ خصم ⟵ تقريب ⟵ حد أدنى."""
	margin = flt(doc.get("margin_percent"), flt(settings.get("default_margin_percent")))
	price = flt(total_cost) * (1 + margin / 100.0)
	rush_amount = 0.0
	if cint(doc.get("rush")):
		rush_amount = price * flt(doc.get("rush_percent"), flt(settings.get("default_rush_percent"))) / 100.0
		price += rush_amount
	discount = price * flt(doc.get("discount_percent")) / 100.0
	price -= discount
	price = round_to(price, doc.get("round_to") or settings.get("default_round_to") or 0)
	min_price = flt(settings.get("min_job_price"))
	if min_price and price < min_price:
		price = min_price
	return r3(price), r3(rush_amount), r3(discount)


def compute(doc, masters, settings=None):
	"""يحسب التقدير كاملًا.

	doc: قاموس المستند (الحقول الرئيسية + components + finishing + extras + tiers)
	masters: {"paper": {name: dict}, "machine": {name: dict}, "finishing": {name: dict}}
	settings: إعدادات المطبعة (الافتراضيات)
	يُرجع قاموسًا بالقيم الرئيسية المحسوبة + components/finishing/tiers قوائم بترتيب الإدخال.
	"""
	settings = settings or {}
	qty = max(cint(doc.get("quantity")), 0)
	bleed = flt(doc.get("bleed_mm"), flt(settings.get("default_bleed_mm"), 3.0))
	waste = flt(doc.get("waste_percent"), flt(settings.get("default_waste_percent"), 5.0))
	fw, fh = flt(doc.get("finished_width_mm")), flt(doc.get("finished_height_mm"))
	preset = doc.get("size_preset")
	if preset in SIZE_PRESETS and (not fw or not fh):
		fw, fh = SIZE_PRESETS[preset]
	binding = doc.get("binding") or "بلا"
	structure = doc.get("structure") or SINGLE
	pages = cint(doc.get("pages"))

	comps = list(doc.get("components") or [])
	inner_paper = None
	for c in comps:
		if c.get("component") == INNER and c.get("paper") in masters.get("paper", {}):
			inner_paper = masters["paper"][c["paper"]]
			break
	spine = spine_mm(pages, inner_paper, binding) if structure != SINGLE else 0.0

	def run(q):
		comp_out, paper_cost, print_cost, sheets, impressions, hours = [], 0.0, 0.0, 0, 0, 0.0
		if q <= 0:
			return {"components": [dict(ups=0, sheets=0, impressions=0, paper_cost=0.0, print_cost=0.0, amount=0.0, hours=0.0, run_w=0, run_h=0,
				area_sqm=0.0, orientation="portrait", warning="الكمية صفر", piece_width_mm=fw, piece_height_mm=fh, pages=cint(c.get("pages")) or 1) for c in comps],
				"finishing": [dict(basis=r.get("basis") or BASIS_PER_COPY, qty=0.0, rate=0.0, setup_cost=0.0, amount=0.0) for r in doc.get("finishing") or []],
				"extras": [dict(amount=0.0) for _ in doc.get("extras") or []],
				"paper_cost": 0.0, "print_cost": 0.0, "finishing_cost": 0.0, "extras_cost": 0.0, "design_cost": 0.0, "total_cost": 0.0,
				"rush_amount": 0.0, "discount_amount": 0.0, "net_total": 0.0, "unit_price": 0.0, "unit_cost": 0.0,
				"tax_rate": flt(doc.get("tax_rate"), flt(settings.get("default_tax_rate"))), "tax_amount": 0.0, "grand_total": 0.0,
				"total_sheets": 0, "total_impressions": 0, "production_hours": 0.0}
		for c in comps:
			paper = masters.get("paper", {}).get(c.get("paper")) or {}
			machine = masters.get("machine", {}).get(c.get("machine")) or {}
			cc = dict(c)
			if cint(c.get("auto_size", 1)):
				# الغلاف والقطعة الواحدة: الصفحات المطبوعة = عدد الأوجه (وجه ⟵ 1، وجهان ⟵ 2)؛ الداخلي: من عدد صفحات المستند
				if c.get("component") in (COVER, SINGLE):
					cc["pages"] = 2 if (c.get("sides") or "وجهان") == "وجهان" else 1
				if c.get("component") == COVER and structure != SINGLE:
					cc["piece_width_mm"], cc["piece_height_mm"] = round(2 * fw + spine, 1), fh
				else:
					cc["piece_width_mm"], cc["piece_height_mm"] = fw, fh
					if c.get("component") == INNER and not cint(c.get("pages")):
						cc["pages"] = pages
			if not paper or not machine:
				o = {"ups": 0, "sheets": 0, "impressions": 0, "paper_cost": 0.0, "print_cost": 0.0, "amount": 0.0, "hours": 0.0,
					"run_w": 0, "run_h": 0, "area_sqm": 0.0, "orientation": "portrait", "warning": "حدد الورق والآلة"}
			else:
				o = component_cost(cc, q, paper, machine, waste_percent=waste, bleed=bleed)
			o["piece_width_mm"], o["piece_height_mm"], o["pages"] = cc.get("piece_width_mm"), cc.get("piece_height_mm"), cint(cc.get("pages")) or 1
			comp_out.append(o)
			paper_cost += o["paper_cost"]
			print_cost += o["print_cost"]
			sheets += o["sheets"]
			impressions += o["impressions"]
			hours += o["hours"]

		fin_out, fin_cost = [], 0.0
		piece_area = fw * fh / 1e6
		for r in doc.get("finishing") or []:
			svc = masters.get("finishing", {}).get(r.get("finishing_service")) or {}
			rr = dict(r)
			rr["basis"] = r.get("basis") or svc.get("basis") or BASIS_PER_COPY
			fq = finishing_qty(rr, svc, q, comp_out, comps, piece_area) if cint(r.get("auto_qty", 1)) else flt(r.get("qty"))
			amt = finishing_amount(rr, svc, flt(fq))
			rate = flt(r.get("rate")) if r.get("rate") not in (None, "") else flt(svc.get("rate"))
			setup = flt(r.get("setup_cost")) if r.get("setup_cost") not in (None, "") else flt(svc.get("setup_cost"))
			fin_out.append({"basis": rr["basis"], "qty": r3(fq), "rate": r3(rate), "setup_cost": r3(setup), "amount": amt})
			fin_cost += amt

		extras_cost = 0.0
		extras_out = []
		for r in doc.get("extras") or []:
			amt = r3(flt(r.get("qty"), 1.0) * flt(r.get("rate")))
			extras_out.append({"amount": amt})
			extras_cost += amt
		design_cost = r3(flt(doc.get("design_hours")) * flt(doc.get("design_rate"), flt(settings.get("default_design_rate"))))
		extras_cost += design_cost

		total_cost = r3(paper_cost + print_cost + fin_cost + extras_cost)
		net_total, rush_amount, discount_amount = price_from_cost(total_cost, settings, doc)
		tax_rate = flt(doc.get("tax_rate"), flt(settings.get("default_tax_rate")))
		tax_amount = r3(net_total * tax_rate / 100.0)
		grand_total = r3(net_total + tax_amount)
		return {
			"components": comp_out, "finishing": fin_out, "extras": extras_out,
			"paper_cost": r3(paper_cost), "print_cost": r3(print_cost), "finishing_cost": r3(fin_cost),
			"extras_cost": r3(extras_cost), "design_cost": design_cost, "total_cost": total_cost,
			"rush_amount": rush_amount, "discount_amount": discount_amount, "net_total": net_total,
			"unit_price": r3(net_total / q) if q else 0.0, "unit_cost": r3(total_cost / q) if q else 0.0,
			"tax_rate": tax_rate, "tax_amount": tax_amount, "grand_total": grand_total,
			"total_sheets": sheets, "total_impressions": impressions, "production_hours": round(hours, 2),
		}

	result = run(qty)
	result.update(finished_width_mm=fw, finished_height_mm=fh, spine_mm=spine, quantity=qty)
	tiers = []
	for t in doc.get("tiers") or []:
		tq = cint(t.get("qty"))
		if tq <= 0:
			tiers.append({"qty": tq, "total_cost": 0, "price": 0, "unit_price": 0, "grand_total": 0})
			continue
		r = run(tq)
		tiers.append({"qty": tq, "total_cost": r["total_cost"], "price": r["net_total"], "unit_price": r["unit_price"], "grand_total": r["grand_total"]})
	result["tiers"] = tiers
	result["estimated_days"] = max(1, math.ceil(result["production_hours"] / 8.0)) + (0 if cint(doc.get("rush")) else 1)
	return result


def parse_tiers(text):
	"""«100, 250, 500» ⟵ [100, 250, 500]."""
	out = []
	for part in str(text or "").replace("،", ",").split(","):
		q = cint(part.strip())
		if q > 0 and q not in out:
			out.append(q)
	return out
