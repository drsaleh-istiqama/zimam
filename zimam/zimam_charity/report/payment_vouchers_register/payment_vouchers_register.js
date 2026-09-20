// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Payment Vouchers Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "workflow_state", label: __("المرحلة"), fieldtype: "Select", options: "\nمسودة\nمراجعة المالية\nبانتظار اعتماد الرئيس التنفيذي\nجاهز للدفع\nمدفوع\nمرفوض\nملغى" },
		{ fieldname: "pending_only", label: __("بانتظار الاعتماد/الدفع فقط"), fieldtype: "Check" },
		{ fieldname: "expense_classification", label: __("تصنيف المصروف"), fieldtype: "Link", options: "Expense Classification" },
		{ fieldname: "fund", label: __("حساب الصرف"), fieldtype: "Link", options: "Charity Fund" },
		{ fieldname: "branch", label: __("الفرع / الدولة"), fieldtype: "Link", options: "Branch" },
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project" },
		{ fieldname: "payment_method", label: __("طريقة الدفع"), fieldtype: "Select", options: "\nنقد\nتحويل بنكي\nشيك\nبطاقة\nبوابة إلكترونية" },
	],
};
