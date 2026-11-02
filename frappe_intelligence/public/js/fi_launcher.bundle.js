// Puts the assistant in the dock and the sidebar and opens it with Ctrl+.
// The panel itself loads on first use (fi_assistant.bundle.js).

frappe.provide("frappe_intelligence");

const LAUNCHER = "fi-assistant-launcher";
const OPEN_KEY = "fi_assistant_open";
let panel = null;
let loading = null;

frappe_intelligence.assistant = {
	toggle: () => load().then(() => panel.toggle()),
	open: () => load().then(() => panel.open()),
};

function load() {
	// One shared promise: two frappe.require calls for the same file would run it twice.
	loading ??= frappe.require("fi_assistant.bundle.js").then(() => {
		panel = new frappe_intelligence.ui.AssistantPanel({ on_toggle: mark_open });
	});
	return loading;
}

function mark_open(open) {
	$(`.${LAUNCHER}`).toggleClass("active", open).attr("aria-pressed", open);
	try {
		open ? localStorage.setItem(OPEN_KEY, "1") : localStorage.removeItem(OPEN_KEY);
	} catch {
		// storage unavailable: the panel just starts closed next time
	}
}

// The dock is built lazily and the sidebar's standard rows once, so check after each page change.
function add_launchers() {
	const sidebar = frappe.app?.sidebar;
	const label = frappe.boot.fi_assistant.name;
	const toggle = () => frappe_intelligence.assistant.toggle();

	const $dock = sidebar?.dock?.$dock;
	const $utilities = $dock?.find(".dock-utilities");
	if ($utilities?.length && !$utilities.find(`.${LAUNCHER}`).length) {
		sidebar.dock
			.make_utility({ label, icon: "sparkles", css_class: LAUNCHER })
			.on("click", toggle)
			.appendTo($utilities);
		// The dock takes over search and notifications while pinned (dock.js → apply_pin).
		new MutationObserver(sync_sidebar_row).observe($dock[0], { attributeFilter: ["class"] });
	}

	const $band = sidebar?.$standard_items_band;
	if ($band?.length && !$band.find(`.${LAUNCHER}`).length) {
		sidebar.add_item($band, {
			label,
			icon: "sparkles",
			standard: true,
			type: "Button",
			class: LAUNCHER,
			onClick: toggle,
		});
	}
	sync_sidebar_row();
	// Built after the panel may have reopened, so take its state now.
	if (panel) mark_open(panel.is_open);
}

// Same rule as search and notifications: one entry, in the dock when it owns them, else in the
// sidebar. `.hidden` (not CSS) so the band's own empty-state spacing still applies.
function sync_sidebar_row() {
	const dock_owns = $(".dock").hasClass("dock-owns-utilities");
	$(`.standard-items-band > .${LAUNCHER}`).toggleClass("hidden", dock_owns);
}

$(document).on("app_ready", () => {
	if (!frappe.boot.fi_assistant) return;
	add_launchers();
	$(document).on("page-change", () => setTimeout(add_launchers));
	frappe.ui.keys.add_shortcut({
		// Ctrl+. — Frappe's key map names the period key (190) ">" (ui/keyboard.js).
		shortcut: "ctrl+>",
		action: () => frappe_intelligence.assistant.toggle(),
		description: __("Open the Assistant"),
		ignore_inputs: true,
	});
	try {
		if (localStorage.getItem(OPEN_KEY)) frappe_intelligence.assistant.open();
	} catch {
		// storage unavailable
	}
});
