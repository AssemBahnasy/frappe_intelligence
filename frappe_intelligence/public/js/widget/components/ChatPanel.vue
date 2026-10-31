<template>
  <div class="fi-chat-panel-inner">

    <!-- Header -->
    <div class="fi-chat-header">
      <div class="fi-header-left">
        <div class="fi-header-avatar">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2"/>
            <circle cx="12" cy="5" r="2"/>
            <line x1="12" y1="7" x2="12" y2="11"/>
            <line x1="8" y1="15" x2="8" y2="15"/>
            <line x1="12" y1="15" x2="12" y2="15"/>
            <line x1="16" y1="15" x2="16" y2="15"/>
          </svg>
        </div>
        <div class="fi-header-title-block">
          <span class="fi-header-title">{{ __("AI Assistant") }}</span>
          <span class="fi-header-status">{{ __("Online") }}</span>
        </div>
      </div>
      <div class="fi-header-right">
        <ModeToggle v-model="mode" />
        <WorkflowSelector
          v-if="mode === 'agent'"
          v-model="selectedWorkflow"
          :workflows="workflows"
        />
      </div>
    </div>

    <!-- Body -->
    <div class="fi-chat-body">
      <UploadChecklist
        v-if="view === 'upload'"
        :widget-mode="widgetModeFromInstance"
        :required-docs="requiredDocs"
        @result="onUploadResult"
        @cancel="view = 'chat'"
      />
      <ResultDisplay
        v-else-if="view === 'result' && uploadResult"
        :result="uploadResult"
        :current-doctype="currentDoctype"
        :current-docname="currentDocname"
        @done="onResultDone"
      />
      <ChatFeed
        v-else
        :turns="turns"
        :loading="loading"
        :mode="mode"
        :selected-workflow="selectedWorkflow"
        @suggest-workflow="onSuggestWorkflow"
      />
    </div>

    <!-- Footer -->
    <div v-if="view === 'chat'" class="fi-chat-footer">
      <button class="fi-attach-btn" @click="view = 'upload'" :title="__('Upload document')">
        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
        </svg>
      </button>
      <textarea
        v-model="inputText"
        class="fi-chat-input"
        :placeholder="inputPlaceholder"
        rows="1"
        @keydown.enter.exact.prevent="sendMessage"
        @input="autoResize"
        ref="inputEl"
      ></textarea>
      <!-- Mic button -->
      <button
        class="fi-mic-btn"
        :class="{ 'fi-mic-recording': voiceState === 'recording' }"
        :disabled="voiceState === 'transcribing' || loading"
        @click="toggleVoice"
        :aria-label="voiceState === 'recording' ? __('Stop recording') : __('Voice input')"
        :title="voiceState === 'recording' ? __('Stop recording') : __('Voice input')"
      >
        <!-- Idle: microphone -->
        <svg v-if="voiceState === 'idle'" xmlns="http://www.w3.org/2000/svg" width="15" height="15"
             viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
        <!-- Recording: stop square -->
        <svg v-else-if="voiceState === 'recording'" xmlns="http://www.w3.org/2000/svg" width="13" height="13"
             viewBox="0 0 24 24" fill="currentColor">
          <rect x="4" y="4" width="16" height="16" rx="2"/>
        </svg>
        <!-- Transcribing: spinner -->
        <span v-else class="fi-mic-spinner"></span>
      </button>
      <button
        class="fi-send-btn"
        :class="{ 'fi-send-ready': canSend }"
        :disabled="!canSend"
        @click="sendMessage"
        :aria-label="__('Send')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      </button>
    </div>

  </div>
</template>

<script>
import ModeToggle       from "./ModeToggle.vue";
import WorkflowSelector from "./WorkflowSelector.vue";
import ChatFeed         from "./ChatFeed.vue";
import UploadChecklist  from "./UploadChecklist.vue";
import ResultDisplay    from "./ResultDisplay.vue";

