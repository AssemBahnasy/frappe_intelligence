<template>
  <div class="fi-builder-page">

    <!-- Loading -->
    <div v-if="loading" class="fi-builder-state-center">
      <div class="fi-builder-spinner"></div>
      <span>{{ __("Loading workflow…") }}</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="fi-builder-state-center fi-builder-error">
      {{ error }}
    </div>

    <!-- No workflow selected — picker -->
    <div v-else-if="!workflowKey" class="fi-builder-picker">
      <h2 class="fi-builder-picker-title">{{ __("AI Workflow Builder") }}</h2>
      <p class="fi-builder-picker-sub">{{ __("Select a workflow to edit, or create a new one.") }}</p>
      <div class="fi-builder-wf-list">
        <button
          v-for="wf in availableWorkflows"
          :key="wf.workflow_key"
          class="fi-builder-wf-item"
          @click="openWorkflow(wf.workflow_key)"
        >
          <span class="fi-builder-wf-key">{{ wf.workflow_key }}</span>
          <span class="fi-builder-wf-title">{{ wf.title }}</span>
          <span class="fi-builder-wf-badge" :class="wf.is_active ? 'fi-active' : 'fi-inactive'">
            {{ wf.is_active ? __("Active") : __("Inactive") }}
          </span>
        </button>

        <div v-if="!availableWorkflows.length" class="fi-builder-empty">
          <span>{{ __("No workflows yet.") }}</span>
          <button class="fi-builder-new-btn" @click="newWorkflow">
            {{ __("+ Create AI Workflow") }}
          </button>
        </div>

        <button v-else class="fi-builder-new-btn fi-builder-new-inline" @click="newWorkflow">
          {{ __("+ New Workflow") }}
        </button>
      </div>
    </div>

    <!-- Builder canvas -->
    <template v-else>
      <WorkflowHeader
        :workflow="workflow"
        :is-dirty="isDirty"
        :saving="saving"
        @update:workflow="onWorkflowUpdate"
        @save="save"
        @discard="discard"
      />

      <!-- Scrollable body -->
      <div class="fi-builder-scroll">

        <!-- Step canvas: sequencer + editor -->
        <div class="fi-builder-canvas">
          <StepSequencer
            :steps="steps"
            :selected-step-key="selectedStepKey"
            @select-step="selectedStepKey = $event"
            @update:steps="onStepsUpdate"
            @add-step="addStep"
            @remove-step="removeStep"
          />

          <StepEditor
            v-if="selectedStep"
            :step="selectedStep"
            :all-steps="steps"
            :requirements="requirements"
            :processor-assignments="processorAssignments"
            :available-templates="availableTemplates"
            :available-processors="availableProcessors"
            :available-wa-flows="availableWaFlows"
            :allow-whatsapp="!!workflow.allow_whatsapp"
            @update:step="onStepUpdate"
            @update:requirements="onRequirementsUpdate"
            @update:processors="onProcessorsUpdate"
          />
          <div v-else class="fi-builder-no-step">
            {{ __("Select a step to edit") }}
          </div>
        </div>

        <!-- Scope -->
        <div class="fi-builder-section">
          <div class="fi-builder-section-title">{{ __("Scope") }}</div>
          <ScopeEditor
            :scope-description="workflow.scope_description || ''"
            :out-of-scope-reply="workflow.out_of_scope_reply || ''"
            @update:scopeDescription="onWorkflowUpdate({ scope_description: $event })"
            @update:outOfScopeReply="onWorkflowUpdate({ out_of_scope_reply: $event })"
          />
        </div>

        <!-- Knowledge Packs -->
        <div class="fi-builder-section">
          <div class="fi-builder-section-title">{{ __("Knowledge Packs") }}</div>
          <KnowledgePanel
            :knowledge-packs="knowledgePacks"
            :available-packs="availablePacks"
            @update:knowledgePacks="onKnowledgePacksUpdate"
          />
        </div>

        <!-- Prompt Preview -->
        <PromptPreview :selected-step="selectedStep" />

      </div>
    </template>

  </div>
</template>

