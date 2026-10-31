<template>
	<Card :label="__('Proposed change')" :note="preview.note">
		<template #header>
			<Icon :name="ICONS[preview.action] || 'pen'" />
			<span class="fi-card-title">{{ preview.title }}</span>
			<span class="fi-badge">{{ __("Needs approval") }}</span>
		</template>
		<dl v-if="preview.fields?.length" class="fi-card-fields">
			<template v-for="field in preview.fields" :key="field.label">
				<dt>{{ field.label }}</dt>
				<dd dir="auto">{{ field.value }}</dd>
			</template>
		</dl>
		<template #actions>
			<button type="button" class="fi-button subtle" :disabled="deciding" @click="decide(false)">
				{{ __("Reject") }}
			</button>
			<button type="button" class="fi-button solid" :disabled="deciding" @click="decide(true)">
				<Icon name="check" size="xs" />
				{{ __("Confirm") }}
			</button>
		</template>
	</Card>
</template>

<script setup>
import { computed, ref } from "vue";
import { useAssistant } from "../store";
import Card from "./Card.vue";
import Icon from "./Icon.vue";

const props = defineProps({
	turn: { type: Object, required: true },
	proposal: { type: Object, required: true },
});
const ICONS = { create: "plus", update: "pen", delete: "trash-2", submit: "file-check", cancel: "file-x" };
const store = useAssistant();
const deciding = ref(false);
const preview = computed(() => props.proposal.preview || {});

async function decide(approve) {
	deciding.value = true;
	try {
		await store.decide(props.turn, props.proposal, approve);
	} finally {
		deciding.value = false;
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
	color: var(--ink-gray-9);
	overflow-wrap: anywhere;
}
</style>
