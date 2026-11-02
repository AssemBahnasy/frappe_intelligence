<template>
	<div class="fi-pic" aria-hidden="true">
		<!-- The dock, with the assistant's sparkles ringed -->
		<div v-if="name === 'dock'" class="fi-desk">
			<span class="fi-mini-dock">
				<span class="fi-logo"></span>
				<span class="fi-dock-button is-ring"><Icon name="sparkles" size="xs" /></span>
				<span class="fi-square"></span>
				<span class="fi-square"></span>
			</span>
			<span class="fi-page">
				<span class="fi-bar w-50"></span>
				<span class="fi-bar w-80 is-soft"></span>
				<span class="fi-key">Ctrl+.</span>
			</span>
		</div>

		<!-- The assistant panel beside a page -->
		<div v-else-if="PANEL.includes(name)" class="fi-desk">
			<span class="fi-page">
				<span class="fi-bar w-50"></span>
				<span class="fi-bar w-80 is-soft"></span>
				<span class="fi-bar w-60 is-soft"></span>
			</span>
			<span :class="['fi-panel', { 'is-ring-edge': name === 'resize' }]">
				<span class="fi-panel-head">
					<span class="fi-bar w-40"></span>
					<span :class="['fi-tiny', { 'is-ring': name === 'history' }]"
						><Icon name="history" size="xs"
					/></span>
				</span>
				<span class="fi-panel-body">
					<template v-if="name === 'answer' || name === 'rating'">
						<span class="fi-bubble">{{ __("Overdue invoices?") }}</span>
						<span class="fi-bar w-90 is-soft"></span>
						<span class="fi-table"><span></span><span></span><span></span></span>
						<span v-if="name === 'rating'" class="fi-thumbs is-ring">
							<Icon name="thumbs-up" size="xs" /><Icon
								name="thumbs-down"
								size="xs"
							/>
						</span>
					</template>
					<span v-else-if="name === 'review'" class="fi-card">
						<span class="fi-bar w-50"></span>
						<span class="fi-pair"><span></span><span class="is-mark"></span></span>
						<span class="fi-pair"><span></span><span></span></span>
						<span class="fi-button is-ring">{{ __("Use these values") }}</span>
					</span>
					<template v-else-if="name === 'workflows'">
						<span class="fi-row is-ring"
							><Icon name="play" size="xs" />{{ __("New customer") }}</span
						>
						<span class="fi-row"
							><Icon name="play" size="xs" />{{ __("Leave request") }}</span
						>
					</template>
					<template v-else-if="name === 'workflow-bar'">
						<span class="fi-progress-strip is-ring">{{
							__("Step {0} of {1}", [2, 4])
						}}</span>
						<span class="fi-bar w-80 is-soft"></span>
						<span class="fi-chips"
							><span>{{ __("Yes") }}</span
							><span>{{ __("No") }}</span></span
						>
					</template>
					<span v-else-if="name === 'proposal'" class="fi-card">
						<span class="fi-badge">{{ __("Needs approval") }}</span>
						<span class="fi-bar w-80 is-soft"></span>
						<span class="fi-actions">
							<span class="fi-button is-plain">{{ __("Reject") }}</span>
							<span class="fi-button is-ring">{{ __("Confirm") }}</span>
						</span>
					</span>
					<span v-else-if="name === 'mode'" class="fi-menu">
						<span>{{ __("Ask") }}</span>
						<span class="is-ring">{{ __("Agent") }}</span>
					</span>
					<template v-else>
						<span class="fi-bar w-60"></span>
						<span class="fi-bar w-40 is-soft"></span>
					</template>
				</span>
				<span v-if="name === 'context'" class="fi-context is-ring">{{
					__("This page")
				}}</span>
				<span :class="['fi-composer', { 'is-ring': name === 'composer' }]">
					<span :class="['fi-tiny', { 'is-ring': name === 'attach' }]"
						><Icon name="paperclip" size="xs"
					/></span>
					<span :class="['fi-tiny', { 'is-ring': name === 'microphone' }]"
						><Icon name="mic" size="xs"
					/></span>
					<span :class="['fi-mode', { 'is-ring': name === 'mode' }]">{{
						__("Ask")
					}}</span>
				</span>
			</span>
		</div>

		<!-- A form -->
		<div v-else-if="FORM.includes(name)" class="fi-form">
			<template v-if="name === 'settings'">
				<span class="fi-field is-ring"
					><span class="fi-bar w-40"></span>{{ __("Provider") }}</span
				>
				<span class="fi-field"><span class="fi-bar w-40"></span></span>
				<span class="fi-field"><span class="fi-bar w-40"></span></span>
				<span class="fi-field"><span class="fi-bar w-40"></span></span>
			</template>
			<template v-else-if="name === 'filled'">
				<span v-for="n in 4" :key="n" class="fi-field is-filled"
					><span class="fi-bar w-40"></span
				></span>
			</template>
			<template v-else>
				<span class="fi-label">
					<span class="fi-bar w-30"></span>
					<span :class="['fi-tiny', { 'is-ring': name === 'field' }]"
						><Icon name="sparkles" size="xs"
					/></span>
				</span>
				<span :class="['fi-text', { 'is-written': name === 'undo' }]">
					<span v-if="name === 'popover'" class="fi-popover is-ring">{{
						__("A polite reminder…")
					}}</span>
				</span>
				<span v-if="name === 'undo'" class="fi-toast">
					{{ __("Written") }} <span class="is-ring">{{ __("Undo") }}</span>
				</span>
			</template>
		</div>

		<!-- A list -->
		<div v-else-if="name === 'list'" class="fi-list">
			<span class="fi-list-head"
				><span class="fi-bar w-30"></span><span class="fi-button">+</span></span
			>
			<span v-for="n in 3" :key="n" class="fi-list-row"
				><span class="fi-bar w-60 is-soft"></span
			></span>
		</div>

		<!-- The Workflow Builder: steps, the step editor, the preview -->
		<div v-else-if="name === 'builder'" class="fi-builder">
			<span class="fi-col"><span class="is-ring"></span><span></span><span></span></span>
			<span class="fi-col is-wide"
				><span class="fi-bar w-60"></span><span class="fi-bar w-80 is-soft"></span
			></span>
			<span class="fi-col"><span class="fi-bar w-80 is-soft"></span></span>
		</div>

		<!-- A report chart -->
		<div v-else-if="name === 'chart'" class="fi-chart">
			<span style="height: 40%"></span>
			<span class="is-accent" style="height: 80%"></span>
			<span style="height: 55%"></span>
			<span style="height: 30%"></span>
		</div>
	</div>
