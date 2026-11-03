// Records the tutorial's demo videos. Run by `bench fi-record-tutorial` (recorder.py), which passes
// a signed-in session and reads each topic's timings, printed as a JSON line once its video is
// written. See docs/tutorial/videos.md.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright-core");

const { base_url, sid, lang, topics, videos_dir } = JSON.parse(process.env.FI_DEMO);
const VIEWPORT = { width: 1280, height: 720 };
const SIZE = "1600:900";
const FPS = 30;
const RUN_ID = "fi-demo-run";
const JOB_ID = "fi-demo-job";

(async () => {
	const browser = await chromium.launch({
		executablePath: process.env.FI_CHROME || undefined,
		channel: process.env.FI_CHROME ? undefined : "chrome",
		// Voice input needs a secure origin and a microphone: the site counts as one, and Chrome's
		// fake device is it.
		args: [
			"--hide-scrollbars",
			`--unsafely-treat-insecure-origin-as-secure=${new URL(base_url).origin}`,
			"--use-fake-ui-for-media-stream",
			"--use-fake-device-for-media-stream",
		],
	});
	try {
		const keys = topics.length ? topics : await demo_keys(await desk_context(browser));
		for (const key of keys) {
			// A fresh browser per topic: what one scene leaves (an open panel, a draft) is not
			// where the next one starts.
			const context = await desk_context(browser);
			const out = path.join(videos_dir, lang, `${key}.mp4`);
			const timing = await record(context, key, out);
			await context.close();
			console.log(JSON.stringify({ [key]: timing }));
			console.error(`${lang}/${key}: ${timing.duration}s`);
		}
	} finally {
		await browser.close();
	}
})().catch((e) => {
	console.error(e);
	process.exit(1);
});

async function desk_context(browser) {
	const context = await browser.newContext({
		viewport: VIEWPORT,
		deviceScaleFactor: 1.5,
		locale: lang,
	});
	const { hostname } = new URL(base_url);
	await context.addCookies([{ name: "sid", value: sid, domain: hostname, path: "/" }]);
	// A developer-mode desk reloads when `bench watch` rebuilds (desk.js setup_build_events),
	// and shows a toast: neither may happen during a recording.
	await context.route("**/build_events.bundle.*.js", (route) =>
		route.fulfill({ contentType: "text/javascript", body: "" })
	);
	return context;
}

async function demo_keys(context) {
	const page = await open_desk(context, "/desk");
	const keys = await page.evaluate(() => Object.keys(frappe_intelligence.tutorial.DEMOS));
	await page.close();
	return keys;
}

async function open_desk(context, route) {
	const page = await context.newPage();
	await page.goto(base_url + route, { waitUntil: "networkidle" });
	await load_demos(page);
	return page;
}

// frappe.require resolves even when the file is missing, as it is while `bench watch` rebuilds:
// reload until the build has written it.
async function load_demos(page) {
	for (let attempt = 0; attempt < 6; attempt++) {
		const loaded = await page.evaluate(async () => {
			await frappe.require("fi_tutorial_demos.bundle.js");
			return Boolean(window.frappe_intelligence?.tutorial?.Stage);
		});
		if (loaded) return;
		await page.waitForTimeout(5000);
		await page.reload({ waitUntil: "networkidle" });
	}
	throw new Error("fi_tutorial_demos.bundle.js did not load; is a build failing?");
}

async function record(context, key, out) {
	const scene = await scene_of(context, key);
	const page = await context.newPage();
	const chat = await fake_chat(page, scene);
	await page.goto(base_url + scene.route, { waitUntil: "networkidle" });
	await load_demos(page);
	await page.evaluate(() => (window.fi_demo_stage = new frappe_intelligence.tutorial.Stage()));
	if (scene.boot) await page.evaluate((values) => window.fi_demo_stage.boot(values), scene.boot);
	await page.waitForTimeout(800);

	const frames_dir = fs.mkdtempSync(path.join(os.tmpdir(), "fi-demo-"));
	const frames = [];
	const cdp = await context.newCDPSession(page);
	cdp.on("Page.screencastFrame", async ({ data, sessionId }) => {
		const file = path.join(frames_dir, `${String(frames.length).padStart(5, "0")}.jpg`);
		fs.writeFileSync(file, Buffer.from(data, "base64"));
		frames.push({ file, t: performance.now() / 1000 });
		await cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
	});
	await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92 });
	const marks = [];
	const actor = new Actor(page, chat);
	await actor.wait(500);
	await actor.stage("show", VIEWPORT.width / 2, VIEWPORT.height * 0.6);
	await actor.wait(600);
	try {
		for (const action of scene.scene) {
			if ("step" in action) marks[action.step] = performance.now() / 1000;
			else await actor.play(action);
		}
	} catch (e) {
		const shot = path.join(frames_dir, "failed.png");
		await page.screenshot({ path: shot });
		e.message = `${lang}/${key}: ${e.message} (screen: ${shot})`;
		throw e;
	}
	const end = performance.now() / 1000;
	await cdp.send("Page.stopScreencast");
	await page.close();

	encode(frames, end, frames_dir, out);
	fs.rmSync(frames_dir, { recursive: true, force: true });
	// The video starts at its first frame.
	const start = frames[0].t;
	return { duration: round(end - start), steps: marks.map((t) => round(t - start)) };
}

