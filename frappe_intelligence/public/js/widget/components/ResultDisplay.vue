<template>
  <div class="fi-result-view">
    <!-- Header -->
    <div class="fi-result-header">
      <div class="fi-result-meta">
        <span class="fi-badge">{{ result.document_type_key || "—" }}</span>
        <span :class="['fi-confidence', parseFloat(confidence) >= 70 ? 'fi-good' : 'fi-warn']">
          {{ confidence }}% {{ __("confidence") }}
        </span>
      </div>
      <div class="fi-result-actions-header">
        <button v-if="view === 'result'" class="fi-res-btn fi-res-secondary" @click="openCorrection">
          {{ __("Correct") }}
        </button>
        <button class="fi-res-btn fi-res-primary" @click="handleDone">{{ __("Done") }}</button>
      </div>
    </div>

    <!-- Low-confidence review banner -->
    <div v-if="result.needs_review && view === 'review'" class="fi-review-banner">
      ⚠️ {{ __("Low confidence — edit if needed, then accept.") }}
    </div>

    <!-- Body -->
    <div class="fi-result-body">
      <!-- Correction form -->
      <template v-if="view === 'correct'">
        <div v-for="(_, key) in editedData" :key="key" class="fi-correction-row">
          <label class="fi-correction-label">{{ key }}</label>
          <input v-model="editedData[key]" class="fi-correction-input" dir="auto" />
        </div>
        <button class="fi-res-btn fi-res-primary fi-submit-btn" @click="submitCorrection">
          {{ __("Submit Correction") }}
        </button>
      </template>

      <!-- Result / Review table -->
      <template v-else>
        <table class="fi-result-table">
          <tbody>
            <tr v-for="(val, key) in result.extracted_data || {}" :key="key">
              <td class="fi-key">{{ key }}</td>
              <td class="fi-val" dir="auto">
                <input v-if="view === 'review'" v-model="editedData[key]" class="fi-review-input" dir="auto" />
                <template v-else>
                  <em v-if="val === null || val === undefined || val === ''" class="fi-empty">—</em>
                  <span v-else>{{ val }}</span>
                </template>
              </td>
            </tr>
            <tr v-if="!Object.keys(result.extracted_data || {}).length">
              <td colspan="2" style="color:var(--text-muted,#888)">{{ __("No data extracted.") }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Review mode buttons -->
        <div v-if="view === 'review'" class="fi-review-actions">
          <button class="fi-res-btn fi-res-secondary" @click="$emit('done')">{{ __("Discard") }}</button>
          <button class="fi-res-btn fi-res-primary" @click="acceptReview">{{ __("Accept") }}</button>
        </div>
      </template>

      <p v-if="result.log_name" class="fi-log-ref">
        {{ __("Log") }}:
        <a :href="`/app/ai-processing-log/${result.log_name}`" target="_blank">{{ result.log_name }}</a>
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: "ResultDisplay",
  props: {
    result: { type: Object, required: true },
    currentDoctype: { type: String, default: null },
    currentDocname: { type: String, default: null },
  },
  emits: ["done"],
  data() {
    return {
      view: this.result.needs_review ? "review" : "result",
      editedData: Object.fromEntries(
        Object.entries(this.result.extracted_data || {}).map(([k, v]) => [k, String(v ?? "")])
      ),
    };
  },
  computed: {
    confidence() {
      return ((this.result.confidence_score || 0) * 100).toFixed(1);
    },
  },
  methods: {
    openCorrection() {
      this.editedData = Object.fromEntries(
        Object.entries(this.result.extracted_data || {}).map(([k, v]) => [k, String(v ?? "")])
      );
      this.view = "correct";
    },
    handleDone() {
      this.$emit("done");
    },
    async acceptReview() {
      const original = this.result.extracted_data || {};
      const hasEdits = Object.keys(this.editedData).some(
        (k) => this.editedData[k] !== String(original[k] ?? "")
      );
      const doConfirm = () => {
        frappe.call({
          method: "frappe_intelligence.api.documents.confirm_extraction",
          args: {
            log_name: this.result.log_name,
            doctype: this.currentDoctype,
            docname: this.currentDocname,
          },
          callback: () => {
            frappe.show_alert({ message: __("Extraction confirmed!"), indicator: "green" }, 4);
            this.$emit("done");
          },
        });
      };
      if (hasEdits) {
        frappe.call({
          method: "frappe_intelligence.api.documents.submit_correction",
          args: { log_name: this.result.log_name, corrected_extraction: this.editedData },
          callback: doConfirm,
        });
      } else {
        doConfirm();
      }
    },
    submitCorrection() {
      frappe.call({
        method: "frappe_intelligence.api.documents.submit_correction",
        args: { log_name: this.result.log_name, corrected_extraction: this.editedData },
        callback: () => {
          frappe.show_alert({ message: __("Correction saved!"), indicator: "green" }, 5);
          this.$emit("done");
        },
      });
    },
  },
};
</script>

<style scoped>
.fi-result-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.fi-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 6px;
}
.fi-result-meta { display: flex; align-items: center; gap: 8px; }
.fi-result-actions-header { display: flex; gap: 6px; }

.fi-badge {
  background: #ede9ff; color: #5b50c4;
  border-radius: 4px; padding: 2px 7px;
  font-size: 11px; font-weight: 600;
}
.fi-confidence { font-size: 12px; font-weight: 600; }
.fi-good { color: #388e3c; }
.fi-warn { color: #f57c00; }

.fi-review-banner {
  background: #fff8e1;
  border-bottom: 1px solid #ffe082;
  padding: 6px 12px;
  font-size: 12px;
  color: #5d4037;
  flex-shrink: 0;
}

.fi-result-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fi-result-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.fi-result-table td { padding: 5px 6px; border-bottom: 1px solid var(--border-color, #f0f0f0); }
.fi-key { color: var(--text-muted, #888); width: 42%; word-break: break-all; }
.fi-val { font-weight: 500; }
.fi-empty { color: #ccc; font-style: italic; }

.fi-review-input {
  border: 1px solid var(--border-color, #ddd);
  border-radius: 4px; padding: 3px 7px;
  font-size: 12px; width: 100%;
  box-sizing: border-box; font-family: inherit;
  background: var(--control-bg, #fff);
}
.fi-review-input:focus { border-color: var(--primary, #2c9af1); outline: none; }

.fi-review-actions { display: flex; gap: 8px; padding-top: 4px; }

.fi-correction-row { display: flex; flex-direction: column; gap: 2px; }
.fi-correction-label { font-size: 11px; color: var(--text-muted, #888); }
.fi-correction-input {
  border: 1px solid var(--border-color, #ddd);
  border-radius: 6px; padding: 6px 9px;
  font-size: 13px; font-family: inherit;
  background: var(--control-bg, #fff);
}
.fi-correction-input:focus { border-color: var(--primary, #2c9af1); outline: none; }

.fi-submit-btn { width: 100%; margin-top: 4px; }

.fi-res-btn {
  padding: 6px 12px; border-radius: 6px;
  border: none; cursor: pointer;
  font-size: 13px; font-weight: 500;
  font-family: inherit; flex: 1;
}
.fi-res-primary { background: var(--primary, #2c9af1); color: #fff; }
.fi-res-secondary { background: var(--bg-light-gray, #f0f0f0); color: var(--text-color, #333); }

.fi-log-ref { font-size: 11px; color: var(--text-muted, #aaa); margin-top: auto; }
.fi-log-ref a { color: var(--text-muted, #aaa); }
</style>
