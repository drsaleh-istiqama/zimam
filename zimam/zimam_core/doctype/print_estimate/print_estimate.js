// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt
// تقدير وعرض سعر طباعة: حساب فوري على الخادم (محرّك واحد) عند كل تغيير، بلا حفظ.

const PE = "zimam.zimam_core.doctype.print_estimate.print_estimate";
let pe_timer = null;

function pe_recalc(frm, immediate) {
	if (frm.doc.docstatus !== 0) return;
	clearTimeout(pe_timer);
	const run = () => {
		if (!(frm.doc.components || []).length) return;
		frm.call({ doc: frm.doc, method: "recalculate" }).then(() => {
			frm.refresh_fields();
			frm.dirty();
			pe_show_summary(frm);
		});
	};
	if (immediate) run(); else pe_timer = setTimeout(run, 400);
}

function pe_show_summary(frm) {
	const d = frm.doc;
	if (!d.total_cost && !d.net_total) { frm.dashboard.clear_headline(); return; }
	const cur = (v) => format_currency(v, frappe.get_doc("Company", d.company)?.default_currency || frappe.boot.sysdefaults.currency);
	const warnings = (d.components || []).filter((c) => c.warning).map((c) => `⚠ ${c.component}: ${c.warning}`);
	let html = `<b>${__("التكلفة")}</b> ${cur(d.total_cost)} · <b>${__("السعر قبل الضريبة")}</b> ${cur(d.net_total)} · <b>${__("للوحدة")}</b> ${cur(d.unit_price)} · <b>${__("شامل الضريبة")}</b> ${cur(d.grand_total)}`;
	if (d.total_sheets) html += ` · ${__("الأفرخ")}: ${d.total_sheets} · ${__("الساعات")}: ${d.production_hours}`;
	if (warnings.length) html += `<br><span class="text-danger">${warnings.join(" · ")}</span>`;
	frm.dashboard.set_headline(html);
}

