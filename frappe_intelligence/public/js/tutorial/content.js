// The tutorial's chapters and topics. A new feature adds its topic here (docs/tutorial/content.md).
//
// Topic fields:
//   key        the route segment: /desk/intelligence-tutorial/<key>
//   steps      [{ title, text, picture }]; picture names a drawing in components/StepPicture.vue
//   tips       "Good to know" lines
//   related    other topics' keys
//   tour       Show me: [{ target, step }] reuses step <step>'s text, or [{ target, title, text }];
//              targets are the elements named in tour.js
//   try        what Try it now opens: { panel: true }, { route: [...] } or { new_doc: "<DocType>" }
//   doctype    Setting it up: shown only to people who can read it
//   report     the same for a report: shown only to people who may open it
//   status     (assistant) => null | "hidden" | { tag, tone }: hidden, or a tag beside the title

const assistant_topic = (topic) => ({ group: "use", try: { panel: true }, ...topic });
const setup_topic = (topic) => ({ group: "setup", ...topic });

export const CHAPTERS = [
	{ key: "start", group: "use", title: __("Get started") },
	{ key: "faster", group: "use", title: __("Work faster") },
	{ key: "work", group: "use", title: __("Let it do the work") },
	{ key: "yours", group: "use", title: __("Make it yours") },
	{ key: "connect", group: "setup", title: __("Connect") },
	{ key: "teach", group: "setup", title: __("Teach") },
	{ key: "automate", group: "setup", title: __("Automate") },
	{ key: "improve", group: "setup", title: __("Improve") },
];

