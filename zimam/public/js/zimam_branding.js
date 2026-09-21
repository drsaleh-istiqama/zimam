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
		bar.style.cssText = "position:fixed;inset-inline:0;bottom:0;z-index:5;font-size:12px;line-height:1.6;text-align:center;padding:3px 12px;pointer-events:none;" +
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
// في v16 يعرض المسار الفارغ (/desk) صفحة «desktop» دائمًا ولا تغيّره إعدادات التطبيق الافتراضي وحدها.
// لا نعتمد على أحداث التحميل (ثبت في 0.12.7 أنها لا تصل لهذا الملف)؛ نراقب جاهزية سطح المكتب ثم نوجّه مرة واحدة في الجلسة.
(function () {
	var tries = 0, done = false;
	function ready() {
		return window.frappe && frappe.boot && frappe.session && frappe.session.user && frappe.session.user !== "Guest" &&
			frappe.router && typeof frappe.set_route === "function" && frappe.boot.home_page !== "setup-wizard";
	}
	function land() {
		if (done) return true;
		if (!ready()) return false;
		var path = (location.pathname || "").replace(/\/+$/, "");
		if (path !== "/desk" && path !== "/app") { done = true; return true; }
		if (location.hash && location.hash.length > 1) { done = true; return true; }
		if (!document.querySelector(".icons-container, .desktop-icons, #page-desktop, .page-container")) return false;
		done = true;
		try { sessionStorage.setItem("zimam_landed", "1"); } catch (e) {}
		frappe.route_flags = frappe.route_flags || {};
		frappe.route_flags.replace_route = true;
		frappe.set_route("zimam");
		return true;
	}
	try { if (sessionStorage.getItem("zimam_landed")) done = true; } catch (e) {}
	var timer = setInterval(function () {
		tries += 1;
		if (land() || tries > 60) clearInterval(timer);
	}, 250);
})();

// الشريط يقتصر على منطقة المحتوى: يترك عرض الشريط الجانبي (اسم المستخدم وقائمته في أسفله) مكشوفًا — ملاحظة د. صالح 2026-09-21
(function () {
	function fit() {
		var bar = document.getElementById("zimam-powered-by");
		if (!bar) return;
		var sb = document.querySelector(".body-sidebar, .layout-side-section.sidebar-toggled, .desk-sidebar");
		var w = sb && sb.offsetWidth && sb.offsetHeight ? sb.getBoundingClientRect().width : 0;
		bar.style.insetInlineStart = w ? w + "px" : "0";
		bar.style.insetInlineEnd = "0";
		var a = bar.querySelector("a");
		if (a) a.style.pointerEvents = "auto";
	}
	window.addEventListener("resize", fit);
	document.addEventListener("DOMContentLoaded", function () { setTimeout(fit, 1200); });
	if (window.jQuery) {
		jQuery(document).on("startup page-change", function () { setTimeout(fit, 400); });
		jQuery(document).on("click", ".sidebar-toggle-btn, .body-sidebar-toggle, [data-toggle-sidebar]", function () { setTimeout(fit, 500); });
	}
	setInterval(fit, 3000);
})();
