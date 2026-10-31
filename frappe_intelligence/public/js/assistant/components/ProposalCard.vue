<template>
	<section class="fi-card" :aria-label="__('Proposed change')">
		<header class="fi-card-header">
			<Icon :name="ICONS[preview.action] || 'pen'" />
			<span class="fi-card-title">{{ preview.title }}</span>
			<span class="fi-badge">{{ __("Needs approval") }}</span>
		</header>
		<dl v-if="preview.fields?.length" class="fi-card-fields">
			<template v-for="field in preview.fields" :key="field.label">
				<dt>{{ field.label }}</dt>
				<dd dir="auto">{{ field.value }}</dd>
			</template>
		</dl>
		<footer class="fi-card-footer">
			<span class="fi-card-note">{{ preview.note }}</span>
			<button type="button" class="fi-button subtle" :disabled="deciding" @click="decide(false)">
				{{ __("Reject") }}
			</button>
			<button type="button" class="fi-button solid" :disabled="deciding" @click="decide(true)">
				<Icon name="check" size="xs" />
				{{ __("Confirm") }}
			</button>
		</footer>
	</section>
</template>

<script setup>
import { computed, ref } from "vue";
import { useAssistant } from "../store";
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
.fi-card {
	border-radius: var(--radius-lg);
	background: var(--surface-elevation-1);
	box-shadow: inset 0 0 0 1px var(--outline-gray-2);
	overflow: hidden;
}
.fi-card-header {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border-bottom: 1px solid var(--outline-gray-1);
	color: var(--ink-gray-7);
}
.fi-card-title {
	flex: 1;
	min-width: 0;
	font-weight: 600;
	font-size: var(--text-sm);
	color: var(--ink-gray-9);
}
.fi-badge {
	flex: none;
	font-size: 11px;
	font-weight: 500;
	padding: 1px 8px;
	border-radius: var(--radius-full);
	background: var(--surface-amber-2);
	color: var(--ink-amber-7);
}
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
.fi-card-footer {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 10px 12px;
	border-top: 1px solid var(--outline-gray-1);
	background: var(--surface-gray-1);
}
.fi-card-note {
	flex: 1;
	min-width: 0;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-button {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	height: 28px;
	padding-inline: 10px;
	border: 0;
	border-radius: var(--radius);
	font-size: var(--text-sm);
	font-weight: 500;
	white-space: nowrap;
}
.fi-button.subtle {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
.fi-button.solid {
	background: var(--surface-gray-10);
	color: var(--ink-base);
}
.fi-button:disabled {
	opacity: 0.6;
}
</style>
