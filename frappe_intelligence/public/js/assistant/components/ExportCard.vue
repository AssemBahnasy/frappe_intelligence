<template>
	<FileCard
		:label="__('Report export')"
		icon="file-spreadsheet"
		:title="__(action.report_name)"
		:meta="rows"
		:note="note"
		:format="action.file_format || 'Excel'"
		:deliver="deliver"
		:email="emailing"
	>
		<template #fields>
			<template v-for="filter in filters" :key="filter.label">
				<dt>{{ filter.label }}</dt>
				<dd dir="auto">{{ filter.value }}</dd>
			</template>
		</template>
		<template #start>
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
		</template>
		<template #end>
			<button type="button" class="fi-button subtle" @click="open_report(action)">
				{{ __("Open report") }}
			</button>
		</template>
	</FileCard>
</template>

<script setup>
// A report the agent offered (agent/tools/reports.py: export_report); docs/panel/exports.md.
import { computed } from "vue";
import {
	download_report,
	email_report,
	filter_rows,
	open_report,
	print_report,
	row_count,
} from "../exports";
import FileCard from "./FileCard.vue";
import Icon from "./Icon.vue";

const props = defineProps({ action: { type: Object, required: true } });
const emailing = props.action.delivery === "email";
// A file to take: the user has the Export right (cards from before Print had no "print" delivery).
const deliver = ["download", "email"].includes(props.action.delivery)
	? (file_format) => (emailing ? email_report : download_report)(props.action, file_format)
	: null;

const filters = computed(() => filter_rows(props.action.filters));
const rows = computed(() => row_count(props.action.rows));
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
</script>
