<template>
	<FileCard
		:label="__('Sheet')"
		icon="sheet"
		:title="action.title"
		:meta="row_count(action.row_count)"
		:format="action.file_format || 'Excel'"
		:deliver="(file_format) => download_sheet(action, file_format)"
	>
		<template #fields>
			<dt>{{ __("Built from") }}</dt>
			<dd>{{ action.built_from.map((doctype) => __(doctype)).join(", ") }}</dd>
			<dt>{{ __("Columns") }}</dt>
			<dd dir="auto">{{ action.columns.join(", ") }}</dd>
		</template>
		<template #note>
			<span class="fi-sheet-note">
				<Icon name="info" size="xs" />
				{{
					__(
						"Compiled by the assistant, not by a report: the rows above. AI can make mistakes. Check important figures."
					)
				}}
			</span>
		</template>
	</FileCard>
</template>

<script setup>
// A sheet the agent compiled (agent/tools/sheets.py: export_sheet); docs/panel/sheets.md.
import { download_sheet, row_count } from "../exports";
import FileCard from "./FileCard.vue";
import Icon from "./Icon.vue";

defineProps({ action: { type: Object, required: true } });
</script>

<style scoped>
.fi-sheet-note {
	display: inline-flex;
	align-items: flex-start;
	gap: 6px;
}
.fi-sheet-note :deep(.fi-icon) {
	margin-top: 2px;
}
</style>
