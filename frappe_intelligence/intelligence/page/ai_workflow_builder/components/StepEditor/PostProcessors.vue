<template>
  <div class="fi-pp">
    <div class="fi-pp-toolbar">
      <span class="fi-pp-hint">{{ __("Post-processors run after the agent completes this step") }}</span>
      <button class="fi-pp-add-btn" @click="showPicker = true">+ {{ __("Assign Processor") }}</button>
    </div>

    <div class="fi-pp-list">
      <div v-for="asgn in stepAssignments" :key="asgn._id || asgn.name" class="fi-pp-item">
        <div class="fi-pp-item-info">
          <span class="fi-pp-item-name">{{ asgn.processor_name || asgn.processor }}</span>
          <span class="fi-pp-item-method">{{ asgn.callback_method }}</span>
        </div>
        <a
          :href="'/app/ai-post-processor/' + encodeURIComponent(asgn.processor)"
          target="_blank"
          class="fi-pp-edit-link"
        >{{ __("Edit") }} →</a>
        <button class="fi-pp-del" @click="removeAsgn(asgn)" :title="__('Remove')">✕</button>
      </div>

      <div v-if="!stepAssignments.length" class="fi-pp-empty">
        {{ __("No post-processors assigned to this step.") }}
      </div>
    </div>

    <!-- Picker overlay -->
    <div v-if="showPicker" class="fi-pp-picker-overlay" @click.self="showPicker = false">
      <div class="fi-pp-picker">
        <div class="fi-pp-picker-header">
          <span>{{ __("Select Post-Processor") }}</span>
          <button class="fi-pp-picker-close" @click="showPicker = false">✕</button>
        </div>
        <input
          class="fi-pp-picker-search"
          v-model="pickerSearch"
          :placeholder="__('Search…')"
          autofocus
        />
        <div class="fi-pp-picker-list">
          <button
            v-for="p in filteredProcessors"
            :key="p.name"
            class="fi-pp-picker-item"
            @click="addAsgn(p)"
          >
            <span class="fi-pp-picker-name">{{ p.processor_name || p.name }}</span>
            <span class="fi-pp-picker-method">{{ p.callback_method }}</span>
          </button>
          <div v-if="!filteredProcessors.length" class="fi-pp-picker-empty">
            {{ __("No processors found.") }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
let _nextId = 1;

export default {
  name: "PostProcessors",

  props: {
    stepKey:              { type: String, required: true },
    assignments:          { type: Array,  default: () => [] },
    availableProcessors:  { type: Array,  default: () => [] },
  },

  emits: ["update"],

  data() {
    return {
      showPicker: false,
      pickerSearch: "",
    };
  },

  computed: {
    stepAssignments() {
      return this.assignments.filter((a) => a.step_key === this.stepKey);
    },
    filteredProcessors() {
      const q = this.pickerSearch.toLowerCase();
      const used = new Set(this.stepAssignments.map((a) => a.processor));
      return this.availableProcessors.filter(
        (p) => !used.has(p.name) &&
               ((p.processor_name || p.name).toLowerCase().includes(q) ||
                (p.callback_method || "").toLowerCase().includes(q))
      );
    },
  },

  methods: {
    addAsgn(p) {
      const newAsgn = {
        _id: `new_${_nextId++}`,
        step_key:        this.stepKey,
        processor:       p.name,
        processor_name:  p.processor_name || p.name,
        callback_method: p.callback_method || "",
      };
      this.$emit("update", [...this.assignments, newAsgn]);
      this.showPicker = false;
      this.pickerSearch = "";
    },

    removeAsgn(asgn) {
      this.$emit("update", this.assignments.filter((a) => a !== asgn));
    },
  },
};
</script>

<style scoped>
.fi-pp { display: flex; flex-direction: column; gap: 12px; padding: 16px; overflow-y: auto; position: relative; }

.fi-pp-toolbar { display: flex; align-items: center; justify-content: space-between; }
.fi-pp-hint { font-size: 12px; color: var(--text-muted, #888); }
.fi-pp-add-btn {
  font-size: 12px; font-weight: 600; color: #6c63ff;
  background: none; border: 1px solid #6c63ff;
  border-radius: 5px; padding: 4px 10px; cursor: pointer;
  transition: background 0.15s;
}
.fi-pp-add-btn:hover { background: #f0eeff; }

.fi-pp-list { display: flex; flex-direction: column; gap: 6px; }
.fi-pp-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  background: var(--card-bg, #fafafa);
}
.fi-pp-item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.fi-pp-item-name { font-size: 13px; font-weight: 500; color: var(--text-color, #333); }
.fi-pp-item-method {
  font-size: 11px; font-family: monospace;
  color: var(--text-muted, #888);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fi-pp-edit-link {
  font-size: 12px; color: #6c63ff; text-decoration: none;
  white-space: nowrap; flex-shrink: 0;
}
.fi-pp-edit-link:hover { text-decoration: underline; }
.fi-pp-del {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #bbb); font-size: 12px;
  padding: 2px 4px; border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}
.fi-pp-del:hover { color: #c62828; background: #fce4e4; }
.fi-pp-empty { font-size: 12px; color: var(--text-muted, #aaa); padding: 8px 0; }

/* Picker */
.fi-pp-picker-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.3);
  display: flex; align-items: center; justify-content: center;
}
.fi-pp-picker {
  background: var(--card-bg, #fff);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  width: 420px; max-height: 480px;
  display: flex; flex-direction: column; overflow: hidden;
}
.fi-pp-picker-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  font-size: 14px; font-weight: 600; color: var(--text-color, #333);
}
.fi-pp-picker-close {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #888); font-size: 14px; padding: 2px 6px; border-radius: 4px;
}
.fi-pp-picker-close:hover { background: var(--bg-light-gray, #f0f0f0); }
.fi-pp-picker-search {
  margin: 10px 16px;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 6px; padding: 7px 10px;
  font-size: 13px; outline: none; font-family: inherit;
}
.fi-pp-picker-search:focus { border-color: #6c63ff; }
.fi-pp-picker-list { flex: 1; overflow-y: auto; padding: 0 8px 12px; }
.fi-pp-picker-item {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 9px 10px;
  background: none; border: none; cursor: pointer;
  border-radius: 6px; text-align: start; gap: 8px;
  transition: background 0.1s;
}
.fi-pp-picker-item:hover { background: #f0eeff; }
.fi-pp-picker-name { font-size: 13px; font-weight: 500; color: var(--text-color, #333); flex: 1; }
.fi-pp-picker-method {
  font-size: 11px; font-family: monospace;
  color: var(--text-muted, #888); flex-shrink: 0;
  max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.fi-pp-picker-empty { padding: 16px; font-size: 13px; color: var(--text-muted, #aaa); text-align: center; }
</style>
