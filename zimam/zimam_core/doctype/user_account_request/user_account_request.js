// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("User Account Request", {
	setup(frm) {
		frm.set_query("role_profile", () => ({ filters: [["Role Profile", "name", "like", "زِمام%"]] }));
		frm.set_query("employee", () => (frm.doc.company ? { filters: { company: frm.doc.company, status: "Active" } } : {}));
		frm.set_query("department", () => (frm.doc.company ? { filters: { company: frm.doc.company } } : {}));
	},
	refresh(frm) {
		frm.add_custom_button(__("مصفوفة الصلاحيات"), () => window.open("/assets/zimam/permissions-matrix.html", "_blank"), __("مرجع"));
		if (frm.is_new()) {
			frm.set_intro(__("اختر ملف الصلاحيات المناسب للصفة الوظيفية؛ الأدوار الإضافية استثناء يُبرَّر. بعد الحفظ يُخطَر مسؤول الصلاحيات ليعتمد الطلب فيُنشأ الحساب وتصل صاحبه رسالة تعيين كلمة المرور."), "blue");
			return;
		}
		const can_process = frappe.user.has_role(["مسؤول الصلاحيات", "System Manager"]);
		const colors = { "طلب جديد": "orange", "معتمد ومنفَّذ": "green", "مرفوض": "red", "موقوف": "grey" };
		frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "blue");
		if (frm.doc.status === "طلب جديد" && can_process) {
			frm.add_custom_button(__("اعتماد وإنشاء الحساب"), () => {
				const d = new frappe.ui.Dialog({
					title: __("اعتماد الطلب وإنشاء الحساب"),
					fields: [
						{ fieldtype: "HTML", options: `<div class="text-muted small" style="white-space:pre-wrap">${frappe.utils.escape_html(frm.doc.role_profile_summary || "")}</div>` },
						{ fieldname: "send_welcome_email", fieldtype: "Check", label: __("إرسال رسالة الترحيب برابط تعيين كلمة المرور"), default: 1 },
						{ fieldname: "note", fieldtype: "Small Text", label: __("ملاحظة (اختياري)") },
					],
					primary_action_label: __("اعتماد وإنشاء"),
					primary_action(v) {
						d.hide();
						frm.call({ doc: frm.doc, method: "provision", args: v, freeze: true, freeze_message: __("إنشاء الحساب…") }).then((r) => {
							frm.reload_doc();
							if (r.message) frappe.show_alert({ message: __("أُنشئ/حُدِّث الحساب {0}", [r.message]), indicator: "green" });
						});
					},
				});
				d.show();
			}).addClass("btn-primary");
			frm.add_custom_button(__("رفض"), () => {
				frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("سبب الرفض"), reqd: 1 }, (v) => {
					frm.call({ doc: frm.doc, method: "reject", args: { note: v.note } }).then(() => frm.reload_doc());
				}, __("رفض الطلب"), __("رفض"));
			});
		}
		if (frm.doc.status === "معتمد ومنفَّذ" && can_process && frm.doc.user) {
			frm.add_custom_button(__("إيقاف الحساب"), () => {
				frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("سبب الإيقاف (إنهاء خدمة، نقل…)"), reqd: 1 }, (v) => {
					frm.call({ doc: frm.doc, method: "suspend", args: { note: v.note } }).then(() => frm.reload_doc());
				}, __("إيقاف الحساب"), __("إيقاف"));
			});
		}
		if (frm.doc.status === "موقوف" && can_process && frm.doc.user) {
			frm.add_custom_button(__("إعادة تفعيل الحساب"), () => {
				frm.call({ doc: frm.doc, method: "reactivate" }).then(() => frm.reload_doc());
			}).addClass("btn-primary");
		}
		if (frm.doc.user) {
			frm.add_custom_button(__("حساب المستخدم"), () => frappe.set_route("Form", "User", frm.doc.user), __("عرض"));
			frm.add_custom_button(__("قيود المستخدم"), () => frappe.set_route("List", "User Permission", { user: frm.doc.user }), __("عرض"));
		}
	},
	role_profile(frm) {
		if (!frm.doc.role_profile) {
			frm.set_value("role_profile_summary", "");
			return;
		}
		frappe.call({
			method: "zimam.zimam_core.doctype.user_account_request.user_account_request.profile_summary",
			args: { role_profile: frm.doc.role_profile },
		}).then((r) => frm.set_value("role_profile_summary", r.message || ""));
	},
	employee(frm) {
		if (!frm.doc.employee) return;
		frappe.db.get_value("Employee", frm.doc.employee, ["employee_name", "company", "department", "designation", "cell_number", "company_email", "personal_email"]).then((r) => {
			const e = r.message || {};
			if (!frm.doc.full_name) frm.set_value("full_name", e.employee_name);
			if (!frm.doc.email) frm.set_value("email", e.company_email || e.personal_email);
			if (!frm.doc.mobile_no) frm.set_value("mobile_no", e.cell_number);
			if (!frm.doc.job_title) frm.set_value("job_title", e.designation);
			if (e.company) frm.set_value("company", e.company);
			if (e.department) frm.set_value("department", e.department);
		});
	},
});
