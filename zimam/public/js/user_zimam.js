// زِمام — تخصيص حزمة صلاحيات لمستخدم قائم بنقرة من شاشة المستخدم (بقرار د. صالح 2026-09-21)
frappe.ui.form.on("User", {
	refresh(frm) {
		if (frm.is_new() || !frappe.user.has_role(["مسؤول الصلاحيات", "System Manager"])) return;
		if (frm.doc.name === "Administrator" || frm.doc.name === "Guest") return;
		frm.add_custom_button(__("تخصيص حزمة زِمام"), () => {
			frappe.call({ method: "zimam.zimam_core.doctype.user_account_request.user_account_request.role_profiles_catalog" }).then((r) => {
				const packs = (r.message || []).filter((p) => p.name.includes("حزمة:"));
				const others = (r.message || []).filter((p) => !p.name.includes("حزمة:"));
				const options = packs.concat(others).map((p) => p.name).join("\n");
				const d = new frappe.ui.Dialog({
					title: __("تخصيص حزمة صلاحيات زِمام لـ {0}", [frm.doc.full_name || frm.doc.name]),
					fields: [
						{ fieldname: "role_profile", fieldtype: "Select", label: __("الحزمة / ملف الصلاحيات"), options, reqd: 1 },
						{ fieldname: "desc", fieldtype: "HTML" },
						{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("الشركة / الذراع (للقيد)") },
						{ fieldname: "restrict_to_company", fieldtype: "Check", label: __("تقييد المستخدم بمستندات هذه الشركة"), default: 1 },
						{ fieldname: "note", fieldtype: "Small Text", label: __("ملاحظة") },
					],
					primary_action_label: __("تخصيص الآن"),
					primary_action(v) {
						d.hide();
						frappe.call({ method: "zimam.zimam_core.doctype.user_account_request.user_account_request.assign_pack",
							args: { user: frm.doc.name, role_profile: v.role_profile, company: v.company, restrict_to_company: v.restrict_to_company ? 1 : 0, note: v.note },
							freeze: true, freeze_message: __("تطبيق الحزمة…") }).then((res) => {
							frappe.show_alert({ message: __("خُصِّصت الحزمة — الطلب {0}", [res.message]), indicator: "green" });
							frm.reload_doc();
						});
					},
				});
				const all = packs.concat(others);
				d.fields_dict.role_profile.$input.on("change", () => {
					const p = all.find((x) => x.name === d.get_value("role_profile"));
					d.fields_dict.desc.$wrapper.html(p ? `<div class="text-muted small">${frappe.utils.escape_html(p.description)}<br><b>${__("الأدوار")}:</b> ${frappe.utils.escape_html(p.roles.join("، "))}</div>` : "");
					if (p) frappe.call({ method: "zimam.zimam_core.doctype.user_account_request.user_account_request.pack_defaults", args: { role_profile: p.name } }).then((x) => { if (x.message && x.message.company) d.set_value("company", x.message.company); });
				});
				d.show();
			});
		}, __("زِمام"));
		frm.add_custom_button(__("الصلاحيات الفعلية"), () => {
			frappe.call({ method: "zimam.zimam_core.doctype.user_account_request.user_account_request.effective_permissions", args: { user: frm.doc.name }, freeze: true }).then((r) => {
				const m = r.message || {}; const esc = frappe.utils.escape_html;
				const rows = (m.rows || []).map((x) => `<tr><td>${esc(x.module.replace("Zimam ", ""))}</td><td>${esc(__(x.doctype))}</td><td>${esc(x.level)}</td></tr>`).join("");
				new frappe.ui.Dialog({ title: __("الصلاحيات الفعلية: {0}", [m.user]), size: "large", fields: [{ fieldtype: "HTML", options: `<p><b>${__("الأدوار")}:</b> ${esc((m.roles || []).join("، "))}</p><div style="max-height:60vh;overflow:auto"><table class="table table-bordered table-sm"><thead><tr><th>${__("الوحدة")}</th><th>${__("المستند")}</th><th>${__("المستوى")}</th></tr></thead><tbody>${rows}</tbody></table></div>` }] }).show();
			});
		}, __("زِمام"));
	},
});
