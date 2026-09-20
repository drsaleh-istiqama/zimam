// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt
// سند صرف: شريط سلسلة الاعتماد (المحاسب ← مدير المالية ← الرئيس التنفيذي ← أمين الصندوق) كما في وقاف؛
// أزرار الإجراء نفسها يعرضها Frappe من سير العمل.

const PV_CHAIN = ["مسودة", "مراجعة المالية", "بانتظار اعتماد الرئيس التنفيذي", "جاهز للدفع", "مدفوع"];
const PV_LABEL = { "مسودة": "المحاسب", "مراجعة المالية": "مدير المالية", "بانتظار اعتماد الرئيس التنفيذي": "الرئيس التنفيذي", "جاهز للدفع": "أمين الصندوق", "مدفوع": "مدفوع" };

function pv_chain_html(frm) {
	const state = frm.doc.workflow_state || "مسودة";
	const idx = PV_CHAIN.indexOf(state);
	const chips = PV_CHAIN.filter((s) => s !== "بانتظار اعتماد الرئيس التنفيذي" || frm.doc.requires_ceo_approval).map((s) => {
		const i = PV_CHAIN.indexOf(s);
		const cls = i < idx ? "badge-success" : i === idx ? "badge-primary" : "badge-light";
		return `<span class="badge ${cls}" style="font-size:11px;margin-inline-end:4px">${__(PV_LABEL[s])}</span>`;
	});
	let html = `<div dir="rtl">${chips.join(' <span class="text-muted">›</span> ')}`;
	if (state === "مرفوض") html += ` <span class="badge badge-danger">${__("مرفوض")}</span>`;
	if (state === "ملغى") html += ` <span class="badge badge-secondary">${__("ملغى")}</span>`;
	const who = [];
	if (frm.doc.finance_reviewed_by) who.push(`${__("راجعه")}: ${frm.doc.finance_reviewed_by}`);
	if (frm.doc.approved_by) who.push(`${__("اعتمده")}: ${frm.doc.approved_by}`);
	if (frm.doc.paid_by) who.push(`${__("دفعه")}: ${frm.doc.paid_by}`);
	if (who.length) html += `<div class="text-muted small" style="margin-top:4px">${who.join(" · ")}</div>`;
	return html + "</div>";
}

frappe.ui.form.on("Payment Voucher", {
	setup(frm) {
		frm.set_query("expense_classification", () => ({ filters: { is_active: 1 } }));
		frm.set_query("fund", () => ({ filters: { is_active: 1, company: frm.doc.company } }));
		frm.set_query("cost_center", "allocations", () => ({ filters: { company: frm.doc.company, is_group: 0 } }));
	},
	onload(frm) {
		if (frm.is_new()) {
			frappe.xcall("zimam.zimam_core.doctype.payment_voucher.payment_voucher.get_defaults").then((d) => {
				if (!frm.doc.company && d.company) frm.set_value("company", d.company);
				if (!frm.doc.fund && d.fund) frm.set_value("fund", d.fund);
			});
		}
	},
	refresh(frm) {
		frm.dashboard.set_headline(pv_chain_html(frm));
		if (frm.doc.journal_entry) {
			frm.add_custom_button(__("القيد"), () => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry), __("عرض"));
		}
		if (frm.doc.disbursement_request) {
			frm.add_custom_button(__("طلب الصرف"), () => frappe.set_route("Form", "Disbursement Request", frm.doc.disbursement_request), __("عرض"));
		}
		// سبب الرفض يُطلب قبل تنفيذ إجراء «رفض»
		frm.page.wrapper.find(".actions-btn-group").off("click.zimam-pv");
	},
	before_workflow_action(frm) {
		const action = frm.selected_workflow_action;
		if (action !== "رفض" && action !== "إعادة إلى المحاسب") return;
		return new Promise((resolve, reject) => {
			frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("السبب / الملاحظة"), reqd: 1 }, (v) => {
				frm.set_value("rejection_reason", v.reason).then(resolve);
			}, __(action), __("تأكيد"));
		});
	},
	employee(frm) {
		if (frm.doc.employee) frappe.db.get_value("Employee", frm.doc.employee, "employee_name").then((r) => frm.set_value("beneficiary_name", (r.message || {}).employee_name));
	},
});
