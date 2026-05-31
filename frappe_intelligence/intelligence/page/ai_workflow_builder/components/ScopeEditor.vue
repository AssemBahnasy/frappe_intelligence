<template>
  <div class="fi-scope">
    <div class="fi-scope-row">
      <label class="fi-scope-label">{{ __("Scope Description") }}</label>
      <span class="fi-scope-sublabel">{{ __("Injected into the agent's system prompt. Also used for scope enforcement.") }}</span>

      <!-- Bullet-list editor -->
      <div class="fi-scope-bullets">
        <div v-for="(item, idx) in bullets" :key="idx" class="fi-scope-bullet-row">
          <span class="fi-scope-bullet-icon">–</span>
          <input
            class="fi-scope-bullet-input"
            :value="item"
            @input="updateBullet(idx, $event.target.value)"
            :placeholder="__('Add a constraint or description…')"
          />
          <button class="fi-scope-bullet-del" @click="removeBullet(idx)" :title="__('Remove')">✕</button>
        </div>
        <button class="fi-scope-add-bullet" @click="addBullet">+ {{ __("Add line") }}</button>
      </div>

      <!-- Raw textarea (synced from bullets) -->
      <div class="fi-scope-raw-wrap">
        <button class="fi-scope-raw-toggle" @click="showRaw = !showRaw">
          {{ showRaw ? __("Hide raw text") : __("Edit as raw text") }}
        </button>
        <textarea
          v-if="showRaw"
          class="fi-scope-textarea"
          :value="scopeDescription"
          @input="onRawInput($event.target.value)"
          rows="6"
        ></textarea>
      </div>
    </div>

    <div class="fi-scope-row">
      <label class="fi-scope-label">{{ __("Out-of-Scope Reply") }}</label>
      <span class="fi-scope-sublabel">{{ __("Returned immediately when the user's message is off-topic. No LLM tokens consumed.") }}</span>
      <textarea
        class="fi-scope-textarea fi-scope-short"
        :value="outOfScopeReply"
        @input="$emit('update:outOfScopeReply', $event.target.value)"
        :placeholder="__('e.g. I can only assist with service requests on this workflow.')"
        rows="3"
      ></textarea>
    </div>
  </div>
</template>

<script>
export default {
  name: "ScopeEditor",

  props: {
    scopeDescription: { type: String, default: "" },
    outOfScopeReply:  { type: String, default: "" },
  },

  emits: ["update:scopeDescription", "update:outOfScopeReply"],

  data() {
    return {
      bullets: [],
      showRaw: false,
    };
  },

  watch: {
    scopeDescription: {
      immediate: true,
      handler(v) {
        const parsed = this.parseToBullets(v || "");
        if (JSON.stringify(parsed) !== JSON.stringify(this.bullets)) {
          this.bullets = parsed;
        }
      },
    },
  },

  methods: {
    parseToBullets(text) {
      return text
        .split("\n")
        .map((l) => l.replace(/^[-•*]\s*/, "").trim())
        .filter(Boolean);
    },

    bulletsToText(bullets) {
      return bullets.filter(Boolean).map((b) => `- ${b}`).join("\n");
    },

    updateBullet(idx, value) {
      this.bullets[idx] = value;
      this.$emit("update:scopeDescription", this.bulletsToText(this.bullets));
    },

    addBullet() {
      this.bullets.push("");
      this.$emit("update:scopeDescription", this.bulletsToText(this.bullets));
    },

    removeBullet(idx) {
      this.bullets.splice(idx, 1);
      this.$emit("update:scopeDescription", this.bulletsToText(this.bullets));
    },

    onRawInput(value) {
      this.$emit("update:scopeDescription", value);
      this.bullets = this.parseToBullets(value);
    },
  },
};
</script>

<style scoped>
.fi-scope { display: flex; flex-direction: column; gap: 24px; padding: 20px 24px; }

.fi-scope-row { display: flex; flex-direction: column; gap: 8px; }
.fi-scope-label {
  font-size: 12px; font-weight: 700;
  color: var(--text-color, #333);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.fi-scope-sublabel { font-size: 12px; color: var(--text-muted, #888); margin-top: -4px; }

.fi-scope-bullets { display: flex; flex-direction: column; gap: 4px; }
.fi-scope-bullet-row { display: flex; align-items: center; gap: 6px; }
.fi-scope-bullet-icon { color: var(--text-muted, #aaa); font-size: 14px; flex-shrink: 0; width: 12px; }
.fi-scope-bullet-input {
  flex: 1; border: 1px solid var(--border-color, #d1d5db);
  border-radius: 5px; padding: 5px 8px;
  font-size: 13px; font-family: inherit;
  background: var(--control-bg, #fff); color: var(--text-color, #333); outline: none;
}
.fi-scope-bullet-input:focus { border-color: #6c63ff; }
.fi-scope-bullet-del {
  width: 22px; height: 22px; flex-shrink: 0;
  background: none; border: none; cursor: pointer;
  color: var(--text-muted, #bbb); border-radius: 4px; font-size: 11px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, background 0.15s;
}
.fi-scope-bullet-del:hover { color: #c62828; background: #fce4e4; }
.fi-scope-add-bullet {
  align-self: flex-start;
  font-size: 12px; font-weight: 600; color: #6c63ff;
  background: none; border: none; cursor: pointer; padding: 4px 0; margin-top: 2px;
}
.fi-scope-add-bullet:hover { opacity: 0.75; }

.fi-scope-raw-wrap { display: flex; flex-direction: column; gap: 6px; }
.fi-scope-raw-toggle {
  align-self: flex-start;
  font-size: 11px; color: var(--text-muted, #888);
  background: none; border: none; cursor: pointer; padding: 0;
  text-decoration: underline;
}
.fi-scope-raw-toggle:hover { color: var(--text-color, #333); }

.fi-scope-textarea {
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 6px; padding: 8px 10px;
  font-size: 13px; font-family: inherit;
  background: var(--control-bg, #fff);
  color: var(--text-color, #333); outline: none;
  resize: vertical; min-height: 72px;
}
.fi-scope-textarea:focus { border-color: #6c63ff; }
.fi-scope-short { min-height: 56px; }
</style>
