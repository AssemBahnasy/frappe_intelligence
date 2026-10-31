<template>
	<div class="fi-empty">
		<div class="fi-empty-intro">
			<div class="fi-empty-badge"><Icon name="sparkles" size="md" /></div>
			<div class="fi-empty-title">{{ greeting }}</div>
			<div class="fi-empty-text">
				{{ __("I can look up your records, run reports and explain any screen.") }}
			</div>
		</div>

		<section v-for="group in groups" :key="group.label" class="fi-group">
			<div class="fi-group-label">{{ group.label }}</div>
			<button
				v-for="prompt in group.prompts"
				:key="prompt"
				class="fi-suggestion"
				dir="auto"
				@click="emit('send', prompt)"
			>
				<Icon name="search" />
				{{ prompt }}
			</button>
		</section>

		<section v-if="workflows.length" class="fi-group">
			<div class="fi-group-label">{{ __("Guided workflows") }}</div>
			<button
				v-for="workflow in workflows"
				:key="workflow.name"
				class="fi-suggestion"
				dir="auto"
				@click="store.start_workflow(workflow.name)"
			>
				<Icon name="route" />
				<span class="fi-suggestion-label">{{ workflow.title }}</span>
				<span class="fi-suggestion-meta">{{ __("{0} steps", [workflow.steps]) }}</span>
			</button>
		</section>
	</div>
</template>

<script setup>
import { useAssistant } from "../store";
import Icon from "./Icon.vue";

const WORKFLOW_LIMIT = 3; // the rest are in the mode menu

const emit = defineEmits(["send"]);
const store = useAssistant();
const groups = frappe.boot.fi_assistant.suggestions;
const workflows = (frappe.boot.fi_assistant.workflows || []).slice(0, WORKFLOW_LIMIT);
const first_name = (frappe.session.user_fullname || "").split(" ")[0];
const greeting = first_name ? __("How can I help, {0}?", [first_name]) : __("How can I help?");
</script>

<style scoped>
.fi-empty {
	flex: 1;
	min-height: 0;
	overflow-y: auto;
	padding: 28px 16px 16px;
	display: flex;
	flex-direction: column;
	gap: 22px;
}
.fi-empty-intro {
	display: flex;
	flex-direction: column;
	align-items: center;
	text-align: center;
	gap: 8px;
}
.fi-empty-badge {
	width: 44px;
	height: 44px;
	border-radius: var(--radius-full);
	background: var(--surface-violet-2);
	color: var(--ink-violet-6);
	display: flex;
	align-items: center;
	justify-content: center;
}
.fi-empty-title {
	font-size: var(--text-lg);
	font-weight: 600;
	color: var(--ink-gray-9);
}
.fi-empty-text {
	max-width: 300px;
	font-size: var(--text-sm);
	color: var(--ink-gray-6);
}
.fi-group {
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.fi-group-label {
	font-size: 11px;
	font-weight: 500;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--ink-gray-6);
	margin-inline-start: 2px;
}
.fi-suggestion {
	display: flex;
	align-items: center;
	gap: 10px;
	width: 100%;
	text-align: start;
	padding: 10px 12px;
	border: 0;
	border-radius: 10px;
	background: var(--surface-gray-1);
	box-shadow: inset 0 0 0 1px var(--outline-gray-1);
	color: var(--ink-gray-8);
	font-size: var(--text-sm);
}
.fi-suggestion:hover {
	background: var(--surface-gray-2);
}
.fi-suggestion .fi-icon {
	color: var(--ink-gray-6);
}
.fi-suggestion-label {
	flex: 1;
	min-width: 0;
}
.fi-suggestion-meta {
	flex: none;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
</style>
