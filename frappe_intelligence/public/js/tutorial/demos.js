// The demo video scenes, one per topic key (content.js). `bench fi-record-tutorial` plays each on
// the real desk and records it; see docs/tutorial/videos.md for the actions. Answers are built
// from the site's own records (tutorial/sample_data.json), so they match what the video shows.
const LIST = "/desk/sales-invoice";
const HOME = "/desk/intelligence";

export const DEMOS = {
	"open-assistant": async () => ({
		route: LIST,
		scene: [
			{ step: 0 },
			{ zoom: "launcher", scale: 1.8 },
			{ hover: "launcher" },
			{ wait: 1200 },
			{ zoom: null },
			{ step: 1 },
			{ click: "launcher" },
			{ wait: 1200 },
			{ press: "Escape", label: "Esc" },
			{ press: "Control+.", label: "Ctrl + ." },
			{ wait: 900 },
			{ step: 2 },
			{ drag: "resizer", by: -180 },
			{ wait: 1500 },
		],
	}),

	ask: async () => ({
		route: LIST,
		scene: [
			{ step: 0 },
			{ click: "launcher" },
			{ zoom: "composer", scale: 1.5 },
			{ click: "composer" },
			{ type: __("Which invoices are overdue?") },
			{ step: 1 },
			{ click: "send" },
			{ zoom: "panel", scale: 1.25 },
			{ reply: { steps: [reading_list("Sales Invoice")], text: await overdue_invoices() } },
			{ wait: 1500 },
			{ step: 2 },
			{ zoom: "context", scale: 1.6 },
			{ hover: "context" },
			{ wait: 1800 },
			{ zoom: null },
			{ wait: 1200 },
		],
	}),

	"read-document": async () => {
		const due_date = day(30);
		const { file, values, review } = invoice_review();
		return {
			route: "/desk/purchase-invoice",
			scene: [
				{ step: 0 },
				{ click: "launcher" },
				{ wait: 600 },
				{ step: 1 },
				{ zoom: "attach", scale: 1.5 },
				{ attach: file },
				{ click: "composer" },
				{ type: __("Read this invoice") },
				{ click: "send" },
				{ zoom: "panel", scale: 1.25 },
				{
					reply: {
						steps: [reading_file(file)],
						text: __("Here is what I read. Check the values, then use them."),
						proposals: [review],
					},
				},
				{ wait: 800 },
				{ step: 2 },
				{ click: { input: __("Due Date") } },
				{ type: frappe.datetime.str_to_user(due_date) },
				{ wait: 700 },
				{ step: 3 },
				{ click: { button: __("Use these values") } },
				{
					reply: {
						report: true,
						text: __("A new Purchase Invoice is open with these values."),
						actions: [
							{
								type: "new_doc",
								doctype: "Purchase Invoice",
								defaults: { ...values, due_date },
							},
						],
					},
				},
				{ zoom: null },
				{ wait: 2000 },
				{ hover: { field: "bill_no" } },
				{ wait: 1800 },
			],
		};
	},

	voice: async () => ({
		route: LIST,
		boot: { voice: { language: "" } },
		scene: [
			{ click: "launcher" },
			{ wait: 600 },
			{ step: 0 },
			{ zoom: "microphone", scale: 1.6 },
			{ click: "microphone" },
			{ wait: 2500 },
			{ step: 1 },
			{ click: "microphone" },
			{ wait: 700 },
			{ job: __("Which customers have overdue invoices?") },
			{ wait: 900 },
			{ step: 2 },
			{ click: "send" },
			{ zoom: "panel", scale: 1.25 },
			{ reply: { steps: [reading_list("Sales Invoice")], text: await overdue_customers() } },
			{ wait: 2000 },
			{ zoom: null },
			{ wait: 800 },
		],
	}),

	"write-with-ai": async () => {
		const [oldest] = (await overdue_rows()).slice(-1);
		return {
			route: "/desk/todo/new",
			scene: [
				{ step: 0 },
				{ zoom: { label: __("Write with AI") }, scale: 1.6 },
				{ hover: { label: __("Write with AI") } },
				{ wait: 900 },
				{ step: 1 },
				{ click: { label: __("Write with AI") } },
				{ wait: 600 },
				{ type: __("A polite reminder that invoice {0} is overdue", [oldest.name]) },
				{ press: "Control+Enter", label: "Ctrl + Enter" },
				{ wait: 600 },
				{
					job: __(
						"Dear {0},\n\nThis is a friendly reminder that invoice {1} was due on {2} and is still open. We would be grateful if you could arrange the payment at your earliest convenience.\n\nThank you.",
						[
							oldest.customer,
							oldest.name,
							frappe.datetime.str_to_user(oldest.due_date),
						]
					),
				},
				{ step: 2 },
				{ wait: 1500 },
				{ zoom: null },
				{ hover: { button: __("Undo") } },
				{ wait: 2000 },
			],
		};
	},

	workflows: async () => {
		const title = __("Plan a follow-up");
		const task = __("Call Gulf Paper Co. about their overdue invoice");
		const date = day(2);
		const answer = (label, value) => ({ label, value });
		const state = (...args) => follow_up_state(title, ...args);
		const asked = [answer(__("Description"), task)];
		const prioritised = [...asked, answer(__("Priority"), __("High"))];
		return {
			route: LIST,
			boot: { workflows: [{ name: "fi-demo-follow-up", title, steps: 3 }] },
			workflow: follow_up_start(title),
			scene: [
				{ click: "launcher" },
				{ wait: 600 },
				{ step: 0 },
				{ click: { button: title } },
				{ wait: 1500 },
				{ step: 1 },
				{ click: "composer" },
				{ type: task },
				{ click: "send" },
				{ zoom: "panel", scale: 1.25 },
				{
					reply: {
						text: __("Got it. How urgent is it?"),
						workflow: state(
							2,
							__("Priority"),
							asked,
							[__("Priority")],
							["Low", "Medium", "High"]
						),
					},
				},
				{ wait: 700 },
				{ click: { button: "High" } },
				{
					reply: {
						text: __("And when should it be done?"),
						workflow: state(3, __("Due Date"), prioritised, [__("Due Date")]),
					},
				},
				{ zoom: null },
				{ click: "composer" },
				{ type: frappe.datetime.str_to_user(date) },
				{ click: "send" },
				{
					reply: {
						text: __("All set. Here is your ToDo to check and save."),
						workflow: state(
							null,
							null,
							[...prioritised, answer(__("Due Date"), date)],
							[]
						),
						actions: [
							{
								type: "new_doc",
								doctype: "ToDo",
								defaults: { description: task, priority: "High", date },
							},
						],
					},
				},
				{ step: 2 },
				{ zoom: null },
				{ wait: 2200 },
				{ hover: { field: "priority" } },
				{ wait: 1800 },
			],
		};
	},

	"agent-mode": async () => {
		const rows = await overdue_rows();
		const proposals = rows.map((r, i) => ({
			call_id: `p${i}`,
			preview: {
				action: "create",
				doctype: "ToDo",
				title: __("New ToDo"),
				fields: [
					{
						label: __("Description"),
						value: __("Follow up invoice {0} with {1}", [r.name, r.customer]),
					},
					{ label: __("Priority"), value: __("High") },
				],
			},
		}));
		return {
			route: LIST,
			boot: { agent_mode: true },
			scene: [
				{ click: "launcher" },
				{ wait: 600 },
				{ step: 0 },
				{ click: "mode" },
				{ wait: 700 },
				{ click: { menu: __("Agent") } },
				{ wait: 600 },
				{ step: 1 },
				{ click: "composer" },
				{ type: __("Create a ToDo for every overdue invoice") },
				{ click: "send" },
				{ zoom: "panel", scale: 1.25 },
				{
					reply: {
						steps: [reading_list("Sales Invoice")],
						text: __("{0} invoices are overdue. Here is a ToDo for each:", [
							rows.length,
						]),
						proposals,
					},
				},
				{ wait: 800 },
				{ step: 2 },
				{ click: { button: __("Confirm") } },
				{ click: { button: __("Confirm") } },
				{ click: { button: __("Reject") } },
				{
					reply: {
						report: true,
						text: __("Created {0} ToDos. The one you rejected was not created.", [
							rows.length - 1,
						]),
					},
				},
				{ wait: 2000 },
				{ zoom: null },
				{ wait: 800 },
			],
		};
	},

	// Written in the other language on purpose: the reply follows the language of the question.
	language: async () => {
		const { question, answer } = await other_language_exchange();
		return {
			route: LIST,
			scene: [
				{ step: 0 },
				{ click: "launcher" },
				{ zoom: "composer", scale: 1.5 },
				{ click: "composer" },
				{ type: question },
				{ step: 1 },
				{ click: "send" },
				{ zoom: "panel", scale: 1.25 },
				{ reply: { steps: [reading_list("Sales Invoice")], text: answer } },
				{ wait: 2500 },
				{ zoom: null },
				{ wait: 1000 },
			],
		};
	},

	conversations: async () => {
		const overdue = __("Overdue invoices");
		return {
			route: LIST,
			conversations: [
				{
					name: "fi-demo-overdue",
					title: overdue,
					modified: ago(2, "hours"),
					turns: [
						{
							question: __("Which invoices are overdue?"),
							answer: await overdue_invoices(),
						},
					],
				},
				{
					name: "fi-demo-customers",
					title: __("Top customers this quarter"),
					modified: ago(1, "days"),
					turns: [],
				},
				{
					name: "fi-demo-orders",
					title: __("Open sales orders"),
					modified: ago(3, "days"),
					turns: [],
				},
			],
			scene: [
				{ click: "launcher" },
				{ wait: 600 },
				{ step: 0 },
				{ click: "history" },
				{ wait: 900 },
				{ click: { menu: overdue } },
				{ wait: 1500 },
				{ step: 1 },
				{ zoom: { label: __("Good answer") }, scale: 1.6 },
				{ click: { label: __("Good answer") } },
				{ wait: 1200 },
				{ zoom: null },
				{ step: 2 },
				{ click: "new_chat" },
				{ wait: 1800 },
			],
		};
	},

	provider: async () => ({
		route: HOME,
		scene: [
			{ step: 0 },
			{ click: "dock_setup" },
			{ wait: 1800 },
			{ step: 1 },
			{ zoom: { field: "ai_provider" }, scale: 1.5 },
			{ select: { field: "ai_provider" }, value: "Claude" },
			{ wait: 900 },
			{ zoom: null },
			{ hover: { field: "claude_api_key" } },
			{ zoom: { field: "claude_api_key" }, scale: 1.4 },
			{ wait: 900 },
			{ hover: { field: "claude_model" } },
			{ wait: 900 },
			{ zoom: null },
			{ step: 2 },
			{ click: "launcher" },
			{ click: "composer" },
			{ type: __("Hello, are you there?") },
			{ click: "send" },
			{ reply: { text: __("Yes. Ask me about your records, reports or any screen.") } },
			{ wait: 2000 },
		],
	}),

	access: async () => ({
		route: HOME,
		scene: [
			{ click: "dock_setup" },
			{ wait: 1800 },
			{ click: { tab: "widget_tab" } },
			{ wait: 800 },
			{ step: 0 },
			{ hover: { field: "widget_roles" } },
			{ zoom: { field: "widget_roles" }, scale: 1.5 },
			{ wait: 1200 },
			{ zoom: null },
			{ step: 1 },
			{ click: { check: "allow_agent_mode" } },
			{ wait: 700 },
			{ hover: { field: "agent_excluded_doctypes" } },
			{ zoom: { field: "agent_excluded_doctypes" }, scale: 1.5 },
			{ wait: 1200 },
			{ zoom: null },
			{ step: 2 },
			{ hover: { field: "allow_field_writer" } },
			{ zoom: { field: "allow_field_writer" }, scale: 1.5 },
			{ wait: 1500 },
			{ zoom: null },
			{ wait: 800 },
		],
	}),

	// The setup topics show the fictional records of tutorial/sample_data.json by their names,
	// which are data, not translated.
	"knowledge-packs": async () => ({
		route: HOME,
		scene: [
			{ click: "dock_setup" },
			{ wait: 1500 },
			{ click: { sidebar: "Knowledge Packs" } },
			{ wait: 1500 },
			{ step: 0 },
			{ click: { row: "Company policies" } },
			{ wait: 1500 },
			{ hover: { field: "knowledge_entries" } },
			{ zoom: { field: "knowledge_entries" }, scale: 1.3 },
			{ wait: 1800 },
			{ zoom: null },
			{ step: 1 },
			{ click: "dock_workflows" },
			{ wait: 1500 },
			{ click: { css: ".fi-builder-wf-item", text: "Plan a follow-up" } },
			{ wait: 1800 },
			{ hover: { css: ".fi-kp-tag", text: "Company policies" } },
			{ zoom: { css: ".fi-kp" }, scale: 1.4 },
			{ hover: { css: ".fi-kp-add-btn" } },
			{ wait: 1800 },
			{ zoom: null },
			{ wait: 600 },
		],
	}),

	"document-templates": async () => {
		const { file, review } = invoice_review();
		return {
			route: HOME,
			scene: [
				{ click: "dock_documents" },
				{ wait: 1500 },
				{ step: 0 },
				{ click: { row: "supplier_invoice" } },
				{ wait: 1500 },
				{ zoom: { field: "detection_keywords" }, scale: 1.4 },
				{ hover: { field: "detection_keywords" } },
				{ wait: 1500 },
				{ zoom: null },
				{ step: 1 },
				{ hover: { field: "extraction_rules" } },
				{ zoom: { field: "extraction_rules" }, scale: 1.3 },
				{ wait: 2000 },
				{ zoom: null },
				{ step: 2 },
				{ click: "launcher" },
				{ attach: file },
				{ click: "send" },
				{ zoom: "panel", scale: 1.25 },
				{
					reply: {
						steps: [reading_file(file)],
						text: __("Here is what I read. Check the values, then use them."),
						proposals: [review],
					},
				},
				{ wait: 2500 },
				{ zoom: null },
				{ wait: 600 },
			],
		};
	},

	"document-requirements": async () => ({
		route: HOME,
		scene: [
			{ click: "dock_documents" },
			{ wait: 1500 },
			{ click: { sidebar: "Document Requirements" } },
			{ wait: 1500 },
			{ step: 0 },
			{ click: { row: "supplier_invoice" } },
			{ wait: 1500 },
			{ zoom: { field: "target_doctype" }, scale: 1.4 },
			{ hover: { field: "target_doctype" } },
			{ wait: 900 },
			{ hover: { field: "document_type_key" } },
			{ wait: 1200 },
			{ zoom: null },
			{ step: 1 },
			{ click: { sidebar: "Document Requirements" } },
			{ wait: 1500 },
			{ zoom: { css: ".list-row", text: "commercial_registration" }, scale: 1.3 },
			{ hover: { css: ".list-row", text: "commercial_registration" } },
			{ wait: 2000 },
			{ zoom: null },
			{ wait: 600 },
		],
	}),

	"build-workflow": async () => ({
		route: HOME,
		workflow: follow_up_start("Plan a follow-up"),
		scene: [
			{ step: 0 },
			{ click: "dock_workflows" },
			{ wait: 1500 },
			{ click: { css: ".fi-builder-wf-item", text: "Plan a follow-up" } },
			{ wait: 1800 },
			{ step: 1 },
			{ zoom: { css: ".fi-seq-list" }, scale: 1.4 },
			{ click: { css: ".fi-seq-card", text: "priority" } },
			{ wait: 1500 },
			{ zoom: null },
			{ wait: 1200 },
			{ step: 2 },
			{ hover: { css: ".fi-scope" } },
			{ zoom: { css: ".fi-scope" }, scale: 1.3 },
			{ wait: 1800 },
			{ zoom: null },
			{ step: 3 },
			{ hover: { css: ".fi-builder-page button", text: __("Save") } },
			{ wait: 900 },
			{ click: "launcher" },
			{ wait: 600 },
			{ click: { button: "Plan a follow-up" } },
			{ wait: 2000 },
		],
	}),

	"post-processors": async () => ({
		route: HOME,
		scene: [
			{ click: "dock_setup" },
			{ wait: 1500 },
			{ click: { sidebar: "Post Processors" } },
			{ wait: 1500 },
			{ step: 0 },
			{ click: { row: "supplier_invoice" } },
			{ wait: 1500 },
			{ zoom: { field: "callback_method" }, scale: 1.4 },
			{ hover: { field: "callback_method" } },
			{ wait: 1500 },
			{ zoom: null },
			{ step: 1 },
			{ zoom: { field: "document_type_key" }, scale: 1.4 },
			{ hover: { field: "document_type_key" } },
			{ wait: 1000 },
			{ hover: { field: "is_active" } },
			{ wait: 1200 },
			{ zoom: null },
			{ wait: 600 },
		],
	}),

	"processing-log": async () => ({
		route: HOME,
		scene: [
			{ step: 0 },
			{ click: "dock_documents" },
			{ wait: 1500 },
			{ click: { sidebar: "Processing Log" } },
			{ wait: 1500 },
			{ zoom: { css: ".frappe-list .result" }, scale: 1.25 },
			{ hover: { css: ".list-row", text: "supplier-invoice-2304" } },
			{ wait: 1200 },
			{ click: { row: "supplier-invoice-2304" } },
			{ wait: 1500 },
			{ zoom: null },
			{ hover: { field: "confidence_score" } },
			{ wait: 900 },
			{ hover: { field: "extracted_data" } },
			{ wait: 1200 },
			{ step: 1 },
			{ click: { sidebar: "Training Pairs" } },
			{ wait: 1500 },
			{ click: { row: "supplier_invoice" } },
			{ wait: 1500 },
			{ hover: { field: "original_extraction" } },
			{ wait: 900 },
			{ hover: { field: "corrected_extraction" } },
			{ wait: 1500 },
		],
	}),

	analytics: async () => ({
		route: HOME,
		scene: [
			{ step: 0 },
			{ click: { sidebar: "Session Analytics" } },
			{ wait: 2500 },
			{ zoom: { css: ".dt-scrollable" }, scale: 1.4 },
			{ hover: { css: ".dt-row", text: "follow_up" } },
			{ wait: 1500 },
			{ hover: { css: ".dt-row", text: "supplier_registration" } },
			{ wait: 1800 },
			{ zoom: null },
			{ wait: 600 },
		],
	}),
};

