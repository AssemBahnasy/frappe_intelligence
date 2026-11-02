<template>
  <div class="fi-se">
    <!-- Header -->
    <div class="fi-se-header">
      <div class="fi-se-step-key">{{ step.step_key }}</div>
      <div class="fi-se-tabs">
        <button
          v-for="tab in visibleTabs"
          :key="tab.id"
          class="fi-se-tab"
          :class="{ 'fi-se-tab--active': activeTab === tab.id }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>
    </div>

    <!-- Tab panels -->
    <div class="fi-se-body">
      <StepBasics
        v-if="activeTab === 'basics'"
        :step="step"
        :steps="allSteps"
        @update="onStepPatch"
      />
      <RequiredFields
        v-else-if="activeTab === 'fields'"
        :value="step.required_fields"
        :target-doctype="step.target_doctype"
        @update:value="onStepPatch({ required_fields: $event })"
      />
      <WhatsAppFlow
        v-else-if="activeTab === 'whatsapp'"
        :value="step.whatsapp_flow"
        :allow-whatsapp="allowWhatsapp"
        :available-wa-flows="availableWaFlows"
        @update:value="onStepPatch({ whatsapp_flow: $event })"
      />
    </div>
  </div>
</template>

<script>
import StepBasics           from "./StepBasics.vue";
import RequiredFields       from "./RequiredFields.vue";
import WhatsAppFlow         from "./WhatsAppFlow.vue";

const ALL_TABS = [
  { id: "basics",     label: "Basics" },
  { id: "fields",     label: "Fields" },
  { id: "whatsapp",   label: "WhatsApp" },
];

export default {
  name: "StepEditor",
  components: { StepBasics, RequiredFields, WhatsAppFlow },

  props: {
    step:                 { type: Object, required: true },
    allSteps:             { type: Array,  default: () => [] },
    availableWaFlows:     { type: Array,  default: () => [] },
    allowWhatsapp:        { type: Boolean, default: false },
  },

  emits: ["update:step"],

  data() {
    return {
      activeTab: "basics",
    };
  },

  computed: {
    visibleTabs() {
      return ALL_TABS.filter((t) => t.id !== "whatsapp" || this.allowWhatsapp);
    },
  },

  watch: {
    "step.step_key"() {
      this.activeTab = "basics";
    },
  },

  methods: {
    onStepPatch(patch) {
      this.$emit("update:step", { ...this.step, ...patch });
    },
  },
};
</script>

<style scoped>
.fi-se {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--card-bg, #fff);
  border-left: 1px solid var(--border-color, #e0e0e0);
}

.fi-se-header {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  background: var(--card-bg, #fff);
  flex-shrink: 0;
}

.fi-se-step-key {
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  color: #5b50c4;
  background: #f0eeff;
  padding: 6px 16px;
  border-bottom: 1px solid var(--border-color, #e8e8e8);
}

.fi-se-tabs {
  display: flex;
  gap: 0;
  padding: 0 16px;
}
.fi-se-tab {
  padding: 9px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted, #888);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.fi-se-tab:hover { color: var(--text-color, #333); }
.fi-se-tab--active {
  color: #6c63ff;
  border-bottom-color: #6c63ff;
  font-weight: 600;
}

.fi-se-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
</style>
