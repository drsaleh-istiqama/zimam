// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// قائمة تقديرات الطباعة: مؤشر بالحالة (والمتابعة المستحقة)، وإجراء «عرض سعر مجمّع» لعدة تقديرات لعميل واحد.

frappe.listview_settings["Print Estimate"] = {
	add_fields: ["status", "follow_up_date", "docstatus", "quotation", "alternative_of"],
	hide_name_column: false,
	get_indicator(doc) {
		const today = frappe.datetime.get_today();
		if (doc.status === "مُرسل" && doc.follow_up_date && frappe.datetime.get_diff(doc.follow_up_date, today) <= 0) {
			return [__("متابعة مستحقة"), "orange", "status,=,مُرسل"];
		}
		const map = {
			"مسودة": ["مسودة", "gray"],
			"مُرسل": ["مُرسل", "blue"],
			"مقبول": ["مقبول", "green"],
			"مرفوض": ["مرفوض", "red"],
			"منتهي الصلاحية": ["منتهي الصلاحية", "darkgrey"],
			"ملغى": ["ملغى", "gray"],
		};
		const m = map[doc.status] || [doc.status || __("مسودة"), "gray"];
		return [__(m[0]), m[1], "status,=," + (doc.status || "")];
	},
	onload(listview) {
		listview.page.add_inner_button(__("التسعير السريع"), () => frappe.set_route("press-quick-quote"));
		listview.page.add_action_item(__("عرض سعر مجمّع للمختارة"), () => {
			const names = listview.get_checked_items().map((d) => d.name);
			if (names.length < 2) { frappe.msgprint(__("اختر تقديرين أو أكثر (مرحَّلة، لعميل واحد)")); return; }
			frappe.call({
				method: "zimam.zimam_core.doctype.print_estimate.print_estimate.make_quotation",
				args: { names }, freeze: true,
				callback: (r) => { if (r.message) { listview.refresh(); frappe.set_route("Form", "Quotation", r.message); } },
			});
		});
	},
};
