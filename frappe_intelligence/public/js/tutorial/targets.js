// The desk elements a topic can point at, shared by Show me (tour.js) and the demo videos
// (demos.js). Labels go through __() so they match the elements' own translated labels.
export const PANEL = "aside.fi-assistant";

export const TARGETS = {
	launcher: () => visible(".fi-assistant-launcher"),
	panel: () => visible(PANEL),
	resizer: () => visible(`${PANEL} .fi-resizer`),
	composer: () => visible(`${PANEL} textarea`),
	send: () => visible(`${PANEL} .fi-send`),
	context: () => visible(`${PANEL} .fi-chip`),
	mode: () => visible(`${PANEL} .fi-mode`),
	attach: () => visible(`${PANEL} [aria-label="${__("Attach a file")}"]`),
	microphone: () => visible(`${PANEL} .fi-input-actions [aria-pressed]`), // only the mic has it
	history: () => visible(`${PANEL} [aria-label="${__("History")}"]`),
	new_chat: () => visible(`${PANEL} [aria-label="${__("New chat")}"]`),
	try_it: () => visible(".fi-try-it"),
	dock_workflows: () => visible(`.dock-items [aria-label="${__("Workflows")}"]`),
	dock_documents: () => visible(`.dock-items [aria-label="${__("Documents")}"]`),
	dock_setup: () => visible(`.dock-items [aria-label="${__("Setup")}"]`),
	analytics: () => sidebar_item("Session Analytics"),
};

// Targets inside the assistant panel: it is opened first.
export const IN_PANEL = [
	"panel",
	"resizer",
	"composer",
	"send",
	"context",
	"mode",
	"attach",
	"microphone",
	"history",
	"new_chat",
];

// Demo scenes (demos.js) may also name a desk element directly: a sidebar item, a form field, its
// checkbox or tab, a list row by any text in it, any element by its aria-label, an input by its
// <label>, a button by its text, a row of an open menu (frappe.ui.Dropdown), or, for a page's own
// parts, `{ css, text }`. Labels are translated; record names and data are not.
export function find_target(target) {
	if (typeof target === "string") return TARGETS[target]?.();
	if (target.sidebar) return sidebar_item(target.sidebar);
	if (target.field) return visible(`.frappe-control[data-fieldname="${target.field}"]`);
	if (target.check) return visible(`.frappe-control[data-fieldname="${target.check}"] input`);
	if (target.tab) return visible(`.form-tabs .nav-link[data-fieldname="${target.tab}"]`);
	if (target.label) return visible(`[aria-label="${target.label}"]`);
	if (target.row) {
		// The row's title link: its other columns are filter links (list_view.js).
		const row = $(".list-row")
			.filter(":visible")
			.toArray()
			.find((r) => r.textContent.includes(target.row));
		return row && $(row).find("a[data-name]").get(0);
	}
	if (target.css) {
		return $(target.css)
			.filter(":visible")
			.toArray()
			.find((el) => !target.text || el.textContent.includes(target.text));
	}
	if (target.input) {
		const label = $("label")
			.filter(":visible")
			.toArray()
			.find((l) => l.textContent.trim() === target.input);
		return label && document.getElementById(label.htmlFor);
	}
	if (target.button) {
		const buttons = $("button").filter(":visible").toArray();
		const text = (b) => b.textContent.replace(/\s+/g, " ").trim();
		return (
			buttons.find((b) => text(b) === target.button) ||
			buttons.find((b) => text(b).includes(target.button))
		);
	}
	if (target.menu) {
		return $('[role="menuitem"]')
			.filter(":visible")
			.filter((_, row) => menu_label(row) === target.menu)
			.get(0);
	}
}

// A sidebar item by its label: Frappe names it after the translated label (sidebar_item.html).
const sidebar_item = (label) => visible(`.sidebar-item-container[item-name="${__(label)}"]`);

// A menu row's label without its description, which Frappe puts inside it (ui/components/menu.js).
function menu_label(row) {
	const label = $(row).find(".es-menu__label").clone();
	label.find(".es-menu__description").remove();
	return label.text().trim();
}

const visible = (selector) => $(selector).filter(":visible").get(0);
