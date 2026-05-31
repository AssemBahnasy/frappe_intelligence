<template>
  <div class="fi-dr">
    <div class="fi-dr-toolbar">
      <span class="fi-dr-hint">{{ __("Documents the agent must collect at this step") }}</span>
      <button class="fi-dr-add-btn" @click="showPicker = true">+ {{ __("Add Requirement") }}</button>
    </div>

    <!-- Existing requirements for this step -->
    <div class="fi-dr-list">
      <div v-for="req in stepRequirements" :key="req._id || req.name" class="fi-dr-item">
        <div class="fi-dr-item-info">
          <span class="fi-dr-item-label">{{ req.label || req.document_type_key }}</span>
          <span class="fi-dr-item-key">{{ req.document_type_key }}</span>
        </div>
        <label class="fi-dr-mandatory">
          <input
            type="checkbox"
            :checked="!!req.is_mandatory"
            @change="toggleMandatory(req, $event.target.checked)"
          />
          {{ __("Mandatory") }}
        </label>
        <button class="fi-dr-del" @click="removeReq(req)" :title="__('Remove')">✕</button>
      </div>

      <div v-if="!stepRequirements.length" class="fi-dr-empty">
        {{ __("No document requirements for this step.") }}
      </div>
    </div>

    <!-- Template picker overlay -->
    <div v-if="showPicker" class="fi-dr-picker-overlay" @click.self="showPicker = false">
      <div class="fi-dr-picker">
        <div class="fi-dr-picker-header">
          <span>{{ __("Select Document Template") }}</span>
          <button class="fi-dr-picker-close" @click="showPicker = false">✕</button>
        </div>
        <input
          class="fi-dr-picker-search"
          v-model="pickerSearch"
          :placeholder="__('Search templates…')"
          autofocus
        />
        <div class="fi-dr-picker-list">
          <button
            v-for="tpl in filteredTemplates"
            :key="tpl.name"
            class="fi-dr-picker-item"
            @click="addReq(tpl)"
          >
            <span class="fi-dr-picker-name">{{ tpl.document_name }}</span>
            <span class="fi-dr-picker-key">{{ tpl.document_type_key }}</span>
          </button>
          <div v-if="!filteredTemplates.length" class="fi-dr-picker-empty">
            {{ __("No templates found.") }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
let _nextId = 1;

export default {
  name: "DocumentRequirements",

  props: {
    stepKey:            { type: String, required: true },
    requirements:       { type: Array,  default: () => [] },
    availableTemplates: { type: Array,  default: () => [] },
  },

  emits: ["update"],

  data() {
    return {
      showPicker: false,
      pickerSearch: "",
    };
  },

  computed: {
    stepRequirements() {
      return this.requirements.filter((r) => r.step_key === this.stepKey);
    },
    filteredTemplates() {
      const q = this.pickerSearch.toLowerCase();
      const used = new Set(this.stepRequirements.map((r) => r.document_type_key));
      return this.availableTemplates.filter(
        (t) => !used.has(t.document_type_key) &&
               (t.document_name.toLowerCase().includes(q) ||
                t.document_type_key.toLowerCase().includes(q))
      );
    },
  },

  methods: {
    addReq(tpl) {
      const newReq = {
        _id: `new_${_nextId++}`,
        step_key:          this.stepKey,
        document_type_key: tpl.document_type_key,
        label:             tpl.document_name,
        is_mandatory:      0,
        is_active:         1,
      };
      this.$emit("update", [...this.requirements, newReq]);
      this.showPicker = false;
      this.pickerSearch = "";
    },

    removeReq(req) {
      this.$emit("update", this.requirements.filter((r) => r !== req));
    },

    toggleMandatory(req, checked) {
      this.$emit("update", this.requirements.map((r) =>
        r === req ? { ...r, is_mandatory: checked ? 1 : 0 } : r
      ));
    },
  },
};
</script>

<style scoped>
.fi-dr { display: flex; flex-direction: column; gap: 12px; padding: 16px; overflow-y: auto; position: relative; }

.fi-dr-toolbar { display: flex; align-items: center; justify-content: space-between; }
.fi-dr-hint { font-size: 12px; color: var(--text-muted, #888); }
.fi-dr-add-btn {
  font-size: 12px; font-weight: 600; color: #6c63ff;
  background: none; border: 1px solid #6c63ff;
  border-radius: 5px; padding: 4px 10px; cursor: pointer;
  transition: background 0.15s;
}
.fi-dr-add-btn:hover { background: #f0eeff; }

.fi-dr-list { display: flex; flex-direction: column; gap: 6px; }
.fi-dr-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  background: var(--card-bg, #fafafa);
}
.fi-dr-item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.fi-dr-item-label { font-size: 13px; font-weight: 500; color: var(--text-color, #333); }
.fi-dr-item-key {
  font-size: 11px; font-family: monospace;
  color: var(--text-muted, #888);
}
.fi-dr-mandatory {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--text-color, #555);
  cursor: pointer; white-space: nowrap; flex-shrink: 0;
}
.fi-dr-del {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #bbb); font-size: 12px;
  padding: 2px 4px; border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}
.fi-dr-del:hover { color: #c62828; background: #fce4e4; }
.fi-dr-empty { font-size: 12px; color: var(--text-muted, #aaa); padding: 8px 0; }

/* ---- Picker overlay ---- */
.fi-dr-picker-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center;
}
.fi-dr-picker {
  background: var(--card-bg, #fff);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  width: 420px; max-height: 480px;
  display: flex; flex-direction: column; overflow: hidden;
}
.fi-dr-picker-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  font-size: 14px; font-weight: 600; color: var(--text-color, #333);
}
.fi-dr-picker-close {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #888); font-size: 14px; padding: 2px 6px; border-radius: 4px;
}
.fi-dr-picker-close:hover { background: var(--bg-light-gray, #f0f0f0); }
.fi-dr-picker-search {
  margin: 10px 16px;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 6px; padding: 7px 10px;
  font-size: 13px; outline: none; font-family: inherit;
}
.fi-dr-picker-search:focus { border-color: #6c63ff; }
.fi-dr-picker-list { flex: 1; overflow-y: auto; padding: 0 8px 12px; }
.fi-dr-picker-item {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 9px 10px;
  background: none; border: none; cursor: pointer;
  border-radius: 6px; text-align: start; gap: 8px;
  transition: background 0.1s;
}
.fi-dr-picker-item:hover { background: #f0eeff; }
.fi-dr-picker-name { font-size: 13px; font-weight: 500; color: var(--text-color, #333); flex: 1; }
.fi-dr-picker-key {
  font-size: 11px; font-family: monospace;
  background: #f0eeff; color: #5b50c4;
  padding: 2px 6px; border-radius: 3px; flex-shrink: 0;
}
.fi-dr-picker-empty { padding: 16px; font-size: 13px; color: var(--text-muted, #aaa); text-align: center; }
</style>
