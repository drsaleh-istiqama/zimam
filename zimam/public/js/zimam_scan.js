// زِمام — المسح الذكي للمستندات (0.13.0): صوّر أو اختر فاتورة/إيصالًا/مراسلة ⟵ يتعرّف النظام على محتواها ⟵ تُعبَّأ حقول النموذج مباشرة.
// النموذج يقترح والإنسان يراجع: لا ترحيل ولا اعتماد تلقائي، والحقول المعبَّأة تُلوَّن وتبقى قابلة للتعديل.
// الاستخراج على الخادم (zimam.integrations.doc_scan.scan_document)؛ هذا الملف واجهة الالتقاط والرفع والتعبئة فقط.
(function () {
	const API = "zimam.integrations.doc_scan.";
	const MAX_SIDE = 2400; // أطول ضلع للصورة قبل الرفع: يكفي لقراءة الخط الصغير ويقلل زمن الرفع من الهاتف
	const MAX_PDF = 20 * 1024 * 1024;

	// النماذج التي تُعبَّأ مباشرة ⟵ حقل المرفق الذي يحمل الملف الممسوح
	const TARGETS = {
		"Payment Voucher": { attach: "supporting_document", label: "سند صرف", kinds: "فاتورة، إيصال" },
		"Disbursement Request": { attach: "attachment", label: "طلب صرف", kinds: "فاتورة مبدئية، عرض سعر" },
		"Legal Matter": { attach: "document", label: "شأن قانوني", kinds: "عقد، مراسلة رسمية" },
	};

	const zs = (frappe.boot && frappe.boot.zimam) || {};

	function isImage(file) {
		return /^image\//.test(file.type) || /\.(jpe?g|png|webp|gif|heic|heif)$/i.test(file.name || "");
	}

	// يصغّر الصورة ويحوّلها JPEG (يعالج صور الهاتف الكبيرة وHEIC حيث يفكّها المتصفح)
	async function prepare(file) {
		if (!isImage(file)) {
			if (file.size > MAX_PDF) throw new Error(__("حجم الملف أكبر من 20 ميغابايت"));
			return file;
		}
		let bmp;
		try {
			bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
		} catch (e) {
			throw new Error(__("تعذّر فتح الصورة. إن كانت بصيغة HEIC فالتقطها بوضع «الأكثر توافقًا» أو أرسلها JPG."));
		}
		const k = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
		const c = document.createElement("canvas");
		c.width = Math.round(bmp.width * k);
		c.height = Math.round(bmp.height * k);
		c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
		const blob = await new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.88));
		const name = (file.name || "scan").replace(/\.[^.]+$/, "") + ".jpg";
		return new File([blob], name, { type: "image/jpeg" });
	}

	// رفع الملف خاصًا (لا يراه إلا من يملك صلاحية السجل) عبر واجهة Frappe القياسية
	async function upload(file) {
		const fd = new FormData();
		fd.append("file", file, file.name);
		fd.append("is_private", "1");
		fd.append("folder", "Home/Attachments");
		const r = await fetch("/api/method/upload_file", { method: "POST", headers: { "X-Frappe-CSRF-Token": frappe.csrf_token }, body: fd, credentials: "same-origin" });
		const j = await r.json();
		if (!r.ok || !j.message || !j.message.file_url) throw new Error(__("فشل رفع الملف"));
		return j.message.file_url;
	}

	function esc(s) {
		return frappe.utils.escape_html(String(s == null ? "" : s));
	}

	function fill_form(frm, res, replace) {
		const t = TARGETS[frm.doctype];
		const fields = Object.assign({}, res.fields || {});
		if (t) fields[t.attach] = res.file_url;
		const done = [];
		const skipped = [];
		let chain = Promise.resolve();
		Object.keys(fields).forEach((fn) => {
			const df = frm.fields_dict[fn];
			if (!df || df.df.read_only) return;
			const cur = frm.doc[fn];
			if (cur && !replace && fn !== (t && t.attach)) {
				if (String(cur) !== String(fields[fn])) skipped.push(df.df.label || fn);
				return;
			}
			chain = chain.then(() => frm.set_value(fn, fields[fn])).then(() => {
				done.push(fn);
				df.$wrapper && df.$wrapper.addClass("zimam-scanned").attr("title", __("معبّأ من المسح الذكي — راجعه قبل الحفظ"));
			});
		});
		return chain.then(() => ({ done, skipped }));
	}

	function summary_html(res, filled) {
		const warn = (res.warnings || []).map((w) => `<li>${esc(w)}</li>`).join("");
		const link = `<a href="/desk/scanned-document/${encodeURIComponent(res.scan)}" target="_blank">${esc(res.scan)}</a>`;
		let h = `<div dir="rtl" style="line-height:1.9">`;
		h += `<div>${__("نوع المستند")}: <b>${esc(res.kind)}</b> · ${__("ثقة التعرّف")}: <b>${esc(res.confidence)}%</b> · ${__("سجل المسح")}: ${link}</div>`;
		if (filled) {
			h += `<div>${__("عُبّئ {0} حقلًا", [filled.done.length])}`;
			if (filled.skipped.length) h += ` · <span class="text-muted">${__("لم تُستبدل قيم موجودة في")}: ${filled.skipped.map(esc).join("، ")}</span>`;
			h += `</div>`;
		}
		if (warn) h += `<div style="margin-top:6px"><b>${__("للمراجعة")}:</b><ul style="margin:4px 0 0">${warn}</ul></div>`;
		else h += `<div class="text-muted">${__("لا تنبيهات — راجع المبالغ والأسماء مع المستند الأصلي قبل الحفظ.")}</div>`;
		return h + `</div>`;
	}

	async function run(file, opts, d) {
		const ready = await prepare(file);
		d.set_df_property("status", "options", `<div dir="rtl" class="text-muted">${__("جارٍ رفع المستند…")}</div>`);
		const url = await upload(ready);
		d.set_df_property("status", "options", `<div dir="rtl" class="text-muted">${__("جارٍ التعرّف على المحتوى (10–30 ثانية)…")}</div>`);
		const r = await frappe.call({ method: API + "scan_document", args: { file_url: url, target: opts.frm ? opts.frm.doctype : null, kind_hint: d.get_value("kind_hint") || null }, type: "POST" });
		return r.message;
	}

	// نقطة الدخول: zimam.scan.open({frm}) لتعبئة نموذج مفتوح، أو zimam.scan.open({}) لتسجيل مستند ممسوح فقط
	function open(opts) {
		opts = opts || {};
		if (!zs.scan_allowed) {
			frappe.msgprint(__("لا تملك صلاحية المسح الذكي."));
			return;
		}
		if (!zs.scan_enabled) {
			frappe.msgprint({
				title: __("المسح الذكي غير مفعّل"),
				message: __("يُرسل المسح المستند إلى خدمة Claude للتعرّف على محتواه، لذلك يتطلب موافقة صريحة: يفعّله مدير النظام من إعدادات زِمام ← الذكاء الاصطناعي، ويُدخل مفتاح الخدمة."),
				indicator: "orange",
			});
			return;
		}
		const frm = opts.frm;
		const t = frm && TARGETS[frm.doctype];
		const fields = [
			{ fieldname: "kind_hint", fieldtype: "Select", label: __("نوع المستند (اختياري)"), options: ["", "فاتورة مشتريات", "إيصال", "مراسلة", "عقد"].join("\n"), description: __("اتركه فارغًا ليتعرّف عليه النظام") },
			{ fieldname: "pick", fieldtype: "HTML" },
			{ fieldname: "status", fieldtype: "HTML", options: "" },
		];
		if (frm && !frm.is_new()) fields.splice(1, 0, { fieldname: "replace", fieldtype: "Check", label: __("استبدال القيم الموجودة في الحقول"), default: 0 });
		const d = new frappe.ui.Dialog({ title: t ? __("مسح مستند لتعبئة {0}", [__(t.label)]) : __("مسح مستند جديد"), fields });
		d.$wrapper.attr("dir", "rtl");
		const $pick = d.get_field("pick").$wrapper;
		$pick.html(`
			<div dir="rtl" style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 10px">
				<button type="button" class="btn btn-primary btn-sm zs-cam">${frappe.utils.icon("camera", "sm")} ${__("تصوير بالكاميرا")}</button>
				<button type="button" class="btn btn-default btn-sm zs-file">${frappe.utils.icon("upload", "sm")} ${__("اختيار ملف (صورة أو PDF)")}</button>
			</div>
			<div class="text-muted small" dir="rtl">${__("ضع المستند على سطح مستوٍ وفي إضاءة جيدة وصوّره كاملًا بلا انعكاس. المستند يُرسل إلى خدمة Claude للتعرّف، ثم تراجع أنت الحقول قبل الحفظ.")}</div>
			<input type="file" class="zs-input-cam" accept="image/*" capture="environment" hidden>
			<input type="file" class="zs-input-file" accept="image/*,application/pdf" hidden>`);
		const handle = async (ev) => {
			const file = ev.target.files && ev.target.files[0];
			ev.target.value = "";
			if (!file) return;
			$pick.find("button").prop("disabled", true);
			try {
				const res = await run(file, opts, d);
				let filled = null;
				if (frm) filled = await fill_form(frm, res, d.get_value("replace"));
				d.hide();
				if (frm) {
					frappe.msgprint({ title: __("اكتمل التعرّف على المستند"), message: summary_html(res, filled), indicator: (res.warnings || []).length ? "orange" : "green" });
				} else {
					frappe.set_route("Form", "Scanned Document", res.scan);
				}
			} catch (e) {
				$pick.find("button").prop("disabled", false);
				d.set_df_property("status", "options", `<div dir="rtl" class="text-danger">${esc((e && e.message) || __("تعذّر إكمال المسح. تحقق من الرسالة وأعد المحاولة."))}</div>`);
			}
		};
		$pick.find(".zs-input-cam,.zs-input-file").on("change", handle);
		$pick.find(".zs-cam").on("click", () => $pick.find(".zs-input-cam").trigger("click"));
		$pick.find(".zs-file").on("click", () => $pick.find(".zs-input-file").trigger("click"));
		d.show();
	}

	window.zimam = window.zimam || {};
	window.zimam.scan = { open };

	// زر «مسح مستند» في النماذج التي تُعبَّأ مباشرة (يظهر في المسودات فقط)
	Object.keys(TARGETS).forEach((dt) => {
		frappe.ui.form.on(dt, {
			refresh(frm) {
				if (!zs.scan_allowed || frm.doc.docstatus !== 0) return;
				frm.add_custom_button(__("مسح مستند وتعبئة الحقول"), () => open({ frm }), null).addClass("btn-primary-light");
			},
		});
	});

	// شاشة «مستند ممسوح»: إنشاء المستندات المستهدفة من نتيجة المسح
	frappe.ui.form.on("Scanned Document", {
		onload(frm) {
			if (frm.is_new() && !frm.doc.scan_file && zs.scan_allowed) setTimeout(() => open({}), 300);
		},
		refresh(frm) {
			if (frm.is_new()) return;
			const make = (target, label) => frm.add_custom_button(__(label), () => {
				frappe.call({ method: API + "create_from_scan", args: { scan: frm.doc.name, target }, type: "POST", freeze: true }).then((r) => {
					if (r.message) frappe.set_route("Form", r.message.doctype, r.message.name);
				});
			}, __("إنشاء"));
			if (!frm.doc.applied_name) {
				if (["فاتورة", "إيصال"].includes(frm.doc.doc_kind)) {
					make("Payment Voucher", "سند صرف");
					make("Disbursement Request", "طلب صرف");
				}
				if (["عقد", "مراسلة"].includes(frm.doc.doc_kind)) make("Legal Matter", "شأن قانوني");
				if (frm.doc.action_required) make("ToDo", "مهمة متابعة");
			}
			if (frm.doc.warnings) frm.dashboard.set_headline(`<span class="text-warning">${esc(frm.doc.warnings).replace(/\n/g, " · ")}</span>`);
		},
	});

	frappe.listview_settings["Scanned Document"] = Object.assign(frappe.listview_settings["Scanned Document"] || {}, {
		add_fields: ["status", "confidence"],
		get_indicator(doc) {
			const m = { "مستخرج": "blue", "بحاجة مراجعة": "orange", "مُطبَّق": "green", "ملغى": "gray" };
			return [__(doc.status), m[doc.status] || "gray", "status,=," + doc.status];
		},
		onload(list) {
			if (zs.scan_allowed) list.page.set_primary_action(__("مسح مستند جديد"), () => open({}), "camera");
		},
	});
})();
