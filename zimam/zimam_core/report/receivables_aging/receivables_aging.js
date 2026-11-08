// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Receivables Aging"] = {
	filters: [
		{ fieldname: "as_of_date", label: __("كما في"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
		{ fieldname: "customer", label: __("العميل"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "bucket", label: __("الفئة"), fieldtype: "Select", options: [
			{ value: "", label: "" }, { value: "b0", label: __("غير مستحق بعد") }, { value: "b1", label: __("1–30 يومًا") },
			{ value: "b2", label: __("31–60 يومًا") }, { value: "b3", label: __("61–90 يومًا") }, { value: "b4", label: __("أكثر من 90 يومًا") } ] },
		{ fieldname: "min_overdue_days", label: __("أيام التأخر ≥"), fieldtype: "Int" },
		{ fieldname: "without_followup", label: __("بلا أي متابعة فقط"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.fieldname === "days_overdue" && data.days_overdue > 90) value = `<span style="color:#C62828;font-weight:600">${value}</span>`;
		return value;
	},
};
