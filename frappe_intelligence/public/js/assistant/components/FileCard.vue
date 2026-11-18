<template>
	<Card :label="label" :note="false">
		<template #header>
			<Icon :name="icon" />
			<span class="fi-card-title" dir="auto">{{ title }}</span>
			<span v-if="meta" class="fi-card-meta">{{ meta }}</span>
		</template>
		<dl class="fi-card-fields">
			<slot name="fields" />
			<template v-if="deliver">
				<dt class="fi-format-label">{{ __("Format") }}</dt>
				<dd>
					<div class="fi-format" role="group" :aria-label="__('Format')">
						<button
							v-for="option in FORMATS"
							:key="option"
							type="button"
							:aria-pressed="file_format === option"
							@click="file_format = option"
						>
							{{ option }}
						</button>
					</div>
				</dd>
			</template>
		</dl>
		<div class="fi-file-note">
			<span v-if="done_note" class="fi-file-done">
				<Icon name="check" size="xs" />{{ done_note }}
			</span>
			<slot v-else name="note">{{ note }}</slot>
		</div>
		<div v-if="error" class="fi-file-error" role="alert">{{ error }}</div>
		<template #actions>
			<slot name="start" />
			<span class="fi-file-spacer"></span>
			<slot name="end" />
			<button
				v-if="deliver"
				type="button"
				class="fi-button"
				:class="done_note ? 'subtle' : 'solid'"
				:disabled="busy"
				@click="run"
			>
				<span :class="{ 'fi-spin': busy }"><Icon :name="button.icon" size="xs" /></span>
				{{ button.label }}
			</button>
		</template>
	</Card>
</template>

<script setup>
// The frame of a card that hands the user a file (ExportCard, SheetCard): the fields, the format,
// a note, and Download (or Email it to me) with its progress, result and error.
import { computed, ref } from "vue";
import Card from "./Card.vue";
import Icon from "./Icon.vue";

const props = defineProps({
	label: { type: String, required: true },
	icon: { type: String, required: true },
	title: { type: String, required: true },
	meta: { type: String, default: "" },
	note: { type: String, default: "" },
	format: { type: String, default: "Excel" },
	// (file_format) => Promise; none: no format and no Download.
	deliver: { type: Function, default: null },
	// Frappe emails the file instead of the browser downloading it.
	email: { type: Boolean, default: false },
});
const FORMATS = ["Excel", "CSV"];
const file_format = ref(props.format);
const busy = ref(false);
const done_at = ref("");
const error = ref("");

const done_note = computed(() => {
	if (!done_at.value) return "";
	return props.email
		? __("Frappe is emailing you a link")
		: __("Downloaded at {0}", [done_at.value]);
});
const button = computed(() => {
	if (busy.value) return { icon: "loader-circle", label: __("Preparing…") };
	if (props.email) return { icon: "mail", label: __("Email it to me") };
	if (done_at.value) return { icon: "download", label: __("Download again") };
	return { icon: "download", label: __("Download") };
});

async function run() {
	busy.value = true;
	error.value = "";
	try {
		await props.deliver(file_format.value);
		done_at.value = new Date().toLocaleTimeString(frappe.boot.lang, {
			hour: "2-digit",
			minute: "2-digit",
		});
	} catch (e) {
		error.value = e.message || __("The export did not work.");
	} finally {
		busy.value = false;
	}
}
</script>

<style scoped>
.fi-card-fields {
	display: grid;
	grid-template-columns: minmax(96px, 35%) minmax(0, 1fr);
	gap: 6px 12px;
	margin: 0;
	padding: 12px;
	font-size: var(--text-sm);
}
.fi-card-fields :slotted(dt),
.fi-card-fields dt {
	font-weight: 400;
	color: var(--ink-gray-6);
}
.fi-card-fields :slotted(dd),
.fi-card-fields dd {
	margin: 0;
	color: var(--ink-gray-8);
	overflow-wrap: anywhere;
}
.fi-format-label {
	align-self: center;
}
.fi-format {
	display: inline-flex;
	padding: 2px;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
}
.fi-format button {
	height: 24px;
	padding-inline: 12px;
	border: 0;
	border-radius: var(--radius-sm);
	background: transparent;
	font-size: var(--text-xs);
	font-weight: 500;
	color: var(--ink-gray-7);
}
.fi-format button[aria-pressed="true"] {
	/* white on the light theme's grey track, a lighter grey on the dark one */
	background: var(--surface-elevation-3);
	box-shadow: var(--shadow-sm), inset 0 0 0 1px var(--outline-gray-3);
	color: var(--ink-gray-9);
}
.fi-file-note {
	padding: 0 12px 12px;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-file-done {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.fi-file-done :deep(.fi-icon) {
	color: var(--ink-green-6);
}
.fi-file-spacer {
	flex: 1;
}
.fi-file-error {
	margin: 0 12px 12px;
	padding: 6px 10px;
	border-radius: var(--radius);
	background: var(--surface-red-2);
	color: var(--ink-red-6);
	font-size: var(--text-xs);
}
.fi-spin {
	display: inline-flex;
	animation: fi-spin 1s linear infinite;
}
@keyframes fi-spin {
	to {
		transform: rotate(360deg);
	}
}
@media (prefers-reduced-motion: reduce) {
	.fi-spin {
		animation: none;
	}
}
</style>
