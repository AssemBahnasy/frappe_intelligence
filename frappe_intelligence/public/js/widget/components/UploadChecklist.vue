<template>
  <div class="fi-upload-view">
    <div class="fi-upload-header">
      <span class="fi-upload-title">{{ __("Upload Document") }}</span>
      <button class="fi-upload-back" @click="$emit('cancel')" aria-label="Back">✕</button>
    </div>

    <div class="fi-upload-body">
      <!-- Progress state -->
      <div v-if="uploading" class="fi-upload-progress">
        <div class="fi-upload-spinner"></div>
        <div class="fi-upload-msg">{{ progressText }}</div>
      </div>

      <template v-else>
        <!-- Global mode hint -->
        <div v-if="widgetMode === 'global'" class="fi-global-hint">
          <span class="fi-hint-icon">🔍</span>
          <p>{{ __("Upload any document. I'll identify it and suggest where to save it.") }}</p>
        </div>

        <!-- Required docs (proactive / agent mode) -->
        <template v-if="widgetMode !== 'global' && requiredDocs.length">
          <p class="fi-cl-label">{{ __("Required documents") }}</p>
          <button
            v-for="doc in requiredDocs"
            :key="doc.document_type_key"
            class="fi-cl-row fi-cl-highlight"
            @click="pickFile(doc.document_type_key)"
          >
            <span class="fi-cl-icon">⚠️</span>
            <span>{{ doc.label }}</span>
          </button>
        </template>

        <!-- Auto-detect -->
        <button class="fi-cl-row" @click="pickFile(null)">
          <span class="fi-cl-icon">{{ widgetMode === 'global' ? '📤' : '🔍' }}</span>
          <span>{{ widgetMode === 'global' ? __("Upload & Identify") : __("Auto-detect") }}</span>
        </button>

        <!-- All templates -->
        <template v-if="filteredTemplates.length">
          <p class="fi-cl-label">{{ __("All templates") }}</p>
          <button
            v-for="t in filteredTemplates"
            :key="t.document_type_key"
            class="fi-cl-row"
            @click="pickFile(t.document_type_key)"
          >
            <span class="fi-cl-icon">📄</span>
            <span>{{ t.document_name }}</span>
          </button>
        </template>
      </template>
    </div>

    <input type="file" ref="fileInput" style="display:none" @change="onFileSelected" />
  </div>
</template>

