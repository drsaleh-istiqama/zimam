// زِمام — شريط «يعمل هذا النظام من خلال منصة زِمام» في سطح المكتب.
// النص يأتي من إعدادات زِمام (powered_by_text) عبر boot_session، فتُبقي كل مؤسسة اسمها وشعارها ويظهر انتماء المنصة أسفل الشاشة.
(function () {
	function render() {
		if (!window.frappe || !frappe.boot || document.getElementById("zimam-powered-by")) return;
		var text = (frappe.boot.zimam && frappe.boot.zimam.powered_by_text) || "";
		if (!text) return;
		var url = (frappe.boot.zimam && frappe.boot.zimam.powered_by_url) || "";
		var bar = document.createElement("div");
		bar.id = "zimam-powered-by";
		bar.setAttribute("dir", "rtl");
		bar.setAttribute("lang", "ar");
		bar.style.cssText = "position:fixed;inset-inline:0;bottom:0;z-index:1020;font-size:12px;line-height:1.6;text-align:center;padding:3px 12px;" +
			"background:var(--bg-color, #fff);color:var(--text-muted, #6c7680);border-top:1px solid var(--border-color, #e2e6e9);direction:rtl;";
		if (url) {
			var a = document.createElement("a");
			a.href = url; a.target = "_blank"; a.rel = "noopener"; a.textContent = text;
			a.style.cssText = "color:inherit;text-decoration:none;";
			bar.appendChild(a);
		} else {
			bar.textContent = text;
		}
		document.body.appendChild(bar);
		document.body.style.paddingBottom = "28px";
	}
	if (document.readyState === "complete" || document.readyState === "interactive") {
		setTimeout(render, 0);
	} else {
		document.addEventListener("DOMContentLoaded", render);
	}
	if (window.frappe && frappe.router && frappe.router.on) {
		frappe.router.on("change", render);
	}
})();


// الهبوط بعد الدخول: مساحة زِمام مباشرة لا شاشة أيقونات سطح المكتب (بقرار د. صالح 2026-09-21).
// في v16 يعرض المسار الفارغ (/desk) صفحة «desktop» دائمًا ولا تغيّره إعدادات التطبيق الافتراضي وحدها،
// فنُعيد التوجيه مرة واحدة عند أول تحميل للجلسة فقط؛ زر «Desktop» من قائمة الشريط الجانبي يبقى يعمل بعدها.
(function () {
	var done = false;
	function land() {
		if (done || !window.frappe || !frappe.session || frappe.session.user === "Guest") return;
		var path = (location.pathname || "").replace(/\/+$/, "");
		if (path !== "/desk" && path !== "/app") return;
		if (location.hash && location.hash.length > 1) return;
		done = true;
		frappe.route_flags = frappe.route_flags || {};
		frappe.route_flags.replace_route = true;
		frappe.set_route("zimam");
	}
	if (window.jQuery) {
		jQuery(document).on("startup", function () { setTimeout(land, 0); });
	}
	document.addEventListener("DOMContentLoaded", function () { setTimeout(land, 800); });
})();
