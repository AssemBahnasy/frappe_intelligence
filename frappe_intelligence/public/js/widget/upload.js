/**
 * upload.js
 * ---------
 * File upload panel: checklist builder, file upload handler, mismatch prompt.
 *
 * Upload flow (async)
 * -------------------
 * 1. User selects a file → Frappe stores it (fast).
 * 2. Widget calls api.process_document → server enqueues background job,
 *    returns {"status": "queued", "log_name": ...} immediately.
 * 3. Widget shows "Processing in background…" progress state.
 * 4. Background worker finishes → server fires realtime "ai_processing_complete"
 *    AND/OR the widget polls the log every 5 s as a fallback.
 * 5. _handleProcessingResult(result) renders the outcome.
 */

export const uploadMethods = {
    _openUploadPanel() {
        const self = this;
        const list = $("#fi-checklist").empty();

        if (self._widgetMode === "global") {
            // Global mode — general document classifier
            list.append(`
                <div class="fi-global-hint">
                    <span class="fi-global-hint-icon">🔍</span>
                    <p>${__("Upload any document. I'll identify it and suggest where to save it.")}</p>
                </div>`);
            list.append(self._checklistBtn("auto", "📤", __("Upload & Identify"), false));
        } else {
            // Proactive mode — Smart Checklist
            list.append(self._checklistBtn("auto", "🔍", __("Auto-detect"), false));

            if (self._requiredDocs.length > 0) {
                list.append(`<p class="fi-checklist-label">${__("Required documents")}</p>`);
                self._requiredDocs.forEach((doc) => {
                    list.append(self._checklistBtn(doc.document_type_key, "⚠️", doc.label, true));
                });
            }

            frappe.call({
                method: "frappe_intelligence.api.documents.list_templates",
                callback(r) {
                    if (!r.message) return;
                    const requiredKeys = self._requiredDocs.map((d) => d.document_type_key);
                    list.append(`<p class="fi-checklist-label">${__("All templates")}</p>`);
                    r.message.forEach((t) => {
                        if (!requiredKeys.includes(t.document_type_key)) {
                            list.append(
                                self._checklistBtn(t.document_type_key, "📄", t.document_name, false)
                            );
                        }
                    });
                },
            });
        }

        self._openPanel("fi-upload-panel");
    },

    _checklistBtn(key, icon, label, highlight) {
        const cls = highlight ? "fi-checklist-btn fi-highlight" : "fi-checklist-btn";
        return `
      <button class="${cls}" data-key="${key}">
        <span class="fi-btn-icon">${icon}</span>
        <span>${label}</span>
      </button>`;
    },

    _handleFileUpload(file) {
        const self = this;
        self._openPanel("fi-result-panel");
        self._showProgress(__("Uploading file…"));

        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                self._setProgress(`${__("Uploading file…")} ${pct}%`);
            }
        });

        xhr.onreadystatechange = function () {
            if (xhr.readyState !== XMLHttpRequest.DONE) return;

            if (xhr.status !== 200) {
                self._hideProgress();
                self._showError(__("File upload failed. Please try again."));
                return;
            }

            let data;
            try { data = JSON.parse(xhr.responseText); } catch (_) {
                self._hideProgress();
                self._showError(__("File upload failed. Please try again."));
                return;
            }

            const fileUrl = data?.message?.file_url;
            if (!fileUrl) {
                self._hideProgress();
                self._showError(__("File upload failed. Please try again."));
                return;
            }

            self._setProgress(__("Queuing document for processing…"));

            frappe.call({
                method: "frappe_intelligence.api.documents.process_document",
                args: {
                    file_url: fileUrl,
                    target_doctype: self._pendingFileDoctype || null,
                },
                callback(r) {
                    if (r.message && r.message.status === "queued") {
                        self._setProgress(__("Processing in background… you'll be notified when done."));
                        // Realtime is the primary delivery channel.
                        // Poll every 5 s as a fallback in case the socket.io
                        // event doesn't arrive (dev proxies, VPNs, etc.).
                        self._startLogPoller(r.message.log_name);
                        return;
                    }
                    // Unexpected synchronous response — handle directly.
                    self._hideProgress();
                    if (r.message) self._handleProcessingResult(r.message);
                },
                error() {
                    self._hideProgress();
                    self._showError(__("Processing failed. Check the AI Processing Log."));
                },
            });
        };

        const formData = new FormData();
        formData.append("file", file, file.name);
        formData.append("is_private", "1");
        formData.append("folder", "Home/Attachments");

        xhr.open("POST", "/api/method/upload_file", true);
        xhr.setRequestHeader("Accept", "application/json");
        xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
        xhr.send(formData);
    },

    // ------------------------------------------------------------------
    // Polling fallback (in case socket.io realtime event doesn't arrive)
    // ------------------------------------------------------------------

    _startLogPoller(logName) {
        const self = this;
        self._stopLogPoller();  // clear any previous poller
        self._logPollName = logName;
        self._logPollTimer = setInterval(() => {
            frappe.call({
                method: "frappe_intelligence.api.documents.get_log_status",
                args: { log_name: logName },
                callback(r) {
                    const msg = r.message;
                    if (!msg) return;
                    if (msg.status === "Completed" || msg.status === "Failed") {
                        self._stopLogPoller();
                        self._handleProcessingResult(msg.result);
                    }
                },
            });
        }, 5000);
    },

    _stopLogPoller() {
        if (this._logPollTimer) {
            clearInterval(this._logPollTimer);
            this._logPollTimer = null;
        }
        this._logPollName = null;
    },

    // Called by realtime listener (events.js) and by the polling fallback.
    _handleProcessingResult(result) {
        const self = this;
        self._stopLogPoller();  // realtime arrived — cancel polling

        if (result.status === "failed") {
            self._showError(__("Processing failed. Check the AI Processing Log for details."));
            return;
        }

        // Mismatch detection
        if (
            self._pendingFileDoctype &&
            result.document_type_key &&
            result.document_type_key !== self._pendingFileDoctype
        ) {
            self._showMismatchPrompt(result);
            return;
        }

        if (result.needs_review) {
            self._showReviewPrompt(result);
        } else {
            self._showResult(result);
            if (self._widgetMode === "global" && result.document_type_key) {
                self._showGlobalNavigationPrompt(result);
            }
        }
    },

    _showMismatchPrompt(result) {
        const self = this;
        const detected = result.document_type_key || "unknown";
        const detectedLabel = detected.replace(/_/g, " ");

        const body = `
      <div class="fi-mismatch">
        <p>⚠️ ${__("I detected a {0}. Should I extract data from it instead?", [detectedLabel])}</p>
        <button class="fi-action-btn fi-primary" id="fi-mismatch-yes">${__("Yes, use {0}", [detectedLabel])}</button>
        <button class="fi-action-btn fi-secondary" id="fi-mismatch-no">${__("No, cancel")}</button>
      </div>`;

        self._renderResultPanel(__("Document Mismatch Detected"), body);

        $(document).one("click", "#fi-mismatch-yes", () => self._showResult(result));
        $(document).one("click", "#fi-mismatch-no", () => self._closeAll());
    },
};
