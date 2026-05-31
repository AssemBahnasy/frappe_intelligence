/**
 * chat.js
 * -------
 * Text command flow: send/receive, chat message rendering,
 * and tool-result action buttons (navigate, create, search, map).
 */

export const chatMethods = {
    _sendTextCommand() {
        const self = this;
        const input = $("#fi-text-input");
        const text = input.val().trim();
        if (!text) return;

        input.val("");
        self._appendChatMessage("user", text);
        self._appendChatMessage("assistant", "…");

        frappe.call({
            method: "frappe_intelligence.api.handle_widget_input",
            args: {
                input_type: "text",
                text_input: text,
                doctype: self._currentDoctype,
                docname: self._currentDocname,
                widget_mode: self._widgetMode,
            },
            callback(r) {
                // Streaming already populated the bubble — only use the HTTP reply as fallback
                const lastBubble = $("#fi-chat-log .fi-chat-msg.assistant").last();
                if (!self._isStreaming && lastBubble.text() === "…") {
                    const msg = (r.message && r.message.reply) || __("No response from model.");
                    lastBubble.text(msg);
                }
                if (r.message) {
                    const action = r.message.action;
                    const data = r.message.action_data;
                    if (action === "map" && data) {
                        self._appendMapButton(data);
                    } else if (
                        (action === "navigate" || action === "open_record" || action === "create_record") &&
                        data &&
                        data.route
                    ) {
                        self._appendActionButton(action, data);
                    } else if (action === "search_results" && data) {
                        self._appendSearchResults(data);
                    }
                }
            },
            error() {
                $("#fi-chat-log .fi-chat-msg.assistant").last().text(__("Error communicating with server."));
            },
        });
    },

    _appendChatMessage(role, text) {
        const log = $("#fi-chat-log");
        log.append(`<div class="fi-chat-msg ${role}" dir="auto">${frappe.utils.escape_html(text)}</div>`);
        log.scrollTop(log[0].scrollHeight);
    },

    _showGlobalNavigationPrompt(result) {
        const self = this;
        const nav = self._navMap[result.document_type_key];
        if (!nav) return;

        const docLabel = result.document_type_key.replace(/_/g, " ");
        $("#fi-result-body").append(`
            <div class="fi-nav-prompt">
                <p>📂 ${__("{0} identified", [frappe.utils.escape_html(docLabel)])}</p>
                <p>${__("Go to {0} to save this?", [frappe.utils.escape_html(nav.label)])}</p>
                <div style="display:flex;gap:8px;margin-top:6px">
                    <button class="fi-action-btn fi-primary fi-nav-go"
                            data-route="${frappe.utils.escape_html(nav.route)}">
                        ${__("Go to {0}", [frappe.utils.escape_html(nav.label)])}
                    </button>
                    <button class="fi-action-btn fi-secondary fi-nav-dismiss">${__("Not now")}</button>
                </div>
            </div>`);
    },

    _appendMapButton(actionData) {
        const log = $("#fi-chat-log");
        const mapUrl = frappe.utils.escape_html(actionData.map_url || "");
        const lat = parseFloat(actionData.lat || 0).toFixed(5);
        const lon = parseFloat(actionData.lon || 0).toFixed(5);
        log.append(`
            <div class="fi-chat-msg fi-map-action">
                <a href="${mapUrl}" target="_blank" rel="noopener noreferrer" class="fi-map-btn">
                    🗺️ ${__("View on Map")} (${lat}, ${lon})
                </a>
            </div>`);
        log.scrollTop(log[0].scrollHeight);
    },

    _appendActionButton(action, data) {
        const log = $("#fi-chat-log");
        const icon = action === "create_record" ? "➕" : "↗️";
        const label = frappe.utils.escape_html(data.label || data.doctype || data.route || "");

        if (action === "create_record") {
            const doctype = frappe.utils.escape_html(data.doctype || "");
            const defaults = encodeURIComponent(JSON.stringify(data.defaults || {}));
            log.append(`
                <div class="fi-chat-msg fi-action-msg">
                    <button class="fi-map-btn fi-create-btn"
                        data-doctype="${doctype}"
                        data-defaults="${defaults}">
                        ${icon} ${label}
                    </button>
                </div>`);
        } else {
            const route = frappe.utils.escape_html(data.route || "");
            log.append(`
                <div class="fi-chat-msg fi-action-msg">
                    <button class="fi-map-btn fi-route-btn" data-route="${route}">
                        ${icon} ${label}
                    </button>
                </div>`);
        }
        log.scrollTop(log[0].scrollHeight);
    },

    _appendSearchResults(data) {
        const log = $("#fi-chat-log");
        const doctype = frappe.utils.escape_html(data.doctype || "");
        const results = data.results || [];
        if (!results.length) {
            log.append(`<div class="fi-chat-msg fi-action-msg fi-search-empty">${__("No records found.")}</div>`);
            log.scrollTop(log[0].scrollHeight);
            return;
        }
        const links = results.map((name) => {
            const eName = frappe.utils.escape_html(name);
            const slug = (data.doctype || "").toLowerCase().replace(/ /g, "-");
            const nameSlug = name.toLowerCase().replace(/ /g, "-").replace(/_/g, "-");
            const route = frappe.utils.escape_html(`/app/${slug}/${nameSlug}`);
            return `<a class="fi-search-link fi-route-btn" href="#" data-route="${route}">${eName}</a>`;
        }).join("");
        log.append(`
            <div class="fi-chat-msg fi-action-msg fi-search-results">
                <span class="fi-search-label">${doctype}:</span>
                ${links}
            </div>`);
        log.scrollTop(log[0].scrollHeight);
    },
};
