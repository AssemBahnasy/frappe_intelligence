// A topic's demo video in the user's language, else English (docs/tutorial/videos.md).
import TIMINGS from "./videos.json";

const FOLDER = "/assets/frappe_intelligence/tutorial";

export function video_of(topic) {
	const recorded = TIMINGS[topic.key] || {};
	const lang = recorded[frappe.boot.lang] ? frappe.boot.lang : "en";
	const timing = recorded[lang];
	if (!timing) return null;
	return {
		src: `${FOLDER}/${lang}/${topic.key}.mp4?v=${timing.version}`,
		duration: timing.duration,
		steps: timing.steps || [],
	};
}

// The step on screen at `seconds`: the last one that has started.
export function step_at(video, seconds) {
	let current = null;
	video.steps.forEach((start, index) => {
		if (start != null && start <= seconds) current = index;
	});
	return current;
}

export const clock = (seconds) => {
	const s = Math.floor(seconds || 0);
	return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};
