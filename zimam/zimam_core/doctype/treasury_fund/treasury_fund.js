// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt
// صندوق / حساب صرف: الأرصدة الثلاثة (مرحَّل / دفتري / فعلي) تُحدَّث عند فتح النموذج

frappe.ui.form.on("Treasury Fund", {
	setup(frm) {
		frm.set_query("account", () => ({ filters: { company: frm.doc.company, is_group: 0, account_type: ["in", ["Bank", "Cash"]] } }));
		frm.set_query("bank_account", () => ({ filters: { company: frm.doc.company } }));
		frm.set_query("cost_center", () => ({ filters: { company: frm.doc.company, is_group: 0 } }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frappe.xcall("zimam.zimam_core.finance.refresh_fund_balances", { fund: frm.doc.name }).then((v) => {
			["posted_balance", "committed_amount", "book_balance", "statement_difference", "balances_as_of"].forEach((f) => frm.doc[f] = v[f]);
			frm.refresh_fields();
			const cur = (x) => format_currency(x, frappe.boot.sysdefaults.currency);
			frm.dashboard.set_headline(`<b>${__("المرحَّل")}</b> ${cur(v.posted_balance)} · <b>${__("الدفتري")}</b> ${cur(v.book_balance)} · <b>${__("الفعلي (الكشف)")}</b> ${cur(frm.doc.statement_balance || 0)}`);
		});
		frm.add_custom_button(__("دفتر الأستاذ"), () => frappe.set_route("query-report", "General Ledger", { account: frm.doc.account, company: frm.doc.company }), __("عرض"));
		frm.add_custom_button(__("سندات الصرف"), () => frappe.set_route("List", "Payment Voucher", { fund: frm.doc.name }), __("عرض"));
	},
});
