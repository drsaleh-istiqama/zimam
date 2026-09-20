// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Membership Application", {
	refresh(frm) {
		if (frm.is_new() || ["مقبول", "مرفوض"].includes(frm.doc.status)) {
			if (frm.doc.member) frm.add_custom_button(__("العضو"), () => frappe.set_route("Form", "Member", frm.doc.member), __("عرض"));
			return;
		}
		frm.add_custom_button(__("قبول وإنشاء عضو"), () => {
			frm.call({ doc: frm.doc, method: "accept", freeze: true }).then((r) => { if (r.message) frappe.set_route("Form", "Member", r.message); });
		}).addClass("btn-primary");
		frm.add_custom_button(__("رفض"), () => {
			frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("ملاحظة") }, (v) => {
				frm.call({ doc: frm.doc, method: "reject", args: { note: v.note } }).then(() => frm.reload_doc());
			}, __("رفض الطلب"), __("رفض"));
		});
	},
});
