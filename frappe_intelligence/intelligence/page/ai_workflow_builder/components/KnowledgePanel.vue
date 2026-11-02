<template>
	<div class="fi-kp">
		<div class="fi-kp-toolbar">
			<span class="fi-kp-hint">{{
				__("Knowledge packs injected into the agent's context for this workflow")
			}}</span>
			<button class="fi-kp-add-btn" @click="showPicker = true">
				+ {{ __("Add Pack") }}
			</button>
		</div>

		<!-- Active packs as dismissible tags -->
		<div v-if="assignedPacks.length" class="fi-kp-tags">
			<div v-for="p in assignedPacks" :key="p.pack" class="fi-kp-tag">
				<span class="fi-kp-tag-name">{{ packName(p.pack) }}</span>
				<button class="fi-kp-tag-del" @click="removePack(p.pack)" :title="__('Remove')">
					✕
				</button>
			</div>
		</div>
		<div v-else class="fi-kp-empty">
			{{ __("No knowledge packs assigned.") }}
		</div>

		<!-- Picker overlay -->
		<div v-if="showPicker" class="fi-kp-picker-overlay" @click.self="showPicker = false">
			<div class="fi-kp-picker">
				<div class="fi-kp-picker-header">
					<span>{{ __("Select Knowledge Pack") }}</span>
					<button class="fi-kp-picker-close" @click="showPicker = false">✕</button>
				</div>
				<input
					class="fi-kp-picker-search"
					v-model="pickerSearch"
					:placeholder="__('Search…')"
					autofocus
				/>
				<div class="fi-kp-picker-list">
					<button
						v-for="p in filteredPacks"
						:key="p.name"
						class="fi-kp-picker-item"
						@click="addPack(p)"
					>
						<span class="fi-kp-picker-name">{{ p.pack_name || p.name }}</span>
						<span v-if="p.description" class="fi-kp-picker-desc">{{
							p.description
						}}</span>
					</button>
					<div v-if="!filteredPacks.length" class="fi-kp-picker-empty">
						{{ __("No packs found.") }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "KnowledgePanel",

	props: {
		knowledgePacks: { type: Array, default: () => [] },
		availablePacks: { type: Array, default: () => [] },
	},

	emits: ["update:knowledgePacks"],

	data() {
		return {
			showPicker: false,
			pickerSearch: "",
		};
	},

	computed: {
		assignedPacks() {
			return this.knowledgePacks;
		},
		assignedSet() {
			return new Set(this.knowledgePacks.map((p) => p.pack));
		},
		filteredPacks() {
			const q = this.pickerSearch.toLowerCase();
			return this.availablePacks.filter(
				(p) =>
					!this.assignedSet.has(p.name) &&
					((p.pack_name || p.name).toLowerCase().includes(q) ||
						(p.description || "").toLowerCase().includes(q))
			);
		},
	},

	methods: {
		packName(packId) {
			const found = this.availablePacks.find((p) => p.name === packId);
			return found ? found.pack_name || found.name : packId;
		},

		addPack(p) {
			this.$emit("update:knowledgePacks", [...this.knowledgePacks, { pack: p.name }]);
			this.showPicker = false;
			this.pickerSearch = "";
		},

		removePack(packId) {
			this.$emit(
				"update:knowledgePacks",
				this.knowledgePacks.filter((p) => p.pack !== packId)
			);
		},
	},
};
</script>

<style scoped>
.fi-kp {
	display: flex;
	flex-direction: column;
	gap: 12px;
	padding: 20px 24px;
	position: relative;
}

.fi-kp-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.fi-kp-hint {
	font-size: 12px;
	color: var(--text-muted, #888);
}
.fi-kp-add-btn {
	font-size: 12px;
	font-weight: 600;
	color: #6c63ff;
	background: none;
	border: 1px solid #6c63ff;
	border-radius: 5px;
	padding: 4px 10px;
	cursor: pointer;
	transition: background 0.15s;
}
.fi-kp-add-btn:hover {
	background: #f0eeff;
}

.fi-kp-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}
.fi-kp-tag {
	display: flex;
	align-items: center;
	gap: 6px;
	background: #f0eeff;
	color: #5b50c4;
	border-radius: 20px;
	padding: 4px 10px 4px 12px;
	font-size: 12px;
	font-weight: 500;
}
.fi-kp-tag-del {
	background: none;
	border: none;
	cursor: pointer;
	color: #9b8de8;
	font-size: 10px;
	padding: 0;
	line-height: 1;
	transition: color 0.1s;
}
.fi-kp-tag-del:hover {
	color: #c62828;
}

.fi-kp-empty {
	font-size: 12px;
	color: var(--text-muted, #aaa);
}

/* Picker */
.fi-kp-picker-overlay {
	position: fixed;
	inset: 0;
	z-index: 200;
	background: rgba(0, 0, 0, 0.3);
	display: flex;
	align-items: center;
	justify-content: center;
}
.fi-kp-picker {
	background: var(--card-bg, #fff);
	border-radius: 10px;
	box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
	width: 440px;
	max-height: 500px;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}
.fi-kp-picker-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 16px;
	border-bottom: 1px solid var(--border-color, #e0e0e0);
	font-size: 14px;
	font-weight: 600;
	color: var(--text-color, #333);
}
.fi-kp-picker-close {
	background: none;
	border: none;
	cursor: pointer;
	color: var(--text-muted, #888);
	font-size: 14px;
	padding: 2px 6px;
	border-radius: 4px;
}
.fi-kp-picker-close:hover {
	background: var(--bg-light-gray, #f0f0f0);
}
.fi-kp-picker-search {
	margin: 10px 16px;
	border: 1px solid var(--border-color, #d1d5db);
	border-radius: 6px;
	padding: 7px 10px;
	font-size: 13px;
	outline: none;
	font-family: inherit;
}
.fi-kp-picker-search:focus {
	border-color: #6c63ff;
}
.fi-kp-picker-list {
	flex: 1;
	overflow-y: auto;
	padding: 0 8px 12px;
}
.fi-kp-picker-item {
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	width: 100%;
	padding: 9px 10px;
	background: none;
	border: none;
	cursor: pointer;
	border-radius: 6px;
	text-align: start;
	transition: background 0.1s;
}
.fi-kp-picker-item:hover {
	background: #f0eeff;
}
.fi-kp-picker-name {
	font-size: 13px;
	font-weight: 500;
	color: var(--text-color, #333);
}
.fi-kp-picker-desc {
	font-size: 11px;
	color: var(--text-muted, #888);
	margin-top: 2px;
}
.fi-kp-picker-empty {
	padding: 16px;
	font-size: 13px;
	color: var(--text-muted, #aaa);
	text-align: center;
}
</style>
