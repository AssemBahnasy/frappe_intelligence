<template>
	<span class="fi-icon" aria-hidden="true" v-html="svg"></span>
</template>

<script setup>
import { computed } from "vue";

// Lucide icons from Frappe's sprite; they follow the text colour.
const props = defineProps({
	name: { type: String, required: true },
	size: { type: String, default: "sm" },
});
const svg = computed(() => frappe.utils.icon(props.name, props.size, "", "", "", true));
</script>

<style scoped>
.fi-icon {
	display: inline-flex;
	flex: none;
	--icon-stroke: currentColor;
}
</style>
