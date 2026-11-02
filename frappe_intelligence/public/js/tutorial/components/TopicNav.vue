<template>
	<nav v-if="store.folded" class="fi-rail" :aria-label="__('Chapters')">
		<button
			class="fi-fold"
			:title="__('Show the topic list')"
			:aria-label="__('Show the topic list')"
			aria-expanded="false"
			@click="store.toggle_fold()"
		>
			<Icon name="panel-left-open" />
		</button>
		<template v-for="chapter in store.all_chapters" :key="chapter.key">
			<span
				v-if="chapter.key === first_setup(store.all_chapters)"
				class="fi-rail-gap"
			></span>
			<a
				:href="url(store.chapter_start(chapter))"
				:class="['fi-rail-chapter', 'is-' + store.chapter_state(chapter)]"
				:title="rail_title(chapter)"
				:aria-label="rail_title(chapter)"
				@click.prevent="go(store.chapter_start(chapter))"
				>{{ chapter.n }}</a
			>
		</template>
	</nav>

	<nav v-else class="fi-topics" :aria-label="__('Topics')">
		<div class="fi-topics-head">
			<div class="fi-progress">
				<span>{{
					__("{0} of {1} done", [store.progress.done, store.progress.total])
				}}</span>
				<span class="fi-progress-bar" aria-hidden="true">
					<span :style="{ width: percent + '%' }"></span>
				</span>
			</div>
			<button
				class="fi-fold"
				:title="__('Fold the topic list')"
				:aria-label="__('Fold the topic list')"
				aria-expanded="true"
				@click="store.toggle_fold()"
			>
				<Icon name="panel-left-close" />
			</button>
		</div>
		<label class="fi-search">
			<Icon name="search" />
			<span class="sr-only">{{ __("Search topics") }}</span>
			<input v-model="store.search" type="search" :placeholder="__('Search topics')" />
		</label>
		<div v-for="chapter in store.chapters" :key="chapter.key" class="fi-chapter">
			<div v-if="chapter.key === first_setup(store.chapters)" class="fi-group">
				{{ __("Setting it up") }}
			</div>
			<button
				:class="['fi-chapter-head', 'is-' + store.chapter_state(chapter)]"
				:aria-expanded="store.is_expanded(chapter)"
				@click="store.toggle_chapter(chapter)"
			>
				<Icon name="chevron-right" class="fi-chevron" />
				<span class="fi-chapter-title">{{ chapter.n }} · {{ chapter.title }}</span>
				<span v-if="store.is_expanded(chapter)" class="fi-chapter-meta">
					{{ __("{0} of {1}", [chapter.done, chapter.total]) }}
				</span>
				<span
					v-else
					class="fi-dots"
					role="img"
					:aria-label="__('{0} of {1} done', [chapter.done, chapter.total])"
				>
					<span
						v-for="topic in chapter.topics"
						:key="topic.key"
						:class="['fi-dot', 'is-' + store.state_of(topic)]"
					></span>
				</span>
			</button>
			<ol v-if="store.is_expanded(chapter)" class="fi-line">
				<li
					v-for="topic in chapter.topics"
					:key="topic.key"
					:class="['fi-topic', 'is-' + store.state_of(topic)]"
				>
					<span class="fi-node" aria-hidden="true"></span>
					<a
						:href="url(topic)"
						:aria-current="store.state_of(topic) === 'open' ? 'page' : null"
						@click.prevent="go(topic)"
					>
						<span>{{ topic.title }}</span>
						<span v-if="store.state_of(topic) === 'next'" class="fi-tag is-next">
							{{ __("Next up") }}
						</span>
						<span
							v-else-if="topic.status"
							:class="['fi-tag', 'is-' + topic.status.tone]"
						>
							{{ topic.status.tag }}
						</span>
					</a>
				</li>
			</ol>
		</div>
		<p v-if="!store.chapters.length" class="fi-none">
			{{ __("No topic matches your search.") }}
		</p>
	</nav>
</template>

<script setup>
import { computed } from "vue";
import Icon from "../../assistant/components/Icon.vue";
import { useTutorial } from "../store";

const PAGE = "intelligence-tutorial";
const store = useTutorial();

const percent = computed(() =>
	store.progress.total ? Math.round((store.progress.done / store.progress.total) * 100) : 0
);
// "Setting it up" goes above the first setup chapter in the list.
const first_setup = (chapters) => chapters.find((c) => c.group === "setup")?.key;
const url = (topic) => frappe.router.make_url([PAGE, topic.key]);
const go = (topic) => frappe.set_route(PAGE, topic.key);
const rail_title = (chapter) =>
	`${chapter.n} · ${chapter.title} · ${__("{0} of {1} done", [chapter.done, chapter.total])}`;
</script>

