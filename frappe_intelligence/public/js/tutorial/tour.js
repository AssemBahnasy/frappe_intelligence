// Show me: walks through a topic on the real desk with Frappe's tour engine (driver.js, the one
// Form Tour uses). Started only from the button, never by itself as Form Tour records are.

// The elements a topic's tour can point at (content.js → tour). Labels go through __() so they
// match the elements' own translated labels.
const PANEL = "aside.fi-assistant";
const TARGETS = {
	launcher: () => visible(".fi-assistant-launcher"),
	panel: () => visible(PANEL),
	resizer: () => visible(`${PANEL} .fi-resizer`),
	composer: () => visible(`${PANEL} textarea`),
	mode: () => visible(`${PANEL} .fi-mode`),
	attach: () => visible(`${PANEL} [aria-label="${__("Attach a file")}"]`),
	microphone: () => visible(`${PANEL} .fi-input-actions [aria-pressed]`), // only the mic has it
	history: () => visible(`${PANEL} [aria-label="${__("History")}"]`),
	new_chat: () => visible(`${PANEL} [aria-label="${__("New chat")}"]`),
	try_it: () => visible(".fi-try-it"),
	dock_workflows: () => visible(`.dock-items [aria-label="${__("Workflows")}"]`),
	dock_documents: () => visible(`.dock-items [aria-label="${__("Documents")}"]`),
	dock_setup: () => visible(`.dock-items [aria-label="${__("Setup")}"]`),
	analytics: () => visible(`.sidebar-item-container[item-name="Session Analytics"]`),
};
// Targets inside the assistant panel: the tour opens it first.
const IN_PANEL = [
	"panel",
	"resizer",
	"composer",
	"mode",
	"attach",
	"microphone",
	"history",
	"new_chat",
];

const visible = (selector) => $(selector).filter(":visible").get(0);

// Resolves once the tour ends; `finished` is true when the last step's Done was pressed.
export async function show_me(topic) {
	const wanted = topic.tour || [];
	const needs_panel = wanted.some((s) => IN_PANEL.includes(s.target));
	if (needs_panel) await frappe_intelligence.assistant.open();
	// Let the panel lay out before measuring it, and let the click that started the tour finish:
	// driver.js would take it for a click outside the highlight and close at once.
	await frappe.utils.sleep(needs_panel ? 150 : 50);
	const found = wanted
		.map((s) => ({ ...s, element: TARGETS[s.target]?.() }))
		.filter((s) => s.element);
	if (!found.length) {
		frappe.show_alert({
			message: __("This can't be shown on this screen."),
			indicator: "orange",
		});
		return { finished: false };
	}

	return new Promise((resolve) => {
		let finished = false;
		let active = true;
		const driver = new frappe.Driver({
			className: "frappe-driver",
			allowClose: true,
			padding: 6,
			opacity: 0.5,
			keyboardControl: true,
			nextBtnText: __("Next"),
			prevBtnText: __("Previous"),
			doneBtnText: __("Done"),
			closeBtnText: __("Skip"),
			onReset: () => {
				active = false;
				resolve({ finished });
			},
		});
		// Leaving the page ends the walk, as Form Tour does; its overlay would stay on top otherwise.
		// `once`, not on/off: frappe.router.off never removes a handler (it unbinds a new wrapper).
		frappe.router.once("change", () => active && driver.reset());
		driver.defineSteps(
			found.map((s, index) => ({
				element: s.element,
				popover: {
					title: heading(topic, s, index, found.length),
					description: frappe.utils.escape_html(text_of(topic, s)),
				},
				// The last step's Done comes through onNext before the tour resets.
				onNext: () => {
					if (index === found.length - 1) finished = true;
				},
			}))
		);
		driver.start();
	});
}

function title_of(topic, step) {
	if (step.title) return step.title;
	if (step.target === "try_it") return __("Try it now");
	return topic.steps[step.step]?.title || topic.title;
}

function text_of(topic, step) {
	if (step.text) return step.text;
	if (step.target === "try_it") return __("Opens the place this topic is about.");
	return topic.steps[step.step]?.text || topic.text;
}

// "Read a document · 1 of 4" above the step's own title.
function heading(topic, step, index, count) {
	const where = `${topic.title} · ${__("{0} of {1}", [index + 1, count])}`;
	return `<span class="fi-tour-where">${frappe.utils.escape_html(
		where
	)}</span>${frappe.utils.escape_html(title_of(topic, step))}`;
}
