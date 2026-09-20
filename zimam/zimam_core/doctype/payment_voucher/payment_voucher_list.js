// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// قائمة سندات الصرف: مؤشر لوني بحسب مرحلة الاعتماد (كما في تبويبات وقاف: بانتظار الاعتماد / جاهز للدفع / مدفوع / مرفوض)

frappe.listview_settings["Payment Voucher"] = {
	add_fields: ["workflow_state", "requires_ceo_approval"],
	hide_name_column: false,
	get_indicator(doc) {
		const map = {
			"مسودة": ["مسودة", "gray"],
			"مراجعة المالية": ["مراجعة المالية", "blue"],
			"بانتظار اعتماد الرئيس التنفيذي": ["بانتظار الرئيس التنفيذي", "orange"],
			"جاهز للدفع": ["جاهز للدفع", "purple"],
			"مدفوع": ["مدفوع", "green"],
			"مرفوض": ["مرفوض", "red"],
			"ملغى": ["ملغى", "gray"],
		};
		const m = map[doc.workflow_state] || [doc.workflow_state || __("مسودة"), "gray"];
		return [__(m[0]), m[1], "workflow_state,=," + (doc.workflow_state || "")];
	},
};
