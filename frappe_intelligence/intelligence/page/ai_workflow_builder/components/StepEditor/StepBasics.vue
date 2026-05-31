<template>
  <div class="fi-sb">
    <!-- step_key -->
    <div class="fi-sb-row">
      <label class="fi-sb-label">{{ __("Step Key") }}</label>
      <input
        class="fi-sb-input fi-sb-mono"
        :value="step.step_key"
        @change="emit('step_key', $event.target.value.trim())"
        :placeholder="__('e.g. create_customer')"
      />
      <span class="fi-sb-hint">{{ __("Unique slug, no spaces") }}</span>
    </div>

    <!-- prompt_to_user -->
    <div class="fi-sb-row">
      <label class="fi-sb-label">{{ __("Prompt to User") }}</label>
      <textarea
        class="fi-sb-input fi-sb-textarea"
        :value="step.prompt_to_user"
        @input="emit('prompt_to_user', $event.target.value)"
        :placeholder="__('Opening message shown to the user at this step')"
        rows="3"
      ></textarea>
    </div>

    <!-- target_doctype -->
    <div class="fi-sb-row">
      <label class="fi-sb-label">{{ __("Target DocType") }}</label>
      <div class="fi-sb-autocomplete">
        <input
          class="fi-sb-input"
          v-model="doctypeSearch"
          @input="onDoctypeInput"
          @blur="closeDoctypeDrop"
          :placeholder="step.target_doctype || __('Search DocType…')"
        />
        <div v-if="doctypeSuggestions.length" class="fi-sb-drop">
          <button
            v-for="dt in doctypeSuggestions"
            :key="dt"
            class="fi-sb-drop-item"
            @mousedown.prevent="selectDoctype(dt)"
          >{{ dt }}</button>
        </div>
      </div>
      <button
        v-if="step.target_doctype"
        class="fi-sb-clear"
        @click="emit('target_doctype', null)"
        :title="__('Clear')"
      >✕</button>
    </div>

    <!-- next_step_key -->
    <div class="fi-sb-row">
      <label class="fi-sb-label">{{ __("Next Step") }}</label>
      <select
        class="fi-sb-input fi-sb-select"
        :value="step.next_step_key || ''"
        @change="emit('next_step_key', $event.target.value || null)"
      >
        <option value="">— {{ __("End of workflow") }} —</option>
        <option
          v-for="s in siblingSteps"
          :key="s.step_key"
          :value="s.step_key"
        >{{ s.step_key }}</option>
      </select>
    </div>

    <!-- completion_check -->
    <div class="fi-sb-row">
      <label class="fi-sb-label">{{ __("Completion Check") }}</label>
      <input
        class="fi-sb-input fi-sb-mono"
        :value="step.completion_check || ''"
        @change="emit('completion_check', $event.target.value.trim() || null)"
        :placeholder="__('Optional Python callable')"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: "StepBasics",

  props: {
    step:  { type: Object, required: true },
    steps: { type: Array,  default: () => [] },
  },

  emits: ["update"],

  data() {
    return {
      doctypeSearch: "",
      doctypeSuggestions: [],
      _dtTimer: null,
    };
  },

  computed: {
    siblingSteps() {
      return this.steps.filter((s) => s.step_key !== this.step.step_key);
    },
  },

  methods: {
    emit(field, value) {
      this.$emit("update", { [field]: value });
    },

    onDoctypeInput() {
      clearTimeout(this._dtTimer);
      const q = this.doctypeSearch.trim();
      if (q.length < 2) { this.doctypeSuggestions = []; return; }
      this._dtTimer = setTimeout(() => this.searchDoctypes(q), 250);
    },

    async searchDoctypes(q) {
      try {
        const res = await frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "DocType",
            filters: [["name", "like", `%${q}%`]],
            fields: ["name"],
            limit: 10,
          },
        });
        this.doctypeSuggestions = (res.message || []).map((r) => r.name);
      } catch (_) {
        this.doctypeSuggestions = [];
      }
    },

    selectDoctype(dt) {
      this.doctypeSearch = "";
      this.doctypeSuggestions = [];
      this.emit("target_doctype", dt);
    },

    closeDoctypeDrop() {
      setTimeout(() => { this.doctypeSuggestions = []; }, 150);
    },
  },
};
</script>

<style scoped>
.fi-sb { display: flex; flex-direction: column; gap: 14px; padding: 16px; overflow-y: auto; }

.fi-sb-row { display: flex; flex-direction: column; gap: 4px; }
.fi-sb-label {
  font-size: 11px; font-weight: 600;
  color: var(--text-muted, #888);
  text-transform: uppercase; letter-spacing: 0.4px;
}
.fi-sb-input {
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 6px; padding: 6px 10px;
  font-size: 13px; font-family: inherit;
  background: var(--control-bg, #fff);
  color: var(--text-color, #333); outline: none;
}
.fi-sb-input:focus { border-color: #6c63ff; }
.fi-sb-mono { font-family: monospace; }
.fi-sb-textarea { resize: vertical; min-height: 64px; }
.fi-sb-select { cursor: pointer; }
.fi-sb-hint { font-size: 11px; color: var(--text-muted, #aaa); }

.fi-sb-autocomplete { position: relative; }
.fi-sb-drop {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  max-height: 180px; overflow-y: auto;
}
.fi-sb-drop-item {
  display: block; width: 100%; text-align: start;
  padding: 7px 10px; font-size: 13px;
  background: none; border: none; cursor: pointer;
  color: var(--text-color, #333);
}
.fi-sb-drop-item:hover { background: #f0eeff; }

.fi-sb-clear {
  align-self: flex-start; background: none; border: none;
  color: var(--text-muted, #aaa); cursor: pointer;
  font-size: 12px; padding: 2px 4px; border-radius: 4px;
  margin-top: -28px; align-self: flex-end;
}
.fi-sb-clear:hover { color: #c62828; background: #fce4e4; }
</style>
