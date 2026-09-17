// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// For license information, please see license.txt

frappe.ui.form.on("Zimam Settings", {
	refresh(frm) {
		frm.add_custom_button(__("تشغيل التهيئة من ملف تعريف"), () => {
			frappe.call({ method: "zimam.setup.bootstrap.list_profiles" }).then((r) => {
				const profiles = r.message || [];
				const d = new frappe.ui.Dialog({
					title: __("تهيئة المؤسسة على زِمام"),
					fields: [
						{ fieldname: "profile", fieldtype: "Select", label: __("ملف التعريف"), options: profiles.join("\n"), reqd: 1,
							default: frm.doc.institution_profile || profiles[0] },
						{ fieldname: "with_optional_arms", fieldtype: "Check", label: __("إنشاء الأذرع الاختيارية أيضًا") },
						{ fieldname: "note", fieldtype: "HTML", options:
							"<p class='text-muted'>" + __("آمن للتكرار: ما أُنشئ سابقًا لا يُمس. يلزم إكمال معالج الإعداد أولًا وأن تكون الشركة الأولى باسم المؤسسة في ملف التعريف.") + "</p>" },
					],
					primary_action_label: __("تشغيل"),
					primary_action(values) {
						d.hide();
						frappe.dom.freeze(__("جارٍ تهيئة المؤسسة…"));
						frappe.call({
							method: "zimam.setup.bootstrap.run_profile",
							args: { profile: values.profile, with_optional_arms: values.with_optional_arms ? 1 : 0 },
						}).then((res) => {
							frappe.dom.unfreeze();
							frappe.msgprint({ title: __("اكتملت التهيئة"), indicator: "green",
								message: "<pre style='direction:rtl;text-align:right;white-space:pre-wrap'>" + frappe.utils.escape_html((res.message || []).join("\n")) + "</pre>" });
							frm.reload_doc();
						}).catch(() => frappe.dom.unfreeze());
					},
				});
				d.show();
			});
		});
	},
});
