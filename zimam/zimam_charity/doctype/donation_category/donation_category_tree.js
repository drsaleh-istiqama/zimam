// Copyright (c) 2026, جدوى للدراسات والتطوير — منتج زِمام
frappe.treeview_settings["Donation Category"] = {
	get_tree_nodes: "zimam.zimam_charity.doctype.donation_category.donation_category.get_children",
	title: __("فئات التبرع"),
	root_label: __("كل الفئات"),
	fields: [
		{ fieldtype: "Data", fieldname: "category_name", label: __("اسم الفئة"), reqd: 1 },
		{ fieldtype: "Data", fieldname: "category_code", label: __("الرمز") },
		{ fieldtype: "Check", fieldname: "is_group", label: __("فئة رئيسية") },
	],
	ignore_fields: ["parent_donation_category"],
	get_label(node) {
		return node.data.category_code ? `${node.data.category_code} · ${node.title}` : node.title;
	},
};
