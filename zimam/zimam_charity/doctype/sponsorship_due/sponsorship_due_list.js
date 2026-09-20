// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
// استحقاقات الكفالة: «متأخر» يُشتق من التاريخ ولا يُخزَّن

frappe.listview_settings["Sponsorship Due"] = {
	add_fields: ["status", "due_date"],
	get_indicator(doc) {
		if (doc.status === "مدفوع") return [__("مدفوع"), "green", "status,=,مدفوع"];
		if (doc.status === "معفى") return [__("معفى"), "gray", "status,=,معفى"];
		if (doc.due_date && frappe.datetime.get_diff(frappe.datetime.get_today(), doc.due_date) > 0) return [__("متأخر"), "red", "due_date,<,Today"];
		return [__("مستحق"), "orange", "status,=,مستحق"];
	},
};
