<template>
	<div ref="list" class="fi-messages" aria-live="polite">
		<div v-if="store.loading" class="fi-loading"><span class="es-spinner" role="status"></span></div>
		<Turn v-for="turn in store.turns" :key="turn.id" :turn="turn" />
	</div>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";
import { useAssistant } from "../store";
import Turn from "./Turn.vue";

const store = useAssistant();
const list = ref(null);
const STICK_DISTANCE = 80;

// Follow the answer as it grows, unless the user has scrolled up to read.
let stick = true;
watch(
	() => store.turns.map((t) => `${t.id}:${(t.answer || "").length}:${t.steps.length}:${t.pending}`).join(),
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
.fi-loading {
	display: flex;
	justify-content: center;
	padding: 24px;
	color: var(--ink-gray-5);
}
</style>