frappe.ui.form.on("Print Estimate", {
	setup(frm) {
		frm.set_query("paper", "components", () => ({ filters: { is_active: 1 } }));
		frm.set_query("machine", "components", () => ({ filters: { is_active: 1 } }));
		frm.set_query("finishing_service", "finishing", () => ({ filters: { is_active: 1 } }));
		frm.set_query("template", () => ({ filters: { is_active: 1 } }));
	},
	onload(frm) {
		if (frm.is_new()) {
			frappe.call({ method: PE + ".get_defaults" }).then((r) => {
				const d = r.message || {};
				["margin_percent", "tax_rate", "validity_days", "advance_percent", "rush_percent", "design_rate", "round_to", "waste_percent", "bleed_mm"].forEach((f) => {
					if (!frm.doc[f] && d[f] !== undefined && d[f] !== null) frm.set_value(f, d[f]);
				});
				if (!(frm.doc.tiers || []).length && d.tiers) {
					d.tiers.forEach((q) => frm.add_child("tiers", { qty: q }));
					frm.refresh_field("tiers");
				}
			});
		}
	},
	refresh(frm) {
		pe_show_summary(frm);
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("تطبيق القالب"), () => {
				if (!frm.doc.template) { frappe.msgprint(__("اختر قالب المنتج أولًا")); return; }
				frm.call({ doc: frm.doc, method: "apply_template", freeze: true }).then(() => {
					frm.refresh();
					frm.dirty();
					pe_show_summary(frm);
				});
			});
			frm.add_custom_button(__("احسب الآن"), () => pe_recalc(frm, true));
		}
		if (frm.doc.docstatus === 1) {
			if (!frm.doc.quotation) {
				frm.add_custom_button(__("عرض سعر"), () => {
					frappe.call({ method: PE + ".make_quotation", args: { name: frm.doc.name }, freeze: true, callback: (r) => {
						if (r.message) { frm.reload_doc(); frappe.set_route("Form", "Quotation", r.message); }
					} });
				}, __("إنشاء"));
			}
			if (!frm.doc.print_job) {
				frm.add_custom_button(__("أمر طباعة"), () => {
					frappe.call({ method: PE + ".make_print_job", args: { name: frm.doc.name }, freeze: true, callback: (r) => {
						if (r.message) { frm.reload_doc(); frappe.set_route("Form", "Print Job", r.message); }
					} });
				}, __("إنشاء"));
			}
			frm.add_custom_button(__("طباعة عرض الأسعار"), () => frappe.set_route("print", frm.doc.doctype, frm.doc.name));
		}
		if (frm.doc.quotation) {
			frm.add_custom_button(__("عرض السعر {0}", [frm.doc.quotation]), () => frappe.set_route("Form", "Quotation", frm.doc.quotation), __("عرض"));
		}
		if (frm.doc.print_job) {
			frm.add_custom_button(__("أمر الطباعة {0}", [frm.doc.print_job]), () => frappe.set_route("Form", "Print Job", frm.doc.print_job), __("عرض"));
		}
	},
	template(frm) {
		if (frm.doc.template && frm.is_new() && !(frm.doc.components || []).length) {
			frm.call({ doc: frm.doc, method: "apply_template" }).then(() => { frm.refresh(); frm.dirty(); pe_show_summary(frm); });
		}
	},
	size_preset(frm) {
		frappe.call({ method: PE + ".get_defaults" }).then((r) => {
			const presets = (r.message || {}).size_presets || {};
			const p = presets[frm.doc.size_preset];
			if (p) {
				frm.set_value("finished_width_mm", p[0]);
				frm.set_value("finished_height_mm", p[1]);
			}
		});
	},
	structure(frm) {
		if (frm.doc.structure === "قطعة واحدة") {
			(frm.doc.components || []).forEach((c) => { if (c.component === "غلاف") frappe.model.set_value(c.doctype, c.name, "component", "قطعة واحدة"); });
		}
		pe_recalc(frm);
	},
	quantity(frm) {
		const q = cint(frm.doc.quantity);
		if (q && !(frm.doc.tiers || []).some((t) => cint(t.qty) === q)) {
			frm.add_child("tiers", { qty: q });
			frm.doc.tiers.sort((a, b) => cint(a.qty) - cint(b.qty));
			frm.doc.tiers.forEach((t, i) => (t.idx = i + 1));
			frm.refresh_field("tiers");
		}
		pe_recalc(frm);
	},
	finished_width_mm(frm) { pe_recalc(frm); },
	finished_height_mm(frm) { pe_recalc(frm); },
	bleed_mm(frm) { pe_recalc(frm); },
	waste_percent(frm) { pe_recalc(frm); },
	pages(frm) {
		(frm.doc.components || []).forEach((c) => { if (c.component === "داخلي") c.pages = frm.doc.pages; });
		frm.refresh_field("components");
		pe_recalc(frm);
	},
	binding(frm) { pe_recalc(frm); },
	rush(frm) { pe_recalc(frm); },
	rush_percent(frm) { pe_recalc(frm); },
	margin_percent(frm) { pe_recalc(frm); },
	discount_percent(frm) { pe_recalc(frm); },
	round_to(frm) { pe_recalc(frm); },
	tax_rate(frm) { pe_recalc(frm); },
	design_hours(frm) { pe_recalc(frm); },
	design_rate(frm) { pe_recalc(frm); },
});

frappe.ui.form.on("Print Estimate Component", {
	component(frm) { pe_recalc(frm); },
	paper(frm) { pe_recalc(frm); },
	machine(frm) { pe_recalc(frm); },
	color(frm) { pe_recalc(frm); },
	sides(frm) { pe_recalc(frm); },
	pages(frm) { pe_recalc(frm); },
	auto_size(frm) { pe_recalc(frm); },
	piece_width_mm(frm) { pe_recalc(frm); },
	piece_height_mm(frm) { pe_recalc(frm); },
	components_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.component) row.component = frm.doc.structure === "غلاف + داخلي" ? "داخلي" : "قطعة واحدة";
		row.auto_size = 1;
		frm.refresh_field("components");
	},
	components_remove(frm) { pe_recalc(frm); },
});

frappe.ui.form.on("Print Estimate Finishing", {
	finishing_service(frm) { pe_recalc(frm); },
	applies_to(frm) { pe_recalc(frm); },
	auto_qty(frm) { pe_recalc(frm); },
	qty_per_copy(frm) { pe_recalc(frm); },
	qty(frm) { pe_recalc(frm); },
	rate(frm) { pe_recalc(frm); },
	setup_cost(frm) { pe_recalc(frm); },
	finishing_remove(frm) { pe_recalc(frm); },
});

frappe.ui.form.on("Print Cost Item", {
	qty(frm) { pe_recalc(frm); },
	rate(frm) { pe_recalc(frm); },
	extras_remove(frm) { pe_recalc(frm); },
});

frappe.ui.form.on("Print Estimate Tier", {
	qty(frm) { pe_recalc(frm); },
	tiers_remove(frm) { pe_recalc(frm); },
});
