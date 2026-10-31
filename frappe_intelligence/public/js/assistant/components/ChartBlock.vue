<template>
	<figure class="fi-chart">
		<figcaption v-if="chart.title">{{ chart.title }}</figcaption>
		<div ref="canvas"></div>
	</figure>
</template>

<script setup>
import { onMounted, ref } from "vue";

const props = defineProps({ chart: { type: Object, required: true } });
const canvas = ref(null);

// make_chart applies the desk's themed palette (utils.js → get_chart_palette).
onMounted(() => {
	frappe.utils.make_chart(canvas.value, {
		type: props.chart.chart_type,
		height: 220,
		data: { labels: props.chart.labels, datasets: props.chart.datasets },
	});
});
</script>

<style scoped>
.fi-chart {
	margin: 0;
	border: 1px solid var(--outline-gray-1);
	border-radius: 10px;
	padding: 8px;
}
figcaption {
	font-size: var(--text-sm);
	font-weight: 500;
	color: var(--ink-gray-8);
	padding: 2px 4px 0;
}
</style>
