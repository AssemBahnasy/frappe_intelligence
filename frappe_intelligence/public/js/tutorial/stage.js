// What the demo videos draw on the desk while they are recorded: a cursor, a ripple on every click,
// and a zoom that scales the page itself so text stays sharp. Only the recorder loads it.
import { TARGETS } from "./targets";

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

	// Screen centre of a target as it is drawn now, zoom included.
	point(target) {
		const element = TARGETS[target]?.();
		if (!element) return null;
		const r = element.getBoundingClientRect();
		return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
	}

	show(x, y) {
		this.cursor.css({ transition: "none", transform: `translate(${x}px,${y}px)` });
		void this.cursor[0].offsetWidth; // apply the jump before the transition comes back
		this.cursor.css({ transition: "", opacity: 1 });
	}

	move(x, y) {
		this.cursor.css("transform", `translate(${x}px,${y}px)`);
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
		const element = target && TARGETS[target]?.();
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

	// Plays a scripted answer through the assistant's own realtime handler (docs/agent/live-replies.md).
	emit(event) {
		const handlers = frappe.realtime.socket?.listeners("fi_assistant") || [];
		if (!handlers.length) throw new Error("The assistant panel is not listening for answers.");
		handlers.forEach((handler) => handler(event));
	}
}
