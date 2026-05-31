<template>
  <div :class="['fi-msg-row', isUser ? 'fi-msg-user' : 'fi-msg-bot']" dir="ltr">

    <!-- Bot avatar (first in DOM → leftmost in row) -->
    <div v-if="!isUser" class="fi-avatar fi-avatar-bot" aria-hidden="true">
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

    <!-- User avatar (first in DOM → rightmost in row-reverse) -->
    <div v-if="isUser" class="fi-avatar fi-avatar-user" aria-hidden="true">
      {{ userInitial }}
    </div>

    <div class="fi-msg-col" :class="isUser ? 'fi-col-user' : 'fi-col-bot'">

      <!-- Bubble -->
      <div :class="['fi-bubble', isUser ? 'fi-bubble-user' : 'fi-bubble-bot', { 'fi-typing': isTyping }]" dir="auto">
        <template v-if="isUser">{{ turn.content }}</template>
        <template v-else-if="isTyping">
          <span class="fi-dot"></span>
          <span class="fi-dot"></span>
          <span class="fi-dot"></span>
        </template>
        <div v-else class="fi-md" v-html="renderedContent"></div>
      </div>

      <!-- Actions -->
      <button v-if="turn.action === 'suggest_workflow'"
              class="fi-action-pill" @click="$emit('suggest-workflow')">
        {{ __("Switch to Agent mode") }} ↗
      </button>

      <button v-else-if="isRouteAction"
              class="fi-action-pill" @click="$emit('navigate', turn.actionData.route)">
        ↗ {{ turn.actionData.label || turn.actionData.doctype || turn.actionData.route }}
      </button>

      <button v-else-if="turn.action === 'create_record'"
              class="fi-action-pill fi-action-pill-green"
              @click="$emit('create', { doctype: turn.actionData.doctype, defaults: turn.actionData.defaults || {} })">
        + {{ turn.actionData.label || turn.actionData.doctype }}
      </button>

      <a v-else-if="turn.action === 'map'"
         :href="turn.actionData.map_url" target="_blank" rel="noopener noreferrer"
         class="fi-action-pill fi-action-pill-blue">
        🗺 {{ __("View on Map") }}
      </a>

      <div v-else-if="turn.action === 'search_results'" class="fi-search-row">
        <span class="fi-search-type">{{ turn.actionData.doctype }}:</span>
        <button v-for="name in (turn.actionData.results || [])" :key="name"
                class="fi-search-chip" @click="navigateToRecord(turn.actionData.doctype, name)">
          {{ name }}
        </button>
        <span v-if="!(turn.actionData.results || []).length" class="fi-search-empty">
          {{ __("No records found.") }}
        </span>
      </div>

    </div>

  </div>
</template>

