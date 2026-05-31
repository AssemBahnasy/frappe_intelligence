/**
 * chat_island.js
 * --------------
 * Vue 3 island lifecycle manager.
 * Registers window.__fi_mountChatIsland / __fi_unmountChatIsland so that
 * ui.js can drive mount/unmount without importing Vue directly.
 *
 * While the island is active, the vanilla JS _handleProcessingResult is
 * suppressed so upload results route through the Vue island instead of
 * opening the old #fi-result-panel behind the chat panel.
 */

import { createApp } from "vue";
import ChatPanel from "./components/ChatPanel.vue";

let _app = null;
let _widgetInstance = null;
let _originalHandleResult = null;

window.__fi_mountChatIsland = function (widgetInstance) {
    if (_app) return; // already mounted
    const container = document.getElementById("fi-panel-body");
    if (!container) return;

    _widgetInstance = widgetInstance;

    // Suspend vanilla JS upload-result handler while the Vue island is active.
    // Restored in __fi_unmountChatIsland so the old panels keep working after close.
    if (typeof widgetInstance._handleProcessingResult === "function") {
        _originalHandleResult = widgetInstance._handleProcessingResult.bind(widgetInstance);
        widgetInstance._handleProcessingResult = function () {};
    }

    _app = createApp(ChatPanel, {
        widgetInstance,
        currentDoctype: widgetInstance._currentDoctype || null,
        currentDocname: widgetInstance._currentDocname || null,
    });
    // Frappe's __ translation function is a window global; Vue 3's component proxy
    // does not fall through to window, so templates calling __("...") would get
    // undefined and throw. Register it as a global property instead.
    _app.config.globalProperties.__ = window.__;
    _app.mount(container);

    // Allow external callers (e.g. bubble click) to imperatively switch the view.
    window.__fi_chatSetView = function (view) {
        const proxy = _app?._instance?.proxy;
        if (proxy) proxy.view = view;
    };
};

window.__fi_unmountChatIsland = function () {
    if (!_app) return;

    // Restore vanilla JS handler
    if (_widgetInstance && _originalHandleResult) {
        _widgetInstance._handleProcessingResult = _originalHandleResult;
    }
    _widgetInstance = null;
    _originalHandleResult = null;

    _app.unmount();
    _app = null;
    window.__fi_chatSetView = null;
    const container = document.getElementById("fi-panel-body");
    if (container) container.innerHTML = "";
};
