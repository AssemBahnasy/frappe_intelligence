<template>
	<div ref="root" class="fi-turn">
		<div v-if="asked" class="fi-asked">
			<FileChip v-for="file in turn.attachments || []" :key="file.file_url" :file="file" />
			<div v-if="turn.question" class="fi-question" dir="auto">{{ turn.question }}</div>
		</div>

		<Steps :steps="turn.steps" :pending="turn.pending" />

		<div v-if="thinking" class="fi-thinking">
			<span class="fi-spin"><Icon name="loader-circle" /></span>
			{{ turn.stopping ? __("Stopping…") : __("Thinking…") }}
		</div>

		<div
			v-if="turn.answer"
			class="fi-markdown"
			dir="auto"
			v-html="html"
			@click="follow_link"
		></div>
		<div v-if="turn.off_topic" class="fi-meta fi-off-topic">
			<Icon name="ban" size="xs" />
			{{ __("Off-topic · answered without AI") }}
		</div>

		<template v-for="proposal in turn.proposals || []" :key="proposal.call_id">
			<template v-if="proposal.status === 'pending'">
				<ReviewCard
					v-if="proposal.preview?.kind === 'review'"
					:turn="turn"
					:proposal="proposal"
				/>
				<ProposalCard v-else :turn="turn" :proposal="proposal" />
			</template>
			<ChangeResult v-else :proposal="proposal" />
		</template>

		<div
			v-if="turn.report"
			class="fi-markdown"
			dir="auto"
			v-html="report_html"
			@click="follow_link"
		></div>

		<ChartBlock v-for="(chart, i) in charts" :key="i" :chart="chart" />

		<div v-if="turn.error" class="fi-error" role="alert">{{ turn.error }}</div>
		<div v-else-if="turn.stopped && !turn.pending" class="fi-meta">{{ __("Stopped.") }}</div>

		<div v-if="!turn.pending && full_text && asked" class="fi-footer">
			<button
				class="fi-small-button"
				:title="__('Copy as Markdown')"
				:aria-label="__('Copy as Markdown')"
				@click="copy"
			>
				<Icon name="copy" size="xs" />
			</button>
			<template v-if="turn.answer_id">
				<button
					v-for="option in feedback_options"
					:key="option.value"
					class="fi-small-button"
					:class="{ active: turn.feedback === option.value }"
					:title="option.label"
					:aria-label="option.label"
					:aria-pressed="turn.feedback === option.value"
					@click="store.rate(turn, option.value)"
				>
					<Icon :name="option.icon" size="xs" />
				</button>
			</template>
			<span class="fi-meta">{{ frappe.datetime.prettyDate(turn.created) }}</span>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { open_route } from "../actions";
import { isolate_ltr } from "../bidi";
import { useAssistant } from "../store";
import { enhance_tables } from "../tables";
import ChangeResult from "./ChangeResult.vue";
import ChartBlock from "./ChartBlock.vue";
import FileChip from "./FileChip.vue";
import Icon from "./Icon.vue";
import ProposalCard from "./ProposalCard.vue";
import ReviewCard from "./ReviewCard.vue";
import Steps from "./Steps.vue";

const props = defineProps({ turn: { type: Object, required: true } });
const store = useAssistant();
const root = ref(null);

const html = computed(() => frappe.markdown(props.turn.answer || ""));
const report_html = computed(() => frappe.markdown(props.turn.report || ""));
// A workflow's opening question was not asked by the user.
const asked = computed(() => !!(props.turn.question || props.turn.attachments?.length));
const full_text = computed(() =>
	[props.turn.answer, props.turn.report].filter(Boolean).join("\n\n")
);
const charts = computed(() => (props.turn.actions || []).filter((a) => a.type === "chart"));
const thinking = computed(() => {
	const t = props.turn;
	const step_running = t.steps.some((s) => s.status === "running");
	return t.pending && !(t.reporting ? t.report : t.answer) && !step_running;
});
const feedback_options = [
	{ value: "Good", icon: "thumbs-up", label: __("Good answer") },
	{ value: "Bad", icon: "thumbs-down", label: __("Bad answer") },
];

// Once the answer is complete: numbers and codes isolated inside right-to-left text, tables sortable and paged.
watch(
	() => [props.turn.pending, html.value, report_html.value],
	async ([pending]) => {
		if (pending) return;
		await nextTick();
		if (!root.value) return;
		root.value.querySelectorAll(".fi-markdown").forEach(isolate_ltr);
		enhance_tables(root.value);
	},
	{ immediate: true }
);

