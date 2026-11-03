// The AI Workflow Builder's Vue app. The page loads it when it opens (intelligence/page/ai_workflow_builder).
import { createApp } from "vue";
import Page from "../../intelligence/page/ai_workflow_builder/components/Page.vue";

frappe.provide("frappe_intelligence.ui");

frappe_intelligence.ui.WorkflowBuilder = class WorkflowBuilder {
	constructor({ container, workflow_key }) {
		this.app = createApp(Page, { workflowKey: workflow_key });
		SetVueGlobals(this.app);
		this.app.mount(container);
	}

	destroy() {
		this.app.unmount();
	}
};
