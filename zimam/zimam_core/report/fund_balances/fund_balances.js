// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Fund Balances"] = {
	filters: [
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "include_inactive", label: __("إظهار الصناديق غير النشطة"), fieldtype: "Check" },
	],
};