<script>
import WorkflowHeader from "./WorkflowHeader.vue";
import StepSequencer  from "./StepSequencer.vue";
import StepEditor     from "./StepEditor/StepEditor.vue";
import ScopeEditor    from "./ScopeEditor.vue";
import KnowledgePanel from "./KnowledgePanel.vue";
import PromptPreview  from "./PromptPreview.vue";

const BLANK_WORKFLOW = () => ({
  workflow_key: "",
  title: "",
  is_active: 1,
  allow_desk: 1,
  allow_portal: 0,
  allow_whatsapp: 0,
  scope_description: "",
  out_of_scope_reply: "",
});

export default {
  name: "Page",
  components: { WorkflowHeader, StepSequencer, StepEditor, ScopeEditor, KnowledgePanel, PromptPreview },

  props: {
    workflowKey: { type: String, default: null },
  },

  data() {
    return {
      loading: false,
      saving: false,
      error: null,
      availableWorkflows: [],
      // Builder state
      workflow: BLANK_WORKFLOW(),
      steps: [],
      requirements: [],
      processorAssignments: [],
      knowledgePacks: [],
      availableTemplates: [],
      availablePacks: [],
      availableProcessors: [],
      availableWaFlows: [],
      selectedStepKey: null,
      isDirty: false,
      _stepCounter: 0,
    };
  },

  async created() {
    if (this.workflowKey) {
      await this.loadWorkflow(this.workflowKey);
    } else {
      await this.loadWorkflowList();
    }
  },

  computed: {
    selectedStep() {
      if (!this.selectedStepKey) return null;
      return this.steps.find((s) => s.step_key === this.selectedStepKey) || null;
    },
  },

  methods: {
    async loadWorkflowList() {
      this.loading = true;
      this.error = null;
      try {
        const res = await frappe.call({ method: "frappe_intelligence.api.list_workflows" });
        this.availableWorkflows = res.message || [];
      } catch (err) {
        this.error = err?.message || __("Failed to load workflows.");
      } finally {
        this.loading = false;
      }
    },

    async loadWorkflow(key) {
      this.loading = true;
      this.error = null;
      try {
        const res = await frappe.call({
          method: "frappe_intelligence.api.get_workflow_for_builder",
          args: { workflow_key: key },
        });
        const data = res.message;
        this.workflow             = { ...BLANK_WORKFLOW(), ...data.workflow };
        this.steps                = (data.steps || []).map((s, i) => ({ ...s, _id: i }));
        this.requirements         = data.requirements          || [];
        this.processorAssignments = data.processor_assignments || [];
        this.knowledgePacks       = data.knowledge_packs       || [];
        this.availableTemplates   = data.available_templates   || [];
        this.availablePacks       = data.available_packs       || [];
        this.availableProcessors  = data.available_processors  || [];
        this.availableWaFlows     = data.available_wa_flows    || [];
        this._stepCounter = this.steps.length;
        this.isDirty = false;
      } catch (err) {
        this.error = err?.message || __("Failed to load workflow.");
      } finally {
        this.loading = false;
      }
    },

    openWorkflow(key) {
      frappe.set_route("ai-workflow-builder", key);
    },

    newWorkflow() {
      frappe.set_route("Form", "AI Workflow", "new-ai-workflow-1");
    },

    onWorkflowUpdate(patch) {
      this.workflow = { ...this.workflow, ...patch };
      this.isDirty = true;
    },

    onStepsUpdate(newSteps) {
      this.steps = newSteps;
      this.isDirty = true;
    },

    onStepUpdate(updatedStep) {
      this.steps = this.steps.map((s) =>
        s.step_key === updatedStep.step_key ? updatedStep : s
      );
      this.isDirty = true;
    },

    onRequirementsUpdate(newReqs) {
      this.requirements = newReqs;
      this.isDirty = true;
    },

    onProcessorsUpdate(newAssignments) {
      this.processorAssignments = newAssignments;
      this.isDirty = true;
    },

    onKnowledgePacksUpdate(newPacks) {
      this.knowledgePacks = newPacks;
      this.isDirty = true;
    },

    addStep() {
      this._stepCounter++;
      const newKey = `step_${this._stepCounter}`;
      this.steps = [
        ...this.steps,
        {
          _id: this._stepCounter,
          step_order: this.steps.length + 1,
          step_key: newKey,
          prompt_to_user: "",
          target_doctype: null,
          required_fields: null,
          whatsapp_flow: null,
          completion_check: null,
          next_step_key: null,
        },
      ];
      this.selectedStepKey = newKey;
      this.isDirty = true;
    },

    removeStep(stepKey) {
      this.steps = this.steps
        .filter((s) => s.step_key !== stepKey)
        .map((s, i) => ({ ...s, step_order: i + 1 }));
      if (this.selectedStepKey === stepKey) {
        this.selectedStepKey = this.steps[0]?.step_key || null;
      }
      this.isDirty = true;
    },

    async save() {
      if (this.saving) return;
      this.saving = true;
      try {
        await frappe.call({
          method: "frappe_intelligence.api.save_workflow_builder",
          args: {
            workflow_key: this.workflowKey,
            payload: {
              workflow:              this.workflow,
              steps:                 this.steps.map((s, i) => ({ ...s, step_order: i + 1 })),
              requirements:          this.requirements,
              knowledge_packs:       this.knowledgePacks,
              processor_assignments: this.processorAssignments,
            },
          },
        });
        this.isDirty = false;
        frappe.show_alert({ message: __("Workflow saved."), indicator: "green" });
      } catch (err) {
        frappe.msgprint(err?.message || __("Failed to save workflow."));
      } finally {
        this.saving = false;
      }
    },

    async discard() {
      if (!this.isDirty) return;
      await this.loadWorkflow(this.workflowKey);
    },
  },
};
</script>

