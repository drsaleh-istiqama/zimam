// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Former Employees Archive"] = {
	filters: [
		{ fieldname: "from_date", label: __("انتهاء الخدمة من"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date" },
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
		{ fieldname: "department", label: __("القسم"), fieldtype: "Link", options: "Department" },
		{ fieldname: "designation", label: __("المسمى الوظيفي"), fieldtype: "Link", options: "Designation" },
		{ fieldname: "branch", label: __("الفرع"), fieldtype: "Link", options: "Branch" },
		{ fieldname: "reason", label: __("سبب المغادرة (يحتوي)"), fieldtype: "Data" },
	],
};
