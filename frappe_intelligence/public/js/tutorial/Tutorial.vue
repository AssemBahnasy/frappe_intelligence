<template>
	<div v-if="!store.assistant" class="fi-tutorial-empty">
		{{ __("The assistant is not available to you. Ask your administrator for access.") }}
	</div>
	<div v-else class="fi-tutorial">
		<TopicNav />
		<TopicView v-if="store.current" :topic="store.current" />
	</div>
</template>

<script setup>
import TopicNav from "./components/TopicNav.vue";
import TopicView from "./components/TopicView.vue";
import { useTutorial } from "./store";

const store = useTutorial();
</script>

<style scoped>
.fi-tutorial {
	container: fi-tutorial / inline-size;
	display: flex;
	flex-wrap: wrap;
	align-items: flex-start;
	background: var(--surface-base);
	min-height: 70vh;
}
.fi-tutorial-empty {
	padding: var(--padding-xl);
	color: var(--ink-gray-6);
	text-align: center;
}
</style>

<style>
/* The tour's popover is outside the app: "Read a document · 1 of 4" above the step title. */
.frappe-driver .fi-tour-where {
	display: block;
	margin-bottom: 4px;
	font-size: var(--text-xs);
	font-weight: 500;
	color: var(--ink-gray-6);
}
</style>
