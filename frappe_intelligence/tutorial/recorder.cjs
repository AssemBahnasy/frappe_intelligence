// Records the tutorial's demo videos. Run by `bench fi-record-tutorial` (recorder.py), which passes
// a signed-in session and reads the timings printed on the last line. See docs/tutorial/videos.md.
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright-core");

const { base_url, sid, lang, topics, videos_dir } = JSON.parse(process.env.FI_DEMO);
const VIEWPORT = { width: 1280, height: 720 };
const SIZE = "1600:900";
const FPS = 30;
const CHAT_API = "frappe_intelligence.api.chat";
const RUN_ID = "fi-demo-run";

(async () => {
	const browser = await chromium.launch({
		executablePath: process.env.FI_CHROME || undefined,
		channel: process.env.FI_CHROME ? undefined : "chrome",
		args: ["--hide-scrollbars"],
	});
	const timings = {};
	try {
		const context = await browser.newContext({
			viewport: VIEWPORT,
			deviceScaleFactor: 1.5,
			locale: lang,
		});
		const { hostname } = new URL(base_url);
		await context.addCookies([{ name: "sid", value: sid, domain: hostname, path: "/" }]);
		const keys = topics.length ? topics : await demo_keys(context);
		for (const key of keys) {
			const out = path.join(videos_dir, lang, `${key}.mp4`);
			timings[key] = await record(context, key, out);
			console.error(`${lang}/${key}: ${timings[key].duration}s`);
		}
	} finally {
		await browser.close();
	}
	console.log(JSON.stringify(timings));
})().catch((e) => {
	console.error(e);
	process.exit(1);
});

async function demo_keys(context) {
	const page = await open_desk(context, "/desk");
	const keys = await page.evaluate(() => Object.keys(frappe_intelligence.tutorial.DEMOS));
	await page.close();
	return keys;
}

async function open_desk(context, route) {
	const page = await context.newPage();
	await page.goto(base_url + route, { waitUntil: "networkidle" });
	await page.evaluate(() => frappe.require("fi_tutorial_demos.bundle.js"));
	return page;
}

async function record(context, key, out) {
	const scene = await scene_of(context, key);
	const page = await context.newPage();
	const chat = await fake_chat(page);
	await page.goto(base_url + scene.route, { waitUntil: "networkidle" });
	await page.evaluate(() => frappe.require("fi_tutorial_demos.bundle.js"));
	await page.evaluate(() => (window.fi_demo_stage = new frappe_intelligence.tutorial.Stage()));
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
		const p = await this.stage("point", target);
		if (!p) throw new Error(`Demo target not on screen: ${target}`);
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
			this.chat.question = action.type;
			await this.page.keyboard.type(action.type, { delay: 65 });
			await this.wait(400);
		} else if (action.reply) {
			await this.reply(action.reply);
		} else if (action.wait) {
			await this.wait(action.wait);
		}
	}

	// The scripted answer arrives as the real one does: steps, then the text as it is written.
	async reply({ steps = [], text = "" }) {
		const event = (e) => this.stage("emit", { run_id: RUN_ID, conversation: "fi-demo", ...e });
		const done_steps = steps.map((label, i) => ({
			call_id: `c${i}`,
			tool: "demo",
			label,
		}));
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
		this.chat.answer = {
			text,
			steps: done_steps.map((s) => ({ ...s, status: "done" })),
		};
		await event({
			type: "done",
			reply: text,
			actions: [],
			steps: [],
			proposals: [],
		});
	}
}

// The assistant's endpoints answered in the browser: nothing reaches a model or the database.
async function fake_chat(page) {
	const chat = { question: "", answer: null };
	const reply = (route, message) =>
		route.fulfill({
			contentType: "application/json",
			body: JSON.stringify({ message }),
		});
	await page.route(`**/api/method/${CHAT_API}.*`, (route) => {
		const method = new URL(route.request().url()).pathname.split(".").pop();
		if (method === "send_message")
			return reply(route, { conversation: "fi-demo", run_id: RUN_ID });
		if (method === "get_conversation") return reply(route, conversation(chat));
		if (method === "list_conversations") return reply(route, []);
		return reply(route, null);
	});
	return chat;
}

function conversation(chat) {
	const turns = chat.answer
		? [
				{
					id: "fi-demo-turn",
					question: chat.question,
					attachments: [],
					steps: chat.answer.steps,
					proposals: [],
					actions: [],
					answer: chat.answer.text,
					report: "",
					pending: false,
				},
		  ]
		: [];
	return {
		name: "fi-demo",
		mode: "Ask",
		turns,
		workflow: null,
		active_run: null,
	};
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