export default {
  name: "ChatPanel",
  components: { ModeToggle, WorkflowSelector, ChatFeed, UploadChecklist, ResultDisplay },

  props: {
    widgetInstance:  { type: Object, default: null },
    currentDoctype:  { type: String, default: null },
    currentDocname:  { type: String, default: null },
  },

  data() {
    return {
      mode:             "ask",
      selectedWorkflow: null,
      workflows:        [],
      turns:            [],
      inputText:        "",
      loading:          false,
      view:             "chat",
      uploadResult:     null,
      streamHandler:    null,
      voiceState:       "idle",   // "idle" | "recording" | "transcribing"
      _voiceRecorder:   null,
      _voiceChunks:     [],
    };
  },

  computed: {
    canSend() { return this.inputText.trim().length > 0 && !this.loading; },
    inputPlaceholder() {
      return this.mode === "agent" && this.selectedWorkflow
        ? __("Continue workflow…")
        : __("Ask anything…");
    },
    widgetModeFromInstance() {
      return this.widgetInstance?._widgetMode || "global";
    },
    requiredDocs() {
      return this.widgetInstance?._requiredDocs || [];
    },
  },

  async created() {
    await this._loadWorkflows();
    this._bindStreaming();
  },

  beforeUnmount() {
    this._unbindStreaming();
  },

  methods: {
    onSuggestWorkflow()    { this.mode = "agent"; },
    onUploadResult(result) { this.uploadResult = result; this.view = "result"; },
    onResultDone()         { this.uploadResult = null;   this.view = "chat"; },

    autoResize() {
      const el = this.$refs.inputEl;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    },

    async _loadWorkflows() {
      try {
        const res = await frappe.call({ method: "frappe_intelligence.api.builder.list_workflows" });
        this.workflows = res.message || [];
      } catch (_) {
        this.workflows = [];
      }
    },

    _bindStreaming() {
      this.streamHandler = (data) => {
        const last = this.turns[this.turns.length - 1];
        if (!last || last.role !== "assistant" || !last.streaming) return;
        if (data.done) { last.streaming = false; return; }
        if (last.content === "…") last.content = "";
        last.content += data.chunk;
      };
      frappe.realtime.on("ai_stream_chunk", this.streamHandler);
    },

    _unbindStreaming() {
      if (!this.streamHandler) return;
      try {
        if (typeof frappe.realtime.off === "function") {
          frappe.realtime.off("ai_stream_chunk", this.streamHandler);
        } else if (frappe.realtime.socket) {
          frappe.realtime.socket.off("ai_stream_chunk", this.streamHandler);
        }
      } catch (_) {}
      this.streamHandler = null;
    },

    async sendMessage() {
      const text = this.inputText.trim();
      if (!text || this.loading) return;

      this.turns.push({ role: "user",      content: text, action: null, actionData: null });
      this.turns.push({ role: "assistant", content: "…", streaming: true, action: null, actionData: null });
      const aIdx = this.turns.length - 1;
      this.inputText = "";
      this.loading = true;

      // reset textarea height
      this.$nextTick(() => {
        const el = this.$refs.inputEl;
        if (el) el.style.height = "auto";
      });

      try {
        const res = await frappe.call({
          method: "frappe_intelligence.api.chat.handle_widget_input",
          args: {
            input_type:    "text",
            text_input:    text,
            doctype:       this.currentDoctype,
            docname:       this.currentDocname,
            chat_mode:     this.mode,
            workflow_key:  this.mode === "agent" ? this.selectedWorkflow : null,
          },
        });

        const msg = res?.message;
        const t = this.turns[aIdx];
        if (t.content === "…") {
          t.content = typeof msg === "string"
            ? msg
            : msg?.reply || msg?.result || __("No response from model.");
        }
        t.streaming = false;
        if (msg?.action) { t.action = msg.action; t.actionData = msg.action_data; }

      } catch (err) {
        const t = this.turns[aIdx];
        t.content = err?.message || __("An error occurred. Please try again.");
        t.streaming = false;
      } finally {
        this.loading = false;
      }
    },

    // ── Voice ──────────────────────────────────────────────────────────────
    toggleVoice() {
      if (this.voiceState === "recording") this._stopVoice();
      else if (this.voiceState === "idle")  this._startVoice();
    },

    _startVoice() {
      if (!navigator.mediaDevices?.getUserMedia) {
        frappe.msgprint(__("Microphone access requires a secure connection (HTTPS or localhost)."));
        return;
      }
      this._voiceChunks = [];
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then((stream) => {
          const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
          this._voiceRecorder = recorder;
          recorder.ondataavailable = (e) => {
            if (e.data.size > 0) this._voiceChunks.push(e.data);
          };
          recorder.onstop = () => {
            const blob = new Blob(this._voiceChunks, { type: "audio/webm" });
            stream.getTracks().forEach((t) => t.stop());
            this._transcribeVoice(blob);
          };
          recorder.start();
          this.voiceState = "recording";
        })
        .catch((err) => {
          frappe.msgprint(`${__("Microphone error")}: ${err.message}`);
        });
    },

    _stopVoice() {
      if (this._voiceRecorder) {
        this._voiceRecorder.stop();
        this.voiceState = "transcribing";
      }
    },

    async _transcribeVoice(blob) {
      try {
        const fd = new FormData();
        fd.append("file", blob, "voice_command.webm");
        fd.append("is_private", "1");
        const resp = await fetch("/api/method/upload_file", {
          method: "POST",
          headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
          body: fd,
        });
        const data = await resp.json();
        const fileUrl = data?.message?.file_url;
        if (!fileUrl) throw new Error("Upload failed");

        const r = await frappe.call({
          method: "frappe_intelligence.api.chat.handle_widget_input",
          args: {
            input_type:  "voice",
            file_url:    fileUrl,
            doctype:     this.currentDoctype,
            docname:     this.currentDocname,
          },
        });
        const transcript = r?.message?.transcript;
        if (transcript) {
          this.inputText = transcript;
          this.$nextTick(() => this.autoResize());
        }
      } catch (err) {
        frappe.msgprint(`${__("Transcription failed")}: ${err.message}`);
      } finally {
        this.voiceState = "idle";
        this._voiceRecorder = null;
      }
    },
  },
};
</script>

