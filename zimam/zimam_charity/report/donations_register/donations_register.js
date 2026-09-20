// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.query_reports["Donations Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("من"), fieldtype: "Date", default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("إلى"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "donation_category", label: __("الفئة (أو الفئة الأم)"), fieldtype: "Link", options: "Donation Category" },
		{ fieldname: "channel", label: __("القناة"), fieldtype: "Select", options: "\nبنك\nنقد\nشيك\nبطاقة\nثواني\nOMPay\nواتساب\nالموقع الإلكتروني\nأخرى" },
		{ fieldname: "fund", label: __("الصندوق"), fieldtype: "Link", options: "Charity Fund" },
		{ fieldname: "donor", label: __("المتبرع"), fieldtype: "Link", options: "Donor" },
		{ fieldname: "member", label: __("العضو"), fieldtype: "Link", options: "Member" },
		{ fieldname: "project", label: __("المشروع"), fieldtype: "Link", options: "Project" },
		{ fieldname: "source", label: __("مُسجَّل عبر"), fieldtype: "Select", options: "\nإدخال يدوي\nالموقع الإلكتروني\nاستيراد من ملف\nبوابة دفع" },
	],
};