<style scoped>
.fi-topics {
	flex: 1 1 260px;
	max-width: 310px;
	padding: var(--padding-lg) var(--padding-md);
	display: flex;
	flex-direction: column;
	gap: var(--padding-sm);
	border-inline-end: 1px solid var(--outline-gray-1);
	align-self: stretch;
}
.fi-topics-head {
	display: flex;
	align-items: center;
	gap: var(--padding-sm);
}
.fi-progress {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 6px;
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
.fi-progress-bar {
	display: block;
	height: 6px;
	border-radius: var(--radius-full);
	background: var(--surface-gray-2);
	overflow: hidden;
}
.fi-progress-bar span {
	display: block;
	height: 100%;
	background: var(--ink-violet-6);
}
.fi-fold {
	flex: none;
	width: 32px;
	height: 32px;
	display: grid;
	place-items: center;
	border: 0;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-7);
}
.fi-fold:hover {
	background: var(--surface-gray-3);
}
.fi-search {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 0 0 var(--padding-xs);
	padding: 0 10px;
	height: 32px;
	border-radius: var(--radius);
	background: var(--surface-gray-2);
	color: var(--ink-gray-6);
}
.fi-search input {
	flex: 1;
	min-width: 0;
	border: 0;
	background: transparent;
	font-size: var(--text-sm);
	color: var(--ink-gray-9);
	outline: none;
}
.fi-chapter {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.fi-group {
	margin-top: var(--padding-xs);
	padding: var(--padding-sm) 0 var(--padding-xs);
	border-top: 1px solid var(--outline-gray-1);
	font-size: var(--text-xs);
	font-weight: 600;
	color: var(--ink-gray-6);
}
.fi-chapter-head {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 7px 6px;
	border: 0;
	border-radius: var(--radius);
	background: transparent;
	font-size: var(--text-sm);
	color: var(--ink-gray-9);
	text-align: start;
}
.fi-chapter-head:hover {
	background: var(--surface-gray-2);
}
/* A closed chapter holding the open topic stays easy to find. */
.fi-chapter-head.is-open[aria-expanded="false"] {
	background: var(--surface-violet-2);
}
.fi-chevron {
	color: var(--ink-gray-6);
	transition: transform 0.15s ease;
}
.fi-chapter-head[aria-expanded="true"] .fi-chevron {
	transform: rotate(90deg);
}
.fi-chevron:dir(rtl) {
	transform: scaleX(-1);
}
.fi-chapter-title {
	flex: 1;
	font-weight: 600;
}
.fi-chapter-meta {
	font-size: var(--text-xs);
	color: var(--ink-gray-6);
}
/* Dots for a closed chapter: done green, open filled violet, next a violet ring, else grey. */
.fi-dots {
	display: flex;
	gap: 3px;
}
.fi-dot {
	width: 7px;
	height: 7px;
	border-radius: var(--radius-full);
	background: var(--outline-gray-3);
}
.fi-dot.is-done {
	background: var(--ink-green-6);
}
.fi-dot.is-open {
	background: var(--ink-violet-6);
}
.fi-dot.is-next {
	background: var(--surface-base);
	box-shadow: inset 0 0 0 1.5px var(--ink-violet-6);
}
.fi-line {
	list-style: none;
	margin: 2px 0 var(--padding-xs);
	margin-inline-start: 12px;
	padding: 0;
	padding-inline-start: 14px;
	border-inline-start: 2px solid var(--outline-gray-2);
	display: flex;
	flex-direction: column;
	gap: 1px;
}
.fi-topic {
	position: relative;
}
.fi-topic a {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding: 6px 8px;
	border-radius: var(--radius);
	font-size: var(--text-sm);
	color: var(--ink-gray-7);
	text-decoration: none;
}
.fi-topic a:hover {
	background: var(--surface-gray-2);
}
.fi-topic.is-open a {
	background: var(--surface-violet-2);
	color: var(--ink-violet-6);
	font-weight: 500;
}
.fi-node {
	position: absolute;
	inset-inline-start: -21px;
	top: 10px;
	width: 12px;
	height: 12px;
	border-radius: var(--radius-full);
	box-sizing: border-box;
	background: var(--surface-base);
	border: 2px solid var(--outline-gray-3);
}
.is-done .fi-node {
	background: var(--ink-green-6);
	border-color: var(--ink-green-6);
}
.is-next .fi-node {
	border-color: var(--ink-violet-6);
}
.is-open .fi-node {
	background: var(--ink-violet-6);
	border-color: var(--ink-violet-6);
	box-shadow: 0 0 0 2px var(--surface-base), 0 0 0 4px var(--ink-violet-6);
}
.fi-tag {
	flex: none;
	padding: 1px 6px;
	border-radius: var(--radius-full);
	font-size: 10px;
	font-weight: 500;
}
.fi-tag.is-next {
	background: var(--surface-violet-2);
	color: var(--ink-violet-6);
}
.fi-tag.is-off {
	background: var(--surface-amber-2);
	color: var(--ink-amber-7);
}
.fi-none {
	margin: 0;
	font-size: var(--text-sm);
	color: var(--ink-gray-6);
}
/* Folded: a rail of chapter numbers in the same colours as the dots. */
.fi-rail {
	flex: none;
	width: 60px;
	padding: var(--padding-md) 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	border-inline-end: 1px solid var(--outline-gray-1);
	align-self: stretch;
}
.fi-rail-gap {
	width: 20px;
	height: 1px;
	background: var(--outline-gray-2);
}
.fi-rail-chapter {
	width: 32px;
	height: 32px;
	display: grid;
	place-items: center;
	border-radius: var(--radius-full);
	font-size: var(--text-xs);
	font-weight: 600;
	color: var(--ink-gray-6);
	box-shadow: inset 0 0 0 1.5px var(--outline-gray-3);
	text-decoration: none;
}
.fi-rail-chapter:hover {
	background: var(--surface-gray-2);
	text-decoration: none;
}
.fi-rail-chapter.is-done {
	background: var(--surface-green-2);
	color: var(--ink-green-7);
	box-shadow: none;
}
.fi-rail-chapter.is-next {
	color: var(--ink-violet-6);
	box-shadow: inset 0 0 0 2px var(--ink-violet-6);
}
.fi-rail-chapter.is-open {
	background: var(--ink-violet-6);
	color: var(--surface-base);
	box-shadow: 0 0 0 3px var(--surface-base), 0 0 0 5px var(--ink-violet-6);
}
@container fi-tutorial (max-width: 640px) {
	.fi-topics {
		max-width: none;
		border-inline-end: 0;
	}
}
</style>
