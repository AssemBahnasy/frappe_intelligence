// The demo video scenes, one per topic key (content.js). `bench fi-record-tutorial` plays each on
// the real desk and records it; see docs/tutorial/videos.md for the actions. Answers are built
// from the site's own records (tutorial/sample_data.json), so they match what the video shows.
export const DEMOS = {
	ask: async () => ({
		route: "/desk/sales-invoice",
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
};

// The label the assistant shows while reading a list (agent/tools/frappe_data.py).
const reading_list = (doctype) => __("Reading {doctype} list").replace("{doctype}", __(doctype));

async function overdue_invoices() {
	const rows = await frappe.db.get_list("Sales Invoice", {
		filters: {
			docstatus: 1,
			outstanding_amount: [">", 0],
			due_date: ["<", frappe.datetime.get_today()],
		},
		fields: ["name", "customer", "due_date", "outstanding_amount"],
		order_by: "due_date desc",
	});
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

const row = (cells) => `| ${cells.join(" | ")} |`;
const number = (value) => format_number(value, null, 2);
