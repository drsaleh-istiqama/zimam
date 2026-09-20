// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Print Quotes Conversion"] = {
	filters: [
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "group_by", label: __("تجميع بحسب"), fieldtype: "Select", options: "نوع المنتج\nالشهر\nالعميل\nقناة الإرسال\nمُعدّ التقدير\nقالب المنتج", default: "نوع المنتج", reqd: 1 },
		{ fieldname: "include_alternatives", label: __("تضمين الخيارات البديلة"), fieldtype: "Check" },
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "acceptance_percent" && data && data.acceptance_percent !== null && data.acceptance_percent !== undefined) {
			const color = data.acceptance_percent >= 50 ? "var(--green-600)" : data.acceptance_percent >= 25 ? "var(--orange-600)" : "var(--red-600)";
			return `<span style="color:${color};font-weight:600">${value}</span>`;
		}
		return value;
	},
};
