// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// صفحة «التسعير السريع للطباعة»: الكتالوج يُحمَّل مرة واحدة، والحساب يجري في المتصفح بالمحرّك نفسه
// (public/js/print_estimating.js — مطابق لـ zimam_core/print_estimating.py) عند كل تغيير بلا أي طلب للخادم،
// ثم بضغطة: إنشاء «تقدير وعرض سعر طباعة» بالبيانات نفسها (يعيد الخادم الحساب في validate)، أو نسخ الملخص، أو فتح واتساب.

frappe.provide("zimam");

frappe.pages["press-quick-quote"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("التسعير السريع للطباعة"), single_column: true });
	frappe.require("/assets/zimam/js/print_estimating.js", () => {
		wrapper.quick_quote = new zimam.PressQuickQuote(page, wrapper);
	});
};

zimam.PressQuickQuote = class PressQuickQuote {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		this.PE = window.PrintEstimating;
		this.state = { components: [], finishing: [], extras: [], template: null };
		this.last = null;
		this.page.set_secondary_action(__("تقديرات الطباعة"), () => frappe.set_route("List", "Print Estimate"));
		this.page.set_primary_action(__("إنشاء تقدير"), () => this.create_estimate(), "add");
		frappe.call({ method: "zimam.zimam_core.doctype.print_estimate.print_estimate.get_catalog", freeze: true }).then((r) => {
			this.catalog = r.message;
			this.masters = this.build_masters(this.catalog);
			this.settings = this.catalog.settings || {};
			this.render();
			const first = this.catalog.templates[0];
			if (first) this.apply_template(first);
		});
	}

	build_masters(cat) {
		const m = { paper: {}, machine: {}, finishing: {} };
		cat.papers.forEach((p) => (m.paper[p.name] = p));
		cat.machines.forEach((x) => (m.machine[x.name] = x));
		cat.finishing.forEach((f) => (m.finishing[f.name] = f));
		return m;
	}

	// ---------------------------------------------------------------- الواجهة
	render() {
		const $b = $(this.page.body);
		$b.html(`
<style>
.pqq{direction:rtl;text-align:start;font-variant-numeric:tabular-nums}
.pqq .pqq-chips{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 12px}
.pqq .pqq-chip{border:1px solid var(--border-color);background:var(--control-bg);border-radius:999px;padding:4px 12px;font-size:12px;cursor:pointer}
.pqq .pqq-chip.active{background:var(--primary);color:#fff;border-color:var(--primary)}
.pqq .pqq-group{font-size:11px;color:var(--text-muted);margin-inline-end:4px;align-self:center}
.pqq .pqq-grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;align-items:start}
@media (max-width:991px){.pqq .pqq-grid{grid-template-columns:1fr}}
.pqq .pqq-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:var(--border-radius-md);padding:12px 14px;margin-bottom:12px}
.pqq h6{font-weight:700;color:var(--primary);margin:0 0 8px}
.pqq table{width:100%;font-size:12px;border-collapse:collapse}
.pqq th,.pqq td{padding:4px 6px;border-bottom:1px solid var(--border-color);text-align:start;vertical-align:middle}
.pqq th{color:var(--text-muted);font-weight:500}
.pqq td.num,.pqq th.num{text-align:end;direction:ltr}
.pqq select,.pqq input.pqq-in{width:100%;font-size:12px;padding:3px 6px;border:1px solid var(--border-color);border-radius:6px;background:var(--control-bg);color:var(--text-color)}
.pqq input.pqq-in[type=number]{direction:ltr;text-align:end;width:70px}
.pqq .pqq-total{background:var(--primary);color:#fff;border-radius:var(--border-radius-md);padding:12px 14px;margin-bottom:12px}
.pqq .pqq-total .big{font-size:26px;font-weight:700;direction:ltr;text-align:start;unicode-bidi:isolate}
.pqq .pqq-total .row2{display:flex;justify-content:space-between;font-size:13px;margin-top:4px}
.pqq .kv{display:grid;grid-template-columns:1fr auto;gap:2px 10px;font-size:12.5px}
.pqq .kv .v{direction:ltr;text-align:end;unicode-bidi:isolate}
.pqq .kv .sum{font-weight:700;border-top:1px solid var(--border-color);padding-top:3px;margin-top:2px}
.pqq .pqq-warn{background:var(--bg-orange);color:var(--text-on-orange);border-radius:6px;padding:6px 10px;font-size:12px;margin-top:8px}
.pqq .pqq-actions{display:flex;flex-wrap:wrap;gap:6px}
.pqq tr.current td{background:var(--bg-light-gray);font-weight:700}
.pqq .pqq-sticky{position:sticky;top:70px}
.pqq .pqq-mini{color:var(--text-muted);font-size:11px}
.pqq .pqq-del{cursor:pointer;color:var(--text-muted);padding:0 6px}
</style>
<div class="pqq" dir="rtl" lang="ar">
  <div class="pqq-chips" data-role="chips"></div>
  <div class="pqq-grid">
    <div>
      <div class="pqq-card"><h6>${__("العميل والعمل")}</h6><div data-role="head"></div></div>
      <div class="pqq-card"><h6>${__("المواصفات")}</h6><div data-role="specs"></div></div>
      <div class="pqq-card"><h6>${__("المكوّنات — الورق والطباعة")}</h6>
        <table data-role="comps"><thead><tr><th>${__("المكوّن")}</th><th>${__("الورق")}</th><th>${__("الآلة")}</th><th>${__("الألوان")}</th><th>${__("الأوجه")}</th><th class="num">${__("قطع/فرخ")}</th><th class="num">${__("الأفرخ")}</th><th class="num">${__("التكلفة")}</th><th></th></tr></thead><tbody></tbody></table>
        <button class="btn btn-xs btn-default mt-2" data-role="add-comp">+ ${__("مكوّن")}</button></div>
      <div class="pqq-card"><h6>${__("التشطيب")}</h6>
        <table data-role="fins"><thead><tr><th>${__("الخدمة")}</th><th>${__("ينطبق على")}</th><th>${__("الأساس")}</th><th class="num">${__("لكل نسخة")}</th><th class="num">${__("الكمية")}</th><th class="num">${__("التكلفة")}</th><th></th></tr></thead><tbody></tbody></table>
        <button class="btn btn-xs btn-default mt-2" data-role="add-fin">+ ${__("تشطيب")}</button></div>
      <div class="pqq-card"><h6>${__("بنود إضافية")}</h6>
        <table data-role="extras"><thead><tr><th>${__("البيان")}</th><th class="num">${__("الكمية")}</th><th class="num">${__("السعر")}</th><th class="num">${__("المبلغ")}</th><th></th></tr></thead><tbody></tbody></table>
        <button class="btn btn-xs btn-default mt-2" data-role="add-extra">+ ${__("بند")}</button></div>
      <div class="pqq-card"><h6>${__("التسعير")}</h6><div data-role="pricing"></div></div>
    </div>
    <div class="pqq-sticky">
      <div class="pqq-total"><div class="pqq-mini" style="color:#fff;opacity:.85">${__("الإجمالي شامل الضريبة")}</div><div class="big" data-role="grand">0.000</div>
        <div class="row2"><span>${__("سعر الوحدة")}</span><b data-role="unit">0.000</b></div><div class="row2"><span>${__("قبل الضريبة")}</span><b data-role="net">0.000</b></div></div>
      <div class="pqq-card"><h6>${__("تفصيل التكلفة")}</h6><div class="kv" data-role="kv"></div><div class="pqq-warn" data-role="warns" hidden></div></div>
      <div class="pqq-card"><h6>${__("أسعار الكميات")}</h6><table data-role="tiers"><thead><tr><th class="num">${__("الكمية")}</th><th class="num">${__("للوحدة")}</th><th class="num">${__("قبل الضريبة")}</th><th class="num">${__("شامل الضريبة")}</th><th class="num">${__("الهامش")}</th></tr></thead><tbody></tbody></table></div>
      <div class="pqq-card"><h6>${__("الإنتاج")}</h6><div class="kv" data-role="prod"></div></div>
      <div class="pqq-actions">
        <button class="btn btn-primary btn-sm" data-role="create">${__("إنشاء تقدير")}</button>
        <button class="btn btn-default btn-sm" data-role="copy">${__("نسخ الملخص")}</button>
        <button class="btn btn-default btn-sm" data-role="wa">${__("واتساب")}</button>
      </div>
    </div>
  </div>
</div>`);
		this.$ = (role) => $b.find(`[data-role="${role}"]`);
		this.render_chips();
		this.make_fields();
		this.$("add-comp").on("click", () => { this.state.components.push({ component: this.head.get_value("structure") === this.PE.SINGLE ? this.PE.SINGLE : this.PE.INSERT, paper: this.catalog.papers[0]?.name, machine: this.catalog.machines[0]?.name, color: "ملون", sides: "وجهان", pages: 1, auto_size: 1 }); this.recalc(); });
		this.$("add-fin").on("click", () => { this.state.finishing.push({ finishing_service: this.catalog.finishing[0]?.name, applies_to: "الكل", qty_per_copy: 1, auto_qty: 1 }); this.recalc(); });
		this.$("add-extra").on("click", () => { this.state.extras.push({ component: "أخرى", description: "", qty: 1, rate: 0 }); this.recalc(); });
		this.$("create").on("click", () => this.create_estimate());
		this.$("copy").on("click", () => this.copy_summary());
		this.$("wa").on("click", () => this.whatsapp());
	}

	render_chips() {
		const $c = this.$("chips").empty();
		const groups = {};
		this.catalog.templates.forEach((t) => (groups[t.product_type] = groups[t.product_type] || []).push(t));
		Object.keys(groups).forEach((g) => {
			$c.append(`<span class="pqq-group">${frappe.utils.escape_html(g)}:</span>`);
			groups[g].forEach((t) => {
				const $chip = $(`<span class="pqq-chip" title="${frappe.utils.escape_html(t.description || "")}">${frappe.utils.escape_html(t.template_name)}</span>`);
				$chip.on("click", () => this.apply_template(t));
				$c.append($chip);
			});
		});
	}

	make_fields() {
		const change = () => this.recalc();
		const S = this.settings;
		this.head = new frappe.ui.FieldGroup({ body: this.$("head"), fields: [
			{ fieldname: "customer", fieldtype: "Link", label: __("العميل"), options: "Customer", onchange: () => this.on_customer() },
			{ fieldname: "prospect_name", fieldtype: "Data", label: __("اسم طالب العرض (إن لم يكن مسجلًا)") },
			{ fieldtype: "Column Break" },
			{ fieldname: "contact_phone", fieldtype: "Data", label: __("الهاتف (واتساب)"), options: "Phone" },
			{ fieldname: "title", fieldtype: "Data", label: __("عنوان العمل"), reqd: 1 },
			{ fieldtype: "Section Break" },
			{ fieldname: "quantity", fieldtype: "Int", label: __("الكمية"), default: 100, reqd: 1, onchange: () => this.on_qty() },
			{ fieldname: "size_preset", fieldtype: "Select", label: __("المقاس"), options: Object.keys(this.catalog.size_presets).concat(["مخصص"]).join("\n"), onchange: () => this.on_size() },
			{ fieldname: "finished_width_mm", fieldtype: "Float", label: __("العرض (مم)"), onchange: change },
			{ fieldname: "finished_height_mm", fieldtype: "Float", label: __("الطول (مم)"), onchange: change },
			{ fieldtype: "Column Break" },
			{ fieldname: "structure", fieldtype: "Select", label: __("البنية"), options: "قطعة واحدة\nغلاف + داخلي", default: "قطعة واحدة", onchange: () => this.on_structure() },
			{ fieldname: "pages", fieldtype: "Int", label: __("الصفحات الداخلية"), onchange: () => this.on_pages() },
			{ fieldname: "binding", fieldtype: "Select", label: __("التجليد"), options: "بلا\nتدبيس سلك\nغراء (تجليد حراري)\nخياطة وغراء\nسلك حلزوني\nغلاف صلب", default: "بلا", onchange: change },
			{ fieldname: "rush", fieldtype: "Check", label: __("عمل مستعجل"), onchange: change },
		] });
		this.head.make();
		// حقول المواصفات تظهر في بطاقة «المواصفات»: ننقل قسمها الثاني إليها
		const $sections = this.$("head").find(".form-section");
		if ($sections.length > 1) this.$("specs").append($sections.slice(1));
		this.pricing = new frappe.ui.FieldGroup({ body: this.$("pricing"), fields: [
			{ fieldname: "pricing_mode", fieldtype: "Select", label: __("طريقة التسعير"), options: "هامش ثابت\nهامش بحسب الكمية", default: S.default_pricing_mode || "هامش ثابت", onchange: change },
			{ fieldname: "margin_percent", fieldtype: "Percent", label: __("هامش الربح %"), default: S.default_margin_percent, onchange: change },
			{ fieldname: "margin_tiers", fieldtype: "Data", label: __("شرائح الهامش (من الكمية : الهامش %)"), default: S.margin_tiers, onchange: change, description: __("تُطبَّق عند اختيار «هامش بحسب الكمية»") },
			{ fieldtype: "Column Break" },
			{ fieldname: "discount_percent", fieldtype: "Percent", label: __("خصم %"), onchange: change },
			{ fieldname: "rush_percent", fieldtype: "Percent", label: __("نسبة الاستعجال %"), default: S.default_rush_percent, onchange: change },
			{ fieldname: "design_hours", fieldtype: "Float", label: __("ساعات التصميم"), onchange: change },
			{ fieldtype: "Column Break" },
			{ fieldname: "tax_rate", fieldtype: "Percent", label: __("الضريبة %"), default: S.default_tax_rate, onchange: change },
			{ fieldname: "round_to", fieldtype: "Select", label: __("تقريب إلى"), options: "\n0.100\n0.500\n1.000", default: S.default_round_to || "", onchange: change },
			{ fieldname: "tiers", fieldtype: "Data", label: __("شرائح الكمية للعميل"), default: S.default_tiers, onchange: change },
		] });
		this.pricing.make();
	}

	// ---------------------------------------------------------------- الأحداث
	on_customer() {
		const c = this.head.get_value("customer");
		if (!c) return;
		frappe.db.get_value("Customer", c, ["mobile_no", "customer_name"]).then((r) => {
			const v = r.message || {};
			if (v.mobile_no && !this.head.get_value("contact_phone")) this.head.set_value("contact_phone", v.mobile_no);
		});
	}
	on_qty() {
		const q = cint(this.head.get_value("quantity"));
		const tiers = this.PE.parseTiers(this.pricing.get_value("tiers"));
		if (q && !tiers.includes(q)) { tiers.push(q); tiers.sort((a, b) => a - b); this.pricing.set_value("tiers", tiers.join(", ")); }
		this.recalc();
	}
	on_size() {
		const p = this.catalog.size_presets[this.head.get_value("size_preset")];
		if (p) { this.head.set_value("finished_width_mm", p[0]); this.head.set_value("finished_height_mm", p[1]); }
		this.recalc();
	}
	on_structure() {
		if (this.head.get_value("structure") === this.PE.SINGLE) this.state.components.forEach((c) => { if (c.component === this.PE.COVER) c.component = this.PE.SINGLE; });
		this.recalc();
	}
	on_pages() {
		const p = this.head.get_value("pages");
		this.state.components.forEach((c) => { if (c.component === this.PE.INNER) c.pages = p; });
		this.recalc();
	}

	apply_template(t) {
		this.state.template = t;
		const h = this.head, P = this.pricing;
		h.set_value("title", t.template_name);
		h.set_value("structure", t.structure);
		h.set_value("size_preset", t.size_preset || "مخصص");
		h.set_value("finished_width_mm", t.finished_width_mm || (this.catalog.size_presets[t.size_preset] || [0, 0])[0]);
		h.set_value("finished_height_mm", t.finished_height_mm || (this.catalog.size_presets[t.size_preset] || [0, 0])[1]);
		h.set_value("pages", t.default_pages || 0);
		h.set_value("binding", t.binding || "بلا");
		P.set_value("margin_percent", t.margin_percent || this.settings.default_margin_percent);
		P.set_value("design_hours", t.design_hours || 0);
		P.set_value("tiers", t.tiers || this.settings.default_tiers);
		const tiers = this.PE.parseTiers(P.get_value("tiers"));
		h.set_value("quantity", tiers[0] || 100);
		this.state.components = [];
		if (t.structure === this.PE.SINGLE) this.state.components.push({ component: this.PE.SINGLE, paper: t.cover_paper, machine: t.cover_machine, color: t.cover_color, sides: t.cover_sides, auto_size: 1 });
		else {
			this.state.components.push({ component: this.PE.COVER, paper: t.cover_paper, machine: t.cover_machine, color: t.cover_color, sides: t.cover_sides, auto_size: 1 });
			this.state.components.push({ component: this.PE.INNER, paper: t.inner_paper, machine: t.inner_machine, color: t.inner_color, sides: t.inner_sides, pages: t.default_pages, auto_size: 1 });
		}
		this.state.finishing = (t.finishing || []).map((f) => ({ finishing_service: f.finishing_service, applies_to: f.applies_to || "الكل", qty_per_copy: f.qty_per_copy || 1, auto_qty: 1 }));
		this.state.extras = [];
		this.$("chips").find(".pqq-chip").removeClass("active").filter((i, el) => $(el).text() === t.template_name).addClass("active");
		this.recalc();
	}

	// ---------------------------------------------------------------- الحساب والعرض
	read_doc() {
		const h = this.head.get_values(true) || {}, p = this.pricing.get_values(true) || {};
		return Object.assign({}, h, p, {
			components: this.state.components, finishing: this.state.finishing, extras: this.state.extras,
			tiers: this.PE.parseTiers(p.tiers).map((q) => ({ qty: q })),
			template: this.state.template ? this.state.template.name : null,
			product_type: this.state.template ? this.state.template.product_type : "أخرى",
			validity_days: this.settings.default_validity_days, advance_percent: this.settings.default_advance_percent,
		});
	}
	recalc() {
		if (!this.catalog) return;
		const doc = this.read_doc();
		this.last = this.PE.compute(doc, this.masters, this.settings);
		this.render_rows(this.last);
		this.render_result(this.last, doc);
	}
	sel(options, value, on) {
		const $s = $("<select>");
		options.forEach((o) => $s.append($("<option>").val(o).text(o)));
		$s.val(value).on("change", () => on($s.val()));
		return $s;
	}
	num(value, on, step) {
		const $i = $(`<input class="pqq-in" type="number" min="0" step="${step || 1}">`).val(value === undefined || value === null ? "" : value);
		$i.on("input", () => on($i.val()));
		return $i;
	}
	fmt(v) { return (Math.round((v || 0) * 1000) / 1000).toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 3 }); }
	render_rows(res) {
		const papers = this.catalog.papers.map((p) => p.name), machines = this.catalog.machines.map((m) => m.name), fins = this.catalog.finishing.map((f) => f.name);
		const $tc = this.$("comps").find("tbody").empty();
		this.state.components.forEach((c, i) => {
			const r = res.components[i] || {};
			const $tr = $("<tr>");
			$tr.append($("<td>").append(this.sel(["قطعة واحدة", "غلاف", "داخلي", "إدراج/ملحق"], c.component, (v) => { c.component = v; this.recalc(); })));
			$tr.append($("<td>").append(this.sel(papers, c.paper, (v) => { c.paper = v; this.recalc(); })));
			$tr.append($("<td>").append(this.sel(machines, c.machine, (v) => { c.machine = v; this.recalc(); })));
			$tr.append($("<td>").append(this.sel(["ملون", "أحادي"], c.color, (v) => { c.color = v; this.recalc(); })));
			$tr.append($("<td>").append(this.sel(["وجه", "وجهان"], c.sides, (v) => { c.sides = v; this.recalc(); })));
			$tr.append(`<td class="num">${r.ups || 0}</td><td class="num">${r.sheets || 0}</td><td class="num">${this.fmt(r.amount)}</td>`);
			$tr.append($(`<td><span class="pqq-del" title="${__("حذف")}">×</span></td>`).on("click", () => { this.state.components.splice(i, 1); this.recalc(); }));
			$tc.append($tr);
			if (r.warning) $tc.append(`<tr><td colspan="9" class="pqq-warn">⚠ ${frappe.utils.escape_html(r.warning)}</td></tr>`);
		});
		const $tf = this.$("fins").find("tbody").empty();
		this.state.finishing.forEach((f, i) => {
			const r = res.finishing[i] || {};
			const $tr = $("<tr>");
			$tr.append($("<td>").append(this.sel(fins, f.finishing_service, (v) => { f.finishing_service = v; this.recalc(); })));
			$tr.append($("<td>").append(this.sel(["الكل", "الغلاف", "الداخلي"], f.applies_to || "الكل", (v) => { f.applies_to = v; this.recalc(); })));
			$tr.append(`<td>${frappe.utils.escape_html(r.basis || "")}${r.outsourced ? ` <span class="pqq-mini">(${__("خارجي")})</span>` : ""}</td>`);
			$tr.append($("<td class='num'>").append(this.num(f.qty_per_copy || 1, (v) => { f.qty_per_copy = v; this.recalc(); }, 0.5)));
			$tr.append(`<td class="num">${r.qty === undefined ? "" : Number(r.qty).toLocaleString("en-US", { maximumFractionDigits: 2 })}</td><td class="num">${this.fmt(r.amount)}</td>`);
			$tr.append($(`<td><span class="pqq-del" title="${__("حذف")}">×</span></td>`).on("click", () => { this.state.finishing.splice(i, 1); this.recalc(); }));
			$tf.append($tr);
		});
		const $te = this.$("extras").find("tbody").empty();
		this.state.extras.forEach((e, i) => {
			const r = res.extras[i] || {};
			const $tr = $("<tr>");
			const $d = $(`<input class="pqq-in" type="text" placeholder="${__("مثال: تغليف هدايا")}">`).val(e.description || "").on("input", () => (e.description = $d.val()));
			$tr.append($("<td>").append($d));
			$tr.append($("<td class='num'>").append(this.num(e.qty, (v) => { e.qty = v; this.recalc(); })));
			$tr.append($("<td class='num'>").append(this.num(e.rate, (v) => { e.rate = v; this.recalc(); }, 0.1)));
			$tr.append(`<td class="num">${this.fmt(r.amount)}</td>`);
			$tr.append($(`<td><span class="pqq-del" title="${__("حذف")}">×</span></td>`).on("click", () => { this.state.extras.splice(i, 1); this.recalc(); }));
			$te.append($tr);
		});
	}
	render_result(res, doc) {
		this.$("grand").text(this.fmt(res.grand_total)); this.$("unit").text(this.fmt(res.unit_price)); this.$("net").text(this.fmt(res.net_total));
		const kv = [[__("الورق"), res.paper_cost], [__("الطباعة"), res.print_cost], [__("التشطيب"), res.finishing_cost], [__("إضافي وتصميم"), res.extras_cost],
			[__("إجمالي التكلفة"), res.total_cost, "sum"], [__("تكلفة الوحدة"), res.unit_cost], [__("هامش الربح {0}%", [res.margin_applied]), res.net_total - res.total_cost + res.discount_amount - res.rush_amount]];
		if (res.rush_amount) kv.push([__("الاستعجال"), res.rush_amount]);
		if (res.discount_amount) kv.push([__("الخصم"), -res.discount_amount]);
		kv.push([__("السعر قبل الضريبة"), res.net_total, "sum"], [__("الضريبة {0}%", [res.tax_rate]), res.tax_amount], [__("الإجمالي"), res.grand_total, "sum"]);
		this.$("kv").html(kv.map((k) => `<span class="${k[2] || ""}">${k[0]}</span><span class="v ${k[2] || ""}">${this.fmt(k[1])}</span>`).join(""));
		const q = cint(doc.quantity);
		this.$("tiers").find("tbody").html(res.tiers.map((t) => `<tr class="${t.qty === q ? "current" : ""}"><td class="num">${t.qty}</td><td class="num">${this.fmt(t.unit_price)}</td><td class="num">${this.fmt(t.price)}</td><td class="num">${this.fmt(t.grand_total)}</td><td class="num">${t.margin_applied}%</td></tr>`).join(""));
		const prod = [[__("إجمالي الأفرخ"), res.total_sheets], [__("المرورات/النقرات"), res.total_impressions], [__("ساعات الإنتاج"), res.production_hours], [__("أيام التنفيذ المتوقعة"), res.estimated_days]];
		if (res.lead_days) prod.push([__("منها مهلة خدمات خارجية"), res.lead_days]);
		if (res.spine_mm) prod.push([__("كعب الكتاب (مم)"), res.spine_mm]);
		this.$("prod").html(prod.map((k) => `<span>${k[0]}</span><span class="v">${k[1]}</span>`).join(""));
		const warns = res.components.filter((c) => c.warning).map((c) => "⚠ " + c.warning);
		this.$("warns").prop("hidden", !warns.length).text(warns.join(" · "));
	}

	// ---------------------------------------------------------------- الإجراءات
	summary() {
		const doc = this.read_doc();
		return this.PE.summaryText(doc, this.last, this.settings, this.catalog.company_name || "");
	}
	message() {
		const doc = this.read_doc();
		const tpl = this.settings.whatsapp_template || "{summary}";
		const values = { customer: doc.prospect_name || doc.customer || "", company: this.catalog.company_name || "", summary: this.summary(), title: doc.title || "", grand_total: this.fmt(this.last.grand_total), name: "" };
		return tpl.replace(/\{(customer|company|summary|title|grand_total|name)\}/g, (m, k) => values[k]);
	}
	copy_summary() {
		if (!this.last) return;
		const text = this.summary();
		const done = () => frappe.show_alert({ message: __("نُسخ ملخص عرض السعر"), indicator: "green" });
		if (navigator.clipboard) navigator.clipboard.writeText(text).then(done).catch(() => frappe.msgprint({ title: __("انسخ النص"), message: `<pre style="white-space:pre-wrap;direction:rtl">${frappe.utils.escape_html(text)}</pre>` }));
		else frappe.msgprint({ title: __("انسخ النص"), message: `<pre style="white-space:pre-wrap;direction:rtl">${frappe.utils.escape_html(text)}</pre>` });
	}
	whatsapp() {
		if (!this.last) return;
		let phone = String(this.head.get_value("contact_phone") || "").replace(/\D/g, "");
		if (phone.startsWith("00")) phone = phone.slice(2);
		if (phone.length === 8) phone = "968" + phone;
		window.open(`https://wa.me/${phone}?text=${encodeURIComponent(this.message())}`, "_blank");
	}
	create_estimate() {
		if (!this.last) return;
		const doc = this.read_doc();
		if (!doc.customer && !doc.prospect_name) { frappe.msgprint(__("حدد العميل أو اكتب اسم طالب العرض")); return; }
		if (!doc.title) { frappe.msgprint(__("اكتب عنوان العمل")); return; }
		if (!this.state.components.length) { frappe.msgprint(__("أضف مكوّنًا واحدًا على الأقل")); return; }
		frappe.call({ method: "zimam.zimam_core.doctype.print_estimate.print_estimate.create_from_quick", args: { data: doc }, freeze: true, freeze_message: __("إنشاء التقدير…") })
			.then((r) => { if (r.message) frappe.set_route("Form", "Print Estimate", r.message); });
	}
};
