// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Sponsorship", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("تسجيل سداد"), () => {
			frappe.new_doc("Donation", { donor: frm.doc.sponsor, sponsorship: frm.doc.name, amount: frm.doc.due_unpaid || frm.doc.amount,
				donation_category: frm.doc.donation_category, project: frm.doc.project, purpose: __("سداد كفالة {0}", [frm.doc.beneficiary_name]) });
		}).addClass("btn-primary");
		frm.add_custom_button(__("الاستحقاقات"), () => frappe.set_route("List", "Sponsorship Due", { sponsorship: frm.doc.name }), __("عرض"));
		if (frappe.user.has_role(["System Manager", "محاسب مالي", "مدير مالي"])) {
			frm.add_custom_button(__("توليد الاستحقاقات المستحقة الآن"), () => {
				frappe.xcall("zimam.zimam_charity.doctype.sponsorship.sponsorship.generate_dues_now").then(() => frm.reload_doc());
			}, __("إجراء"));
		}
	},
});
