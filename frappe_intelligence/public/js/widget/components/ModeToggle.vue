<template>
  <div class="fi-mode-toggle" role="group" :aria-label="__('Chat mode')">
    <button
      :class="['fi-mode-btn', modelValue === 'ask' ? 'active' : '']"
      @click="$emit('update:modelValue', 'ask')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2.5"
           stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      {{ __("Ask") }}
    </button>
    <button
      :class="['fi-mode-btn', modelValue === 'agent' ? 'active' : '']"
      @click="$emit('update:modelValue', 'agent')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2.5"
           stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
      {{ __("Agent") }}
    </button>
  </div>
</template>

<script>
export default {
  name: "ModeToggle",
  props: { modelValue: { type: String, default: "ask" } },
  emits: ["update:modelValue"],
};
</script>

<style scoped>
.fi-mode-toggle {
  display: inline-flex;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
  flex-shrink: 0;
}

.fi-mode-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 500;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.75);
  transition: background 0.15s, color 0.15s;
  font-family: inherit;
  white-space: nowrap;
}
.fi-mode-btn:hover { color: #fff; }
.fi-mode-btn.active {
  background: rgba(255, 255, 255, 0.95);
  color: var(--primary, #2c9af1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
}
</style>
