<template>
	<ul v-if="pending && steps.length" class="fi-steps" role="status">
		<li
			v-for="(step, i) in steps"
			:key="step.call_id || i"
			class="fi-step"
			:class="step.status"
		>
			<span class="fi-step-icon" :class="{ 'fi-spin': step.status === 'running' }">
				<Icon :name="ICONS[step.status]" />
			</span>
			{{ step.label }}
		</li>
	</ul>

	<div v-else-if="steps.length" class="fi-steps-done">
		<button class="fi-steps-toggle" :aria-expanded="open" @click="open = !open">
			<span class="fi-step-icon" :class="failed ? 'failed' : 'done'">
				<Icon :name="failed ? 'x' : 'check'" />
			</span>
			<span class="fi-steps-summary">{{ summary }}</span>
			<Icon :name="open ? 'chevron-up' : 'chevron-down'" size="xs" />
		</button>
		<ul v-if="open" class="fi-steps">
			<li v-for="(step, i) in steps" :key="i" class="fi-step" :class="step.status">
				<span class="fi-step-icon"><Icon :name="ICONS[step.status]" /></span>
				{{ step.label }}
			</li>
		</ul>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
	steps: { type: Array, required: true },
	pending: { type: Boolean, default: false },
});
const ICONS = { running: "loader-circle", done: "check", failed: "x", stopped: "square" };
const open = ref(false);
const failed = computed(() => props.steps.some((s) => s.status === "failed"));

// "Reading Customer list · Counting Customer · 3 steps"
const summary = computed(() => {
	const labels = [...new Set(props.steps.map((s) => s.label))].slice(0, 2);
	const count = props.steps.length;
	return [...labels, count === 1 ? __("1 step") : __("{0} steps", [count])].join(" · ");
});
</script>

<style scoped>
.fi-steps {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.fi-step {
	display: flex;
	align-items: center;
	gap: 8px;
	min-height: 24px;
	font-size: var(--text-sm);
	color: var(--ink-gray-7);
}
.fi-step.running {
	color: var(--ink-gray-9);
}
.fi-step-icon {
	display: inline-flex;
	color: var(--ink-green-6);
}
.fi-step.running .fi-step-icon {
	color: var(--ink-violet-6);
}
.fi-step.failed .fi-step-icon,
.fi-step-icon.failed {
	color: var(--ink-red-6);
}
.fi-step.stopped .fi-step-icon {
	color: var(--ink-gray-5);
}
.fi-spin {
	animation: fi-spin 1s linear infinite;
}
@keyframes fi-spin {
	to {
		transform: rotate(360deg);
	}
}
@media (prefers-reduced-motion: reduce) {
	.fi-spin {
		animation: none;
	}
}
.fi-steps-done {
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.fi-steps-toggle {
	align-self: flex-start;
	display: inline-flex;
	align-items: center;
	gap: 6px;
	max-width: 100%;
	height: 24px;
	padding-inline: 2px 6px;
	border: 0;
	border-radius: var(--radius);
	background: transparent;
	color: var(--ink-gray-6);
	font-size: var(--text-xs);
}
.fi-steps-toggle:hover {
	background: var(--surface-gray-2);
}
.fi-steps-summary {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
</style>