// Each scene is built in the page, so its texts come translated into the recording's language.
async function scene_of(context, key) {
	const page = await open_desk(context, "/desk");
	const scene = await page.evaluate((key) => frappe_intelligence.tutorial.DEMOS[key]?.(), key);
	await page.close();
	if (!scene) throw new Error(`No demo scene for the topic "${key}" (demos.js).`);
	return scene;
}

class Actor {
	constructor(page, chat) {
		this.page = page;
		this.chat = chat;
	}

	wait(ms) {
		return this.page.waitForTimeout(ms);
	}

	stage(method, ...args) {
		return this.page.evaluate(([m, a]) => window.fi_demo_stage[m](...a), [method, args]);
	}

	async point(target) {
		let p = await this.stage("point", target);
		if (p?.scrolled) {
			await this.wait(700);
			p = await this.stage("point", target);
		}
		if (p?.outside)
			throw new Error(`Demo target outside the zoomed view: ${JSON.stringify(target)}`);
		if (!p || p.scrolled)
			throw new Error(`Demo target not on screen: ${JSON.stringify(target)}`);
		return p;
	}

	async play(action) {
		if (action.click) {
			const p = await this.point(action.click);
			await this.stage("move", p.x, p.y);
			await this.wait(850);
			await this.stage("press", p.x, p.y);
			await this.page.mouse.click(p.x, p.y);
			await this.wait(450);
		} else if (action.hover) {
			const p = await this.point(action.hover);
			await this.stage("move", p.x, p.y);
			await this.wait(850);
		} else if ("zoom" in action) {
			await this.stage("zoom_to", action.zoom, action.scale || 1.5);
			await this.wait(1100);
		} else if (action.type) {
			await this.page.keyboard.type(action.type, { delay: 65 });
			await this.wait(400);
		} else if (action.reply) {
			await this.reply(action.reply);
		} else if (action.attach) {
			// The file goes to the browser's file chooser from memory; its upload is answered here.
			const chooser = this.page.waitForEvent("filechooser");
			await this.play({ click: "attach" });
			await (
				await chooser
			).setFiles({
				name: action.attach,
				mimeType: "application/pdf",
				buffer: Buffer.from("%PDF-1.4\n"),
			});
			await this.wait(900);
		} else if ("job" in action) {
			await this.stage("emit", { job: JOB_ID, value: action.job }, "fi_job");
			await this.wait(900);
		} else if (action.press) {
			await this.stage("keys", action.label || action.press);
			await this.page.keyboard.press(action.press);
			await this.wait(900);
		} else if (action.drag) {
			await this.drag(action.drag, action.by);
		} else if (action.select) {
			const p = await this.point(action.select);
			await this.stage("move", p.x, p.y);
			await this.wait(850);
			await this.stage("press", p.x, p.y);
			await this.stage("select", action.select, action.value);
			await this.wait(700);
		} else if (action.wait) {
			await this.wait(action.wait);
		}
	}

	// Drags the target `by` pixels along the line (positive: towards its end, in either direction).
	async drag(target, by) {
		const p = await this.point(target);
		await this.stage("move", p.x, p.y);
		await this.wait(850);
		const dx = await this.stage("logical", by);
		await this.page.mouse.move(p.x, p.y);
		await this.page.mouse.down();
		for (let i = 1; i <= 24; i++) {
			const x = p.x + (dx * i) / 24;
			await this.page.mouse.move(x, p.y);
			await this.stage("track", x, p.y);
			await this.wait(25);
		}
		await this.page.mouse.up();
		await this.stage("release");
		await this.wait(500);
	}

	// The scripted answer arrives as the real one does: steps, then the text as it is written. It
	// may bring changes to approve or a document's values to check (`proposals`), browser actions,
	// the workflow's next state; `report: true` is the text after a change was confirmed.
	async reply({ steps = [], text = "", proposals = [], actions = [], workflow, report }) {
		const event = (e) =>
			this.stage("emit", { run_id: RUN_ID, conversation: this.chat.conversation, ...e });
		const done_steps = steps.map((label, i) => ({ call_id: `c${i}`, tool: "demo", label }));
		await this.wait(700);
		for (const step of done_steps) {
			await event({ type: "step", ...step, status: "running" });
			await this.wait(900);
			await event({ type: "step", ...step, status: "done" });
		}
		for (let i = 0; i < text.length; i += 14) {
			await event({ type: "text", text: text.slice(i, i + 14) });
			await this.wait(45);
		}
		const finished = done_steps.map((s) => ({ ...s, status: "done" }));
		if (report) this.chat.turns.at(-1).report = text;
		else
			this.chat.turns.push({
				question: this.chat.question,
				answer: text,
				steps: finished,
				proposals,
			});
		if (workflow) this.chat.workflow = workflow;
		await event({
			type: "done",
			reply: report ? "" : text,
			actions,
			steps: [],
			proposals: report ? [] : proposals,
		});
	}
}

