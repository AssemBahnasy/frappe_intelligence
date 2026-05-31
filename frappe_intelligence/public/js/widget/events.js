/**
 * events.js
 * ---------
 * DOM event bindings and real-time Socket.io listeners.
 */

export const eventMethods = {
    _bindEvents() {
        const self = this;

        // FAB toggle — guard against drag-end firing as a click
        $(document).on("click", "#fi-fab", () => {
            if (self._dragMoved) { self._dragMoved = false; return; }
            if (self._state === "fi-chat-panel") { self._closeAll(); }
            else { self._openPanel("fi-chat-panel"); }
        });

        // Bubble close
        $(document).on("click", "#fi-bubble-close", () => self._hideBubble());

        // Bubble text click — open chat and jump straight to the upload view
        $(document).on("click", "#fi-bubble-text", () => {
            self._hideBubble();
            self._openPanel("fi-chat-panel");
            window.__fi_chatSetView?.("upload");
        });
    },

    _bindRealtime() {
        const self = this;

        frappe.realtime.on("ai_processing_update", (data) => {
            self._setProgress(data.message || __("Processing…"));
        });

        // Fired by process_document_background when the background job finishes.
        frappe.realtime.on("ai_processing_complete", (result) => {
            self._hideProgress();
            self._handleProcessingResult(result);
        });

        // Streaming chat — update the last assistant bubble token by token.
        // SECURITY: always use .text() here, never .html().
        // Streamed content is LLM output and must be treated as untrusted text.
        frappe.realtime.on("ai_stream_chunk", (data) => {
            const chunk = String(data.chunk || "");
            const done = Boolean(data.done);

            if (chunk) {
                const lastBubble = $("#fi-chat-log .fi-chat-msg.assistant").last();
                if (!self._isStreaming) {
                    self._isStreaming = true;
                    self._streamBuffer = "";
                    lastBubble.text("");
                }
                self._streamBuffer += chunk;
                // .text() escapes HTML — do NOT change to .html()
                lastBubble.text(self._streamBuffer);
                const log = $("#fi-chat-log");
                log.scrollTop(log[0].scrollHeight);
            }

            if (done) {
                self._isStreaming = false;
                self._streamBuffer = "";
            }
        });
    },
};