<script>
export default {
  name: "MessageBubble",
  props: { turn: { type: Object, required: true } },
  emits: ["suggest-workflow", "navigate", "create"],

  computed: {
    isUser()   { return this.turn.role === "user"; },
    isTyping() { return !this.isUser && this.turn.streaming && this.turn.content === "…"; },
    isRouteAction() {
      return this.turn.action === "navigate" || this.turn.action === "open_record";
    },
    userInitial() {
      try {
        const name = frappe?.session?.user_fullname || frappe?.session?.user || "U";
        return name.charAt(0).toUpperCase();
      } catch { return "U"; }
    },
    renderedContent() {
      const text = this.turn.content || "";
      try {
        if (typeof frappe?.utils?.markdown === "function") {
          return frappe.utils.markdown(text);
        }
      } catch { /* fall through */ }
      return text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/`([^`\n]+)`/g, "<code>$1</code>")
        .replace(/\n/g, "<br>");
    },
  },

  methods: {
    navigateToRecord(doctype, name) {
      const slug = s => (s || "").toLowerCase().replace(/ /g, "-").replace(/_/g, "-");
      this.$emit("navigate", `/app/${slug(doctype)}/${slug(name)}`);
    },
  },
};
</script>

<style scoped>
.fi-msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.fi-msg-user { flex-direction: row-reverse; }
.fi-msg-bot  { flex-direction: row; }

/* ── Avatars ── */
.fi-avatar {
  flex-shrink: 0;
  width: 26px; height: 26px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600;
  margin-bottom: 2px;
}
.fi-avatar-bot {
  background: var(--primary, #2c9af1);
  color: #fff;
}
.fi-avatar-user {
  background: var(--control-bg, #f0f0f0);
  color: var(--text-muted, #6c757d);
  border: 1px solid var(--border-color, #d1d5db);
}

/* ── Column ── */
.fi-msg-col { display: flex; flex-direction: column; gap: 4px; max-width: 78%; }
.fi-col-user { align-items: flex-end; }
.fi-col-bot  { align-items: flex-start; }

/* ── Bubbles ── */
.fi-bubble {
  padding: 9px 13px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.55;
  word-break: break-word;
}
.fi-bubble-user {
  background: var(--primary, #2c9af1);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.fi-bubble-bot {
  background: var(--control-bg, #f4f4f5);
  color: var(--text-color, #1a1a1a);
  border: 1px solid var(--border-color, #e4e4e7);
  border-bottom-left-radius: 4px;
}

/* ── Markdown rendering inside bot bubble ── */
.fi-md :deep(p)      { margin: 0 0 6px; }
.fi-md :deep(p:last-child) { margin-bottom: 0; }
.fi-md :deep(strong) { font-weight: 600; }
.fi-md :deep(em)     { font-style: italic; }
.fi-md :deep(code)   {
  background: var(--subtle-fg, #f0f0f0);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 12px;
  font-family: monospace;
}
.fi-md :deep(pre) {
  background: var(--subtle-fg, #f0f0f0);
  border-radius: 6px;
  padding: 8px 10px;
  overflow-x: auto;
  font-size: 12px;
}
.fi-md :deep(ul), .fi-md :deep(ol) {
  padding-inline-start: 18px;
  margin: 4px 0;
}
.fi-md :deep(li) { margin: 2px 0; }

/* ── Typing dots (streaming placeholder) ── */
.fi-typing {
  display: flex; align-items: center; gap: 5px;
  padding: 10px 14px;
  min-width: 52px;
}
.fi-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.5;
  animation: fi-bounce 1.2s ease-in-out infinite;
}
.fi-dot:nth-child(1) { animation-delay: 0s; }
.fi-dot:nth-child(2) { animation-delay: 0.2s; }
.fi-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes fi-bounce {
  0%, 80%, 100% { transform: translateY(0);    opacity: 0.4; }
  40%           { transform: translateY(-5px); opacity: 1;   }
}

/* ── Action pills ── */
.fi-action-pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px; font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--primary, #2c9af1);
  background: transparent;
  color: var(--primary, #2c9af1);
  font-family: inherit;
  text-decoration: none;
  transition: background 0.15s;
}
.fi-action-pill:hover { background: var(--bg-blue, rgba(44,154,241,0.08)); }
.fi-action-pill-green { border-color: var(--green-500, #22c55e); color: var(--green-600, #16a34a); }
.fi-action-pill-green:hover { background: var(--bg-green, rgba(34,197,94,0.08)); }
.fi-action-pill-blue { border-color: var(--blue-400, #60a5fa); color: var(--blue-600, #2563eb); }
.fi-action-pill-blue:hover { background: var(--bg-light-blue, rgba(96,165,250,0.08)); }

/* ── Search chips ── */
.fi-search-row { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.fi-search-type { font-size: 11px; color: var(--text-muted, #6c757d); font-weight: 600; }
.fi-search-chip {
  background: var(--bg-blue, #dbeafe);
  color: var(--text-on-light-blue, #1d4ed8);
  border: none; border-radius: 4px;
  padding: 2px 8px; font-size: 12px; cursor: pointer; font-family: inherit;
}
.fi-search-chip:hover { filter: brightness(0.94); }
.fi-search-empty { font-size: 12px; color: var(--text-muted, #6c757d); }
</style>
