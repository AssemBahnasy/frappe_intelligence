<template>
	<section class="fi-card" :aria-label="label">
		<header class="fi-card-header"><slot name="header" /></header>
		<slot />
		<footer class="fi-card-footer">
			<span class="fi-card-note">{{ note }}</span>
			<slot name="actions" />
		</footer>
	</section>
</template>

<script setup>
// The frame shared by cards that wait for the user: a change to approve, a document to review.
defineProps({ label: { type: String, required: true }, note: { type: String, default: "" } });
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
.fi-card-header :slotted(.fi-card-title) {
	flex: 1;
	min-width: 0;
	font-weight: 600;
	font-size: var(--text-sm);
	color: var(--ink-gray-9);
}
.fi-card-header :slotted(.fi-card-meta) {
	flex: none;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-card-header :slotted(.fi-badge) {
	flex: none;
	font-size: 11px;
	font-weight: 500;
	padding: 1px 8px;
	border-radius: var(--radius-full);
	background: var(--surface-amber-2);
	color: var(--ink-amber-7);
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
.fi-card-footer :slotted(.fi-button) {
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
.fi-card-footer :slotted(.fi-button.subtle) {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
.fi-card-footer :slotted(.fi-button.solid) {
	background: var(--surface-gray-10);
	color: var(--ink-base);
}
.fi-card-footer :slotted(.fi-button:disabled) {
	opacity: 0.6;
}
</style>
