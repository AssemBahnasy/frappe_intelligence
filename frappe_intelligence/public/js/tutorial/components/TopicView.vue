<template>
	<article class="fi-topic-view">
		<a
			v-if="store.next && store.next.key !== topic.key"
			class="fi-continue"
			:href="url(store.next)"
			@click.prevent="go(store.next)"
		>
			<span class="fi-continue-text">
				<span class="fi-continue-where">
					{{
						__("Continue where you left off · Chapter {0}", [chapter_of(store.next).n])
					}}
				</span>
				<span class="fi-continue-title">
					{{ store.next.title }} · {{ minutes(store.next) }}
				</span>
			</span>
			<span class="fi-continue-button">{{ __("Continue") }}</span>
		</a>

		<header class="fi-head">
			<span class="fi-where">{{ where }}</span>
			<h1>{{ topic.title }}</h1>
			<p>{{ topic.text }}</p>
			<span class="fi-chips">
				<span class="fi-chip">
					{{ __("{0} steps", [topic.steps.length]) }} · {{ minutes(topic) }}
				</span>
				<span v-if="video" class="fi-chip">{{
					__("Video · {0}", [clock(video.duration)])
				}}</span>
				<span v-if="store.done.has(topic.key)" class="fi-chip is-done">{{
					__("Done")
				}}</span>
				<span v-else-if="topic.status" :class="['fi-chip', 'is-' + topic.status.tone]">
					{{ topic.status.tag }}
				</span>
			</span>
		</header>

		<TopicVideo
			v-if="video"
			:key="topic.key"
			ref="player"
			@step="playing_step = $event"
			@playing="playing = $event"
			:video="video"
			:title="topic.title"
		/>

		<ol :class="['fi-steps', { 'has-video': video }]">
			<li
				v-for="(step, index) in topic.steps"
				:key="index"
				:class="['fi-step', { 'is-playing': video && index === playing_step }]"
			>
				<!-- With a video, the whole panel plays that step; without one, its picture shows it. -->
				<button
					v-if="video"
					type="button"
					class="fi-step-seek"
					:aria-label="__('Play step {0}', [index + 1])"
					@click="player.seek(index)"
				></button>
				<StepPicture v-else :name="step.picture" />
				<span class="fi-step-number">
					{{ __("Step {0}", [index + 1]) }}
					<span v-if="playing && index === playing_step" class="fi-step-playing">
						{{ __("Playing") }}
					</span>
				</span>
				<span class="fi-step-title">{{ step.title }}</span>
				<span class="fi-step-text">{{ step.text }}</span>
			</li>
		</ol>

		<div class="fi-more">
			<section v-if="topic.tips?.length" class="fi-tips">
				<h2>{{ __("Good to know") }}</h2>
				<ul>
					<li v-for="tip in topic.tips" :key="tip">{{ tip }}</li>
				</ul>
			</section>
			<section v-if="related.length" class="fi-related">
				<h2>{{ __("Related") }}</h2>
				<a v-for="t in related" :key="t.key" :href="url(t)" @click.prevent="go(t)">
					{{ t.title }}
				</a>
			</section>
		</div>

		<nav class="fi-neighbours" :aria-label="__('Other topics')">
			<a
				v-if="store.previous_topic"
				:href="url(store.previous_topic)"
				@click.prevent="go(store.previous_topic)"
			>
				{{ __("Previous: {0}", [store.previous_topic.title]) }}
			</a>
			<span v-else></span>
			<a
				v-if="store.next_topic"
				:href="url(store.next_topic)"
				@click.prevent="go(store.next_topic)"
			>
				{{ __("Next: {0}", [store.next_topic.title]) }}
			</a>
		</nav>
	</article>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useTutorial } from "../store";
import { clock, video_of } from "../videos";
import StepPicture from "./StepPicture.vue";
import TopicVideo from "./TopicVideo.vue";

const PAGE = "intelligence-tutorial";
const props = defineProps({ topic: { type: Object, required: true } });
const store = useTutorial();

const url = (topic) => frappe.router.make_url([PAGE, topic.key]);
const go = (topic) => frappe.set_route(PAGE, topic.key);
const minutes = (topic) => __("{0} min", [topic.minutes]);
const chapter_of = (topic) => store.all_chapters.find((c) => c.key === topic.chapter);
const related = computed(() => store.related(props.topic));
const video = computed(() => video_of(props.topic));
const player = ref(null);
const playing_step = ref(null);
const playing = ref(false);
watch(
	() => props.topic.key,
	() => {
		playing_step.value = null;
		playing.value = false;
	}
);

// "Chapter 2 · Work faster · Topic 1 of 3"
const where = computed(() => {
	const chapter = chapter_of(props.topic);
	const position = chapter.topics.findIndex((t) => t.key === props.topic.key) + 1;
	return [
		__("Chapter {0}", [chapter.n]),
		chapter.title,
		__("Topic {0} of {1}", [position, chapter.total]),
	].join(" · ");
});
</script>

