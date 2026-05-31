<template>
  <div class="fi-rf">
    <!-- Load from DocType -->
    <div class="fi-rf-toolbar">
      <span class="fi-rf-hint">{{ __("Fields the agent must collect at this step") }}</span>
      <button
        v-if="targetDoctype"
        class="fi-rf-load-btn"
        :disabled="loadingMeta"
        @click="loadFromDoctype"
      >{{ loadingMeta ? __("Loading…") : __("Load from DocType") }}</button>
    </div>

    <!-- Field rows -->
    <div class="fi-rf-list">
      <div class="fi-rf-list-header">
        <span class="fi-rf-col-head">{{ __("Field Name") }}</span>
        <span class="fi-rf-col-head">{{ __("Label") }}</span>
        <span style="width:28px"></span>
      </div>

      <div v-for="(row, idx) in rows" :key="idx" class="fi-rf-row">
        <input
          class="fi-rf-input fi-rf-mono"
          v-model="row.fieldname"
          @input="emitChange"
          :placeholder="__('fieldname')"
        />
        <input
          class="fi-rf-input"
          v-model="row.label"
          @input="emitChange"
          :placeholder="__('Human label')"
        />
        <button class="fi-rf-del" @click="removeRow(idx)" :title="__('Remove')">✕</button>
      </div>

      <div v-if="!rows.length" class="fi-rf-empty">
        {{ __("No required fields yet.") }}
      </div>
    </div>

    <button class="fi-rf-add-btn" @click="addRow">+ {{ __("Add Field") }}</button>
  </div>
</template>

<script>
export default {
  name: "RequiredFields",

  props: {
    value:         { type: String, default: null },
    targetDoctype: { type: String, default: null },
  },

  emits: ["update:value"],

  data() {
    return {
      rows: [],
      loadingMeta: false,
    };
  },

  watch: {
    value: {
      immediate: true,
      handler(v) {
        this.rows = this.parseValue(v);
      },
    },
  },

  methods: {
    parseValue(v) {
      if (!v) return [];
      try {
        const obj = typeof v === "string" ? JSON.parse(v) : v;
        return Object.entries(obj).map(([fieldname, label]) => ({ fieldname, label }));
      } catch (_) {
        return [];
      }
    },

    emitChange() {
      const obj = {};
      for (const row of this.rows) {
        if (row.fieldname.trim()) obj[row.fieldname.trim()] = row.label;
      }
      this.$emit("update:value", Object.keys(obj).length ? JSON.stringify(obj) : null);
    },

    addRow() {
      this.rows.push({ fieldname: "", label: "" });
    },

    removeRow(idx) {
      this.rows.splice(idx, 1);
      this.emitChange();
    },

    async loadFromDoctype() {
      if (!this.targetDoctype || this.loadingMeta) return;
      this.loadingMeta = true;
      try {
        const meta = await frappe.call({
          method: "frappe.client.get",
          args: { doctype: "DocType", name: this.targetDoctype },
        });
        const fields = (meta.message?.fields || [])
          .filter((f) => f.reqd && f.fieldname && !["Section Break", "Column Break", "Tab Break"].includes(f.fieldtype))
          .map((f) => ({ fieldname: f.fieldname, label: f.label || f.fieldname }));

        const existing = new Set(this.rows.map((r) => r.fieldname));
        for (const f of fields) {
          if (!existing.has(f.fieldname)) this.rows.push(f);
        }
        this.emitChange();
      } catch (_) {
        frappe.show_alert({ message: __("Could not load DocType fields."), indicator: "orange" });
      } finally {
        this.loadingMeta = false;
      }
    },
  },
};
</script>

<style scoped>
.fi-rf { display: flex; flex-direction: column; gap: 10px; padding: 16px; overflow-y: auto; }

.fi-rf-toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
.fi-rf-hint { font-size: 12px; color: var(--text-muted, #888); }
.fi-rf-load-btn {
  font-size: 12px; font-weight: 600; color: #6c63ff;
  background: none; border: 1px solid #6c63ff;
  border-radius: 5px; padding: 4px 10px; cursor: pointer;
  transition: background 0.15s;
}
.fi-rf-load-btn:hover { background: #f0eeff; }
.fi-rf-load-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.fi-rf-list { display: flex; flex-direction: column; gap: 4px; }
.fi-rf-list-header {
  display: flex; gap: 6px; padding: 0 2px;
}
.fi-rf-col-head {
  flex: 1; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.4px;
  color: var(--text-muted, #aaa);
}

.fi-rf-row { display: flex; align-items: center; gap: 6px; }
.fi-rf-input {
  flex: 1; border: 1px solid var(--border-color, #d1d5db);
  border-radius: 5px; padding: 5px 8px;
  font-size: 12px; font-family: inherit;
  background: var(--control-bg, #fff); color: var(--text-color, #333); outline: none;
}
.fi-rf-input:focus { border-color: #6c63ff; }
.fi-rf-mono { font-family: monospace; }
.fi-rf-del {
  width: 22px; height: 22px; flex-shrink: 0;
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #bbb); border-radius: 4px; font-size: 11px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, background 0.15s;
}
.fi-rf-del:hover { color: #c62828; background: #fce4e4; }

.fi-rf-empty { font-size: 12px; color: var(--text-muted, #aaa); padding: 8px 0; }

.fi-rf-add-btn {
  align-self: flex-start;
  font-size: 12px; font-weight: 600; color: #6c63ff;
  background: none; border: none; cursor: pointer; padding: 0;
}
.fi-rf-add-btn:hover { opacity: 0.75; }
</style>
