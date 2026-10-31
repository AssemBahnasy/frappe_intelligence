// Frappe keeps a page once built, so the builder mounts once; its bundle loads only here.
frappe.pages["ai-workflow-builder"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("AI Workflow Builder"),
		single_column: true,
	});
	const container = $(`<div class="fi-workflow-builder-root"></div>`)
		.css({
			height: "calc(100vh - var(--navbar-height, 48px) - var(--page-head-height, 45px))",
			width: "100%",
			overflow: "auto",
		})
		.appendTo(page.main)[0];

	// /app/ai-workflow-builder/<workflow_key> opens that workflow.
	const workflow_key = frappe.get_route()[1] || null;
	frappe.require("frappe_intelligence_workflow_builder.bundle.js").then(() => {
		wrapper.builder = new frappe_intelligence.ui.WorkflowBuilder({ container, workflow_key });
	});
};
