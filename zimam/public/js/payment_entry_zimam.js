// زِمام — سند القبض فوق «قيد دفع» (0.14.0): اختيار الصندوق يملأ حساب الاستلام، وزر طباعة السند
frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		if (frm.doc.payment_type !== "Receive") return;
		frm.set_df_property("zimam_fund", "hidden", 0);
		if (!frm.is_new() && frm.doc.docstatus < 2) {
			frm.add_custom_button(__("طباعة سند القبض"), () => {
				const q = $.param({ doctype: "Payment Entry", name: frm.doc.name, format: "Receipt Voucher Form", no_letterhead: 0, _lang: "ar" });
				window.open(frappe.urllib.get_full_url("/printview?" + q));
			}, __("زِمام"));
		}
	},
	zimam_fund(frm) {
		if (frm.doc.payment_type !== "Receive" || !frm.doc.zimam_fund) return;
		frappe.db.get_value("Treasury Fund", frm.doc.zimam_fund, ["account", "company"]).then((r) => {
			const v = (r && r.message) || {};
			if (!v.account) {
				frappe.msgprint(__("الصندوق المختار بلا حساب أستاذ."));
				return;
			}
			if (v.company && frm.doc.company !== v.company) frm.set_value("company", v.company);
			frm.set_value("paid_to", v.account);
		});
	},
});
