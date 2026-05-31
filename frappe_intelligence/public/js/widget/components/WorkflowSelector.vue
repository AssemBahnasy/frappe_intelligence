<template>
  <div class="fi-workflow-wrap">
    <svg class="fi-wf-icon" xmlns="http://www.w3.org/2000/svg" width="12" height="12"
         viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
         stroke-linecap="round" stroke-linejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
    <select
      class="fi-workflow-select"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value || null)"
      :aria-label="__('Select workflow')"
    >
      <option value="">{{ __("Select workflow…") }}</option>
      <option v-for="wf in workflows" :key="wf.workflow_key" :value="wf.workflow_key">
        {{ wf.title }}
      </option>
    </select>
  </div>
</template>

<script>
export default {
  name: "WorkflowSelector",
  props: {
    modelValue: { type: String, default: null },
    workflows:  { type: Array,  default: () => [] },
  },
  emits: ["update:modelValue"],
};
</script>

<style scoped>
.fi-workflow-wrap {
  flex: 1; min-width: 0;
  position: relative;
  display: flex; align-items: center;
}
.fi-wf-icon {
  position: absolute;
  left: 8px;
  color: rgba(255, 255, 255, 0.7);
  pointer-events: none;
  flex-shrink: 0;
}
.fi-workflow-select {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 6px;
  padding: 3px 8px 3px 26px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  cursor: pointer;
  outline: none;
  font-family: inherit;
  height: 26px;
  appearance: none;
  -webkit-appearance: none;
}
.fi-workflow-select:focus {
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.2);
}
.fi-workflow-select option {
  background: var(--card-bg, #fff);
  color: var(--text-color, #333);
}
</style>
