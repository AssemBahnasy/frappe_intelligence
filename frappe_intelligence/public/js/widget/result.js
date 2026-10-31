/**
 * result.js
 * ---------
 * Extraction result display, low-confidence review flow, and correction form.
 */

export const resultMethods = {
    _showResult(result) {
        const self = this;
        const data = result.extracted_data || {};
        const confidence = ((result.confidence_score || 0) * 100).toFixed(1);
        const docKey = result.document_type_key || "—";

        let rows = "";
        Object.entries(data).forEach(([k, v]) => {
            const val = v !== null && v !== undefined ? v : '<em class="fi-empty">—</em>';
            rows += `<tr>
                <td class="fi-key">${frappe.utils.escape_html(k)}</td>
                <td class="fi-val" dir="auto">${frappe.utils.escape_html(String(val))}</td>
            </tr>`;
        });

        const body = `
      <div class="fi-result-meta">
        <span class="fi-badge">${frappe.utils.escape_html(docKey)}</span>
        <span class="fi-confidence ${parseFloat(confidence) >= 70 ? "fi-good" : "fi-warn"}">
          ${confidence}% ${__("confidence")}
        </span>
      </div>
      <table class="fi-result-table">
        <tbody>${rows || `<tr><td colspan='2'>${__("No data extracted.")}</td></tr>`}</tbody>
      </table>
      <p class="fi-log-ref">${__("Log")}: <a href="/app/ai-processing-log/${result.log_name}" target="_blank">${frappe.utils.escape_html(result.log_name)}</a></p>
    `;

        self._renderResultPanel(__("Extraction Result"), body);

        // Store for correction flow
        self._lastResult = result;
    },

    _showReviewPrompt(result) {
        const self = this;
        const data = result.extracted_data || {};
        const confidence = ((result.confidence_score || 0) * 100).toFixed(1);
        const docKey = result.document_type_key || "—";

        let rows = "";
        Object.entries(data).forEach(([k, v]) => {
            const val = v !== null && v !== undefined ? String(v) : "";
            rows += `<tr>
                <td class="fi-key">${frappe.utils.escape_html(k)}</td>
                <td class="fi-val">
                    <input class="fi-review-input" data-key="${frappe.utils.escape_html(k)}"
                           value="${frappe.utils.escape_html(val)}" dir="auto">
                </td>
            </tr>`;
        });

        const body = `
            <div class="fi-review-banner">
                ⚠️ ${__("Low confidence ({0}%) — edit if needed, then accept.", [confidence])}
                <span class="fi-badge" style="margin-inline-start:auto">${frappe.utils.escape_html(docKey)}</span>
            </div>
            <table class="fi-result-table">
                <tbody>${rows || `<tr><td colspan="2">${__("No data extracted.")}</td></tr>`}</tbody>
            </table>
            <p class="fi-log-ref">${__("Log")}: <a href="/app/ai-processing-log/${result.log_name}" target="_blank">${frappe.utils.escape_html(result.log_name)}</a></p>
        `;

        self._lastResult = result;
        self._pendingReview = {
            log_name: result.log_name,
            doctype: self._currentDoctype,
            docname: self._currentDocname,
        };

        $("#fi-result-title").text(__("Review Required"));
        $("#fi-result-body").html(body);
        $(".fi-result-footer").html(`
            <button id="fi-review-discard" class="fi-action-btn fi-secondary">${__("Discard")}</button>
            <button id="fi-review-accept" class="fi-action-btn fi-primary">${__("Accept")}</button>
        `).show();
        this._hideProgress();
        this._openPanel("fi-result-panel");

        $(document).one("click", "#fi-review-discard", () => self._closeAll());
        $(document).one("click", "#fi-review-accept", () => self._acceptReview());
    },

    _acceptReview() {
        const self = this;
        if (!self._pendingReview) { self._closeAll(); return; }

        // Collect values from the editable review inputs
        const original = self._lastResult.extracted_data || {};
        const edited = {};
        let hasEdits = false;
        $(".fi-review-input").each(function () {
            const key = $(this).data("key");
            const newVal = $(this).val();
            edited[key] = newVal;
            if (newVal !== String(original[key] ?? "")) hasEdits = true;
        });

        const { log_name, doctype, docname } = self._pendingReview;

        const doConfirm = () => {
            frappe.call({
                method: "frappe_intelligence.api.documents.confirm_extraction",
                args: { log_name, doctype, docname },
                callback() {
                    frappe.show_alert({ message: __("Extraction confirmed!"), indicator: "green" }, 4);
                    self._closeAll();
                },
            });
        };

        if (hasEdits) {
            // Save the user's corrections as a training pair, then confirm
            frappe.call({
                method: "frappe_intelligence.api.documents.submit_correction",
                args: { log_name, corrected_extraction: edited },
                callback: doConfirm,
            });
        } else {
            doConfirm();
        }
    },

    _renderResultPanel(title, bodyHtml) {
        $("#fi-result-title").text(title);
        $("#fi-result-body").html(bodyHtml);
        // Restore standard footer buttons (may have been replaced by review mode)
        $(".fi-result-footer").html(`
            <button id="fi-result-correct" class="fi-action-btn fi-secondary">${__("Correct")}</button>
            <button id="fi-result-done" class="fi-action-btn fi-primary">${__("Done")}</button>
        `).show();
        this._hideProgress();
        this._openPanel("fi-result-panel");
    },

    _showError(msg) {
        this._renderResultPanel("Error", `<p class="fi-error">${frappe.utils.escape_html(msg)}</p>`);
    },

    _openCorrectionFlow() {
        const self = this;
        if (!self._lastResult) return;

        const data = self._lastResult.extracted_data || {};
        let fields = "";
        Object.entries(data).forEach(([k, v]) => {
            fields += `
        <div class="fi-correction-row">
          <label class="fi-correction-label">${frappe.utils.escape_html(k)}</label>
          <input class="fi-correction-input" data-key="${frappe.utils.escape_html(k)}"
                 value="${frappe.utils.escape_html(String(v ?? ""))}" dir="auto">
        </div>`;
        });

        const body = `
      <div class="fi-correction-form">${fields}</div>
      <button id="fi-correction-submit" class="fi-action-btn fi-primary">${__("Submit Correction")}</button>`;

        self._renderResultPanel(__("Correct Extraction"), body);

        $(document).one("click", "#fi-correction-submit", () => {
            const corrected = {};
            $(".fi-correction-input").each(function () {
                corrected[$(this).data("key")] = $(this).val();
            });

            frappe.call({
                method: "frappe_intelligence.api.documents.submit_correction",
                args: {
                    log_name: self._lastResult.log_name,
                    corrected_extraction: corrected,
                },
                callback() {
                    frappe.show_alert({ message: __("Correction saved!"), indicator: "green" }, 5);
                    self._closeAll();
                },
            });
        });
    },
};
