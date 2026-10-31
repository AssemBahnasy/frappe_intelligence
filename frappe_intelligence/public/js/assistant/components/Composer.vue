<template>
	<form class="fi-composer" @submit.prevent="submit">
		<div v-if="chip" class="fi-chip-row">
			<span class="fi-chip">
				<Icon name="file-text" size="xs" />
				<span class="fi-chip-label">{{ chip }}</span>
				<button
					type="button"
					class="fi-chip-remove"
					:aria-label="__('Leave this page out')"
					@click="store.context_dismissed = true"
				>
					<Icon name="x" size="xs" />
				</button>
			</span>
		</div>

		<div class="fi-input">
			<div v-if="files.length" class="fi-files">
				<FileChip
					v-for="file in files"
					:key="file.key"
					:file="file"
					:uploading="file.uploading"
					removable
					@remove="remove_file(file)"
				/>
			</div>
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
				<button
					v-show="!store.workflow"
					ref="mode_button"
					type="button"
					class="fi-mode"
					:class="{ agent: store.mode === 'Agent' }"
				>
					{{ store.mode === "Agent" ? __("Agent") : __("Ask") }}
					<Icon name="chevron-down" size="xs" />
				</button>
				<button
					type="button"
					class="fi-icon-button"
					:disabled="files.length >= MAX_FILES"
					:title="__('Attach a file')"
					:aria-label="__('Attach a file')"
					@click="file_input.click()"
				>
					<Icon name="paperclip" />
				</button>
				<input ref="file_input" type="file" hidden multiple :accept="ACCEPTED_FILES" @change="add_files" />
				<button
					v-if="voice"
					type="button"
					class="fi-icon-button"
					:class="{ recording: listening === 'recording' }"
					:disabled="listening === 'transcribing'"
					:title="voice_label"
					:aria-label="voice_label"
					:aria-pressed="listening === 'recording'"
					@click="toggle_voice"
				>
					<span v-if="listening === 'transcribing'" class="es-spinner" aria-hidden="true"></span>
					<Icon v-else :name="listening === 'recording' ? 'square' : 'mic'" />
				</button>
				<span class="fi-spacer"></span>
				<button v-if="store.run" type="button" class="fi-stop" @click="store.stop()">
					<Icon name="square" size="xs" />
					{{ __("Stop") }}
				</button>
				<button v-else type="submit" class="fi-send" :disabled="!can_send" :aria-label="__('Send')">
					<Icon name="arrow-up" />
				</button>
			</div>
		</div>
		<div class="fi-disclaimer">
			{{
				store.workflow
					? __("Saved after every answer. You can leave and come back.")
					: __("AI can make mistakes. Check important figures.")
			}}
		</div>
	</form>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { context_label } from "../page_context";
import { useAssistant } from "../store";
import { ACCEPTED_FILES, MAX_FILES, upload_file } from "../uploads";
import { Recorder, transcribe } from "../voice";
import FileChip from "./FileChip.vue";
import Icon from "./Icon.vue";

const store = useAssistant();
const draft = ref("");
const input = ref(null);
const input_id = `fi-message-${frappe.utils.get_random(6)}`;
const MAX_INPUT_HEIGHT = 168;

// A workflow does not use the page it is answered on.
const chip = computed(() =>
	store.context_dismissed || store.workflow ? "" : context_label(store.context)
);
const placeholder = computed(() => {
	if (store.workflow) return __("Type your answer…");
	return store.has_pending_proposals
		? __("Reply, or ask for a change to the proposal…")
		: __("Ask about your data, or describe a task…");
});

function on_enter(e) {
	if (e.isComposing) return;
	e.preventDefault();
	submit();
}

function submit() {
	if (store.run || !can_send.value) return;
	store.send(
		draft.value,
		files.value.map(({ file_url, file_name }) => ({ file_url, file_name }))
	);
	draft.value = "";
	files.value = [];
	nextTick(grow);
}

// Files upload as soon as they are chosen, so sending does not wait for them.
const files = ref([]);
const file_input = ref(null);
const can_send = computed(
	() => !files.value.some((f) => f.uploading) && (draft.value.trim() || files.value.length)
);

function add_files(e) {
	const chosen = [...e.target.files].slice(0, MAX_FILES - files.value.length);
	e.target.value = "";
	for (const file of chosen) {
		const entry = reactive({ key: frappe.utils.get_random(6), file_name: file.name, uploading: true });
		files.value.push(entry);
		upload_file(file)
			.then((uploaded) => Object.assign(entry, uploaded, { uploading: false }))
			.catch((error) => {
				remove_file(entry);
				frappe.show_alert({ message: error.message, indicator: "red" });
			});
	}
}

function remove_file(entry) {
	files.value = files.value.filter((f) => f !== entry);
}

function grow() {
	const el = input.value;
	el.style.height = "auto";
	el.style.height = `${Math.min(el.scrollHeight, MAX_INPUT_HEIGHT)}px`;
}

// Voice input: the text goes into the box to be checked before sending.
const voice = frappe.boot.fi_assistant.voice;
const listening = ref(""); // "", "recording" or "transcribing"
let recorder = null;
const voice_label = computed(() => {
	if (listening.value === "recording") return __("Stop recording");
	if (listening.value === "transcribing") return __("Turning your recording into text…");
	return voice.language ? __("Voice input ({0})", [voice.language]) : __("Voice input");
});

async function toggle_voice() {
	if (listening.value === "recording") return finish_recording();
	recorder = new Recorder();
	try {
		await recorder.start();
		listening.value = "recording";
	} catch (e) {
		voice_failed(e);
	}
}

async function finish_recording() {
	listening.value = "transcribing";
	try {
		const text = await transcribe(await recorder.stop());
		if (!text) throw new Error(__("No speech was heard. Please try again."));
		draft.value = [draft.value.trim(), text].filter(Boolean).join(" ");
		await nextTick();
		grow();
		input.value.focus();
	} catch (e) {
		voice_failed(e);
	} finally {
		listening.value = "";
	}
}

function voice_failed(e) {
	recorder?.release();
	frappe.show_alert({
		message: e.message || __("The recording could not be turned into text."),
		indicator: "red",
	});
}
onBeforeUnmount(() => recorder?.release());

// Mode menu: Frappe's own menu, rebuilt on every open so the choice shows as selected.
const mode_button = ref(null);
let mode_menu = null;
onMounted(() => {
	const agent_allowed = frappe.boot.fi_assistant.agent_mode;
	const workflows = frappe.boot.fi_assistant.workflows || [];
	mode_menu = new frappe.ui.Dropdown({
		trigger: mode_button.value,
		side: "top",
		align: "start",
		options: () => [
			{
				group: "",
				hide_label: true,
				options: modes(agent_allowed),
			},
			{
				group: "",
				hide_label: true,
				options: workflows.length
					? [
							{
								label: __("Start a guided workflow"),
								icon: "route",
								submenu: workflows.map((w) => ({
									label: w.title,
									description: __("{0} steps", [w.steps]),
									onclick: () => store.start_workflow(w.name),
								})),
							},
					  ]
					: [],
			},
		],
	});
});
onBeforeUnmount(() => mode_menu?.destroy());

function modes(agent_allowed) {
	return [
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
	];
}
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
.fi-files {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
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
.fi-icon-button:hover:not(:disabled) {
	background: var(--surface-gray-2);
}
.fi-icon-button:disabled {
	opacity: 0.5;
}
.fi-icon-button.recording,
.fi-icon-button.recording:hover:not(:disabled) {
	background: var(--surface-red-2);
	color: var(--ink-red-6);
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
