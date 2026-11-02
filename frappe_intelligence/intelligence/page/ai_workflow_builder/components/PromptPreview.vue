<template>
	<div class="fi-pp-preview">
		<button class="fi-pp-preview-toggle" @click="open = !open">
			<span class="fi-pp-preview-icon">{{ open ? "▾" : "▸" }}</span>
			{{ __("Prompt Preview") }}
			<span v-if="selectedStepKey" class="fi-pp-preview-step">{{ selectedStepKey }}</span>
		</button>

		<div v-if="open" class="fi-pp-preview-body">
			<div v-if="!selectedStepKey" class="fi-pp-preview-hint">
				{{ __("Select a step to preview its rendered prompt.") }}
			</div>
			<div v-else-if="loading" class="fi-pp-preview-loading">
				<div class="fi-pp-preview-spinner"></div>
				<span>{{ __("Rendering…") }}</span>
			</div>
			<pre v-else-if="prompt" class="fi-pp-preview-pre">{{ prompt }}</pre>
			<div v-else class="fi-pp-preview-hint">{{ __("No prompt yet.") }}</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "PromptPreview",

	props: {
		selectedStep: { type: Object, default: null },
	},

	data() {
		return {
			open: false,
			loading: false,
			prompt: "",
			_debounceTimer: null,
		};
	},

	computed: {
		selectedStepKey() {
			return this.selectedStep?.step_key || null;
		},
	},

	watch: {
		selectedStep: {
			deep: true,
			handler() {
				if (this.open && this.selectedStep) {
					this.schedulePreview();
				}
			},
		},
		open(val) {
			if (val && this.selectedStep) {
				this.schedulePreview();
			} else if (!val) {
				clearTimeout(this._debounceTimer);
			}
		},
	},

	methods: {
		schedulePreview() {
			clearTimeout(this._debounceTimer);
			this._debounceTimer = setTimeout(() => this.fetchPreview(), 500);
		},

		async fetchPreview() {
			if (!this.selectedStep) return;
			this.loading = true;
			try {
				const res = await frappe.call({
					method: "frappe_intelligence.api.builder.preview_step_prompt",
					args: { step_data: this.selectedStep },
				});
				this.prompt = res.message?.prompt || "";
			} catch (_) {
				this.prompt = "";
			} finally {
				this.loading = false;
			}
		},
	},

	beforeUnmount() {
		clearTimeout(this._debounceTimer);
	},
};
</script>

<style scoped>
.fi-pp-preview {
	border-top: 1px solid var(--border-color, #e0e0e0);
	background: var(--card-bg, #fff);
}

.fi-pp-preview-toggle {
	width: 100%;
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 12px 24px;
	background: none;
	border: none;
	cursor: pointer;
	font-size: 13px;
	font-weight: 600;
	color: var(--text-color, #444);
	text-align: start;
	transition: background 0.1s;
}
.fi-pp-preview-toggle:hover {
	background: var(--bg-light-gray, #f8f8f8);
}
.fi-pp-preview-icon {
	font-size: 11px;
	color: var(--text-muted, #888);
}
.fi-pp-preview-step {
	margin-left: auto;
	font-family: monospace;
	font-size: 11px;
	background: #f0eeff;
	color: #5b50c4;
	padding: 2px 7px;
	border-radius: 4px;
	font-weight: 400;
}

.fi-pp-preview-body {
	padding: 0 24px 20px;
}
.fi-pp-preview-hint {
	font-size: 12px;
	color: var(--text-muted, #aaa);
	padding: 8px 0;
}
.fi-pp-preview-loading {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12px;
	color: var(--text-muted, #888);
	padding: 8px 0;
}
.fi-pp-preview-spinner {
	width: 14px;
	height: 14px;
	border: 2px solid #e0e0e0;
	border-top-color: #6c63ff;
	border-radius: 50%;
	animation: fi-pp-spin 0.7s linear infinite;
}
@keyframes fi-pp-spin {
	to {
		transform: rotate(360deg);
	}
}

.fi-pp-preview-pre {
	margin: 0;
	padding: 12px 14px;
	background: #1e1e2e;
	color: #cdd6f4;
	border-radius: 8px;
	font-family: "Courier New", monospace;
	font-size: 12px;
	line-height: 1.6;
	overflow-x: auto;
	white-space: pre-wrap;
	word-break: break-word;
}
</style>