<style scoped>
.fi-builder-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: var(--bg-color, #f5f5f5);
  font-family: inherit;
}

/* ---- State screens ---- */
.fi-builder-state-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted, #888);
  font-size: 14px;
}
.fi-builder-error { color: #c62828; }
.fi-builder-spinner {
  width: 36px; height: 36px;
  border: 3px solid #e0e0e0;
  border-top-color: #6c63ff;
  border-radius: 50%;
  animation: fi-bld-spin 0.8s linear infinite;
}
@keyframes fi-bld-spin { to { transform: rotate(360deg); } }

/* ---- Workflow picker ---- */
.fi-builder-picker {
  max-width: 640px;
  margin: 40px auto;
  padding: 0 16px;
}
.fi-builder-picker-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--heading-color, #1a1a1a);
}
.fi-builder-picker-sub {
  font-size: 13px;
  color: var(--text-muted, #888);
  margin-bottom: 20px;
}
.fi-builder-wf-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.fi-builder-wf-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  cursor: pointer;
  text-align: start;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.fi-builder-wf-item:hover {
  border-color: #6c63ff;
  box-shadow: 0 2px 8px rgba(108,99,255,0.12);
}
.fi-builder-wf-key {
  font-size: 11px;
  font-family: monospace;
  background: #f0eeff;
  color: #5b50c4;
  border-radius: 4px;
  padding: 2px 7px;
  flex-shrink: 0;
}
.fi-builder-wf-title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color, #333);
}
.fi-builder-wf-badge {
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  padding: 2px 8px;
  flex-shrink: 0;
}
.fi-builder-wf-badge.fi-active { background: #e8f5e9; color: #388e3c; }
.fi-builder-wf-badge.fi-inactive { background: #f5f5f5; color: #888; }
.fi-builder-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-muted, #888);
  padding: 12px 0;
}
.fi-builder-new-btn {
  background: #6c63ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 7px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.fi-builder-new-btn:hover { opacity: 0.88; }
.fi-builder-new-inline {
  margin-top: 4px;
  align-self: flex-start;
}

/* ---- Scrollable body (below header) ---- */
.fi-builder-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ---- Step canvas: sequencer + editor ---- */
.fi-builder-canvas {
  display: flex;
  height: 480px;
  flex-shrink: 0;
  gap: 0;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

/* ---- No step selected ---- */
.fi-builder-no-step {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--text-muted, #aaa);
  background: var(--bg-color, #f5f5f5);
  border-left: 1px solid var(--border-color, #e0e0e0);
}

/* ---- Support panels (Scope, Knowledge, Preview) ---- */
.fi-builder-section {
  border-bottom: 1px solid var(--border-color, #e0e0e0);
  background: var(--card-bg, #fff);
}
.fi-builder-section-title {
  padding: 14px 24px 0;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #888);
}
</style>
