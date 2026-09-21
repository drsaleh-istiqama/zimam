# -*- coding: utf-8 -*-
"""v0.12.1 — عدّادات ترقيم مستقلة لكل نوع مستند.

كانت الأنواع تُرقَّم بـ`format:SR-{YYYY}-{####}`؛ في Frappe v16 يشترك جزء `{####}` في عدّاد واحد (مفتاح فارغ في tabSeries) بين كل
الأنواع، فظهرت أرقام متتابعة عبر أنواع مختلفة (SR-0008 ثم EV-009 ثم MA-0010…). صار الترقيم بنمط السلسلة `SR-.YYYY.-.####`
(عدّاد لكل بادئة). هذا الترقيع يضبط عدّاد كل بادئة على أعلى رقم قائم كي لا تتصادم الأسماء الجديدة مع القديمة."""
import re

import frappe


def execute():
	for dt in frappe.get_all("DocType", filters={"module": ["in", ["Zimam Core", "Zimam Giving", "Zimam Heritage", "Zimam Charity"]], "istable": 0}, pluck="name"):
		autoname = frappe.db.get_value("DocType", dt, "autoname") or ""
		if not autoname or ":" in autoname or "." not in autoname:
			continue
		# النمط مثل SR-.YYYY.-.#### ⟵ تعبير يلتقط الأسماء القائمة بأي سنة
		parts = autoname.split(".")
		regex = "^"
		for part in parts:
			if not part:
				continue
			if part in ("YYYY", "YY", "MM", "DD"):
				regex += r"(\d{%d})" % len(part)
			elif set(part) == {"#"}:
				regex += r"(\d+)$"
			else:
				regex += re.escape(part)
		try:
			names = frappe.get_all(dt, pluck="name", limit=100000)
		except Exception:
			continue
		maxes = {}
		for n in names:
			m = re.match(regex, n)
			if not m:
				continue
			groups = m.groups()
			key = autoname
			# إعادة بناء مفتاح السلسلة كما يبنيه Frappe: البادئة بعد تعويض التاريخ حتى جزء #
			gi = 0
			key = ""
			for part in parts:
				if not part:
					continue
				if part in ("YYYY", "YY", "MM", "DD"):
					key += groups[gi]; gi += 1
				elif set(part) == {"#"}:
					break
				else:
					key += part
			num = int(groups[-1])
			maxes[key] = max(maxes.get(key, 0), num)
		for key, cur in maxes.items():
			existing = frappe.db.get_value("Series", key, "current", order_by="name")
			if existing is None:
				frappe.db.sql("INSERT INTO `tabSeries` (`name`, `current`) VALUES (%s, %s)", (key, cur))
			elif int(existing) < cur:
				frappe.db.sql("UPDATE `tabSeries` SET `current` = %s WHERE `name` = %s", (cur, key))
	frappe.db.commit()
