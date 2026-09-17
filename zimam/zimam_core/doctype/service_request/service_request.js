// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Service Request", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.sales_invoice && !frm.doc.is_free && flt(frm.doc.fees) > 0) {
			frm.add_custom_button(__("فاتورة"), () => {
				frm.call({ doc: frm.doc, method: "make_invoice" }).then((r) => {
					if (r.message) frappe.set_route("Form", "Sales Invoice", r.message);
				});
			}, __("إنشاء"));
		}
	},
	service_type(frm) {
		if (!frm.doc.service_type) return;
		frappe.db.get_value("Service Type", frm.doc.service_type, ["is_free", "default_fees"]).then((r) => {
			const m = r.message || {};
			frm.set_value("is_free", cint(m.is_free));
			if (!cint(m.is_free)) frm.set_value("fees", flt(m.default_fees));
		});
	},
});
