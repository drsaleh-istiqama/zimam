// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Print Job", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			if (!frm.doc.quotation) {
				frm.add_custom_button(__("عرض سعر"), () => {
					frm.call({ doc: frm.doc, method: "make_quotation" }).then((r) => {
						if (r.message) frappe.set_route("Form", "Quotation", r.message);
					});
				}, __("إنشاء"));
			}
			if (!frm.doc.sales_invoice) {
				frm.add_custom_button(__("فاتورة مبيعات"), () => {
					frm.call({ doc: frm.doc, method: "make_sales_invoice" }).then((r) => {
						if (r.message) frappe.set_route("Form", "Sales Invoice", r.message);
					});
				}, __("إنشاء"));
			}
		}
	},
	margin_percent(frm) {
		frm.set_value("quoted_price", 0);
	},
});

frappe.ui.form.on("Print Cost Item", {
	qty(frm, cdt, cdn) { recalc(frm, cdt, cdn); },
	rate(frm, cdt, cdn) { recalc(frm, cdt, cdn); },
	cost_items_remove(frm) { frm.set_value("quoted_price", 0); },
});

function recalc(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
	frm.set_value("quoted_price", 0);
}
