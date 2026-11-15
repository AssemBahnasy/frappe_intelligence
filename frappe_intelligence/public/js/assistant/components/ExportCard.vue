<template>
	<Card :label="__('Report export')" :note="false">
		<template #header>
			<Icon name="file-spreadsheet" />
			<span class="fi-card-title" dir="auto">{{ __(action.report_name) }}</span>
			<span v-if="rows" class="fi-card-meta">{{ rows }}</span>
		</template>
		<dl class="fi-card-fields">
			<template v-for="filter in filters" :key="filter.label">
				<dt>{{ filter.label }}</dt>
				<dd dir="auto">{{ filter.value }}</dd>
			</template>
			<template v-if="downloads">
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
		<div class="fi-export-note">
			<span v-if="done_note" class="fi-export-done">
				<Icon name="check" size="xs" />{{ done_note }}
			</span>
			<template v-else>{{ note }}</template>
		</div>
		<div v-if="error" class="fi-export-error" role="alert">{{ error }}</div>
		<template #actions>
			<template v-if="action.can_print">
				<button
					type="button"
					class="fi-button subtle"
					@click="print_report(action, 'Print')"
				>
					<Icon name="printer" size="xs" />{{ __("Print") }}
				</button>
				<button
					type="button"
					class="fi-button subtle"
					@click="print_report(action, 'PDF')"
				>
					<Icon name="file-text" size="xs" />{{ __("PDF") }}
				</button>
			</template>
			<span class="fi-export-spacer"></span>
			<button type="button" class="fi-button subtle" @click="open_report(action)">
				{{ __("Open report") }}
			</button>
			<button
				v-if="downloads"
				type="button"
				class="fi-button"
				:class="done_note ? 'subtle' : 'solid'"
				:disabled="busy"
				@click="deliver"
			>
				<span :class="{ 'fi-spin': busy }"><Icon :name="button.icon" size="xs" /></span>
				{{ button.label }}
			</button>
		</template>
	</Card>
</template>

<script setup>
import { computed, ref } from "vue";
import { download_report, email_report, filter_rows, open_report, print_report } from "../exports";
import Card from "./Card.vue";
import Icon from "./Icon.vue";

const props = defineProps({ action: { type: Object, required: true } });
const FORMATS = ["Excel", "CSV"];
const file_format = ref(props.action.file_format || "Excel");
const busy = ref(false);
const done_at = ref("");
const error = ref("");
const emailing = props.action.delivery === "email";
// A file to take: the user has the Export right (cards from before Print had no "print" delivery).
const downloads = ["download", "email"].includes(props.action.delivery);

const filters = computed(() => filter_rows(props.action.filters));
const rows = computed(() => {
	const count = props.action.rows;
	if (count == null) return "";
	return count === 1 ? __("1 row") : __("{0} rows", [format_number(count, null, 0)]);
});
const note = computed(() => {
	const { delivery, can_print } = props.action;
	if (delivery === "open") return __("Prepared in the background: open it and use Export there");
	if (delivery === "print")
		return __("Frappe's own Print and PDF, run again with these filters");
	if (emailing) return __("Too big to wait for: Frappe emails you a link");
	return can_print
		? __("Frappe's own Export, Print and PDF, run again with these filters")
		: __("Frappe's own Export, run again with these filters");
});
const done_note = computed(() => {
	if (!done_at.value) return "";
	return emailing
		? __("Frappe is emailing you a link")
		: __("Downloaded at {0}", [done_at.value]);
});
const button = computed(() => {
	if (busy.value) return { icon: "loader-circle", label: __("Preparing…") };
	if (emailing) return { icon: "mail", label: __("Email it to me") };
	if (done_at.value) return { icon: "download", label: __("Download again") };
	return { icon: "download", label: __("Download") };
});

async function deliver() {
	busy.value = true;
	error.value = "";
	try {
		await (emailing ? email_report : download_report)(props.action, file_format.value);
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
.fi-card-fields dt {
	font-weight: 400;
	color: var(--ink-gray-6);
}
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
.fi-export-note {
	padding: 0 12px 12px;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-export-done {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}
.fi-export-spacer {
	flex: 1;
}
.fi-export-done :deep(.fi-icon) {
	color: var(--ink-green-6);
}
.fi-export-error {
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