<style scoped>
.fi-chat-panel-inner {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: var(--card-bg, #fff);
}

/* ── Header ── */
.fi-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  background: var(--primary, #2c9af1);
  flex-shrink: 0;
}
.fi-header-left {
  display: flex; align-items: center; gap: 9px; min-width: 0;
}
.fi-header-avatar {
  width: 30px; height: 30px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.fi-header-title-block {
  display: flex; flex-direction: column; gap: 1px; min-width: 0;
}
.fi-header-title {
  font-size: 13px; font-weight: 600; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fi-header-status {
  font-size: 10px; color: rgba(255,255,255,0.75);
  display: flex; align-items: center; gap: 4px;
}
.fi-header-status::before {
  content: "";
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #4ade80;
  display: inline-block;
}
.fi-header-right {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
}

/* ── Body ── */
.fi-chat-body {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column;
  overflow: hidden;
}

/* ── Footer ── */
.fi-chat-footer {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  padding: 10px 12px;
  border-top: 1px solid var(--border-color, #e4e4e7);
  flex-shrink: 0;
  background: var(--card-bg, #fff);
}

.fi-attach-btn {
  flex-shrink: 0;
  width: 32px; height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-color, #d1d5db);
  background: transparent;
  cursor: pointer;
  color: var(--text-muted, #6c757d);
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.fi-attach-btn:hover {
  background: var(--control-bg, #f4f4f5);
  color: var(--text-color, #1a1a1a);
}

.fi-chat-input {
  flex: 1;
  resize: none;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 13px;
  line-height: 1.45;
  background: var(--control-bg, #f4f4f5);
  color: var(--text-color, #1a1a1a);
  outline: none;
  font-family: inherit;
  min-height: 32px;
  max-height: 120px;
  overflow-y: auto;
  transition: border-color 0.15s;
}
.fi-chat-input:focus {
  border-color: var(--primary, #2c9af1);
  background: var(--card-bg, #fff);
}
.fi-chat-input::placeholder { color: var(--text-muted, #9ca3af); }

.fi-send-btn {
  flex-shrink: 0;
  width: 32px; height: 32px;
  border-radius: 8px;
  border: none;
  background: var(--control-bg, #f4f4f5);
  color: var(--text-muted, #9ca3af);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.fi-send-btn.fi-send-ready {
  background: var(--primary, #2c9af1);
  color: #fff;
}
.fi-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.fi-send-btn.fi-send-ready:hover { filter: brightness(0.9); }

.fi-mic-btn {
  flex-shrink: 0;
  width: 32px; height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-color, #d1d5db);
  background: transparent;
  cursor: pointer;
  color: var(--text-muted, #6c757d);
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.fi-mic-btn:hover {
  background: var(--control-bg, #f4f4f5);
  color: var(--text-color, #1a1a1a);
}
.fi-mic-btn.fi-mic-recording {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
  animation: fi-mic-pulse 1.2s ease infinite;
}
.fi-mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }

@keyframes fi-mic-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50%       { box-shadow: 0 0 0 5px rgba(239, 68, 68, 0); }
}

.fi-mic-spinner {
  width: 13px; height: 13px;
  border: 2px solid var(--border-color, #d1d5db);
  border-top-color: var(--primary, #2c9af1);
  border-radius: 50%;
  animation: fi-mic-spin 0.7s linear infinite;
  display: inline-block;
}
@keyframes fi-mic-spin { to { transform: rotate(360deg); } }
</style>
