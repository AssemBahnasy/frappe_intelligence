/**
 * fi.portal_client.js
 * ----------------
 * Framework-agnostic base class for consuming the frappe_intelligence portal
 * channel from any frontend: React, Vue, or vanilla JS.
 *
 * No DOM — no document.getElementById, no innerHTML, no Frappe desk imports.
 * This file is delivered as a static asset; integrating apps import it via a
 * <script> tag or a bundler alias.
 *
 * Usage (React example — wire to useAIChat hook in the hawya app):
 *   const client = new AIPortalClient({
 *     customer: "CUST-001",
 *     workflow: "service_request",
 *     onDone: (reply, action, actionData) => { ... },
 *     onAction: (action, actionData) => { ... },
 *     onError: (err) => { ... },
 *   });
 *   await client.chat("I need to register a new facility.");
 *   client.destroy(); // call on component unmount
 *
 * The `onDone` callback fires for both:
 *   - Direct text replies (from portal_chat)
 *   - ai_processing_complete realtime events (from portal_upload_document)
 */

class AIPortalClient {
    /**
     * @param {object} opts
     * @param {string}   opts.customer   - ERPNext Customer name
     * @param {string}   opts.workflow   - AI Workflow.workflow_key
     * @param {function} [opts.onDone]   - (reply, action, actionData) => void
     * @param {function} [opts.onAction] - (action, actionData) => void  (convenience alias)
     * @param {function} [opts.onError]  - (errorMessage) => void
     */
    constructor({ customer, workflow, onDone, onAction, onError }) {
        this._customer = customer;
        this._workflow = workflow;
        this._onDone = onDone || (() => { });
        this._onAction = onAction || (() => { });
        this._onError = onError || (() => { });

        // Subscribe to the realtime event that signals async processing complete.
        // frappe.realtime is available on all Frappe-served pages including portals.
        if (typeof frappe !== "undefined" && frappe.realtime) {
            frappe.realtime.on("ai_processing_complete", this._handleRealtime.bind(this));
        }
    }

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Send a text message on the portal channel.
     *
     * @param {string}      text        - The user's message.
     * @param {string|null} contextHint - Optional context from the portal UI.
     * @returns {Promise<{reply, action, actionData}>}
     */
    async chat(text, contextHint = null) {
        try {
            const r = await frappe.call({
                method: "frappe_intelligence.api_portal.portal_chat",
                args: {
                    text,
                    customer: this._customer,
                    workflow_key: this._workflow,
                    context_hint: contextHint,
                },
            });
            const { reply, action, action_data: actionData } = r.message || {};
            this._onDone(reply, action, actionData);
            if (action) this._onAction(action, actionData);
            return { reply, action, actionData };
        } catch (err) {
            const msg = err?.message || String(err);
            this._onError(msg);
            throw err;
        }
    }

    /**
     * Enqueue processing for an uploaded file on the portal channel.
     * The result arrives asynchronously via the ai_processing_complete realtime
     * event — the onDone callback fires when it lands.
     *
     * @param {string}      fileUrl       - Frappe file URL (/files/… or /private/files/…)
     * @param {string|null} targetDoctype - AI Document Template document_type_key, or null
     * @returns {Promise<{status, log_name}>}
     */
    async uploadDocument(fileUrl, targetDoctype = null) {
        try {
            const r = await frappe.call({
                method: "frappe_intelligence.api_portal.portal_upload_document",
                args: {
                    file_url: fileUrl,
                    customer: this._customer,
                    target_doctype: targetDoctype,
                },
            });
            return r.message || {};
        } catch (err) {
            const msg = err?.message || String(err);
            this._onError(msg);
            throw err;
        }
    }

    /**
     * Fetch the current AI Agent Session state for this user + workflow.
     *
     * @returns {Promise<{status, current_step, step_prompt, collected_data}>}
     */
    async getSessionState() {
        try {
            const r = await frappe.call({
                method: "frappe_intelligence.api_portal.portal_get_session_state",
                args: {
                    customer: this._customer,
                    workflow_key: this._workflow,
                },
            });
            return r.message || {};
        } catch (err) {
            const msg = err?.message || String(err);
            this._onError(msg);
            throw err;
        }
    }

    /**
     * Remove the realtime listener.  Call on component unmount to prevent leaks.
     */
    destroy() {
        if (typeof frappe !== "undefined" && frappe.realtime) {
            frappe.realtime.off("ai_processing_complete", this._handleRealtime.bind(this));
        }
    }

    // -----------------------------------------------------------------------
    // Private
    // -----------------------------------------------------------------------

    /**
     * Handles the ai_processing_complete realtime push from portal_upload_document.
     * Fires onDone the same way a chat() reply would.
     */
    _handleRealtime(data) {
        const reply = data?.reply || null;
        const action = data?.action || null;
        const actionData = data?.action_data || null;
        this._onDone(reply, action, actionData);
        if (action) this._onAction(action, actionData);
    }
}

// CommonJS + ESM dual export so the class works from bundlers and plain <script>.
if (typeof module !== "undefined" && module.exports) {
    module.exports = { AIPortalClient };
} else if (typeof window !== "undefined") {
    window.AIPortalClient = AIPortalClient;
}
