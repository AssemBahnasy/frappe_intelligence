// What the demo videos draw on the desk while they are recorded: a cursor, a ripple on every click,
// and a zoom that scales the page itself so text stays sharp. Only the recorder loads it.
import { find_target } from "./targets";

const EASE = "cubic-bezier(.65,0,.35,1)";
const STYLE = `
#fi-demo-cursor{position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;opacity:0;
	transition:transform .8s ${EASE},opacity .3s;filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
#fi-demo-cursor svg{transition:transform .12s}
#fi-demo-cursor.is-pressed svg{transform:scale(.82)}
.fi-demo-ripple{position:fixed;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;
	border:2px solid #7c5cff;background:rgba(124,92,255,.2);z-index:2147483646;pointer-events:none;
	animation:fi-demo-ripple .55s ease-out forwards}
@keyframes fi-demo-ripple{from{transform:scale(.3);opacity:1}to{transform:scale(1.5);opacity:0}}
.fi-demo-keys{position:fixed;left:50%;bottom:48px;transform:translateX(-50%);z-index:2147483646;
	padding:8px 14px;border-radius:10px;background:rgba(23,23,23,.88);color:#fff;font:600 18px/1 system-ui;
	letter-spacing:.02em;direction:ltr;unicode-bidi:isolate;pointer-events:none;
	animation:fi-demo-keys 1.6s ease forwards}
@keyframes fi-demo-keys{0%,85%{opacity:1}100%{opacity:0}}
body.fi-demo-zoom{transform-origin:0 0;transition:transform 1s ${EASE}}`;
const ARROW = `<svg width="26" height="26" viewBox="0 0 24 24"><path d="M5 2.5v17.2l4.6-4.3 2.9 6.6 2.9-1.3-2.9-6.5h6.3z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>`;

export class Stage {
	constructor() {
		$("<style>").text(STYLE).appendTo(document.head);
		// Outside <body>, so zooming the page does not move or scale the cursor.
		this.cursor = $(`<div id="fi-demo-cursor">${ARROW}</div>`).appendTo(
			document.documentElement
		);
		$(document.body).addClass("fi-demo-zoom");
		this.zoom = { scale: 1, x: 0, y: 0 };
	}

	// Screen centre of a target as it is drawn now, zoom included. A target below or above the
	// screen is scrolled to first (only zoomed out) and comes back as `{ scrolled: true }`; one
	// outside the zoomed view comes back as `{ outside: true }`.
	point(target) {
		const element = find_target(target);
		if (!element) return null;
		const r = element.getBoundingClientRect();
		const off_screen = r.top < 0 || r.bottom > innerHeight;
		if (off_screen && this.zoom.scale === 1) {
			element.scrollIntoView({ block: "center", behavior: "smooth" });
			return { scrolled: true };
		}
		const point = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
		const outside =
			point.x < 0 || point.x > innerWidth || point.y < 0 || point.y > innerHeight;
		return outside ? { outside: true } : point;
	}

	// Sets a select field as a user would, without the browser's own list (it is not recorded).
	select(target, value) {
		$(find_target(target)).find("select").val(value).trigger("change");
	}

	// Shows the keys pressed, e.g. "Ctrl + .".
	keys(label) {
		const badge = $('<div class="fi-demo-keys">')
			.text(label)
			.appendTo(document.documentElement);
		setTimeout(() => badge.remove(), 1700);
	}

	show(x, y) {
		this.cursor.css({ transition: "none", transform: `translate(${x}px,${y}px)` });
		void this.cursor[0].offsetWidth; // apply the jump before the transition comes back
		this.cursor.css({ transition: "", opacity: 1 });
	}

	move(x, y) {
		this.cursor.css("transform", `translate(${x}px,${y}px)`);
	}

	// Follows a drag at once, without the glide.
	track(x, y) {
		this.cursor.css({ transition: "none", transform: `translate(${x}px,${y}px)` });
	}

	release() {
		this.cursor.css("transition", "");
	}

	// Physical pixels for a logical distance: positive goes towards the end of the line.
	logical(dx) {
		return document.documentElement.dir === "rtl" ? -dx : dx;
	}

	press(x, y) {
		this.cursor.addClass("is-pressed");
		setTimeout(() => this.cursor.removeClass("is-pressed"), 160);
		const ripple = $('<div class="fi-demo-ripple">')
			.css({ left: x, top: y })
			.appendTo(document.documentElement);
		setTimeout(() => ripple.remove(), 600);
	}

	// Brings the target's centre to the middle of the screen, kept inside the page; no target zooms
	// back out. The cursor moves with the page.
	zoom_to(target, scale) {
		const cursor = this.cursor_point();
		const page = {
			x: (cursor.x - this.zoom.x) / this.zoom.scale,
			y: (cursor.y - this.zoom.y) / this.zoom.scale,
		};
		const element = target && find_target(target);
		if (!element) {
			this.zoom = { scale: 1, x: 0, y: 0 };
		} else {
			const r = element.getBoundingClientRect();
			const cx = (r.left + r.width / 2 - this.zoom.x) / this.zoom.scale;
			const cy = (r.top + r.height / 2 - this.zoom.y) / this.zoom.scale;
			const [w, h] = [innerWidth, innerHeight];
			this.zoom = {
				scale,
				x: Math.min(0, Math.max(w - w * scale, w / 2 - cx * scale)),
				y: Math.min(0, Math.max(h - h * scale, h / 2 - cy * scale)),
			};
		}
		const { scale: s, x, y } = this.zoom;
		document.body.style.transform = s === 1 ? "" : `translate(${x}px,${y}px) scale(${s})`;
		this.move(x + page.x * s, y + page.y * s);
	}

	cursor_point() {
		const m = new DOMMatrix(getComputedStyle(this.cursor[0]).transform);
		return { x: m.m41, y: m.m42 };
	}

	// Delivers a scripted realtime event to the page's own handlers: an answer (`fi_assistant`,
	// docs/agent/live-replies.md) or a background job's result (`fi_job`, shared/background.js).
	emit(event, channel = "fi_assistant") {
		const handlers = frappe.realtime.socket?.listeners(channel) || [];
		if (!handlers.length) throw new Error(`Nothing on the page is listening for ${channel}.`);
		handlers.forEach((handler) => handler(event));
	}

	// Turns on what a scene shows, though this site has it off (frappe.boot.fi_assistant).
	boot(values) {
		Object.assign(frappe.boot.fi_assistant, values);
	}
}
