<template>
	<form class="fi-composer" @submit.prevent="submit">
		<div v-if="chip" class="fi-chip-row">
			<span class="fi-chip">
				<Icon name="file-text" size="xs" />
				<span class="fi-chip-label">{{ chip }}</span>
				<button
					type="button"
					class="fi-chip-remove"
					:aria-label="__('Don\'t use this page as context')"
					@click="store.context_dismissed = true"
				>
					<Icon name="x" size="xs" />
				</button>
			</span>
		</div>

		<div class="fi-input">
			<label :for="input_id" class="sr-only">{{ __("Message") }}</label>
			<textarea
				:id="input_id"
				ref="input"
				v-model="draft"
				rows="2"
				dir="auto"
				:placeholder="placeholder"
				@input="grow"
				@keydown.enter.exact="on_enter"
			></textarea>
			<div class="fi-input-actions">
				<button ref="mode_button" type="button" class="fi-mode" :class="{ agent: store.mode === 'Agent' }">
					{{ store.mode === "Agent" ? __("Agent") : __("Ask") }}
					<Icon name="chevron-down" size="xs" />
				</button>
				<span class="fi-spacer"></span>
				<button v-if="store.run" type="button" class="fi-stop" @click="store.stop()">
					<Icon name="square" size="xs" />
					{{ __("Stop") }}
				</button>
				<button v-else type="submit" class="fi-send" :disabled="!draft.trim()" :aria-label="__('Send')">
					<Icon name="arrow-up" />
				</button>
			</div>
		</div>
		<div class="fi-disclaimer">{{ __("AI can make mistakes. Check important figures.") }}</div>
	</form>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { context_label } from "../page_context";
import { useAssistant } from "../store";
import Icon from "./Icon.vue";

const store = useAssistant();
const draft = ref("");
const input = ref(null);
const input_id = `fi-message-${frappe.utils.get_random(6)}`;
const MAX_INPUT_HEIGHT = 168;

const chip = computed(() => (store.context_dismissed ? "" : context_label(store.context)));
const placeholder = computed(() =>
	store.has_pending_proposals
		? __("Reply, or ask for a change to the proposal…")
		: __("Ask about your data, or describe a task…")
);

function on_enter(e) {
	if (e.isComposing) return;
	e.preventDefault();
	submit();
}

function submit() {
	if (store.run || !draft.value.trim()) return;
	store.send(draft.value);
	draft.value = "";
	nextTick(grow);
}

function grow() {
	const el = input.value;
	el.style.height = "auto";
	el.style.height = `${Math.min(el.scrollHeight, MAX_INPUT_HEIGHT)}px`;
}

// Mode menu: Frappe's own menu, rebuilt on every open so the choice shows as selected.
const mode_button = ref(null);
let mode_menu = null;
onMounted(() => {
	const agent_allowed = frappe.boot.fi_assistant.agent_mode;
	mode_menu = new frappe.ui.Dropdown({
		trigger: mode_button.value,
		side: "top",
		align: "start",
		options: () => [
			{
				label: __("Ask"),
				description: __("Reads and explains. Never changes data."),
				selected: store.mode === "Ask",
				onclick: () => (store.mode = "Ask"),
			},
			{
				label: __("Agent"),
				description: agent_allowed
					? __("Prepares changes. You approve each one first.")
					: __("Turned off in AI Settings."),
				selected: store.mode === "Agent",
				disabled: !agent_allowed,
				onclick: () => (store.mode = "Agent"),
			},
		],
	});
});
onBeforeUnmount(() => mode_menu?.destroy());
</script>

<style scoped>
.fi-composer {
	flex: none;
	padding: 8px 16px 12px;
	margin: 0;
}
.fi-chip-row {
	display: flex;
	margin-bottom: 8px;
}
.fi-chip {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	max-width: 100%;
	height: 24px;
	padding-inline: 8px 4px;
	border-radius: var(--radius-full);
	background: var(--surface-gray-2);
	font-size: var(--text-xs);
	color: var(--ink-gray-7);
}
.fi-chip-label {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.fi-chip-remove {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 18px;
	height: 18px;
	padding: 0;
	border: 0;
	border-radius: var(--radius-full);
	background: transparent;
	color: var(--ink-gray-6);
}
.fi-chip-remove:hover {
	background: var(--surface-gray-3);
}
.fi-input {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 10px 10px 8px 12px;
	border-radius: var(--radius-lg);
	box-shadow: inset 0 0 0 1px var(--outline-gray-2);
}
.fi-input:focus-within {
	box-shadow:
		inset 0 0 0 1px var(--outline-gray-3),
		var(--focus-default);
}
textarea {
	width: 100%;
	border: 0;
	padding: 0;
	resize: none;
	background: transparent;
	color: inherit;
	font: inherit;
	outline: none;
	max-height: 168px;
}
textarea::placeholder {
	color: var(--ink-gray-5);
}
.fi-input-actions {
	display: flex;
	align-items: center;
	gap: 2px;
}
.fi-spacer {
	flex: 1;
}
.fi-mode {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	height: 26px;
	padding-inline: 8px 6px;
	border: 0;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
	font-size: var(--text-xs);
	font-weight: 500;
}
.fi-mode:hover,
.fi-mode[aria-expanded="true"] {
	background: var(--surface-gray-3);
}
.fi-mode.agent {
	background: var(--surface-violet-2);
	color: var(--ink-violet-6);
}
.fi-send {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	padding: 0;
	border: 0;
	border-radius: var(--radius-full);
	background: var(--surface-gray-10);
	color: var(--ink-base);
}
.fi-send:disabled {
	background: var(--surface-gray-3);
	color: var(--ink-gray-5);
}
.fi-stop {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 28px;
	padding-inline: 8px 10px;
	border: 0;
	border-radius: var(--radius-full);
	background: var(--surface-gray-10);
	color: var(--ink-base);
	font-size: var(--text-xs);
	font-weight: 500;
}
.fi-disclaimer {
	margin-top: 8px;
	text-align: center;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
</style>
