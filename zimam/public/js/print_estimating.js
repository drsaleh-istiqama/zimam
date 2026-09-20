// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// محرّك تقدير تكلفة الطباعة — نسخة JavaScript مطابقة حرفيًا لـ zimam_core/print_estimating.py
// (تُختبر بالحالات نفسها عبر tools/test_print_estimating_js.mjs). تعمل في المتصفح (الحاسبة المستقلة، صفحة التسعير السريع) وفي Node.
(function (root, factory) {
	if (typeof module === "object" && module.exports) module.exports = factory();
	else root.PrintEstimating = factory();
})(typeof self !== "undefined" ? self : this, function () {
	"use strict";
	const EDGE_MM = 5.0;
	const SINGLE = "قطعة واحدة", COVER = "غلاف", INNER = "داخلي", INSERT = "إدراج/ملحق";
	const MACHINE_DIGITAL = "رقمية (لكل نقرة)", MACHINE_OFFSET = "أوفست", MACHINE_WIDE = "واسعة التنسيق (لكل م²)";
	const BASIS_PER_COPY = "لكل نسخة", BASIS_PER_SHEET = "لكل فرخ", BASIS_PER_JOB = "لكل عمل", BASIS_PER_SQM = "لكل متر مربع", BASIS_PER_1000 = "لكل 1000";
	const PAPER_PER_SHEET = "لكل فرخ", PAPER_PER_SQM = "لكل متر مربع", PAPER_PER_LM = "لكل متر طولي";
	const PRICING_FIXED = "هامش ثابت", PRICING_BY_QTY = "هامش بحسب الكمية";
	const BINDING_SPINE = new Set(["غراء (تجليد حراري)", "خياطة وغراء", "غلاف صلب"]);
	const SIZE_PRESETS = {
		A7: [74, 105], A6: [105, 148], A5: [148, 210], A4: [210, 297], A3: [297, 420],
		B5: [176, 250], B4: [250, 353], "Letter 216×279": [216, 279],
		"بطاقة أعمال 90×55": [90, 55], "بطاقة تعريف (باج) 90×130": [90, 130], "DL 99×210": [99, 210],
		"ظرف DL 110×220": [110, 220], "ظرف C5 162×229": [162, 229], "ظرف C4 229×324": [229, 324],
		"10×15": [100, 150], "13×18": [130, 180], "15×15": [150, 150], "20×20": [200, 200], "21×21": [210, 210],
		"بوستر 50×70": [500, 700], "بوستر 60×90": [600, 900], "70×100": [700, 1000],
		"رول أب 85×200": [850, 2000], "بانر 100×200": [1000, 2000], "بانر 200×100": [2000, 1000], "بانر 300×100": [3000, 1000],
	};

	const isNil = (v) => v === null || v === undefined || v === "";
	function flt(v, d) { d = d === undefined ? 0.0 : d; if (isNil(v)) return d; const n = parseFloat(v); return Number.isFinite(n) ? n : d; }
	function cint(v, d) { d = d === undefined ? 0 : d; if (isNil(v)) return d; const n = parseFloat(v); return Number.isFinite(n) ? Math.trunc(n) : d; }
	function r3(v) { return Math.round((flt(v) + 1e-9) * 1000) / 1000; }
	// Python's round() half-to-even vs JS Math.round: القيم هنا تمرّ عبر r3 ثم round(…,1) للكعب فقط
	function round1(v) { return Math.round(v * 10 + 1e-9) / 10; }

	function imposition(pw0, ph0, sw, sh, bleed, gripper, edge) {
		bleed = flt(bleed); gripper = flt(gripper); edge = edge === undefined ? EDGE_MM : flt(edge);
		const pw = flt(pw0) + 2 * bleed, ph = flt(ph0) + 2 * bleed;
		const uw = flt(sw) - 2 * edge, uh = flt(sh) - gripper - edge;
		if (pw <= 0 || ph <= 0 || uw <= 0 || uh <= 0) return [0, "portrait"];
		const a = Math.floor(uw / pw) * Math.floor(uh / ph);
		const b = Math.floor(uw / ph) * Math.floor(uh / pw);
		return a >= b ? [a, "portrait"] : [b, "landscape"];
	}
	function fits(w, h, mw, mh) { return (flt(w) <= flt(mw) && flt(h) <= flt(mh)) || (flt(h) <= flt(mw) && flt(w) <= flt(mh)); }
	function runSheet(paper, machine) {
		const pw = flt(paper.sheet_width_mm), ph = flt(paper.sheet_height_mm);
		const mw = flt(machine.max_sheet_width_mm), mh = flt(machine.max_sheet_height_mm);
		if (!mw || !mh || fits(pw, ph, mw, mh)) return [pw, ph, 1];
		const ups = imposition(mw, mh, pw, ph, 0, 0, 0)[0];
		return [mw, mh, Math.max(ups, 1)];
	}
	function paperCostPerRunSheet(paper, rw, rh, pieces) {
		const basis = paper.pricing_basis || PAPER_PER_SHEET, cost = flt(paper.cost);
		if (basis === PAPER_PER_SQM) return cost * (flt(rw) * flt(rh)) / 1e6;
		if (basis === PAPER_PER_LM) return cost * flt(rh) / 1000.0;
		return cost / Math.max(pieces, 1);
	}
	function caliperMm(paper) { const c = flt(paper.caliper_mm); return c > 0 ? c : flt(paper.gsm) * 0.00125; }
	function spineMm(pages, innerPaper, binding) {
		if (!BINDING_SPINE.has(binding) || !innerPaper) return 0.0;
		const leaves = Math.ceil(cint(pages) / 2.0);
		return round1(leaves * caliperMm(innerPaper) + (binding === "غلاف صلب" ? 1.0 : 0.0));
	}

	function componentCost(comp, qty, paper, machine, wastePercent, bleed) {
		wastePercent = wastePercent === undefined ? 5.0 : wastePercent; bleed = bleed === undefined ? 3.0 : bleed;
		qty = Math.max(cint(qty), 0);
		const pages = Math.max(cint(comp.pages), 1);
		const sides = (comp.sides || "وجهان") === "وجهان" ? 2 : 1;
		const color = (comp.color || "ملون") === "ملون";
		const pw = flt(comp.piece_width_mm), ph = flt(comp.piece_height_mm);
		const mtype = machine.machine_type || MACHINE_DIGITAL;
		const out = { ups: 0, run_w: 0, run_h: 0, sheets: 0, impressions: 0, paper_cost: 0.0, print_cost: 0.0, amount: 0.0, hours: 0.0, area_sqm: 0.0, orientation: "portrait", warning: "" };
		if (qty === 0 || pw <= 0 || ph <= 0) return out;
		if (mtype === MACHINE_WIDE) {
			const area = pw * ph / 1e6;
			const totalArea = area * qty * (1 + flt(wastePercent) / 100.0);
			const basis = paper.pricing_basis || PAPER_PER_SQM;
			let paperCost;
			if (basis === PAPER_PER_SQM) paperCost = flt(paper.cost) * totalArea;
			else if (basis === PAPER_PER_LM) {
				const rollW = flt(paper.sheet_width_mm) || Math.max(pw, ph);
				const across = Math.max(pw, ph) > rollW ? Math.min(pw, ph) : Math.max(pw, ph);
				const along = across === pw ? ph : pw;
				paperCost = flt(paper.cost) * (along / 1000.0) * qty * (1 + flt(wastePercent) / 100.0);
			} else {
				const sheetArea = flt(paper.sheet_width_mm) * flt(paper.sheet_height_mm) / 1e6;
				paperCost = flt(paper.cost) * (sheetArea ? totalArea / sheetArea : 0);
			}
			let printCost = Math.max(flt(machine.cost_per_sqm) * totalArea * sides, flt(machine.min_charge));
			printCost += flt(machine.setup_cost);
			const speed = flt(machine.speed_per_hour);
			const hours = speed ? totalArea / speed : 0.0;
			Object.assign(out, { ups: 1, run_w: pw, run_h: ph, sheets: qty, impressions: qty * sides, area_sqm: r3(totalArea), paper_cost: r3(paperCost), print_cost: r3(printCost), amount: r3(paperCost + printCost), hours: Math.round((hours + 0.25) * 100) / 100 });
			return out;
		}
		let rw, rh, pieces, ups, orientation;
		if (cint(paper.is_precut)) {
			// قطعة جاهزة (ظرف، بطاقة مقصوصة…): تُطبع كما هي — قطعة واحدة بلا هوامش ولا تلقيم
			rw = flt(paper.sheet_width_mm) || pw; rh = flt(paper.sheet_height_mm) || ph; pieces = 1; ups = 1; orientation = "portrait";
		} else {
			[rw, rh, pieces] = runSheet(paper, machine);
			[ups, orientation] = imposition(pw, ph, rw, rh, bleed, flt(machine.gripper_margin_mm));
		}
		if (ups === 0) { out.warning = "القطعة أكبر من فرخ التشغيل"; return out; }
		const duplex = sides === 2 && cint(isNil(machine.duplex) ? 1 : machine.duplex) === 1;
		const leavesPerCopy = sides === 2 ? Math.ceil(pages / 2.0) : pages;
		const netSheets = Math.ceil(qty * leavesPerCopy / ups);
		const waste = Math.ceil(netSheets * flt(wastePercent) / 100.0) + cint(machine.waste_sheets);
		const totalSheets = netSheets + waste;
		const impressions = totalSheets * sides;
		const paperCost = paperCostPerRunSheet(paper, rw, rh, pieces) * totalSheets;
		let printCost;
		if (mtype === MACHINE_OFFSET) {
			const colors = color ? 4 : 1, plates = colors * sides;
			printCost = plates * (flt(machine.plate_cost) + flt(machine.makeready_cost));
			printCost += impressions * flt(machine.run_cost_per_1000) / 1000.0;
			printCost += flt(machine.setup_cost);
		} else {
			const click = color ? flt(machine.click_cost_color) : flt(machine.click_cost_mono);
			printCost = impressions * click + flt(machine.setup_cost);
		}
		if (!duplex && sides === 2 && mtype !== MACHINE_OFFSET) out.warning = "الآلة لا تطبع الوجهين آليًا — يُحسب مروران يدويان";
		const speed = flt(machine.speed_per_hour);
		const hours = (speed ? impressions / speed : 0.0) + 0.25;
		Object.assign(out, { ups, run_w: rw, run_h: rh, orientation, sheets: totalSheets, impressions, paper_cost: r3(paperCost), print_cost: r3(printCost), amount: r3(paperCost + printCost), hours: Math.round(hours * 100) / 100, area_sqm: r3(pw * ph / 1e6 * qty) });
		return out;
	}

	function finishingQty(row, service, qty, compsOut, compsIn, pieceArea) {
		const basis = row.basis || service.basis || BASIS_PER_COPY;
		const perCopy = flt(row.qty_per_copy, 1.0) || 1.0;
		const applies = row.applies_to || "الكل";
		if (basis === BASIS_PER_COPY) return qty * perCopy;
		if (basis === BASIS_PER_SHEET) {
			let total = 0;
			compsIn.forEach((c, i) => {
				const o = compsOut[i]; if (!o) return;
				if (applies === "الكل" || (applies === "الغلاف" && (c.component === COVER || c.component === SINGLE)) || (applies === "الداخلي" && (c.component === INNER || c.component === INSERT))) total += cint(o.sheets);
			});
			return total * perCopy;
		}
		if (basis === BASIS_PER_JOB) return 1;
		if (basis === BASIS_PER_SQM) return r3(pieceArea * qty * perCopy);
		if (basis === BASIS_PER_1000) return Math.ceil(qty * perCopy / 1000.0);
		return flt(row.qty, 1.0) || 1.0;
	}
	function finishingAmount(row, service, q) {
		const rate = !isNil(row.rate) ? flt(row.rate) : flt(service.rate);
		const setup = !isNil(row.setup_cost) ? flt(row.setup_cost) : flt(service.setup_cost);
		let amount = Math.max(q * rate + setup, flt(service.min_charge));
		if (cint(service.is_outsourced)) amount *= 1 + flt(service.outsource_markup_percent) / 100.0;
		return r3(amount);
	}

	// الهامش بحسب الكمية: «1:45, 100:40, 500:35» ⟵ [[1,45],[100,40],[500,35]]
	function parseMarginTiers(text) {
		const out = [];
		String(text || "").replace(/،/g, ",").replace(/؛/g, ",").split(",").forEach((part) => {
			if (!part.includes(":")) return;
			const i = part.indexOf(":");
			const q = cint(part.slice(0, i).trim()), m = flt(part.slice(i + 1).trim(), null);
			if (q > 0 && m !== null && !out.some((x) => x[0] === q)) out.push([q, m]);
		});
		out.sort((a, b) => a[0] - b[0]);
		return out;
	}
	function marginForQty(text, qty, dflt) {
		let margin = flt(dflt);
		for (const [q, m] of parseMarginTiers(text)) if (cint(qty) >= q) margin = m;
		return margin;
	}

	function roundTo(value, step) {
		step = flt(step);
		if (step <= 0) return r3(value);
		return r3(Math.ceil(flt(value) / step - 1e-9) * step);
	}
	function priceFromCost(totalCost, settings, doc, qty) {
		let margin = flt(doc.margin_percent, flt(settings.default_margin_percent));
		const mode = doc.pricing_mode || settings.default_pricing_mode || PRICING_FIXED;
		if (mode === PRICING_BY_QTY && cint(qty) > 0) margin = marginForQty(doc.margin_tiers || settings.margin_tiers, qty, margin);
		let price = flt(totalCost) * (1 + margin / 100.0);
		let rushAmount = 0.0;
		if (cint(doc.rush)) { rushAmount = price * flt(doc.rush_percent, flt(settings.default_rush_percent)) / 100.0; price += rushAmount; }
		const discount = price * flt(doc.discount_percent) / 100.0;
		price -= discount;
		price = roundTo(price, doc.round_to || settings.default_round_to || 0);
		const minPrice = flt(settings.min_job_price);
		if (minPrice && price < minPrice) price = minPrice;
		return [r3(price), r3(rushAmount), r3(discount), r3(margin)];
	}

	function compute(doc, masters, settings) {
		settings = settings || {};
		const qty = Math.max(cint(doc.quantity), 0);
		const bleed = flt(doc.bleed_mm, flt(settings.default_bleed_mm, 3.0));
		const waste = flt(doc.waste_percent, flt(settings.default_waste_percent, 5.0));
		let fw = flt(doc.finished_width_mm), fh = flt(doc.finished_height_mm);
		const preset = doc.size_preset;
		if (preset in SIZE_PRESETS && (!fw || !fh)) [fw, fh] = SIZE_PRESETS[preset];
		const binding = doc.binding || "بلا";
		const structure = doc.structure || SINGLE;
		const pages = cint(doc.pages);
		const comps = (doc.components || []).slice();
		const papers = masters.paper || {}, machines = masters.machine || {}, fins = masters.finishing || {};
		let innerPaper = null;
		for (const c of comps) { if (c.component === INNER && c.paper in papers) { innerPaper = papers[c.paper]; break; } }
		const spine = structure !== SINGLE ? spineMm(pages, innerPaper, binding) : 0.0;
		const taxRateOf = () => flt(doc.tax_rate, flt(settings.default_tax_rate));

		function run(q) {
			if (q <= 0) {
				return {
					components: comps.map((c) => ({ ups: 0, sheets: 0, impressions: 0, paper_cost: 0.0, print_cost: 0.0, amount: 0.0, hours: 0.0, run_w: 0, run_h: 0, area_sqm: 0.0, orientation: "portrait", warning: "الكمية صفر", piece_width_mm: fw, piece_height_mm: fh, pages: cint(c.pages) || 1 })),
					finishing: (doc.finishing || []).map((r) => ({ basis: r.basis || BASIS_PER_COPY, qty: 0.0, rate: 0.0, setup_cost: 0.0, amount: 0.0, outsourced: 0 })),
					extras: (doc.extras || []).map(() => ({ amount: 0.0 })),
					paper_cost: 0.0, print_cost: 0.0, finishing_cost: 0.0, extras_cost: 0.0, design_cost: 0.0, total_cost: 0.0, rush_amount: 0.0, discount_amount: 0.0, net_total: 0.0, unit_price: 0.0, unit_cost: 0.0, margin_applied: 0.0, tax_rate: taxRateOf(), tax_amount: 0.0, grand_total: 0.0, total_sheets: 0, total_impressions: 0, production_hours: 0.0, lead_days: 0,
				};
			}
			const compOut = []; let paperCost = 0.0, printCost = 0.0, sheets = 0, impressions = 0, hours = 0.0;
			for (const c of comps) {
				const paper = papers[c.paper] || null, machine = machines[c.machine] || null;
				const cc = Object.assign({}, c);
				if (cint(isNil(c.auto_size) ? 1 : c.auto_size)) {
					if (c.component === COVER || c.component === SINGLE) cc.pages = (c.sides || "وجهان") === "وجهان" ? 2 : 1;
					if (c.component === COVER && structure !== SINGLE) { cc.piece_width_mm = round1(2 * fw + spine); cc.piece_height_mm = fh; }
					else { cc.piece_width_mm = fw; cc.piece_height_mm = fh; if (c.component === INNER && !cint(c.pages)) cc.pages = pages; }
				}
				let o;
				if (!paper || !machine) o = { ups: 0, sheets: 0, impressions: 0, paper_cost: 0.0, print_cost: 0.0, amount: 0.0, hours: 0.0, run_w: 0, run_h: 0, area_sqm: 0.0, orientation: "portrait", warning: "حدد الورق والآلة" };
				else o = componentCost(cc, q, paper, machine, waste, bleed);
				o.piece_width_mm = cc.piece_width_mm; o.piece_height_mm = cc.piece_height_mm; o.pages = cint(cc.pages) || 1;
				compOut.push(o);
				paperCost += o.paper_cost; printCost += o.print_cost; sheets += o.sheets; impressions += o.impressions; hours += o.hours;
			}
			const finOut = []; let finCost = 0.0, leadDays = 0;
			const pieceArea = fw * fh / 1e6;
			for (const r of doc.finishing || []) {
				const svc = fins[r.finishing_service] || {};
				const rr = Object.assign({}, r); rr.basis = r.basis || svc.basis || BASIS_PER_COPY;
				const fq = cint(isNil(r.auto_qty) ? 1 : r.auto_qty) ? finishingQty(rr, svc, q, compOut, comps, pieceArea) : flt(r.qty);
				const amt = finishingAmount(rr, svc, flt(fq));
				const rate = !isNil(r.rate) ? flt(r.rate) : flt(svc.rate);
				const setup = !isNil(r.setup_cost) ? flt(r.setup_cost) : flt(svc.setup_cost);
				finOut.push({ basis: rr.basis, qty: r3(fq), rate: r3(rate), setup_cost: r3(setup), amount: amt, outsourced: cint(svc.is_outsourced) ? 1 : 0 });
				finCost += amt;
				leadDays = Math.max(leadDays, cint(svc.lead_days));
			}
			let extrasCost = 0.0; const extrasOut = [];
			for (const r of doc.extras || []) { const amt = r3(flt(r.qty, 1.0) * flt(r.rate)); extrasOut.push({ amount: amt }); extrasCost += amt; }
			const designCost = r3(flt(doc.design_hours) * flt(doc.design_rate, flt(settings.default_design_rate)));
			extrasCost += designCost;
			const totalCost = r3(paperCost + printCost + finCost + extrasCost);
			const [netTotal, rushAmount, discountAmount, marginApplied] = priceFromCost(totalCost, settings, doc, q);
			const taxRate = taxRateOf();
			const taxAmount = r3(netTotal * taxRate / 100.0);
			const grandTotal = r3(netTotal + taxAmount);
			return {
				components: compOut, finishing: finOut, extras: extrasOut,
				paper_cost: r3(paperCost), print_cost: r3(printCost), finishing_cost: r3(finCost), extras_cost: r3(extrasCost), design_cost: designCost, total_cost: totalCost,
				rush_amount: rushAmount, discount_amount: discountAmount, net_total: netTotal, margin_applied: marginApplied,
				unit_price: q ? r3(netTotal / q) : 0.0, unit_cost: q ? r3(totalCost / q) : 0.0,
				tax_rate: taxRate, tax_amount: taxAmount, grand_total: grandTotal,
				total_sheets: sheets, total_impressions: impressions, production_hours: Math.round(hours * 100) / 100, lead_days: leadDays,
			};
		}
		const result = run(qty);
		Object.assign(result, { finished_width_mm: fw, finished_height_mm: fh, spine_mm: spine, quantity: qty });
		result.tiers = (doc.tiers || []).map((t) => {
			const tq = cint(t.qty);
			if (tq <= 0) return { qty: tq, total_cost: 0, price: 0, unit_price: 0, grand_total: 0, margin_applied: 0 };
			const r = run(tq);
			return { qty: tq, total_cost: r.total_cost, price: r.net_total, unit_price: r.unit_price, grand_total: r.grand_total, margin_applied: r.margin_applied };
		});
		result.estimated_days = Math.max(1, Math.ceil(result.production_hours / 8.0)) + (cint(doc.rush) ? 0 : 1) + cint(result.lead_days);
		return result;
	}
	function parseTiers(text) {
		const out = [];
		String(text || "").replace(/،/g, ",").split(",").forEach((p) => { const q = cint(p.trim()); if (q > 0 && !out.includes(q)) out.push(q); });
		return out;
	}

	// ملخص عرض السعر نصًّا عاديًا (لواتساب/البريد/النسخ) — مطابق لـ summary_text في Python
	function summaryText(doc, result, settings, company) {
		settings = settings || {};
		const money = (v) => flt(v).toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
		const g = (v) => (isNil(v) ? "" : String(Number(flt(v))));
		const lines = [("عرض سعر طباعة — " + (doc.title || "")).replace(/\s—\s*$/, "").replace(/ —$/, "")];
		if (company) lines[0] += ` (${company})`;
		const spec = [`الكمية: ${cint(doc.quantity)}`, `المقاس: ${g(result.finished_width_mm)}×${g(result.finished_height_mm)} مم`];
		if ((doc.structure || SINGLE) !== SINGLE) {
			spec.push(`${cint(doc.pages)} صفحة داخلية`);
			if (doc.binding && doc.binding !== "بلا") spec.push(`التجليد: ${doc.binding}`);
		}
		lines.push(spec.join(" · "));
		for (const c of doc.components || []) {
			const label = c.component === SINGLE ? "الورق" : c.component;
			lines.push(`${label}: ${c.paper} — ${c.color || "ملون"}، ${c.sides || "وجهان"}`);
		}
		const fins = (doc.finishing || []).map((f) => `${f.finishing_service}` + (f.applies_to && f.applies_to !== "الكل" ? ` (${f.applies_to})` : ""));
		if (fins.length) lines.push("التشطيب: " + fins.join("، "));
		lines.push("");
		lines.push(`السعر قبل الضريبة: ${money(result.net_total)} ر.ع (سعر الوحدة ${money(result.unit_price)})`);
		if (flt(result.tax_amount)) lines.push(`الضريبة ${g(result.tax_rate)}%: ${money(result.tax_amount)}`);
		lines.push(`الإجمالي شامل الضريبة: ${money(result.grand_total)} ر.ع`);
		const tiers = (result.tiers || []).filter((t) => cint(t.qty) > 0);
		if (tiers.length > 1) {
			lines.push("");
			lines.push("أسعار الكميات الأخرى:");
			for (const t of tiers) lines.push(`${t.qty} نسخة: ${money(t.unit_price)} للوحدة — ${money(t.grand_total)} شامل الضريبة`);
		}
		const tail = [];
		if (result.estimated_days) tail.push(`مدة التنفيذ المتوقعة: ${result.estimated_days} يوم عمل`);
		const validity = doc.validity_days || settings.default_validity_days;
		if (validity) tail.push(`صلاحية العرض ${cint(validity)} يومًا`);
		const advance = doc.advance_percent || settings.default_advance_percent;
		if (flt(advance)) tail.push(`دفعة مقدمة ${g(advance)}%`);
		if (tail.length) { lines.push(""); lines.push(tail.join(" · ")); }
		return lines.join("\n");
	}

	return { compute, imposition, componentCost, spineMm, parseTiers, parseMarginTiers, marginForQty, summaryText, SIZE_PRESETS, PRICING_FIXED, PRICING_BY_QTY, SINGLE, COVER, INNER, INSERT, flt, cint, r3 };
});
