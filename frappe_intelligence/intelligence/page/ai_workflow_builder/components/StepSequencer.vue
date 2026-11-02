<template>
	<div class="fi-seq-panel">
		<div class="fi-seq-header">
			<span class="fi-seq-title">{{ __("Steps") }}</span>
			<button class="fi-seq-add-btn" @click="$emit('add-step')">
				+ {{ __("Add Step") }}
			</button>
		</div>

		<div ref="listEl" class="fi-seq-list">
			<div
				v-for="step in steps"
				:key="step.step_key"
				class="fi-seq-card"
				:class="{ 'fi-seq-card-selected': selectedStepKey === step.step_key }"
				@click="$emit('select-step', step.step_key)"
			>
				<!-- Drag handle -->
				<span class="fi-seq-handle" title="Drag to reorder">⠿</span>

				<!-- Step number badge -->
				<span class="fi-seq-num">{{ step.step_order }}</span>

				<!-- Step info -->
				<div class="fi-seq-info">
					<span class="fi-seq-key">{{ step.step_key }}</span>
					<span v-if="step.target_doctype" class="fi-seq-doctype">{{
						step.target_doctype
					}}</span>
				</div>

				<!-- Delete button -->
				<button
					class="fi-seq-del"
					:title="__('Remove step')"
					@click.stop="onDelete(step.step_key)"
				>
					✕
				</button>
			</div>
		</div>

		<div v-if="!steps.length" class="fi-seq-empty">
			{{ __("No steps yet. Click the Add Step button to begin.") }}
		</div>
	</div>
</template>

<script>
import Sortable from "sortablejs";

export default {
	name: "StepSequencer",

	props: {
		steps: { type: Array, default: () => [] },
		selectedStepKey: { type: String, default: null },
	},

	emits: ["select-step", "update:steps", "add-step", "remove-step"],

	mounted() {
		this._initSortable();
	},

	beforeUnmount() {
		this._sortable?.destroy();
	},

	methods: {
		_initSortable() {
			const el = this.$refs.listEl;
			if (!el) return;

			// Created here, not with useSortable: from mounted() that only registers another onMounted,
			// which never runs.
			this._sortable = Sortable.create(el, {
				handle: ".fi-seq-handle",
				animation: 150,
				ghostClass: "fi-seq-ghost",
				onEnd: () => {
					// After drag, rebuild step_order based on new DOM order
					const cards = el.querySelectorAll(".fi-seq-card");
					const orderedKeys = Array.from(cards).map((c) =>
						c.querySelector(".fi-seq-key")?.textContent?.trim()
					);
					const reordered = orderedKeys
						.map((key) => this.steps.find((s) => s.step_key === key))
						.filter(Boolean)
						.map((s, i) => ({ ...s, step_order: i + 1 }));
					this.$emit("update:steps", reordered);
				},
			});
		},

		onDelete(stepKey) {
			frappe.confirm(__('Remove step "{0}"? This cannot be undone.', [stepKey]), () =>
				this.$emit("remove-step", stepKey)
			);
		},
	},
};
</script>

<style scoped>
.fi-seq-panel {
	width: 260px;
	flex-shrink: 0;
	display: flex;
	flex-direction: column;
	background: var(--card-bg, #fff);
	border-right: 1px solid var(--border-color, #e0e0e0);
	overflow: hidden;
}

.fi-seq-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10px 12px;
	border-bottom: 1px solid var(--border-color, #e0e0e0);
	flex-shrink: 0;
}
.fi-seq-title {
	font-size: 12px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.4px;
	color: var(--text-muted, #888);
}
.fi-seq-add-btn {
	font-size: 12px;
	font-weight: 600;
	color: #6c63ff;
	background: none;
	border: none;
	cursor: pointer;
	padding: 0;
	transition: opacity 0.15s;
}
.fi-seq-add-btn:hover {
	opacity: 0.75;
}

.fi-seq-list {
	flex: 1;
	overflow-y: auto;
	padding: 8px;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.fi-seq-card {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 10px;
	border: 1px solid var(--border-color, #e0e0e0);
	border-radius: 8px;
	background: var(--bg-color, #fafafa);
	cursor: pointer;
	transition: border-color 0.15s, background 0.15s;
	user-select: none;
}
.fi-seq-card:hover {
	background: #f0eeff;
	border-color: #6c63ff;
}
.fi-seq-card-selected {
	background: #ede9ff;
	border-color: #6c63ff;
}

.fi-seq-ghost {
	opacity: 0.4;
	background: #f0eeff;
}

.fi-seq-handle {
	color: var(--text-muted, #bbb);
	cursor: grab;
	font-size: 14px;
	flex-shrink: 0;
	line-height: 1;
}
.fi-seq-handle:active {
	cursor: grabbing;
}

.fi-seq-num {
	width: 20px;
	height: 20px;
	background: #6c63ff;
	color: #fff;
	border-radius: 50%;
	font-size: 10px;
	font-weight: 700;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.fi-seq-info {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.fi-seq-key {
	font-size: 12px;
	font-family: monospace;
	color: var(--text-color, #333);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.fi-seq-doctype {
	font-size: 10px;
	color: var(--text-muted, #888);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	background: #f5f5f5;
	border-radius: 3px;
	padding: 1px 5px;
	width: fit-content;
}

.fi-seq-del {
	background: none;
	border: none;
	cursor: pointer;
	color: var(--text-muted, #bbb);
	font-size: 12px;
	padding: 2px 4px;
	border-radius: 4px;
	flex-shrink: 0;
	transition: color 0.15s, background 0.15s;
}
.fi-seq-del:hover {
	color: #c62828;
	background: #fce4e4;
}

.fi-seq-empty {
	padding: 16px 12px;
	font-size: 12px;
	color: var(--text-muted, #888);
	text-align: center;
}
</style>