</template>

<script setup>
import Icon from "../../assistant/components/Icon.vue";

defineProps({ name: { type: String, required: true } });

const PANEL = [
	"panel",
	"resize",
	"composer",
	"answer",
	"context",
	"attach",
	"microphone",
	"review",
	"workflows",
	"workflow-bar",
	"mode",
	"proposal",
	"history",
	"rating",
];
const FORM = ["settings", "filled", "field", "popover", "undo"];
</script>

<style scoped>
.fi-pic {
	height: 112px;
	border-radius: var(--radius-md, 8px);
	background: var(--surface-base);
	border: 1px solid var(--outline-gray-1);
	overflow: hidden;
	font-size: 9px;
	color: var(--ink-gray-7);
	display: flex;
}
.fi-pic > div {
	flex: 1;
	min-width: 0;
}
/* The ring that points at the element the step is about. */
.is-ring {
	box-shadow: 0 0 0 2px var(--ink-violet-6) !important;
}
.fi-bar {
	display: block;
	height: 6px;
	border-radius: 3px;
	background: var(--outline-gray-2);
}
.fi-bar.is-soft {
	background: var(--surface-gray-2);
}
.w-30 {
	width: 30%;
}
.w-40 {
	width: 40%;
}
.w-50 {
	width: 50%;
}
.w-60 {
	width: 60%;
}
.w-80 {
	width: 80%;
}
.w-90 {
	width: 90%;
}
.fi-desk {
	display: flex;
}
.fi-mini-dock {
	width: 30px;
	padding-top: 8px;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 7px;
	background: var(--surface-gray-1);
	border-inline-end: 1px solid var(--outline-gray-1);
}
.fi-logo {
	width: 14px;
	height: 14px;
	border-radius: 4px;
	background: #1e1b4b;
}
.fi-dock-button {
	width: 20px;
	height: 20px;
	border-radius: 6px;
	display: grid;
	place-items: center;
	background: var(--surface-base);
	color: var(--ink-violet-6);
}
.fi-square {
	width: 12px;
	height: 12px;
	border-radius: 3px;
	background: var(--outline-gray-2);
}
.fi-page {
	flex: 1;
	padding: 10px;
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.fi-key {
	margin-top: auto;
	align-self: flex-start;
	padding: 2px 6px;
	border-radius: 4px;
	background: var(--surface-gray-2);
}
.fi-panel {
	width: 58%;
	display: flex;
	flex-direction: column;
	border-inline-start: 1px solid var(--outline-gray-2);
	background: var(--surface-base);
}
.fi-panel.is-ring-edge {
	border-inline-start: 2px solid var(--ink-violet-6);
}
.fi-panel-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 5px 6px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.fi-panel-body {
	flex: 1;
	min-height: 0;
	overflow: hidden;
	padding: 6px;
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.fi-tiny {
	width: 16px;
	height: 16px;
	border-radius: 4px;
	display: grid;
	place-items: center;
	color: var(--ink-gray-6);
}
.fi-bubble {
	align-self: flex-end;
	padding: 2px 6px;
	border-radius: 6px;
	background: var(--surface-gray-2);
}
.fi-table {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.fi-table span {
	height: 5px;
	border-radius: 2px;
	background: var(--surface-gray-2);
}
.fi-thumbs {
	align-self: flex-start;
	display: flex;
	gap: 2px;
	padding: 1px 3px;
	border-radius: 4px;
	color: var(--ink-gray-6);
}
.fi-card {
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding: 5px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 5px;
}
.fi-pair {
	display: flex;
	gap: 4px;
}
.fi-pair span {
	flex: 1;
	height: 5px;
	border-radius: 2px;
	background: var(--surface-gray-2);
}
.fi-pair .is-mark {
	background: var(--surface-amber-2);
}
.fi-button {
	align-self: flex-start;
	white-space: nowrap;
	padding: 2px 6px;
	border-radius: 4px;
	background: var(--ink-gray-9);
	color: var(--surface-base);
}
.fi-button.is-plain {
	background: var(--surface-gray-2);
	color: var(--ink-gray-8);
}
.fi-actions {
	display: flex;
	gap: 4px;
}
.fi-badge {
	align-self: flex-start;
	padding: 1px 5px;
	border-radius: 6px;
	background: var(--surface-amber-2);
	color: var(--ink-amber-7);
}
.fi-row {
	display: flex;
	align-items: center;
	gap: 4px;
	white-space: nowrap;
	overflow: hidden;
	padding: 3px 5px;
	border-radius: 4px;
	background: var(--surface-gray-1);
}
.fi-progress-strip {
	padding: 2px 5px;
	border-radius: 4px;
	background: var(--surface-violet-2);
	color: var(--ink-violet-6);
}
.fi-chips {
	display: flex;
	gap: 3px;
}
.fi-chips span {
	padding: 1px 6px;
	border-radius: 6px;
	border: 1px solid var(--outline-gray-2);
}
.fi-menu {
	align-self: flex-end;
	margin-top: auto;
	display: flex;
	flex-direction: column;
	gap: 2px;
	padding: 3px;
	border-radius: 5px;
	background: var(--surface-base);
	box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.12));
}
.fi-menu span {
	padding: 2px 8px;
	border-radius: 3px;
}
.fi-context {
	margin: 0 6px 3px;
	align-self: flex-start;
	padding: 1px 6px;
	border-radius: 6px;
	background: var(--surface-gray-2);
}
.fi-composer {
	margin: 0 6px 6px;
	height: 20px;
	display: flex;
	align-items: center;
	gap: 2px;
	padding: 0 3px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 5px;
}
.fi-mode {
	margin-inline-start: auto;
	padding: 0 4px;
	border-radius: 4px;
	background: var(--surface-gray-2);
}
.fi-form {
	padding: 10px;
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 8px;
	align-content: start;
	position: relative;
}
.fi-field {
	display: flex;
	flex-direction: column;
	gap: 3px;
	padding: 4px;
	border-radius: 4px;
	background: var(--surface-gray-1);
}
.fi-field.is-filled {
	background: var(--surface-violet-2);
}
.fi-label {
	grid-column: 1 / -1;
	display: flex;
	align-items: center;
	gap: 4px;
}
.fi-text {
	grid-column: 1 / -1;
	height: 50px;
	border-radius: 4px;
	border: 1px solid var(--outline-gray-2);
	position: relative;
}
.fi-text.is-written {
	background: var(--surface-violet-2);
}
.fi-popover {
	position: absolute;
	inset-inline-start: 8px;
	top: 8px;
	padding: 4px 8px;
	border-radius: 5px;
	background: var(--surface-base);
	box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.12));
}
.fi-toast {
	position: absolute;
	inset-inline-end: 10px;
	bottom: 8px;
	display: flex;
	gap: 6px;
	padding: 3px 8px;
	border-radius: 5px;
	background: var(--ink-gray-9);
	color: var(--surface-base);
}
.fi-list {
	padding: 10px;
	display: flex;
	flex-direction: column;
	gap: 6px;
}
.fi-list-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
}
.fi-list-row {
	padding: 5px;
	border-bottom: 1px solid var(--outline-gray-1);
}
.fi-builder {
	padding: 8px;
	display: flex;
	gap: 6px;
}
.fi-col {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 4px;
	padding: 5px;
	border-radius: 4px;
	border: 1px solid var(--outline-gray-2);
}
.fi-col.is-wide {
	flex: 2;
}
.fi-col > span:not(.fi-bar) {
	height: 12px;
	border-radius: 3px;
	background: var(--surface-gray-1);
}
.fi-chart {
	padding: 12px 18px;
	display: flex;
	align-items: flex-end;
	gap: 8px;
}
.fi-chart span {
	flex: 1;
	border-radius: 3px 3px 0 0;
	background: var(--outline-gray-2);
}
.fi-chart .is-accent {
	background: var(--ink-violet-6);
}
</style>
