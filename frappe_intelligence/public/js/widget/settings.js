/**
 * settings.js
 * -----------
 * AI Settings loader, page-context watcher, and proactive bubble logic.
 */

export const settingsMethods = {
    _applySettings() {
        const self = this;
        frappe.call({
            method: "frappe_intelligence.api.settings.get_widget_settings",
            callback(r) {
                const s = (r && r.message) || {};
                const root = document.getElementById("fi-widget-root");
                if (!root) return;

                // Role-based access — remove widget entirely if user lacks permission
                if (s.allowed_roles && s.allowed_roles.length > 0) {
                    const userRoles = frappe.user_roles || [];
                    const hasAccess = s.allowed_roles.some((role) => userRoles.includes(role));
                    if (!hasAccess) {
                        root.remove();
                        return;
                    }
                }

                if (s.assistant_name) {
                    self._assistantName = s.assistant_name;
                }

                if (s.widget_icon) {
                    self._fabDefaultIcon = `<img src="${frappe.utils.escape_html(s.widget_icon)}" class="fi-fab-custom-icon" alt="">`;
                    if (self._state === "idle") {
                        const iconEl = root.querySelector(".fi-fab-icon");
                        if (iconEl) iconEl.innerHTML = self._fabDefaultIcon;
                    }
                }

                if (s.route_map && typeof s.route_map === "object") {
                    self._navMap = s.route_map;
                }
            },
        });
    },

    _startPageWatcher() {
        const self = this;
        self._checkPageContext();
        $(document).on("page-change", () => self._checkPageContext());
    },

    _checkPageContext() {
        const self = this;
        const route = frappe.get_route();
        const isForm = route && route[0] === "Form" && route[1] && route[2];

        if (!isForm) {
            self._currentDoctype = (route && route[1]) ? route[1] : null;
            self._currentDocname = null;
            self._requiredDocs = [];
            self._widgetMode = "global";
            self._hideBubble();
            return;
        }

        self._currentDoctype = route[1];
        self._currentDocname = route[2];

        frappe.call({
            method: "frappe_intelligence.api.documents.get_required_documents",
            args: { doctype: self._currentDoctype, docname: self._currentDocname },
            callback(r) {
                const docs = (r.message && r.message.missing) || [];
                self._requiredDocs = docs;
                if (docs.length > 0) {
                    self._widgetMode = "proactive";
                    const first = docs[0];
                    const label = first.label || first.document_type_key;
                    self._showBubble(__("{0} missing document(s)", [label]));
                } else {
                    self._widgetMode = "global";
                    self._hideBubble();
                }
            },
            error() {
                self._widgetMode = "global";
                self._hideBubble();
            },
        });
    },
};
