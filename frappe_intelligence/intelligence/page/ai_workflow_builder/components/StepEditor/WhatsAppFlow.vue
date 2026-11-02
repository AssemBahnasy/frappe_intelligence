<template>
	<div class="fi-waf">
		<div v-if="!allowWhatsapp" class="fi-waf-disabled">
			<span>{{ __("Enable WhatsApp channel on the workflow to configure this.") }}</span>
		</div>

		<template v-else>
			<div class="fi-waf-row">
				<label class="fi-waf-label">{{ __("WhatsApp Flow") }}</label>
				<div class="fi-waf-select-wrap">
					<select
						class="fi-waf-select"
						:value="value || ''"
						@change="$emit('update:value', $event.target.value || null)"
					>
						<option value="">— {{ __("None") }} —</option>
						<option
							v-for="flow in availableWaFlows"
							:key="flow.name"
							:value="flow.name"
						>
							{{ flow.flow_name || flow.name }}
						</option>
					</select>
				</div>
			</div>

			<div v-if="!availableWaFlows.length" class="fi-waf-hint">
				{{ __("No WhatsApp flows found. Create one in the WhatsApp Flow DocType.") }}
			</div>

			<div v-if="value" class="fi-waf-link-row">
				<a
					:href="'/app/whatsapp-flow/' + encodeURIComponent(value)"
					target="_blank"
					class="fi-waf-link"
					>{{ __("Edit flow") }} →</a
				>
			</div>
		</template>
	</div>
</template>

<script>
export default {
	name: "WhatsAppFlow",

	props: {
		value: { type: String, default: null },
		allowWhatsapp: { type: Boolean, default: false },
		availableWaFlows: { type: Array, default: () => [] },
	},

	emits: ["update:value"],
};
</script>

<style scoped>
.fi-waf {
	display: flex;
	flex-direction: column;
	gap: 14px;
	padding: 16px;
	overflow-y: auto;
}

.fi-waf-disabled {
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 32px 16px;
	font-size: 13px;
	color: var(--text-muted, #999);
	text-align: center;
	border: 1px dashed var(--border-color, #d1d5db);
	border-radius: 8px;
}

.fi-waf-row {
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.fi-waf-label {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted, #888);
	text-transform: uppercase;
	letter-spacing: 0.4px;
}
.fi-waf-select-wrap {
	position: relative;
}
.fi-waf-select {
	width: 100%;
	border: 1px solid var(--border-color, #d1d5db);
	border-radius: 6px;
	padding: 6px 10px;
	font-size: 13px;
	font-family: inherit;
	background: var(--control-bg, #fff);
	color: var(--text-color, #333);
	outline: none;
	cursor: pointer;
}
.fi-waf-select:focus {
	border-color: #6c63ff;
}

.fi-waf-hint {
	font-size: 12px;
	color: var(--text-muted, #aaa);
}
.fi-waf-link-row {
	display: flex;
}
.fi-waf-link {
	font-size: 12px;
	color: #6c63ff;
	text-decoration: none;
}
.fi-waf-link:hover {
	text-decoration: underline;
}
</style>
