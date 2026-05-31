/**
 * intelligence_widget.js
 * ----------------------
 * Composition entry point — imports all focused modules and assembles
 * the frappe_intelligence.widget object via Object.assign().
 *
 * Module map
 * ----------
 *  dom.js      — _buildDOM(), _injectStyles()
 *  events.js   — _bindEvents(), _bindRealtime()
 *  settings.js — _applySettings(), _startPageWatcher(), _checkPageContext()
 *  ui.js       — FAB drag, panel state machine, progress/bubble helpers
 *  chat.js     — text command flow, action buttons, search results
 *  upload.js   — upload panel, checklist, file upload handler, mismatch prompt
 *  voice.js    — MediaRecorder, audio upload, Whisper transcription
 *  result.js   — extraction result, review flow, correction form
 */

import { domMethods } from "./dom.js";
import { eventMethods } from "./events.js";
import { settingsMethods } from "./settings.js";
import { uiMethods } from "./ui.js";
import { chatMethods } from "./chat.js";
import { uploadMethods } from "./upload.js";
import { voiceMethods } from "./voice.js";
import { resultMethods } from "./result.js";

frappe.provide("frappe_intelligence");

frappe_intelligence.widget = Object.assign(
    {},

    // -----------------------------------------------------------------------
    // Bootstrap (init + shared state — lives here, not in any module)
    // -----------------------------------------------------------------------
    {
        init() {
            if (this._initialised) return;
            this._initialised = true;

            this._state = "idle";
            this._mediaRecorder = null;
            this._audioChunks = [];
            this._currentDoctype = null;
            this._currentDocname = null;
            this._requiredDocs = [];
            this._pendingFileDoctype = null;
            this._widgetMode = "global";
            this._dragMoved = false;
            this._fabDefaultIcon = "🧠";
            this._navMap = {};
            this._pendingReview = null;
            this._lastResult = null;
            this._isStreaming = false;
            this._streamBuffer = "";

            this._buildDOM();
            this._bindEvents();
            this._bindRealtime();
            this._makeFabDraggable();
            this._startPageWatcher();
            this._applySettings();
        },
    },

    domMethods,
    eventMethods,
    settingsMethods,
    uiMethods,
    chatMethods,
    uploadMethods,
    voiceMethods,
    resultMethods,
);

// -----------------------------------------------------------------------
// Auto-init after Frappe desk is ready
// -----------------------------------------------------------------------
$(document).ready(function () {
    if (frappe && frappe.user && frappe.user.name !== "Guest") {
        frappe_intelligence.widget.init();
    }
});

// Re-init on login (SPA navigation)
frappe.after_ajax && frappe.after_ajax(function () {
    if (frappe.user && frappe.user.name !== "Guest") {
        frappe_intelligence.widget.init();
    }
});

