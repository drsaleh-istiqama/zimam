// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Member", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (flt(frm.doc.annual_fee) > 0) {
			frm.add_custom_button(__("تسجيل اشتراك"), () => {
				frm.call({ doc: frm.doc, method: "make_fee_donation" }).then((r) => { if (r.message) frappe.set_route("Form", "Donation", r.message); });
			}).addClass("btn-primary");
		}
		if (frm.doc.donor) frm.add_custom_button(__("بطاقة المتبرع"), () => frappe.set_route("Form", "Donor", frm.doc.donor), __("عرض"));
	},
});
