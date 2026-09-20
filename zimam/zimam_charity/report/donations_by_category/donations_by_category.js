// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Donations by Category"] = {
	filters: [
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "channel", label: __("القناة"), fieldtype: "Select", options: "\nبنك\nنقد\nشيك\nبطاقة\nثواني\nOMPay\nواتساب\nالموقع الإلكتروني\nأخرى" },
		{ fieldname: "fund", label: __("الصندوق"), fieldtype: "Link", options: "Charity Fund" },
		{ fieldname: "hide_empty", label: __("إخفاء الفئات الفارغة"), fieldtype: "Check", default: 1 },
	],
	tree: true,
	name_field: "category",
	parent_field: "parent",
	initial_depth: 1,
};
