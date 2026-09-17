// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Waqf Contribution", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.certificate_issued) {
			frm.add_custom_button(__("طباعة الشهادة الوقفية"), () => {
				frappe.set_route("print", frm.doc.doctype, frm.doc.name);
			});
		}
	},
	share_type(frm) { calc(frm); },
	shares(frm) { calc(frm); },
});

function calc(frm) {
	if (!frm.doc.share_type) return;
	frappe.db.get_value("Waqf Share Type", frm.doc.share_type, "amount").then((r) => {
		const amt = flt(r.message && r.message.amount);
		frm.set_value("share_amount", amt);
		frm.set_value("amount", amt * (cint(frm.doc.shares) || 1));
	});
}