export const TOPICS = [
	assistant_topic({
		key: "open-assistant",
		chapter: "start",
		minutes: 1,
		title: __("Open the assistant"),
		text: __(
			"The assistant sits in a panel beside every desk page and stays open while you move around."
		),
		steps: [
			{
				title: __("Find the sparkles"),
				text: __("In the dock, next to search and notifications."),
				picture: "dock",
			},
			{
				title: __("Open it"),
				text: __("Click the sparkles, or press Ctrl+. on any page."),
				picture: "panel",
			},
			{
				title: __("Make room"),
				text: __("Drag the panel's inner edge to make it wider or narrower."),
				picture: "resize",
			},
		],
		tips: [
			__("The panel remembers whether it was open, so it is still there after a reload."),
			__("Press Escape to close it."),
		],
		related: ["ask", "conversations"],
		tour: [
			{ target: "launcher", step: 0 },
			{
				target: "panel",
				title: __("Here it is"),
				text: __("The assistant opens beside the page you are on."),
			},
			{ target: "resizer", step: 2 },
		],
	}),
	assistant_topic({
		key: "ask",
		chapter: "start",
		minutes: 2,
		title: __("Ask about your data"),
		text: __(
			"Ask a question in your own words. The assistant looks up records and runs reports, using only what you are allowed to see."
		),
		steps: [
			{
				title: __("Ask"),
				text: __("Type a question, for example: Which invoices are overdue?"),
				picture: "composer",
			},
			{
				title: __("Follow the answer"),
				text: __(
					"The answer arrives as it is written, with the records and reports it used."
				),
				picture: "answer",
			},
			{
				title: __("Ask about this page"),
				text: __(
					"The page you are on goes with your question, so this customer or this report is understood."
				),
				picture: "context",
			},
		],
		tips: [
			__("Ask mode reads and explains. It never changes data."),
			__("Leave this page out removes the page from your question."),
			__("AI can make mistakes. Check important figures."),
		],
		related: ["agent-mode", "conversations"],
		tour: [
			{ target: "composer", step: 0 },
			{
				target: "mode",
				title: __("Ask mode"),
				text: __("Ask mode reads and explains. It never changes data."),
			},
		],
	}),
	assistant_topic({
		key: "read-document",
		chapter: "faster",
		minutes: 2,
		title: __("Read a document"),
		text: __(
			"Attach a PDF, a photo or a text file. The assistant shows what it read, you check the values, and only the values you confirm are used."
		),
		steps: [
			{
				title: __("Open the assistant"),
				text: __("The sparkles in the dock, or Ctrl+. on any page."),
				picture: "dock",
			},
			{
				title: __("Attach the file"),
				text: __("Click Attach a file and pick a PDF, a photo or a text file."),
				picture: "attach",
			},
			{
				title: __("Check the values"),
				text: __("A card lists what was read. Fix any value that is wrong."),
				picture: "review",
			},
			{
				title: __("Use them"),
				text: __("Use these values fills the open form, or opens a new one."),
				picture: "filled",
			},
		],
		tips: [
			__("The assistant only reads files you are allowed to open."),
			__("Every value you correct is kept, so the next reading is better."),
			__(
				"A document that matches a template comes back with exactly that template's fields."
			),
		],
		related: ["document-templates", "processing-log"],
		tour: [
			{ target: "launcher", step: 0 },
			{ target: "attach", step: 1 },
			{
				target: "composer",
				title: __("Add a question"),
				text: __("Say what you need from the file, or just send it."),
			},
		],
	}),
	assistant_topic({
		key: "voice",
		chapter: "faster",
		minutes: 1,
		title: __("Speak instead of typing"),
		text: __(
			"Record your question in the panel. It is written out for you to check before you send it."
		),
		steps: [
			{
				title: __("Start recording"),
				text: __("Click the microphone beside the message box and speak."),
				picture: "microphone",
			},
			{
				title: __("Stop"),
				text: __("Click it again. Your words appear in the message box."),
				picture: "composer",
			},
			{
				title: __("Send"),
				text: __("Correct anything misheard, then send it like any message."),
				picture: "answer",
			},
		],
		tips: [__("The recording is deleted once it has been turned into text.")],
		related: ["ask", "language"],
		tour: [{ target: "microphone", step: 0 }],
		status: (assistant) => (assistant.voice ? null : "hidden"),
	}),
	assistant_topic({
		key: "write-with-ai",
		chapter: "faster",
		minutes: 1,
		title: __("Write with AI"),
		text: __(
			"Long text fields in every form get a sparkles button. Say what the field should say and it is written in place."
		),
		steps: [
			{
				title: __("Find the button"),
				text: __("Open a form. The sparkles sit beside the label of a long text field."),
				picture: "field",
			},
			{
				title: __("Say what you want"),
				text: __(
					"Describe the text, for example: a polite reminder that the invoice is due."
				),
				picture: "popover",
			},
			{
				title: __("Keep it or undo"),
				text: __(
					"The text appears in the field. Undo puts the old text back. Save the form as usual."
				),
				picture: "undo",
			},
		],
		tips: [
			__("Nothing is saved until you save the form."),
			__("A field you edit while the text is being written is never overwritten."),
		],
		related: ["ask"],
		tour: [
			{
				target: "try_it",
				text: __("Opens a new ToDo. The sparkles sit beside its long text field."),
			},
		],
		try: { new_doc: "ToDo" },
		status: (assistant) =>
			assistant.field_writer?.length ? null : { tag: __("Off"), tone: "off" },
	}),
	assistant_topic({
		key: "workflows",
		chapter: "work",
		minutes: 3,
		title: __("Guided workflows"),
		text: __(
			"A workflow asks its questions one step at a time and ends with a filled form for you to check."
		),
		steps: [
			{
				title: __("Start one"),
				text: __(
					"In the panel, pick a workflow under Guided workflows, or choose Start a guided workflow from the mode menu."
				),
				picture: "workflows",
			},
			{
				title: __("Answer"),
				text: __(
					"Answer each question. The bar shows the step you are on, and quick replies save typing."
				),
				picture: "workflow-bar",
			},
			{
				title: __("Check the form"),
				text: __(
					"When the steps are done, a new form opens with your answers. Check it and save it."
				),
				picture: "filled",
			},
		],
		tips: [
			__("Saved after every answer. You can leave and come back."),
			__("Exit leaves the workflow at any time."),
		],
		related: ["build-workflow"],
		tour: [
			{
				target: "mode",
				title: __("Start one"),
				text: __(
					"Open this menu and choose Start a guided workflow. It is there once a workflow is ready for you."
				),
			},
		],
		status: (assistant) =>
			assistant.workflows?.length ? null : { tag: __("None yet"), tone: "off" },
	}),
	assistant_topic({
		key: "agent-mode",
		chapter: "work",
		minutes: 2,
		title: __("Agent mode"),
		text: __(
			"In Agent mode the assistant can prepare changes: new records, edits, submissions. You approve each one before it happens."
		),
		steps: [
			{
				title: __("Switch to Agent"),
				text: __("Click Ask in the message box and choose Agent."),
				picture: "mode",
			},
			{
				title: __("Describe the task"),
				text: __("For example: create a ToDo for every overdue invoice."),
				picture: "composer",
			},
			{
				title: __("Approve or reject"),
				text: __(
					"Each change shows as a card marked Needs approval. Confirm it, or Reject it."
				),
				picture: "proposal",
			},
		],
		tips: [
			__("The assistant can only change what you could change yourself."),
			__("Your administrator decides who may use Agent mode."),
			__("Some DocTypes can be kept out of reach in AI Settings."),
		],
		related: ["ask", "access"],
		tour: [{ target: "mode", step: 0 }],
		status: (assistant) => (assistant.agent_mode ? null : { tag: __("Off"), tone: "off" }),
	}),
	assistant_topic({
		key: "language",
		chapter: "yours",
		minutes: 1,
		title: __("Arabic and English"),
		text: __(
			"Write in Arabic or English and the reply comes in the same language. When the desk is in Arabic, the panel reads right to left."
		),
		steps: [
			{
				title: __("Write in your language"),
				text: __("Type or speak in Arabic or English."),
				picture: "composer",
			},
			{
				title: __("Read the reply"),
				text: __("The answer comes back in the language you wrote in."),
				picture: "answer",
			},
		],
		tips: [__("Your administrator can fix the reply language in AI Settings.")],
		related: ["voice"],
		tour: [{ target: "composer", step: 0 }],
	}),
	assistant_topic({
		key: "conversations",
		chapter: "yours",
		minutes: 1,
		title: __("Your conversations"),
		text: __(
			"Every chat is kept, so you can go back to it later. Rating answers helps improve them."
		),
		steps: [
			{
				title: __("Open History"),
				text: __("History at the top of the panel lists your recent conversations."),
				picture: "history",
			},
			{
				title: __("Rate an answer"),
				text: __("Thumbs up for a good answer, thumbs down for a bad one."),
				picture: "rating",
			},
			{
				title: __("Start fresh"),
				text: __("New chat starts an empty conversation."),
				picture: "panel",
			},
		],
		tips: [__("Other users cannot see your conversations; System Managers can.")],
		related: ["ask"],
		tour: [
			{ target: "history", step: 0 },
			{ target: "new_chat", step: 2 },
		],
	}),
	setup_topic({
		key: "provider",
		chapter: "connect",
		minutes: 3,
		title: __("Choose the AI provider"),
		text: __(
			"One provider answers for the whole site: OpenAI, Claude, Gemini, or Ollama running on your own server."
		),
		steps: [
			{
				title: __("Open AI Settings"),
				text: __("Setup in the dock, then AI Settings."),
				picture: "settings",
			},
			{
				title: __("Pick the provider"),
				text: __("Choose it and enter its API key and model."),
				picture: "settings",
			},
			{
				title: __("Save"),
				text: __("Ask the assistant a question to check it answers."),
				picture: "answer",
			},
		],
		tips: [__("With Ollama, your data stays on your server.")],
		related: ["access"],
		tour: [
			{
				target: "dock_setup",
				title: __("Open AI Settings"),
				text: __("Setup in the dock opens AI Settings."),
			},
			{ target: "try_it" },
		],
		doctype: "AI Settings",
		try: { route: ["Form", "AI Settings"] },
	}),
	setup_topic({
		key: "access",
		chapter: "connect",
		minutes: 2,
		title: __("Who can use it"),
		text: __(
			"Give people the Intelligence User role to use the assistant, and the Intelligence Agent role for Agent mode as well. Choose what Agent mode may never touch and whether forms get Write with AI."
		),
		steps: [
			{
				title: __("Give the role"),
				text: __(
					"Add the Intelligence User role to each person who may use the assistant, on their User form or through a Role Profile."
				),
				picture: "settings",
			},
			{
				title: __("Agent mode"),
				text: __(
					"Turn on Allow Agent Mode in AI Settings, and give the Intelligence Agent role to the people who may use it."
				),
				picture: "settings",
			},
			{
				title: __("Write with AI"),
				text: __("Turn Write with AI in Forms on or off."),
				picture: "settings",
			},
		],
		tips: [
			__("Permissions still apply: the assistant never goes beyond what each user may do."),
			__("Excluded DocTypes in AI Settings are never changed, whoever asks."),
		],
		related: ["provider", "agent-mode"],
		tour: [
			{
				target: "dock_setup",
				title: __("Open AI Settings"),
				text: __("Setup in the dock opens AI Settings."),
			},
			{ target: "try_it" },
		],
		doctype: "AI Settings",
		try: { route: ["Form", "AI Settings"] },
	}),
	setup_topic({
		key: "knowledge-packs",
		chapter: "teach",
		minutes: 2,
		title: __("Knowledge packs"),
		text: __(
			"Facts, policies and answers the assistant can search, so it answers questions your records cannot."
		),
		steps: [
			{
				title: __("Create a pack"),
				text: __("Name it and add entries, each a topic and its content."),
				picture: "list",
			},
			{
				title: __("Give it to a workflow"),
				text: __("In the Workflow Builder, add the pack to the workflows that need it."),
				picture: "builder",
			},
		],
		tips: [__("Keep entries short; one fact per entry is easiest to find.")],
		related: ["build-workflow"],
		tour: [
			{
				target: "dock_setup",
				title: __("Find Knowledge Packs"),
				text: __("Setup in the dock lists Knowledge Packs."),
			},
			{ target: "try_it" },
		],
		doctype: "AI Knowledge Pack",
		try: { route: ["List", "AI Knowledge Pack"] },
	}),
	setup_topic({
		key: "document-templates",
		chapter: "teach",
		minutes: 4,
		title: __("Teach it a document"),
		text: __(
			"A template tells the assistant what a kind of document looks like and which fields to read from it."
		),
		steps: [
			{
				title: __("Create a template"),
				text: __("Give the document type a key and the detection keywords printed on it."),
				picture: "list",
			},
			{
				title: __("Add the fields"),
				text: __(
					"Add an extraction rule per field: a regex pattern, or a hint for the AI."
				),
				picture: "review",
			},
			{
				title: __("Try it"),
				text: __("Attach such a document in the panel and check what comes back."),
				picture: "attach",
			},
		],
		tips: [__("Corrections users make become training pairs for the template.")],
		related: ["read-document", "processing-log"],
		tour: [
			{
				target: "dock_documents",
				title: __("Find the templates"),
				text: __("Documents in the dock opens Document Templates."),
			},
			{ target: "try_it" },
		],
		doctype: "AI Document Template",
		try: { route: ["List", "AI Document Template"] },
	}),
	setup_topic({
		key: "document-requirements",
		chapter: "teach",
		minutes: 2,
		title: __("Required documents"),
		text: __(
			"Say which documents a DocType's records should have, so other apps can show what is still missing."
		),
		steps: [
			{
				title: __("Add a requirement"),
				text: __("Choose the DocType and the document type it needs."),
				picture: "list",
			},
			{
				title: __("See what is missing"),
				text: __("Records report their present and missing documents from what was read."),
				picture: "review",
			},
		],
		tips: [__("Requirements belong to a DocType, not to a workflow.")],
		related: ["document-templates"],
		tour: [
			{
				target: "dock_documents",
				title: __("Find the requirements"),
				text: __("Documents in the dock lists Document Requirements."),
			},
			{ target: "try_it" },
		],
		doctype: "AI Document Requirement",
		try: { route: ["List", "AI Document Requirement"] },
	}),
	setup_topic({
		key: "build-workflow",
		chapter: "automate",
		minutes: 5,
		title: __("Build a workflow"),
		text: __(
			"Design the questions a guided workflow asks, the form it fills, and where it runs: desk, portal or WhatsApp."
		),
		steps: [
			{
				title: __("Open the builder"),
				text: __("Workflows in the dock opens the Workflow Builder."),
				picture: "builder",
			},
			{
				title: __("Add steps"),
				text: __("Each step has a question, a target DocType and the fields it collects."),
				picture: "builder",
			},
			{
				title: __("Set the scope"),
				text: __(
					"Describe what the workflow is for, so off-topic messages are turned away."
				),
				picture: "builder",
			},
			{
				title: __("Save and try"),
				text: __("Start it from the assistant panel."),
				picture: "workflows",
			},
		],
		tips: [__("Changes reach conversations already in progress.")],
		related: ["workflows", "knowledge-packs"],
		tour: [{ target: "dock_workflows", step: 0 }, { target: "try_it" }],
		doctype: "AI Workflow",
		try: { route: ["ai-workflow-builder"] },
	}),
	setup_topic({
		key: "post-processors",
		chapter: "automate",
		minutes: 3,
		title: __("Post processors"),
		text: __(
			"Python callbacks that fill or create records from a document's values once it has been read."
		),
		steps: [
			{
				title: __("Write the callback"),
				text: __("A developer adds a function to an app."),
				picture: "list",
			},
			{
				title: __("Register it"),
				text: __(
					"Create a Post Processor with the document type and the function's path."
				),
				picture: "list",
			},
		],
		tips: [__("They run for documents read by the portal, WhatsApp and other apps.")],
		related: ["document-templates"],
		tour: [
			{
				target: "dock_setup",
				title: __("Find Post Processors"),
				text: __("Setup in the dock lists Post Processors."),
			},
			{ target: "try_it" },
		],
		doctype: "AI Post Processor",
		try: { route: ["List", "AI Post Processor"] },
	}),
	setup_topic({
		key: "processing-log",
		chapter: "improve",
		minutes: 2,
		title: __("Check what was read"),
		text: __(
			"Every reading is logged with its values and confidence; every correction becomes a training pair."
		),
		steps: [
			{
				title: __("Open the Processing Log"),
				text: __("Documents in the dock, then Processing Log."),
				picture: "list",
			},
			{
				title: __("Look at corrections"),
				text: __("Training Pairs list what was read next to what the user confirmed."),
				picture: "review",
			},
		],
		tips: [__("Low-confidence readings wait for a person to confirm them.")],
		related: ["document-templates", "read-document"],
		tour: [{ target: "dock_documents", step: 0 }, { target: "try_it" }],
		doctype: "AI Processing Log",
		try: { route: ["List", "AI Processing Log"] },
	}),
	setup_topic({
		key: "analytics",
		chapter: "improve",
		minutes: 1,
		title: __("Session analytics"),
		text: __(
			"How often each workflow is started, finished or left, and how many turns it takes."
		),
		steps: [
			{
				title: __("Open the report"),
				text: __("Session Analytics in the Intelligence sidebar."),
				picture: "chart",
			},
		],
		tips: [__("A workflow often left halfway may ask too much in one step.")],
		related: ["build-workflow"],
		tour: [{ target: "analytics", step: 0 }],
		report: "AI Session Analytics",
		try: { route: ["query-report", "AI Session Analytics"] },
	}),
];
