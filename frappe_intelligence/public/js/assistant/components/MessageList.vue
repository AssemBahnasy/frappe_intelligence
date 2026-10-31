<template>
	<div ref="list" class="fi-messages" aria-live="polite">
		<div v-if="store.loading" class="fi-loading"><span class="es-spinner" role="status"></span></div>
		<Turn v-for="turn in store.turns" :key="turn.id" :turn="turn" />
		<div v-if="choices.length" class="fi-choices">
			<button v-for="choice in choices" :key="choice" class="fi-choice" dir="auto" @click="store.send(choice)">
				{{ choice }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { useAssistant } from "../store";
import Turn from "./Turn.vue";

const store = useAssistant();
const list = ref(null);
const STICK_DISTANCE = 80;

// A workflow's quick replies for the field it asks next (workflows/desk.py).
const choices = computed(() => (store.run ? [] : store.workflow?.choices || []));

// Follow the answer as it grows, unless the user has scrolled up to read.
let stick = true;
watch(
	() =>
		store.turns
			.map((t) => {
				const proposals = (t.proposals || []).map((p) => p.status).join("|");
				return `${t.id}:${(t.answer || "").length}:${t.steps.length}:${proposals}:${(t.report || "").length}:${t.pending}`;
			})
			.join() + `:${choices.value.length}`,
	async (now, before) => {
		const el = list.value;
		if (!el) return;
		const opened = !before || now.split(",")[0] !== before.split(",")[0];
		stick = opened || el.scrollHeight - el.scrollTop - el.clientHeight < STICK_DISTANCE;
		await nextTick();
		if (stick) el.scrollTop = el.scrollHeight;
	},
	{ flush: "pre" }
);
</script>

<style scoped>
.fi-messages {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
	padding: 16px;
	display: flex;
	flex-direction: column;
	gap: 14px;
}
.fi-choices {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}
.fi-choice {
	height: 26px;
	padding: 0 10px;
	border: 0;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
	font-size: var(--text-xs);
}
.fi-choice:hover {
	background: var(--surface-gray-3);
}
.fi-loading {
	display: flex;
	justify-content: center;
	padding: 24px;
	color: var(--ink-gray-5);
}
</style>
