// زِمام — طباعة فاتورة المبيعات بالنموذج العربي (0.14.0)
frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus === 2) return;
		if (frm.doc.docstatus === 1 && !frm.doc.is_return && flt(frm.doc.outstanding_amount) > 0) {
			frm.add_custom_button(__("تسجيل متابعة تحصيل"), () => frappe.new_doc("Collection Followup", { sales_invoice: frm.doc.name }), __("زِمام"));
		}
		frm.add_custom_button(__("طباعة الفاتورة (زِمام)"), () => {
			const q = $.param({ doctype: "Sales Invoice", name: frm.doc.name, format: "Sales Invoice Form", no_letterhead: 0, _lang: "ar" });
			window.open(frappe.urllib.get_full_url("/printview?" + q));
		}, __("زِمام"));
	},
});
