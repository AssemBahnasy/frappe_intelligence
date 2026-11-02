<template>
	<div class="fi-wh-bar">
		<!-- Left: identity fields -->
		<div class="fi-wh-fields">
			<div class="fi-wh-field">
				<label class="fi-wh-label">{{ __("Title") }}</label>
				<input
					class="fi-wh-input"
					:value="workflow.title"
					@input="emit('title', $event.target.value)"
					:placeholder="__('Workflow title')"
				/>
			</div>
			<div class="fi-wh-field">
				<label class="fi-wh-label">{{ __("Key") }}</label>
				<input
					class="fi-wh-input fi-wh-mono"
					:value="workflow.workflow_key"
					readonly
					:title="__('Workflow key is read-only')"
				/>
			</div>
		</div>

		<!-- Centre: toggles -->
		<div class="fi-wh-toggles">
			<!-- Active toggle -->
			<label class="fi-wh-toggle-row">
				<div
					class="fi-wh-toggle"
					:class="{ 'fi-wh-toggle-on': workflow.is_active }"
					@click="emit('is_active', workflow.is_active ? 0 : 1)"
					role="switch"
					:aria-checked="!!workflow.is_active"
				>
					<div class="fi-wh-toggle-thumb"></div>
				</div>
				<span class="fi-wh-toggle-label">{{ __("Active") }}</span>
			</label>

			<!-- Channel checkboxes -->
			<div class="fi-wh-channels">
				<label v-for="ch in channels" :key="ch.field" class="fi-wh-ch-label">
					<input
						type="checkbox"
						:checked="!!workflow[ch.field]"
						@change="emit(ch.field, $event.target.checked ? 1 : 0)"
					/>
					{{ ch.label }}
				</label>
			</div>
		</div>

		<!-- Right: dirty indicator + actions -->
		<div class="fi-wh-actions">
			<span v-if="isDirty" class="fi-wh-dirty">{{ __("Unsaved changes") }}</span>
			<button
				class="fi-wh-btn fi-wh-discard"
				:disabled="!isDirty || saving"
				@click="$emit('discard')"
			>
				{{ __("Discard") }}
			</button>
			<button
				class="fi-wh-btn fi-wh-save"
				:disabled="!isDirty || saving"
				@click="$emit('save')"
			>
				<span v-if="saving">{{ __("Saving…") }}</span>
				<span v-else>{{ __("Save") }}</span>
			</button>
		</div>
	</div>
</template>

<script>
export default {
	name: "WorkflowHeader",

	props: {
		workflow: { type: Object, required: true },
		isDirty: { type: Boolean, default: false },
		saving: { type: Boolean, default: false },
	},

	emits: ["update:workflow", "save", "discard"],

	data() {
		return {
			channels: [
				{ field: "allow_desk", label: __("Desk") },
				{ field: "allow_portal", label: __("Portal") },
				{ field: "allow_whatsapp", label: __("WhatsApp") },
			],
		};
	},

	methods: {
		emit(field, value) {
			this.$emit("update:workflow", { [field]: value });
		},
	},
};
</script>

<style scoped>
.fi-wh-bar {
	display: flex;
	align-items: center;
	gap: 16px;
	padding: 10px 16px;
	background: var(--card-bg, #fff);
	border-bottom: 1px solid var(--border-color, #e0e0e0);
	flex-shrink: 0;
	flex-wrap: wrap;
}

/* ---- Fields ---- */
.fi-wh-fields {
	display: flex;
	gap: 10px;
	align-items: flex-end;
}
.fi-wh-field {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.fi-wh-label {
	font-size: 10px;
	font-weight: 600;
	color: var(--text-muted, #888);
	text-transform: uppercase;
	letter-spacing: 0.4px;
}
.fi-wh-input {
	border: 1px solid var(--border-color, #d1d5db);
	border-radius: 6px;
	padding: 5px 9px;
	font-size: 13px;
	background: var(--control-bg, #fff);
	color: var(--text-color, #333);
	min-width: 140px;
	outline: none;
	font-family: inherit;
}
.fi-wh-input:focus {
	border-color: #6c63ff;
}
.fi-wh-input[readonly] {
	background: var(--bg-light-gray, #f5f5f5);
	cursor: default;
	color: var(--text-muted, #888);
}
.fi-wh-mono {
	font-family: monospace;
	font-size: 12px;
}

/* ---- Toggles ---- */
.fi-wh-toggles {
	display: flex;
	align-items: center;
	gap: 16px;
	flex-wrap: wrap;
}
.fi-wh-toggle-row {
	display: flex;
	align-items: center;
	gap: 6px;
	cursor: pointer;
	user-select: none;
}
.fi-wh-toggle {
	width: 34px;
	height: 18px;
	border-radius: 9px;
	background: #ccc;
	position: relative;
	transition: background 0.2s;
	cursor: pointer;
}
.fi-wh-toggle-on {
	background: #6c63ff;
}
.fi-wh-toggle-thumb {
	position: absolute;
	top: 2px;
	left: 2px;
	width: 14px;
	height: 14px;
	background: #fff;
	border-radius: 50%;
	transition: transform 0.2s;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
.fi-wh-toggle-on .fi-wh-toggle-thumb {
	transform: translateX(16px);
}
.fi-wh-toggle-label {
	font-size: 12px;
	color: var(--text-color, #333);
}

.fi-wh-channels {
	display: flex;
	gap: 10px;
	align-items: center;
}
.fi-wh-ch-label {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 12px;
	color: var(--text-color, #333);
	cursor: pointer;
}
.fi-wh-ch-label input[type="checkbox"] {
	cursor: pointer;
}

/* ---- Actions ---- */
.fi-wh-actions {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-left: auto;
}
.fi-wh-dirty {
	font-size: 11px;
	color: #f57c00;
	font-weight: 500;
}
.fi-wh-btn {
	padding: 6px 14px;
	border-radius: 6px;
	font-size: 13px;
	font-weight: 500;
	border: none;
	cursor: pointer;
	transition: opacity 0.15s;
}
.fi-wh-btn:disabled {
	opacity: 0.45;
	cursor: not-allowed;
}
.fi-wh-discard {
	background: var(--bg-light-gray, #f0f0f0);
	color: var(--text-color, #333);
}
.fi-wh-discard:not(:disabled):hover {
	background: #e0e0e0;
}
.fi-wh-save {
	background: #6c63ff;
	color: #fff;
}
.fi-wh-save:not(:disabled):hover {
	opacity: 0.88;
}
</style>