function follow_link(e) {
	const href = e.target.closest("a")?.getAttribute("href") || "";
	if (/^\/(app|desk)\//.test(href)) {
		e.preventDefault();
		open_route(href);
	}
}

function copy() {
	frappe.utils.copy_to_clipboard(full_text.value);
}
</script>

<style scoped>
.fi-turn {
	display: flex;
	flex-direction: column;
	gap: 10px;
}
.fi-asked {
	align-self: flex-end;
	max-width: 85%;
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: 6px;
}
.fi-question {
	max-width: 100%;
	background: var(--surface-gray-2);
	border-radius: var(--radius-lg);
	padding: 8px 12px;
	white-space: pre-wrap;
	overflow-wrap: anywhere;
}
.fi-thinking {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: var(--text-sm);
	color: var(--ink-gray-6);
}
.fi-spin {
	display: inline-flex;
	color: var(--ink-violet-6);
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
.fi-markdown {
	line-height: 1.55;
	overflow-wrap: anywhere;
}
.fi-markdown :deep(p) {
	margin: 0 0 8px;
}
.fi-markdown :deep(p:last-child),
.fi-markdown :deep(ul:last-child),
.fi-markdown :deep(ol:last-child) {
	margin-bottom: 0;
}
.fi-markdown :deep(ul),
.fi-markdown :deep(ol) {
	padding-inline-start: 20px;
	margin: 0 0 8px;
}
.fi-markdown :deep(a) {
	color: var(--ink-blue-link);
}
.fi-markdown :deep(code) {
	background: var(--surface-gray-2);
	border-radius: var(--radius-sm);
	padding: 1px 4px;
	font-size: var(--text-sm);
}
.fi-markdown :deep(pre) {
	background: var(--surface-gray-1);
	border-radius: var(--radius);
	padding: 8px 10px;
	overflow-x: auto;
}
.fi-markdown :deep(.fi-table) {
	border: 1px solid var(--outline-gray-1);
	border-radius: 10px;
	overflow: hidden;
	margin-bottom: 8px;
}
.fi-markdown :deep(table) {
	width: 100%;
	border-collapse: collapse;
	font-size: var(--text-sm);
}
.fi-markdown :deep(th) {
	text-align: start;
	font-weight: 500;
	color: var(--ink-gray-6);
	padding: 6px 8px;
	border-bottom: 1px solid var(--outline-gray-2);
	white-space: nowrap;
}
.fi-markdown :deep(td) {
	padding: 6px 8px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.fi-markdown :deep(tbody tr:last-child td) {
	border-bottom: 0;
}
.fi-markdown :deep(.fi-sort) {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 0;
	border: 0;
	background: none;
	color: inherit;
	font: inherit;
}
.fi-markdown :deep(.fi-num) {
	text-align: end;
	font-variant-numeric: tabular-nums;
}
.fi-markdown :deep(.fi-table-pager) {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 4px;
	padding: 4px 6px;
	border-top: 1px solid var(--outline-gray-1);
	background: var(--surface-gray-1);
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-markdown :deep(.fi-table-range) {
	margin-inline-end: 4px;
}
.fi-markdown :deep(.fi-table-page) {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	padding: 0;
	border: 0;
	border-radius: var(--radius);
	background: transparent;
	color: var(--ink-gray-6);
}
.fi-markdown :deep(.fi-table-page:hover:not(:disabled)) {
	background: var(--surface-gray-2);
}
.fi-markdown :deep(.fi-table-page:disabled) {
	opacity: 0.4;
}
.fi-error {
	padding: 8px 10px;
	border-radius: var(--radius);
	background: var(--surface-red-2);
	color: var(--ink-red-6);
	font-size: var(--text-sm);
}
.fi-meta {
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-off-topic {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	margin-top: -6px;
}
.fi-footer {
	display: flex;
	align-items: center;
	gap: 2px;
}
.fi-footer .fi-meta {
	margin-inline-start: 6px;
}
.fi-small-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 26px;
	height: 26px;
	padding: 0;
	border: 0;
	border-radius: var(--radius);
	background: transparent;
	color: var(--ink-gray-6);
}
.fi-small-button:hover,
.fi-small-button.active {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
</style>
