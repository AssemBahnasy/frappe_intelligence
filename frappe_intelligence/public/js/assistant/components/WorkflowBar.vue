<template>
	<section class="fi-workflow" :aria-label="__('Guided workflow')">
		<div class="fi-workflow-head">
			<span class="fi-workflow-icon"><Icon name="route" /></span>
			<span class="fi-workflow-title" dir="auto">{{ workflow.title }}</span>
			<span class="fi-workflow-meta">{{ where }}</span>
			<button
				class="fi-workflow-exit"
				:disabled="!!store.run"
				@click="store.exit_workflow()"
			>
				{{ __("Exit") }}
			</button>
		</div>

		<div
			v-if="workflow.steps"
			class="fi-workflow-progress"
			role="progressbar"
			:aria-label="__('Workflow progress')"
			aria-valuemin="0"
			:aria-valuemax="workflow.steps"
			:aria-valuenow="done"
			:style="{ gridTemplateColumns: `repeat(${workflow.steps}, minmax(0, 1fr))` }"
		>
			<span
				v-for="n in workflow.steps"
				:key="n"
				class="fi-workflow-segment"
				:class="{ done: n <= done, current: n === workflow.step }"
			></span>
		</div>

		<div v-if="workflow.answers.length || workflow.missing.length" class="fi-workflow-chips">
			<span
				v-for="(answer, i) in workflow.answers"
				:key="i"
				class="fi-workflow-chip"
				dir="auto"
				:title="`${answer.label}: ${answer.value}`"
			>
				<Icon name="check" size="xs" />
				<span class="fi-workflow-chip-text">{{ answer.value }}</span>
			</span>
			<span
				v-for="label in workflow.missing"
				:key="label"
				class="fi-workflow-chip missing"
				dir="auto"
			>
				{{ label }}
			</span>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue";
import { useAssistant } from "../store";
import Icon from "./Icon.vue";

const store = useAssistant();
const workflow = computed(() => store.workflow);
const done = computed(() =>
	workflow.value.status === "Completed" ? workflow.value.steps : (workflow.value.step || 1) - 1
);
const where = computed(() => {
	const w = workflow.value;
	if (w.status === "Completed") return __("All {0} steps done", [w.steps]);
	if (w.status === "Abandoned" || !w.step) return __("Ended");
	return __("Step {0} of {1} · {2}", [w.step, w.steps, w.step_label]);
});
</script>

<style scoped>
.fi-workflow {
	flex: none;
	display: flex;
	flex-direction: column;
	gap: 10px;
	padding: 12px 16px;
	border-bottom: 1px solid var(--outline-gray-1);
	background: var(--surface-gray-1);
}
.fi-workflow-head {
	display: flex;
	align-items: center;
	gap: 8px;
	min-width: 0;
}
.fi-workflow-icon {
	display: inline-flex;
	color: var(--ink-violet-6);
}
.fi-workflow-title {
	flex: 1;
	min-width: 0;
	font-size: var(--text-sm);
	font-weight: 600;
	color: var(--ink-gray-9);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.fi-workflow-meta {
	flex: none;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-workflow-exit {
	flex: none;
	height: 24px;
	padding: 0 8px;
	border: 0;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
	font-size: var(--text-xs);
	font-weight: 500;
}
.fi-workflow-exit:hover:not(:disabled) {
	background: var(--surface-gray-3);
}
.fi-workflow-exit:disabled {
	opacity: 0.5;
}
.fi-workflow-progress {
	display: grid;
	gap: 4px;
}
.fi-workflow-segment {
	height: 4px;
	border-radius: var(--radius-full);
	background: var(--surface-gray-3);
}
.fi-workflow-segment.done {
	background: var(--ink-violet-6);
}
.fi-workflow-segment.current {
	background: var(--ink-violet-6);
	opacity: 0.45;
}
.fi-workflow-chips {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}
.fi-workflow-chip {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	max-width: 100%;
	height: 24px;
	padding: 0 8px;
	border-radius: var(--radius-full);
	background: var(--surface-base);
	box-shadow: inset 0 0 0 1px var(--outline-gray-2);
	font-size: var(--text-xs);
	color: var(--ink-gray-8);
}
.fi-workflow-chip .fi-icon {
	color: var(--ink-green-7);
}
.fi-workflow-chip-text {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.fi-workflow-chip.missing {
	background: transparent;
	box-shadow: none;
	border: 1px dashed var(--outline-gray-2);
	color: var(--ink-gray-6);
}
</style>
