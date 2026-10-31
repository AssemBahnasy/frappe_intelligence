<template>
	<span class="fi-file">
		<span class="fi-file-icon" :class="{ 'fi-spin': uploading }">
			<Icon :name="uploading ? 'loader-circle' : 'file'" />
		</span>
		<span class="fi-file-text">
			<span class="fi-file-name" dir="auto">{{ file.file_name }}</span>
			<span class="fi-file-kind">{{ uploading ? __("Uploading…") : file_kind(file.file_name) }}</span>
		</span>
		<button
			v-if="removable"
			type="button"
			class="fi-file-remove"
			:aria-label="__('Remove {0}', [file.file_name])"
			@click="$emit('remove')"
		>
			<Icon name="x" size="xs" />
		</button>
	</span>
</template>

<script setup>
import { file_kind } from "../uploads";
import Icon from "./Icon.vue";

defineProps({
	file: { type: Object, required: true },
	uploading: { type: Boolean, default: false },
	removable: { type: Boolean, default: false },
});
defineEmits(["remove"]);
</script>

<style scoped>
.fi-file {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	max-width: 100%;
	padding: 6px 10px 6px 8px;
	border-radius: 10px;
	box-shadow: inset 0 0 0 1px var(--outline-gray-2);
	background: var(--surface-base);
	font-size: var(--text-sm);
}
.fi-file-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: none;
	width: 28px;
	height: 28px;
	border-radius: 6px;
	background: var(--surface-gray-2);
	color: var(--ink-gray-6);
}
.fi-file-text {
	display: flex;
	flex-direction: column;
	min-width: 0;
	line-height: 1.3;
}
.fi-file-name {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--ink-gray-9);
}
.fi-file-kind {
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-file-remove {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: none;
	width: 20px;
	height: 20px;
	padding: 0;
	border: 0;
	border-radius: var(--radius-full);
	background: transparent;
	color: var(--ink-gray-6);
}
.fi-file-remove:hover {
	background: var(--surface-gray-3);
}
.fi-spin :deep(svg) {
	animation: fi-spin 1s linear infinite;
}
@keyframes fi-spin {
	to {
		transform: rotate(360deg);
	}
}
@media (prefers-reduced-motion: reduce) {
	.fi-spin :deep(svg) {
		animation: none;
	}
}
</style>
