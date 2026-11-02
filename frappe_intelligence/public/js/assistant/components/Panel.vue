<template>
	<div class="fi-panel" @keydown.esc="on_escape">
		<div
			class="fi-resizer"
			role="separator"
			aria-orientation="vertical"
			:aria-label="__('Resize')"
			@pointerdown="start_resize"
			@dblclick="reset_width"
		></div>

		<header class="fi-header">
			<span class="fi-header-icon"><Icon name="sparkles" /></span>
			<span class="fi-header-title">{{ name }}</span>
			<span class="fi-header-actions">
				<button
					class="fi-icon-button"
					:title="__('New chat')"
					:aria-label="__('New chat')"
					@click="store.new_chat()"
				>
					<Icon name="square-pen" />
				</button>
				<button
					ref="history_button"
					class="fi-icon-button"
					:title="__('History')"
					:aria-label="__('History')"
				>
					<Icon name="history" />
				</button>
				<button
					class="fi-icon-button"
					:title="__('Close')"
					:aria-label="__('Close')"
					@click="host.close()"
				>
					<Icon name="x" />
				</button>
			</span>
		</header>

		<WorkflowBar v-if="store.workflow" />

		<EmptyState v-if="!store.turns.length && !store.loading" @send="store.send" />
		<MessageList v-else />

		<Composer />
	</div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useAssistant } from "../store";
import Composer from "./Composer.vue";
import EmptyState from "./EmptyState.vue";
import Icon from "./Icon.vue";
import MessageList from "./MessageList.vue";
import WorkflowBar from "./WorkflowBar.vue";

const props = defineProps({ host: { type: Object, required: true } });
const store = useAssistant();
const name = frappe.boot.fi_assistant.name;

// History: Frappe's own menu, filled fresh on every open.
const history_button = ref(null);
let history_menu = null;
onMounted(() => {
	history_menu = new frappe.ui.Dropdown({
		trigger: history_button.value,
		side: "bottom",
		align: "end",
		empty_text: __("No conversations yet"),
		options: async () =>
			(await store.list_conversations()).map((c) => ({
				label: c.title || __("Untitled"),
				description: frappe.datetime.prettyDate(c.modified),
				selected: c.name === store.conversation,
				onclick: () => store.open_conversation(c.name),
			})),
	});
	apply_width(stored_width());
});
onBeforeUnmount(() => history_menu?.destroy());

function on_escape(e) {
	if (!e.defaultPrevented) props.host.close();
}

// Width: dragged from the inner edge, kept per browser.
const WIDTH_KEY = "fi_assistant_width";
const MIN_WIDTH = 360;
const DEFAULT_WIDTH = 420;

function start_resize(e) {
	const handle = e.currentTarget;
	const start_x = e.clientX;
	const start_width = props.host.$aside.outerWidth();
	const direction = frappe.utils.is_rtl() ? -1 : 1;
	handle.setPointerCapture(e.pointerId);
	document.body.classList.add("fi-assistant-resizing");
	const move = (event) => apply_width(start_width + (start_x - event.clientX) * direction);
	const stop = () => {
		handle.removeEventListener("pointermove", move);
		document.body.classList.remove("fi-assistant-resizing");
		storage(() => localStorage.setItem(WIDTH_KEY, props.host.$aside.outerWidth()));
	};
	handle.addEventListener("pointermove", move);
	handle.addEventListener("pointerup", stop, { once: true });
}

function reset_width() {
	storage(() => localStorage.removeItem(WIDTH_KEY));
	apply_width(DEFAULT_WIDTH);
}

function apply_width(width) {
	const max = Math.max(MIN_WIDTH, Math.min(760, window.innerWidth * 0.6));
	const clamped = Math.round(Math.min(Math.max(width, MIN_WIDTH), max));
	props.host.$aside[0].style.setProperty("--fi-assistant-width", `${clamped}px`);
}

function stored_width() {
	return Number(storage(() => localStorage.getItem(WIDTH_KEY))) || DEFAULT_WIDTH;
}

function storage(fn) {
	try {
		return fn();
	} catch {
		return null;
	}
}
</script>

<style scoped>
.fi-panel {
	position: relative;
	display: flex;
	flex-direction: column;
	height: 100%;
	background: var(--surface-base);
	color: var(--ink-gray-8);
	font-size: var(--text-base);
}
.fi-resizer {
	position: absolute;
	inset-block: 0;
	inset-inline-start: -3px;
	width: 6px;
	cursor: col-resize;
	z-index: 1;
}
.fi-header {
	height: 48px;
	flex: none;
	display: flex;
	align-items: center;
	gap: 8px;
	padding-inline: 16px 8px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.fi-header-icon {
	display: inline-flex;
	color: var(--ink-violet-6);
}
.fi-header-title {
	flex: 1;
	min-width: 0;
	font-size: 15px;
	font-weight: 600;
	color: var(--ink-gray-9);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.fi-header-actions {
	display: flex;
	gap: 2px;
}
.fi-icon-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	padding: 0;
	border: 0;
	border-radius: var(--radius);
	background: transparent;
	color: var(--ink-gray-6);
}
.fi-icon-button:hover,
.fi-icon-button[aria-expanded="true"] {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
.fi-icon-button:focus-visible {
	box-shadow: var(--focus-default);
	outline: none;
}
</style>
