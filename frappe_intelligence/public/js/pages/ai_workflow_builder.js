import { createApp } from "vue";
import Page from "../../../intelligence/page/ai_workflow_builder/components/Page.vue";

let _app = null;

function mount(container, props = {}) {
    if (_app) unmount();
    _app = createApp(Page, props);
    _app.config.globalProperties.__ = window.__;
    _app.mount(container);
}

function unmount() {
    if (_app) {
        _app.unmount();
        _app = null;
    }
}

document.addEventListener("ai-workflow-builder-page-ready", (e) => {
    mount(e.detail.container, { workflowKey: e.detail.workflowKey || null });
});

document.addEventListener("ai-workflow-builder-page-unload", () => unmount());
