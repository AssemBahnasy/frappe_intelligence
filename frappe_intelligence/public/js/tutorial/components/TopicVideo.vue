<template>
	<figure class="fi-video">
		<video
			ref="element"
			:src="source"
			:aria-label="__('{0}, shown on the desk', [title])"
			:autoplay="!reduced_motion"
			muted
			loop
			playsinline
			@play="
				playing = true;
				follow();
			"
			@pause="playing = false"
			@timeupdate="follow"
			@loadedmetadata="duration = element.duration"
		></video>
		<div class="fi-video-bar">
			<button
				type="button"
				class="fi-video-button"
				:aria-label="playing ? __('Pause') : __('Play')"
				@click="toggle"
			>
				<svg v-if="playing" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
					<rect x="2" y="1.5" width="2.6" height="9" rx="0.6" />
					<rect x="7.4" y="1.5" width="2.6" height="9" rx="0.6" />
				</svg>
				<svg
					v-else
					class="fi-flip"
					width="12"
					height="12"
					viewBox="0 0 12 12"
					aria-hidden="true"
				>
					<path d="M3 1.5v9l7.5-4.5z" />
				</svg>
			</button>
			<span class="fi-video-track">
				<input
					type="range"
					min="0"
					:max="duration"
					step="0.1"
					:value="time"
					:aria-label="__('Video position')"
					:aria-valuetext="clock(time)"
					:style="{ '--fill': percent(time) }"
					@input="seek_to(Number($event.target.value))"
				/>
				<span
					v-for="(start, index) in markers"
					:key="index"
					:class="['fi-video-marker', { 'is-passed': start <= time }]"
					:style="{ insetInlineStart: percent(start) }"
					:title="__('Step {0}', [index + 1])"
				></span>
			</span>
			<span class="fi-video-time">{{ clock(time) }} / {{ clock(duration) }}</span>
			<button
				type="button"
				class="fi-video-button"
				:aria-label="__('Full screen')"
				@click="element.requestFullscreen?.()"
			>
				<svg
					width="14"
					height="14"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					aria-hidden="true"
				>
					<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
				</svg>
			</button>
		</div>
	</figure>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { clock, step_at } from "../videos";

const props = defineProps({
	video: { type: Object, required: true },
	title: { type: String, required: true },
});
// The step on screen and whether the video plays, for the step panels below it.
const emit = defineEmits(["step", "playing"]);
const step = ref(null);
const playing = ref(false);
watch(step, (index) => emit("step", index));
watch(playing, (value) => emit("playing", value));

const element = ref(null);
const source = ref(null);
const time = ref(0);
const duration = ref(props.video.duration);
const reduced_motion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const markers = computed(() => props.video.steps.filter((start) => start != null));

// timeupdate comes about four times a second; while playing, the bar follows every frame.
let frame = null;
function follow() {
	time.value = element.value.currentTime;
	step.value = step_at(props.video, time.value);
	cancelAnimationFrame(frame);
	if (playing.value) frame = requestAnimationFrame(follow);
}

// play() refuses until the file is in; nothing to report then.
const play = () => element.value.play().catch(() => {});

function toggle() {
	element.value.paused ? play() : element.value.pause();
}

function seek_to(seconds) {
	element.value.currentTime = seconds;
	follow();
}

// Plays from where step `index` starts (a click on its panel).
function seek(index) {
	const start = props.video.steps[index];
	if (start == null) return;
	seek_to(start);
	play();
}

const percent = (seconds) => `${Math.min(100, (seconds / (duration.value || 1)) * 100)}%`;

// Played from memory: a server that does not answer range requests (the development server)
// cannot be sought in otherwise. The clips are small, and the browser caches the file.
let unmounted = false;
onMounted(async () => {
	const blob = await fetch(props.video.src)
		.then((r) => (r.ok ? r.blob() : null))
		.catch(() => null);
	if (unmounted) return;
	source.value = blob ? URL.createObjectURL(blob) : props.video.src;
});
onBeforeUnmount(() => {
	unmounted = true;
	cancelAnimationFrame(frame);
	if (source.value?.startsWith("blob:")) URL.revokeObjectURL(source.value);
});
defineExpose({ seek });
</script>

<style scoped>
.fi-video {
	margin: 0;
	max-width: 820px;
	display: flex;
	flex-direction: column;
	gap: 8px;
}
video {
	display: block;
	width: 100%;
	aspect-ratio: 16 / 9;
	border-radius: var(--radius-lg);
	border: 1px solid var(--outline-gray-2);
	background: var(--surface-gray-1);
}
.fi-video-bar {
	display: flex;
	align-items: center;
	gap: var(--padding-md);
}
.fi-video-button {
	flex: none;
	width: 30px;
	height: 30px;
	border: 0;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-9);
	display: grid;
	place-items: center;
}
.fi-video-button:hover {
	background: var(--surface-gray-3);
}
.fi-video-button svg {
	fill: currentColor;
}
.fi-video-button svg[fill="none"] {
	fill: none;
}
.fi-flip:dir(rtl) {
	transform: scaleX(-1);
}
.fi-video-track {
	position: relative;
	flex: 1;
	display: flex;
	align-items: center;
}
input[type="range"] {
	width: 100%;
	height: 14px;
	margin: 0;
	background: transparent;
	appearance: none;
	cursor: pointer;
}
input[type="range"]::-webkit-slider-runnable-track {
	height: 4px;
	border-radius: 2px;
	background: linear-gradient(
		to right,
		var(--ink-violet-6) var(--fill),
		var(--surface-gray-3) var(--fill)
	);
}
input[type="range"]::-moz-range-track {
	height: 4px;
	border-radius: 2px;
	background: linear-gradient(
		to right,
		var(--ink-violet-6) var(--fill),
		var(--surface-gray-3) var(--fill)
	);
}
input[type="range"]:dir(rtl)::-webkit-slider-runnable-track {
	background: linear-gradient(
		to left,
		var(--ink-violet-6) var(--fill),
		var(--surface-gray-3) var(--fill)
	);
}
input[type="range"]:dir(rtl)::-moz-range-track {
	background: linear-gradient(
		to left,
		var(--ink-violet-6) var(--fill),
		var(--surface-gray-3) var(--fill)
	);
}
input[type="range"]::-webkit-slider-thumb {
	appearance: none;
	width: 12px;
	height: 12px;
	margin-top: -4px;
	border-radius: var(--radius-full);
	background: var(--ink-violet-6);
	border: 2px solid var(--surface-base);
}
input[type="range"]::-moz-range-thumb {
	width: 12px;
	height: 12px;
	border-radius: var(--radius-full);
	background: var(--ink-violet-6);
	border: 2px solid var(--surface-base);
}
.fi-video-marker {
	position: absolute;
	top: 50%;
	width: 10px;
	height: 10px;
	margin-top: -5px;
	margin-inline-start: -5px;
	border-radius: var(--radius-full);
	box-sizing: border-box;
	background: var(--surface-base);
	border: 2px solid var(--outline-gray-3);
	pointer-events: none;
}
.fi-video-marker.is-passed {
	background: var(--ink-violet-6);
	border-color: var(--surface-base);
}
/* A clock reads left to right in Arabic players too. */
.fi-video-time {
	flex: none;
	direction: ltr;
	unicode-bidi: isolate;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
	font-variant-numeric: tabular-nums;
}
</style>
