<template>
  <div class="fi-chat-feed" ref="feedEl">

    <!-- Empty state -->
    <div v-if="!turns.length && !loading" class="fi-feed-empty">
      <div class="fi-empty-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      </div>
      <p class="fi-empty-label">{{ emptyLabel }}</p>
      <p class="fi-empty-hint">{{ __("Type a message below to get started") }}</p>
    </div>

    <!-- Messages -->
    <MessageBubble
      v-for="(turn, i) in turns"
      :key="i"
      :turn="turn"
      @suggest-workflow="$emit('suggest-workflow')"
      @navigate="handleNavigate"
      @create="handleCreate"
    />

    <!-- Loading dots — hidden once streaming starts -->
    <div v-if="loading && !streamingStarted" class="fi-msg-row fi-msg-bot" dir="ltr">
      <div class="fi-avatar fi-avatar-bot" aria-hidden="true">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
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
      <div class="fi-bubble fi-bubble-bot fi-typing">
        <span class="fi-dot"></span>
        <span class="fi-dot"></span>
        <span class="fi-dot"></span>
      </div>
    </div>

  </div>
</template>

<script>
import MessageBubble from "./MessageBubble.vue";

export default {
  name: "ChatFeed",
  components: { MessageBubble },
  props: {
    turns:            { type: Array,   default: () => [] },
    loading:          { type: Boolean, default: false },
    mode:             { type: String,  default: "ask" },
    selectedWorkflow: { type: String,  default: null },
  },
  emits: ["suggest-workflow"],

  computed: {
    emptyLabel() {
      return this.mode === "agent" && this.selectedWorkflow
        ? __("Ready to start the workflow")
        : __("How can I help you today?");
    },
    streamingStarted() {
      const last = this.turns[this.turns.length - 1];
      return last && last.role === "assistant" && last.streaming;
    },
  },

  watch: {
    turns()   { this.scrollToBottom(); },
    loading() { this.scrollToBottom(); },
  },

  methods: {
    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.feedEl;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },
    handleNavigate(route) {
      frappe.set_route(...route.replace(/^\//, "").split("/").filter(Boolean));
    },
    handleCreate({ doctype, defaults }) {
      frappe.call({
        method: "frappe_intelligence.api.create_document",
        args: { doctype, defaults },
        callback(r) {
          if (r.message?.route) {
            frappe.set_route(...r.message.route.replace(/^\//, "").split("/").filter(Boolean));
          }
        },
      });
    },
  },
};
</script>

<style scoped>
.fi-chat-feed {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-300, #d1d5db) transparent;
}

/* ── Empty state ── */
.fi-feed-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 16px;
  text-align: center;
}
.fi-empty-icon {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: var(--bg-blue, #dbeafe);
  color: var(--primary, #2c9af1);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 4px;
}
.fi-empty-label {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color, #1a1a1a);
}
.fi-empty-hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted, #6c757d);
}

/* ── Typing indicator ── */
.fi-bubble { padding: 9px 13px; border-radius: 14px; }
.fi-bubble-bot {
  background: var(--control-bg, #f4f4f5);
  border: 1px solid var(--border-color, #e4e4e7);
  border-bottom-left-radius: 4px;
}
.fi-typing {
  display: flex; align-items: center; gap: 5px;
  padding: 10px 14px;
  min-width: 52px;
}
.fi-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--text-muted, #9ca3af);
  animation: fi-bounce 1.2s ease-in-out infinite;
}
.fi-dot:nth-child(1) { animation-delay: 0s; }
.fi-dot:nth-child(2) { animation-delay: 0.2s; }
.fi-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes fi-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40%           { transform: translateY(-5px); opacity: 1; }
}

/* Avatar (duplicate for loading row — scoped) */
.fi-msg-row { display: flex; align-items: flex-end; gap: 8px; }
.fi-msg-bot  { flex-direction: row; }
.fi-avatar {
  flex-shrink: 0; width: 26px; height: 26px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 2px;
}
.fi-avatar-bot { background: var(--primary, #2c9af1); color: #fff; }
</style>
