// The builder's bundle loads only here. /desk/ai-workflow-builder/<workflow_key> opens that
// workflow; with no key, the picker shows.
frappe.pages["ai-workflow-builder"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("AI Workflow Builder"),
		single_column: true,
	});
	wrapper.container = $(`<div class="fi-workflow-builder-root"></div>`)
		.css({
			height: "calc(100vh - var(--navbar-height, 48px) - var(--page-head-height, 45px))",
			width: "100%",
			overflow: "auto",
		})
		.appendTo(page.main)[0];
};

// Frappe keeps the page once built and only shows it again, also when the picker opens a workflow
// on the same page: the builder follows the route on every show.
frappe.pages["ai-workflow-builder"].on_page_show = function (wrapper) {
	const workflow_key = frappe.get_route()[1] || null;
	if (wrapper.builder && wrapper.workflow_key === workflow_key) return;
	wrapper.workflow_key = workflow_key;
	frappe.require("fi_workflow_builder.bundle.js").then(() => {
		if (wrapper.workflow_key !== workflow_key) return; // the route moved on meanwhile
		wrapper.builder?.destroy();
		wrapper.builder = new frappe_intelligence.ui.WorkflowBuilder({
			container: wrapper.container,
			workflow_key,
		});
	});
};
