// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام (الحزمة التراثية)
// For license information, please see license.txt

frappe.ui.form.on("Restoration Assessment", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			if (!frm.doc.quotation && frm.doc.billing_type !== "بلا فوترة") {
				frm.add_custom_button(__("إنشاء عرض سعر"), () => {
					frappe.call({
						method: "zimam.zimam_heritage.doctype.restoration_assessment.restoration_assessment.make_quotation",
						args: { name: frm.doc.name },
						freeze: true,
						callback: (r) => {
							if (r.message) {
								frm.reload_doc();
								frappe.set_route("Form", "Quotation", r.message);
							}
						},
					});
				}, __("إنشاء"));
			}
			if (!frm.doc.jobs_created) {
				frm.add_custom_button(__("إنشاء طلبات الترميم"), () => {
					frappe.confirm(__("إنشاء طلب ترميم (مسودة) لكل وعاء في التقييم؟"), () => {
						frappe.call({
							method: "zimam.zimam_heritage.doctype.restoration_assessment.restoration_assessment.make_restoration_jobs",
							args: { name: frm.doc.name },
							freeze: true,
							callback: (r) => {
								frm.reload_doc();
								frappe.msgprint(__("أُنشئ {0} طلب ترميم", [(r.message || []).length]));
							},
						});
					});
				}, __("إنشاء"));
			}
			frm.add_custom_button(__("طباعة عرض الأسعار"), () => {
				frappe.set_route("print", frm.doc.doctype, frm.doc.name);
			});
		}
		if (frm.doc.quotation) {
			frm.add_custom_button(__("عرض السعر {0}", [frm.doc.quotation]), () => {
				frappe.set_route("Form", "Quotation", frm.doc.quotation);
			}, __("عرض"));
		}
	},
	tax_rate(frm) { recompute(frm); },
	round_tax(frm) { recompute(frm); },
});

frappe.ui.form.on("Restoration Assessment Item", {
	service_item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.service_item) return;
		frappe.call({
			method: "zimam.zimam_heritage.doctype.restoration_assessment.restoration_assessment.get_rate",
			args: { item: row.service_item, price_list: frm.doc.price_list },
			callback: (r) => {
				frappe.model.set_value(cdt, cdn, "rate", flt(r.message));
				if (!row.qty && row.pages) frappe.model.set_value(cdt, cdn, "qty", row.pages);
			},
		});
	},
	pages(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.pages && (!row.qty || row.qty === 1)) frappe.model.set_value(cdt, cdn, "qty", row.pages);
	},
	qty(frm, cdt, cdn) { row_amount(frm, cdt, cdn); },
	rate(frm, cdt, cdn) { row_amount(frm, cdt, cdn); },
	items_remove(frm) { recompute(frm); },
});

function row_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
	recompute(frm);
}

function recompute(frm) {
	let net = 0, pages = 0;
	const objects = new Set();
	(frm.doc.items || []).forEach((r) => {
		net += flt(r.qty) * flt(r.rate);
		pages += cint(r.pages);
		objects.add(r.object_code || r.cabinet_item || r.title || r.name);
	});
	const tax = net * flt(frm.doc.tax_rate) / 100;
	frm.set_value("net_total", net);
	frm.set_value("total_pages", pages);
	frm.set_value("total_objects", objects.size);
	frm.set_value("tax_amount", frm.doc.round_tax ? Math.round(tax) : Math.round(tax * 1000) / 1000);
	frm.set_value("grand_total", net + flt(frm.doc.tax_amount));
}
