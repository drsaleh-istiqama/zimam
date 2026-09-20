// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Sponsorship Dues"] = {
	filters: [
		{ fieldname: "sponsor", label: __("الكافل"), fieldtype: "Link", options: "Donor" },
		{ fieldname: "sponsorship", label: __("الكفالة"), fieldtype: "Link", options: "Sponsorship" },
		{ fieldname: "status", label: __("الحالة"), fieldtype: "Select", options: "\nمستحق\nمدفوع\nمعفى", default: "مستحق" },
		{ fieldname: "overdue_only", label: __("المتأخر فقط"), fieldtype: "Check" },
	],
};
