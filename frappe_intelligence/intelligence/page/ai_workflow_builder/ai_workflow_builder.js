frappe.pages['ai-workflow-builder'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('AI Workflow Builder'),
		single_column: true,
	});

	const container = document.createElement('div');
	container.id = 'ai-workflow-builder-vue-root';
	container.style.cssText = 'height: calc(100vh - var(--navbar-height, 48px) - var(--page-head-height, 45px)); width: 100%; overflow: auto;';
	page.main.append(container);

	// Second URL segment is the workflow_key, e.g. /app/ai-workflow-builder/my-workflow
	const workflowKey = frappe.get_route()[1] || null;

	document.dispatchEvent(new CustomEvent('ai-workflow-builder-page-ready', {
		detail: { container, workflowKey },
	}));
};

frappe.pages['ai-workflow-builder'].on_page_unload = function () {
	document.dispatchEvent(new CustomEvent('ai-workflow-builder-page-unload'));
};
