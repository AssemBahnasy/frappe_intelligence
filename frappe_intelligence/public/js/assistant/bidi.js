// Numbers, dates and codes inside right-to-left answers (board 3c): each left-to-right run goes in a
// <bdi>, so "ACC-SINV-2026-00017" or "86,400.00" keeps its order inside an Arabic sentence. Latin
// words next to each other stay in one run, or the sentence would lay them out right to left.

const RTL = /[֐-ࣿ]/;
const LTR = /[A-Za-z0-9]/;
const LTR_RUN = /[A-Za-z0-9](?:[A-Za-z0-9.,:/_%+\-]|\s(?=[A-Za-z0-9]))*/g;
const SKIP = "code, pre, bdi, kbd";

export function isolate_ltr(root) {
	if (!RTL.test(root.textContent)) return;
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
		acceptNode: (node) =>
			LTR.test(node.nodeValue) && !node.parentElement.closest(SKIP)
				? NodeFilter.FILTER_ACCEPT
				: NodeFilter.FILTER_REJECT,
	});
	const nodes = [];
	while (walker.nextNode()) nodes.push(walker.currentNode);
	nodes.forEach(isolate);
}

function isolate(node) {
	const text = node.nodeValue;
	const parts = [];
	let last = 0;
	for (const match of text.matchAll(LTR_RUN)) {
		parts.push(text.slice(last, match.index));
		const bdi = document.createElement("bdi");
		bdi.textContent = match[0];
		parts.push(bdi);
		last = match.index + match[0].length;
	}
	parts.push(text.slice(last));
	node.replaceWith(...parts.filter((part) => part !== ""));
}
