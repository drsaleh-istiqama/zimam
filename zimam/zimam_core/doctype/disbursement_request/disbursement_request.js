// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Disbursement Request", {
	refresh(frm) {
		if (frm.is_new()) return;
		const can_review = frappe.user.has_role(["محاسب مالي", "مدير مالي", "System Manager"]);
		if (frm.doc.status === "للمراجعة" && can_review) {
			frm.add_custom_button(__("تحويل إلى سند صرف"), () => {
				const d = new frappe.ui.Dialog({
					title: __("ترميز الطلب وتحويله إلى سند صرف"),
					fields: [
						{ fieldname: "expense_classification", fieldtype: "Link", options: "Expense Classification", label: __("تصنيف المصروف"), reqd: 1 },
						{ fieldname: "fund", fieldtype: "Link", options: "Treasury Fund", label: __("حساب الصرف / الصندوق"), reqd: 1 },
						{ fieldname: "payment_method", fieldtype: "Select", options: "نقد\nتحويل بنكي\nشيك\nبطاقة\nبوابة إلكترونية", label: __("طريقة الدفع"), default: "تحويل بنكي", reqd: 1 },
					],
					primary_action_label: __("إنشاء السند"),
					primary_action(v) {
						d.hide();
						frm.call({ doc: frm.doc, method: "make_voucher", args: v, freeze: true }).then((r) => {
							if (r.message) frappe.set_route("Form", "Payment Voucher", r.message);
						});
					},
				});
				d.show();
			}).addClass("btn-primary");
			frm.add_custom_button(__("إعادة إلى مقدم الطلب"), () => {
				frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("ملاحظة الإعادة"), reqd: 1 }, (v) => {
					frm.call({ doc: frm.doc, method: "return_to_requester", args: { note: v.note } }).then(() => frm.reload_doc());
				}, __("إعادة الطلب"), __("إعادة"));
			});
			frm.add_custom_button(__("رفض"), () => {
				frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("سبب الرفض"), reqd: 1 }, (v) => {
					frm.call({ doc: frm.doc, method: "reject", args: { note: v.note } }).then(() => frm.reload_doc());
				}, __("رفض الطلب"), __("رفض"));
			});
		}
		if (frm.doc.status === "مُعادة" && (frm.doc.requester_user === frappe.session.user || can_review)) {
			frm.add_custom_button(__("إعادة التقديم بعد التعديل"), () => {
				frm.call({ doc: frm.doc, method: "resubmit" }).then(() => frm.reload_doc());
			}).addClass("btn-primary");
		}
		if (frm.doc.payment_voucher) {
			frm.add_custom_button(__("سند الصرف"), () => frappe.set_route("Form", "Payment Voucher", frm.doc.payment_voucher), __("عرض"));
		}
	},
});