// The label the assistant shows while reading a list (agent/tools/frappe_data.py).
// … and while reading a file (agent/tools/documents.py).
const reading_file = (name) => __("Reading {file_name}").replace("{file_name}", name);
const reading_list = (doctype) => __("Reading {doctype} list").replace("{doctype}", __(doctype));

async function overdue_rows() {
	return frappe.db.get_list("Sales Invoice", {
		filters: {
			docstatus: 1,
			outstanding_amount: [">", 0],
			due_date: ["<", frappe.datetime.get_today()],
		},
		fields: ["name", "customer", "due_date", "outstanding_amount"],
		order_by: "due_date desc",
	});
}

async function overdue_invoices() {
	const rows = await overdue_rows();
	const total = rows.reduce((sum, r) => sum + r.outstanding_amount, 0);
	const table = [
		row([__("Invoice"), __("Customer"), __("Due Date"), __("Outstanding Amount")]),
		row(["---", "---", "---", "---"]),
		...rows.map((r) =>
			row([
				r.name,
				r.customer,
				frappe.datetime.str_to_user(r.due_date),
				number(r.outstanding_amount),
			])
		),
	];
	return [
		__("{0} invoices are overdue, {1} in all:", [rows.length, number(total)]),
		table.join("\n"),
		__("The oldest is from {0}.", [rows.at(-1)?.customer]),
	].join("\n\n");
}

