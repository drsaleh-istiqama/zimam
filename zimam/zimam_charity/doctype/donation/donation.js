// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt
// إيصال تبرع: حساب فوري للرسوم والصافي، وتصحيح الإيصال المرحَّل بإلغاء + تعديل في خطوة واحدة.

const DON = "zimam.zimam_charity.doctype.donation.donation";
let don_timer = null;

function don_recalc(frm) {
	if (frm.doc.docstatus !== 0 || !flt(frm.doc.amount)) return;
	clearTimeout(don_timer);
	don_timer = setTimeout(() => {
		if (!frm.doc.donation_category && !(frm.doc.allocations || []).length) return;
		frm.call({ doc: frm.doc, method: "recalculate" }).then(() => {
			frm.refresh_fields();
			frm.dirty();
			don_headline(frm);
		});
	}, 300);
}

function don_headline(frm) {
	const d = frm.doc;
	if (!flt(d.amount)) { frm.dashboard.clear_headline(); return; }
	const cur = (v) => format_currency(v, frappe.boot.sysdefaults.currency);
	frm.dashboard.set_headline(`<b>${__("الإجمالي")}</b> ${cur(d.amount)} · <b>${__("الرسوم الإدارية")}</b> ${cur(d.admin_fee_amount)} · <b>${__("الصافي")}</b> ${cur(d.net_amount)}`);
}

frappe.ui.form.on("Donation", {
	setup(frm) {
		frm.set_query("donation_category", () => ({ filters: { is_group: 0, is_active: 1 } }));
		frm.set_query("donation_category", "allocations", () => ({ filters: { is_group: 0, is_active: 1 } }));
		frm.set_query("fund", () => ({ filters: { is_active: 1 } }));
		frm.set_query("sponsorship", () => ({ filters: { status: "نشطة", ...(frm.doc.donor ? { sponsor: frm.doc.donor } : {}) } }));
	},
	onload(frm) {
		if (frm.is_new()) {
			frappe.call({ method: DON + ".get_defaults" }).then((r) => {
				const d = r.message || {};
				if (!frm.doc.company && d.company) frm.set_value("company", d.company);
				if (!frm.doc.fund && d.fund) frm.set_value("fund", d.fund);
				if (!frm.doc.date_hijri && d.date_hijri) frm.set_value("date_hijri", d.date_hijri);
			});
		}
	},
	refresh(frm) {
		don_headline(frm);
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("تصحيح الإيصال"), () => {
				frappe.confirm(__("سيُلغى هذا الإيصال وقيده ويُفتح إيصال مصحَّح يحمل رقمه مع لاحقة. أتريد المتابعة؟"), () => {
					frappe.xcall("frappe.client.cancel", { doctype: frm.doctype, name: frm.docname }).then(() => {
						frm.reload_doc().then(() => frm.amend_doc());
					});
				});
			});
			if (frm.doc.journal_entry) {
				frm.add_custom_button(__("القيد"), () => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry), __("عرض"));
			}
		}
	},
	amount: don_recalc,
	donation_category: don_recalc,
	donation_date(frm) {
		if (frm.doc.donation_date) {
			frappe.xcall("zimam.zimam_charity.utils.get_hijri", { date: frm.doc.donation_date }).then((h) => frm.set_value("date_hijri", h));
		}
	},
	donor(frm) {
		if (frm.doc.donor) frappe.db.get_value("Donor", frm.doc.donor, "donor_name").then((r) => frm.set_value("donor_name", (r.message || {}).donor_name));
	},
});

frappe.ui.form.on("Donation Allocation", {
	amount: (frm) => don_recalc(frm),
	admin_fee_percent: (frm) => don_recalc(frm),
	donation_category: (frm) => don_recalc(frm),
	allocations_remove: (frm) => don_recalc(frm),
});
