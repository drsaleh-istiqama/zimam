// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Receipts Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "status", label: __("الحالة"), fieldtype: "Select", options: "\nمسودة\nمعتمد\nملغى" },
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
		{ fieldname: "fund", label: __("الصندوق"), fieldtype: "Link", options: "Treasury Fund" },
		{ fieldname: "mode_of_payment", label: __("طريقة القبض"), fieldtype: "Link", options: "Mode of Payment" },
		{ fieldname: "party_type", label: __("نوع الطرف"), fieldtype: "Link", options: "DocType" },
		{ fieldname: "party", label: __("الطرف"), fieldtype: "Dynamic Link", get_options: () => frappe.query_report.get_filter_value("party_type") },
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project" },
		{ fieldname: "min_amount", label: __("الحد الأدنى للمبلغ"), fieldtype: "Currency" },
	],
	onload(report) {
		report.page.add_inner_button(__("سند قبض جديد"), () => frappe.new_doc("Payment Entry", { payment_type: "Receive" }));
	},
};
