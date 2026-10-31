<template>
	<Card
		:label="__('Values read from {0}', [card.document])"
		:note="__('Your edits are used, and kept to improve future reads.')"
	>
		<template #header>
			<span class="fi-card-title">{{ card.title }}</span>
			<span class="fi-card-meta">{{ __("{0} of {1} fields found", [found, card.fields.length]) }}</span>
			<span v-if="card.needs_review" class="fi-badge">{{ __("Review needed") }}</span>
		</template>
		<div class="fi-card-fields">
			<div v-for="field in card.fields" :key="field.key" class="fi-row">
				<label :for="`${id}-${field.key}`">{{ field.label }}</label>
				<input
					:id="`${id}-${field.key}`"
					v-model="values[field.key]"
					class="fi-field"
					:class="{ missing: !field.value && !values[field.key] }"
					dir="auto"
					:placeholder="field.value ? '' : __('Not found — enter or leave blank')"
				/>
			</div>
		</div>
		<template #actions>
			<button type="button" class="fi-button subtle" :disabled="deciding" @click="decide(false)">
				{{ __("Discard") }}
			</button>
			<button type="button" class="fi-button solid" :disabled="deciding" @click="decide(true)">
				{{ __("Use these values") }}
			</button>
		</template>
	</Card>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { useAssistant } from "../store";
import Card from "./Card.vue";

const props = defineProps({
	turn: { type: Object, required: true },
	proposal: { type: Object, required: true },
});
const store = useAssistant();
const card = computed(() => props.proposal.preview);
const id = `fi-review-${frappe.utils.get_random(6)}`;
const values = reactive(Object.fromEntries(card.value.fields.map((f) => [f.key, f.value])));
const found = computed(() => card.value.fields.filter((f) => f.value).length);
const deciding = ref(false);

async function decide(approve) {
	deciding.value = true;
	try {
		await store.decide(props.turn, props.proposal, approve, approve ? { ...values } : null);
	} finally {
		deciding.value = false;
	}
}
</script>

<style scoped>
.fi-card-fields {
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 12px;
}
.fi-row {
	display: grid;
	grid-template-columns: minmax(96px, 35%) minmax(0, 1fr);
	align-items: center;
	gap: 10px;
	font-size: var(--text-sm);
}
.fi-row label {
	margin: 0;
	font-weight: 400;
	color: var(--ink-gray-6);
}
.fi-field {
	width: 100%;
	height: 28px;
	padding-inline: 8px;
	border: 0;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-9);
	font: inherit;
	font-size: var(--text-sm);
}
.fi-field:focus {
	outline: none;
	box-shadow: var(--focus-default);
}
.fi-field.missing {
	background: var(--surface-amber-2);
	box-shadow: inset 0 0 0 1px var(--outline-amber-3);
}
.fi-field::placeholder {
	color: var(--ink-gray-5);
}
</style>