// The assistant's endpoints answered in the browser: nothing reaches a model or the database.
// `chat` is the conversation as the server would keep it, so a reload of it shows what the video did.
async function fake_chat(page, scene) {
	const chat = { conversation: "fi-demo", mode: "Ask", question: "", turns: [], workflow: null };
	const decisions = {};
	const past = scene.conversations || [];
	const reply = (route, message) =>
		route.fulfill({ contentType: "application/json", body: JSON.stringify({ message }) });
	const answers = {
		send_message: (request) => {
			chat.question = arg(request, "message") || "";
			return { conversation: chat.conversation, run_id: RUN_ID };
		},
		get_conversation: (request) => {
			const found = past.find((c) => c.name === arg(request, "name"));
			return found ? stored(found) : live(chat, decisions);
		},
		list_conversations: () =>
			past.map(({ name, title, modified }) => ({ name, title, modified })),
		// A change runs once none is left waiting; then the answer reports on it.
		decide_proposal: (request) => {
			decisions[arg(request, "call_id")] = truthy(arg(request, "approve"))
				? "done"
				: "rejected";
			const waiting = chat.turns
				.flatMap((t) => t.proposals || [])
				.filter((p) => !decisions[p.call_id]);
			return waiting.length ? {} : { run_id: RUN_ID };
		},
		start_workflow: () => {
			Object.assign(chat, { conversation: "fi-demo-workflow", mode: "Workflow" });
			chat.workflow = scene.workflow.state;
			chat.turns = [
				{ question: "", answer: scene.workflow.question, steps: [], proposals: [] },
			];
			return { conversation: chat.conversation };
		},
		exit_workflow: () => ({ ok: true }),
		rate_reply: () => null,
		stop_message: () => null,
		transcribe: () => ({ job: JOB_ID }),
		write_field: () => ({ job: JOB_ID }),
		job_result: () => ({ pending: true }),
	};
	// Only what reaches a model or writes a conversation is answered here; reading the site's own
	// records (the Workflow Builder's list, settings) goes to the server.
	await page.route(`**/api/method/frappe_intelligence.api.**`, (route) => {
		const method = new URL(route.request().url()).pathname.split(".").pop();
		if (!answers[method]) return route.continue();
		return reply(route, answers[method](route.request()));
	});
	await page.route("**/api/method/upload_file", (route) => {
		const name = (route.request().postData() || "").match(/filename="([^"]+)"/)?.[1] || "file";
		return reply(route, { file_url: `/private/files/${name}`, file_name: name });
	});
	return chat;
}

// An argument of a frappe.call, sent as JSON or as a form.
function arg(request, key) {
	const body = request.postData() || "";
	try {
		return JSON.parse(body)[key];
	} catch {
		return new URLSearchParams(body).get(key);
	}
}

const truthy = (value) => [true, 1, "1", "true"].includes(value);

const turn = (id, t, created, decisions = {}) => ({
	id,
	question: t.question,
	attachments: [],
	steps: t.steps || [],
	proposals: (t.proposals || []).map((p) => ({
		...p,
		status: decisions[p.call_id] || "pending",
	})),
	actions: [],
	answer: t.answer,
	report: t.report || "",
	pending: false,
	answer_id: `${id}-answer`,
	feedback: null,
	created,
});

function live(chat, decisions) {
	const turns = chat.turns.map((t, i) => turn(`${chat.conversation}-${i}`, t, now(), decisions));
	return {
		name: chat.conversation,
		mode: chat.mode,
		turns,
		workflow: chat.workflow,
		active_run: null,
	};
}

// A past conversation of the scene: { name, title, modified, turns: [{ question, answer }] }.
function stored(c) {
	const turns = c.turns.map((t, i) => turn(`${c.name}-${i}`, t, c.modified));
	return { name: c.name, mode: "Ask", turns, workflow: null, active_run: null };
}

// Frappe's datetime format, in local time.
function now() {
	const d = new Date();
	const pad = (n) => String(n).padStart(2, "0");
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
		d.getHours()
	)}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// Frames arrive only when the screen changes: each video frame shows the latest one, on an exact
// FPS timeline so the video's length matches the step timings.
function encode(frames, end, dir, out) {
	const sequence = path.join(dir, "sequence");
	fs.mkdirSync(sequence);
	const start = frames[0].t;
	for (let n = 0, i = 0; n < Math.round((end - start) * FPS); n++) {
		while (i + 1 < frames.length && frames[i + 1].t <= start + n / FPS) i++;
		fs.linkSync(frames[i].file, path.join(sequence, `${String(n).padStart(6, "0")}.jpg`));
	}
	fs.mkdirSync(path.dirname(out), { recursive: true });
	// prettier-ignore
	execFileSync("ffmpeg", [
		"-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(sequence, "%06d.jpg"),
		"-vf", `scale=${SIZE}:flags=lanczos,format=yuv420p`,
		"-c:v", "libx264", "-preset", "slow", "-crf", "30", "-movflags", "+faststart", "-an", out,
	]);
}

const round = (seconds) => Math.round(seconds * 10) / 10;
