/**
 * voice.js
 * --------
 * Voice recording (MediaRecorder), audio upload, and Whisper transcription.
 */

export const voiceMethods = {
    _toggleRecording() {
        if (this._mediaRecorder && this._mediaRecorder.state === "recording") {
            this._stopRecording();
        } else {
            this._startRecording();
        }
    },

    _startRecording() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            frappe.msgprint(
                __("Microphone access requires a secure connection (HTTPS or localhost). Voice recording is not available on HTTP.")
            );
            return;
        }

        const self = this;
        self._audioChunks = [];

        navigator.mediaDevices
            .getUserMedia({ audio: true })
            .then((stream) => {
                self._mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

                self._mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) self._audioChunks.push(e.data);
                };

                self._mediaRecorder.onstop = () => {
                    const blob = new Blob(self._audioChunks, { type: "audio/webm" });
                    self._transcribeAudio(blob);
                    // Stop all tracks to release mic
                    stream.getTracks().forEach((t) => t.stop());
                };

                self._mediaRecorder.start();
                $("#fi-voice-record").text("⏹️").addClass("fi-recording");
                $("#fi-voice-status").text(__("Recording…"));
            })
            .catch((err) => {
                frappe.msgprint(__("{0}", [err.message]));
            });
    },

    _stopRecording() {
        if (this._mediaRecorder) {
            this._mediaRecorder.stop();
            $("#fi-voice-record").text("🎙️").removeClass("fi-recording");
            $("#fi-voice-status").text(__("Transcribing…"));
        }
    },

    _transcribeAudio(blob) {
        const self = this;
        const formData = new FormData();
        formData.append("file", blob, "voice_command.webm");
        formData.append("is_private", "1");

        // Upload audio file via fetch, then call transcription endpoint
        fetch("/api/method/upload_file", {
            method: "POST",
            headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
            body: formData,
        })
            .then((r) => r.json())
            .then((data) => {
                const fileUrl = data.message && data.message.file_url;
                if (!fileUrl) throw new Error("Upload failed");

                return frappe.call({
                    method: "frappe_intelligence.api.chat.handle_widget_input",
                    args: {
                        input_type: "voice",
                        file_url: fileUrl,
                        doctype: self._currentDoctype,
                        docname: self._currentDocname,
                        widget_mode: self._widgetMode,
                    },
                });
            })
            .then((r) => {
                const transcript = r.message && r.message.transcript;
                const reply = r.message && r.message.reply;
                if (transcript) {
                    $("#fi-voice-transcript").text(transcript);
                    $("#fi-voice-status").text(__("Transcription complete"));
                }
                if (reply) {
                    frappe.show_alert({ message: reply, indicator: "blue" }, 8);
                }
                // Map action: append a clickable link in the voice panel body
                if (r.message && r.message.action === "map" && r.message.action_data) {
                    const data = r.message.action_data;
                    const mapUrl = frappe.utils.escape_html(data.map_url || "");
                    const lat = parseFloat(data.lat || 0).toFixed(5);
                    const lon = parseFloat(data.lon || 0).toFixed(5);
                    $("#fi-voice-panel .fi-voice-body").append(`
                        <a href="${mapUrl}" target="_blank" rel="noopener noreferrer"
                           class="fi-map-btn" style="margin-top:10px;display:block">
                            🗺️ ${__("View on Map")} (${lat}, ${lon})
                        </a>`);
                }
            })
            .catch((err) => {
                $("#fi-voice-status").text(__("Transcription failed."));
                frappe.msgprint(`${__("Error")}: ${err.message}`);
            });
    },
};
