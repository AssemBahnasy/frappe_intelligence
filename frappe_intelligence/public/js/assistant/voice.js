// Voice input (board 3c): recorded in the browser, turned into text on the server (api/voice.py).
// The text goes into the message box; the user checks it and sends.

import { job_result } from "../shared/background";
import { upload_file } from "./uploads";

// The first the browser can record; Whisper reads them all.
const TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

export class Recorder {
	async start() {
		if (!navigator.mediaDevices?.getUserMedia) {
			throw new Error(__("Voice input needs a secure connection (HTTPS)."));
		}
		try {
			this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		} catch (e) {
			throw new Error(
				e.name === "NotAllowedError"
					? __("The browser was not allowed to use the microphone.")
					: e.message
			);
		}
		const type = TYPES.find((t) => MediaRecorder.isTypeSupported(t));
		this.recorder = new MediaRecorder(this.stream, type ? { mimeType: type } : {});
		this.chunks = [];
		this.recorder.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
		this.recorder.start();
	}

	// The recording as a File.
	stop() {
		return new Promise((resolve) => {
			this.recorder.onstop = () => {
				this.release();
				const type = this.recorder.mimeType || "audio/webm";
				const ext = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "m4a" : "webm";
				resolve(new File(this.chunks, `voice-${Date.now()}.${ext}`, { type }));
			};
			this.recorder.stop();
		});
	}

	release() {
		this.stream?.getTracks().forEach((track) => track.stop());
	}
}

export async function transcribe(recording) {
	const { file_url } = await upload_file(recording);
	const { job } = await frappe.xcall("frappe_intelligence.api.voice.transcribe", { file_url });
	return job_result(job);
}
