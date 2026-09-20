// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Print Estimates Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -3) },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "status", label: __("الحالة"), fieldtype: "Select", options: "\nمسودة\nمُرسل\nمقبول\nمرفوض\nمنتهي الصلاحية\nملغى" },
		{ fieldname: "open_only", label: __("المفتوحة فقط (مسودة/مُرسل)"), fieldtype: "Check" },
		{ fieldname: "follow_up_due", label: __("المتابعة مستحقة"), fieldtype: "Check" },
		{ fieldname: "customer", label: __("العميل"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "product_type", label: __("نوع المنتج"), fieldtype: "Data" },
		{ fieldname: "template", label: __("قالب المنتج"), fieldtype: "Link", options: "Print Product Template" },
		{ fieldname: "sent_via", label: __("أُرسل عبر"), fieldtype: "Select", options: "\nواتساب\nبريد إلكتروني\nطباعة\nيدويًا" },
		{ fieldname: "company", label: __("الشركة"), fieldtype: "Link", options: "Company" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const color = { "مقبول": "green", "مرفوض": "red", "مُرسل": "blue", "منتهي الصلاحية": "gray", "مسودة": "orange" }[data.status] || "gray";
			return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		if (column.fieldname === "follow_up_date" && data && data.status === "مُرسل" && data.follow_up_date && frappe.datetime.get_diff(data.follow_up_date, frappe.datetime.get_today()) <= 0) {
			return `<span style="color:var(--orange-600);font-weight:600">${value}</span>`;
		}
		return value;
	},
};
