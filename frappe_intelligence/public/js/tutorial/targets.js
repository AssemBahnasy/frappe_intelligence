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
	analytics: () => visible(`.sidebar-item-container[item-name="Session Analytics"]`),
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

const visible = (selector) => $(selector).filter(":visible").get(0);
