<template>
	<div class="fi-change" :class="proposal.status" role="status">
		<span class="fi-change-icon" :class="{ 'fi-spin': running }"><Icon :name="icon" /></span>
		<span class="fi-change-title">
			{{ title }}
			<a v-if="link" :href="link" @click.prevent="open">{{ proposal.result }}</a>
		</span>
		<span class="fi-change-meta">{{ meta }}</span>
	</div>
	<div v-if="proposal.error" class="fi-change-error">{{ proposal.error }}</div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({ proposal: { type: Object, required: true } });
const STATES = {
	approved: { icon: "loader-circle", meta: () => __("Confirmed · running") },
	done: { icon: "check", meta: () => __("You confirmed") },
	failed: { icon: "x", meta: () => __("Confirmed, but it did not work") },
	rejected: { icon: "ban", meta: () => __("You rejected") },
};
// A document reading: the user checked the values or set them aside.
const REVIEW_STATES = {
	done: { icon: "check", meta: () => __("You checked the values") },
	rejected: { icon: "ban", meta: () => __("You discarded the values") },
};
const state = computed(() => {
	const states = props.proposal.preview?.kind === "review" ? REVIEW_STATES : STATES;
	return states[props.proposal.status] || states.rejected;
});
const icon = computed(() => state.value.icon);
const meta = computed(() => state.value.meta());
const running = computed(() => props.proposal.status === "approved");
const title = computed(() => props.proposal.preview?.title || "");
const link = computed(() => {
	const { result } = props.proposal;
	const doctype = props.proposal.preview?.doctype;
	return result && doctype ? frappe.utils.get_form_link(doctype, result) : null;
});

function open() {
	frappe.set_route("Form", props.proposal.preview.doctype, props.proposal.result);
}
</script>

<style scoped>
.fi-change {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 10px;
	border-radius: 10px;
	background: var(--surface-gray-1);
	font-size: var(--text-sm);
}
.fi-change-icon {
	display: inline-flex;
	color: var(--ink-gray-6);
}
.fi-change.done .fi-change-icon {
	color: var(--ink-green-6);
}
.fi-change.failed .fi-change-icon {
	color: var(--ink-red-6);
}
.fi-change.approved .fi-change-icon {
	color: var(--ink-violet-6);
}
.fi-change-title {
	flex: 1;
	min-width: 0;
	color: var(--ink-gray-8);
	overflow-wrap: anywhere;
}
.fi-change-title a {
	color: var(--ink-blue-link);
}
.fi-change-meta {
	flex: none;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-change-error {
	padding: 6px 10px;
	border-radius: var(--radius);
	background: var(--surface-red-2);
	color: var(--ink-red-6);
	font-size: var(--text-xs);
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
</style>