<script>
export default {
  name: "UploadChecklist",
  props: {
    widgetMode: { type: String, default: "global" },
    requiredDocs: { type: Array, default: () => [] },
  },
  emits: ["result", "cancel"],
  data() {
    return {
      templates: [],
      uploading: false,
      progressText: "",
      pendingDoctype: null,
      logPollTimer: null,
      realtimeHandler: null,
    };
  },
  computed: {
    filteredTemplates() {
      const required = new Set(this.requiredDocs.map((d) => d.document_type_key));
      return this.templates.filter((t) => !required.has(t.document_type_key));
    },
  },
  async created() {
    await this._loadTemplates();
    this._bindRealtime();
  },
  beforeUnmount() {
    this._stopPoller();
    this._unbindRealtime();
  },
  methods: {
    async _loadTemplates() {
      try {
        const res = await frappe.call({ method: "frappe_intelligence.api.list_templates" });
        this.templates = res.message || [];
      } catch (_) {
        this.templates = [];
      }
    },
    _bindRealtime() {
      this.realtimeHandler = (data) => {
        this._stopPoller();
        this.uploading = false;
        this.$emit("result", data.result || data);
      };
      frappe.realtime.on("ai_processing_complete", this.realtimeHandler);
    },
    _unbindRealtime() {
      if (!this.realtimeHandler) return;
      try {
        if (typeof frappe.realtime.off === "function") {
          frappe.realtime.off("ai_processing_complete", this.realtimeHandler);
        } else if (frappe.realtime.socket) {
          frappe.realtime.socket.off("ai_processing_complete", this.realtimeHandler);
        }
      } catch (_) { /* ignore */ }
      this.realtimeHandler = null;
    },
    pickFile(doctype) {
      this.pendingDoctype = doctype;
      this.$refs.fileInput.value = "";
      this.$refs.fileInput.click();
    },
    onFileSelected(e) {
      const file = e.target.files[0];
      if (file) this._uploadFile(file);
    },
    _uploadFile(file) {
      this.uploading = true;
      this.progressText = __("Uploading file…");

      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          this.progressText = `${__("Uploading file…")} ${pct}%`;
        }
      });
      xhr.onreadystatechange = () => {
        if (xhr.readyState !== XMLHttpRequest.DONE) return;
        if (xhr.status !== 200) {
          this.uploading = false;
          this.$emit("result", { status: "failed" });
          return;
        }
        let data;
        try { data = JSON.parse(xhr.responseText); } catch (_) {
          this.uploading = false;
          this.$emit("result", { status: "failed" });
          return;
        }
        const fileUrl = data?.message?.file_url;
        if (!fileUrl) {
          this.uploading = false;
          this.$emit("result", { status: "failed" });
          return;
        }
        this.progressText = __("Queuing document for processing…");
        frappe.call({
          method: "frappe_intelligence.api.process_document",
          args: { file_url: fileUrl, target_doctype: this.pendingDoctype || null },
          callback: (r) => {
            if (r.message?.status === "queued") {
              this.progressText = __("Processing… you'll be notified when done.");
              this._startPoller(r.message.log_name);
            } else {
              this.uploading = false;
              if (r.message) this.$emit("result", r.message);
            }
          },
          error: () => {
            this.uploading = false;
            this.$emit("result", { status: "failed" });
          },
        });
      };
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("is_private", "1");
      fd.append("folder", "Home/Attachments");
      xhr.open("POST", "/api/method/upload_file", true);
      xhr.setRequestHeader("Accept", "application/json");
      xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
      xhr.send(fd);
    },
    _startPoller(logName) {
      this._stopPoller();
      this.logPollTimer = setInterval(() => {
        frappe.call({
          method: "frappe_intelligence.api.get_log_status",
          args: { log_name: logName },
          callback: (r) => {
            const msg = r.message;
            if (!msg) return;
            if (msg.status === "Completed" || msg.status === "Failed") {
              this._stopPoller();
              this.uploading = false;
              this.$emit("result", msg.result);
            }
          },
        });
      }, 5000);
    },
    _stopPoller() {
      if (this.logPollTimer) { clearInterval(this.logPollTimer); this.logPollTimer = null; }
    },
  },
};
</script>

<style scoped>
.fi-upload-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.fi-upload-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  flex-shrink: 0;
}
.fi-upload-title { font-size: 13px; font-weight: 600; }
.fi-upload-back {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #888); font-size: 13px;
  padding: 2px 6px; border-radius: 4px; font-family: inherit;
}
.fi-upload-back:hover { background: var(--bg-light-gray, #f0f0f0); }

.fi-upload-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.fi-upload-progress {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  background: var(--bg-color, #fff);
}
.fi-upload-spinner {
  width: 30px; height: 30px;
  border: 3px solid #e0e0e0;
  border-top-color: var(--primary, #2c9af1);
  border-radius: 50%;
  animation: fi-spin 0.8s linear infinite;
}
@keyframes fi-spin { to { transform: rotate(360deg); } }
.fi-upload-msg { font-size: 12px; color: var(--text-muted, #666); text-align: center; padding: 0 16px; }

.fi-global-hint {
  text-align: center; color: var(--text-muted, #666);
  font-size: 12px; padding: 8px 0 4px;
}
.fi-hint-icon { font-size: 22px; display: block; margin-bottom: 4px; }

.fi-cl-label {
  font-size: 10px; color: var(--text-muted, #888);
  text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px;
}

.fi-cl-row {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  background: var(--bg-color, #fafafa);
  cursor: pointer; text-align: start;
  font-size: 13px; font-family: inherit;
  transition: background 0.15s; width: 100%;
}
.fi-cl-row:hover { background: #f0eeff; border-color: var(--primary, #2c9af1); }
.fi-cl-highlight { border-color: #ffc107; background: #fff8e1; }
.fi-cl-highlight:hover { background: #fff3cd; }
.fi-cl-icon { width: 20px; text-align: center; flex-shrink: 0; }
</style>