async function overdue_customers() {
	const names = [...new Set((await overdue_rows()).map((r) => r.customer))];
	return __("{0} customers have overdue invoices: {1}.", [names.length, names.join(", ")]);
}

// A question and its answer in the language the desk is not in; not translated, by design.
async function other_language_exchange() {
	const rows = await overdue_rows();
	const total = number(rows.reduce((sum, r) => sum + r.outstanding_amount, 0));
	if (frappe.boot.lang === "ar") {
		return {
			question: "How many invoices are overdue?",
			answer: `${rows.length} invoices are overdue, ${total} in all.`,
		};
	}
	return {
		question: "كم فاتورة متأخرة لدينا؟",
		answer: `لدينا ${rows.length} فواتير متأخرة، مجموعها ${total}.`,
	};
}

// A supplier invoice read in the panel: the values found, and the card that asks to check them.
function invoice_review() {
	const file = "supplier-invoice-2291.pdf";
	const values = { supplier: "Najd Office Supplies", bill_no: "INV-2291", bill_date: day(-3) };
	const review = {
		call_id: "r0",
		preview: {
			kind: "review",
			document: file,
			title: __("Purchase Invoice"),
			needs_review: true,
			fields: [
				{ key: "supplier", label: __("Supplier"), value: values.supplier },
				{ key: "bill_no", label: __("Supplier Invoice No"), value: values.bill_no },
				{
					key: "bill_date",
					label: __("Supplier Invoice Date"),
					value: frappe.datetime.str_to_user(values.bill_date),
				},
				{ key: "due_date", label: __("Due Date"), value: "" },
			],
		},
	};
	return { file, values, review };
}

// The follow-up workflow's progress (workflows/desk.py progress), and what starting it opens.
function follow_up_state(title, step, label, answers, missing, choices = []) {
	return {
		title,
		status: step ? "Active" : "Completed",
		step,
		steps: 3,
		step_label: label,
		answers,
		missing,
		choices,
	};
}

function follow_up_start(title) {
	return {
		state: follow_up_state(title, 1, __("Task"), [], [__("Description")]),
		question: __("What needs to be done?"),
	};
}

const row = (cells) => `| ${cells.join(" | ")} |`;
const number = (value) => format_number(value, null, 2);
const ago = (amount, unit) => moment().subtract(amount, unit).format("YYYY-MM-DD HH:mm:ss");
const day = (days) => moment().add(days, "days").format("YYYY-MM-DD");