<style scoped>
.fi-topic-view {
	flex: 999 1 360px;
	min-width: 0;
	padding: var(--padding-lg) var(--padding-xl) var(--padding-2xl, 32px);
	display: flex;
	flex-direction: column;
	gap: var(--padding-lg);
}
/* The brand's indigo, as on the Apps screen tile, in light and dark themes alike. */
.fi-continue {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: var(--padding-sm);
	padding: 12px 16px;
	border-radius: var(--radius-lg);
	background: #1e1b4b;
	color: #fff;
	text-decoration: none;
}
.fi-continue:hover {
	text-decoration: none;
	color: #fff;
}
.fi-continue-text {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.fi-continue-where {
	font-size: var(--text-xs);
	color: #c9c0ff;
}
.fi-continue-title {
	font-size: var(--text-base);
	font-weight: 600;
}
.fi-continue-button {
	padding: 6px 14px;
	border-radius: var(--radius);
	background: #fff;
	color: #1e1b4b;
	font-size: var(--text-sm);
	font-weight: 600;
}
.fi-head {
	display: flex;
	flex-direction: column;
	gap: 6px;
	max-width: 640px;
}
.fi-where {
	font-size: var(--text-xs);
	font-weight: 500;
	color: var(--ink-violet-6);
}
h1 {
	margin: 0;
	font-size: var(--text-2xl);
	font-weight: 600;
	color: var(--ink-gray-9);
}
p {
	margin: 0;
	font-size: var(--text-base);
	line-height: 1.55;
	color: var(--ink-gray-6);
}
.fi-chips {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	padding-top: 2px;
}
.fi-chip {
	padding: 2px 8px;
	border-radius: var(--radius-full);
	background: var(--surface-gray-2);
	color: var(--ink-gray-7);
	font-size: var(--text-xs);
	font-weight: 500;
}
.fi-chip.is-done {
	background: var(--surface-green-2);
	color: var(--ink-green-7);
}
.fi-chip.is-off {
	background: var(--surface-amber-2);
	color: var(--ink-amber-7);
}
.fi-steps {
	margin: 0;
	padding: 0;
	list-style: none;
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
	gap: var(--padding-md);
}
.fi-step {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 12px;
	border-radius: var(--radius-lg);
	background: var(--surface-gray-1);
}
.fi-step-number {
	margin-top: 4px;
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--text-xs);
	font-weight: 600;
	color: var(--ink-violet-6);
}
.fi-steps.has-video {
	max-width: 820px;
}
.has-video .fi-step {
	position: relative;
	padding: 14px;
}
.has-video .fi-step-number {
	margin-top: 0;
}
.has-video .fi-step:hover {
	background: var(--surface-gray-2);
}
.fi-step.is-playing,
.fi-step.is-playing:hover {
	background: var(--surface-violet-2);
	box-shadow: inset 0 0 0 2px var(--ink-violet-4);
}
/* Covers the panel, so a click anywhere on it plays that step. */
.fi-step-seek {
	position: absolute;
	inset: 0;
	border: 0;
	border-radius: inherit;
	background: transparent;
	cursor: pointer;
}
.fi-step-playing {
	padding: 1px 6px;
	border-radius: var(--radius-full);
	background: var(--surface-base);
	color: var(--ink-violet-7);
	font-size: var(--text-2xs, 10px);
	font-weight: 500;
}
.fi-step-title {
	font-size: var(--text-base);
	font-weight: 600;
	color: var(--ink-gray-9);
}
.fi-step-text {
	font-size: var(--text-sm);
	line-height: 1.45;
	color: var(--ink-gray-6);
}
.fi-more {
	display: flex;
	flex-wrap: wrap;
	gap: var(--padding-xl);
}
.fi-more h2 {
	margin: 0 0 8px;
	font-size: var(--text-base);
	font-weight: 600;
	color: var(--ink-gray-9);
}
.fi-tips {
	flex: 2 1 320px;
}
.fi-tips ul {
	margin: 0;
	padding-inline-start: 18px;
	display: flex;
	flex-direction: column;
	gap: 5px;
	font-size: var(--text-sm);
	line-height: 1.5;
	color: var(--ink-gray-7);
}
.fi-related {
	flex: 1 1 200px;
	display: flex;
	flex-direction: column;
	gap: 6px;
	font-size: var(--text-sm);
}
.fi-related h2 {
	margin-bottom: 2px;
}
.fi-neighbours {
	display: flex;
	justify-content: space-between;
	gap: var(--padding-md);
	padding-top: var(--padding-md);
	border-top: 1px solid var(--outline-gray-1);
	font-size: var(--text-sm);
}
.fi-related a,
.fi-neighbours a {
	color: var(--ink-violet-6);
}
/* When there is no room beside the topic list, the open topic comes first and the list follows. */
@container fi-tutorial (max-width: 640px) {
	.fi-topic-view {
		order: -1;
		padding: var(--padding-md);
		border-bottom: 1px solid var(--outline-gray-1);
	}
}
</style>
