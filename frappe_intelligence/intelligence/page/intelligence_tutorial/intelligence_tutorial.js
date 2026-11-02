// The tutorial: every feature as a topic (docs/tutorial/). Its bundle loads only here.
const PAGE = "intelligence-tutorial";

// One shared load: concurrent frappe.require calls for the same file run it twice.
let assets = null;
const load_assets = () => (assets ??= frappe.require("fi_tutorial.bundle.js"));

frappe.pages[PAGE].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Tutorial"),
		single_column: true,
	});
	// Mount point of its own: page.main also holds Frappe's filter bar.
	wrapper.vue_host = $("<div></div>").appendTo(page.main);

	// Frappe has no unload hook; the container triggers "hide" on the wrapper when leaving.
	$(wrapper).on("hide", (e) => {
		if (e.target === wrapper) teardown(wrapper);
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => {
			assets = null; // the rebuilt bundle has a new file name
			if (frappe.get_route()[0] === PAGE) {
				teardown(wrapper);
				render(wrapper);
			}
		});
	}
};

// Fires on every route change, including /intelligence-tutorial/<topic> to another topic.
frappe.pages[PAGE].on_page_show = function (wrapper) {
	render(wrapper);
};

function teardown(wrapper) {
	wrapper._render_token = (wrapper._render_token || 0) + 1; // cancels pending loads
	wrapper.tutorial?.destroy();
	wrapper.tutorial = null;
}

const route_topic = () => frappe.get_route()[1] || null;

function render(wrapper) {
	// Switching topics keeps the mounted app (search, scroll of the topic list).
	if (wrapper.tutorial) return wrapper.tutorial.open(route_topic());

	const token = wrapper._render_token;
	load_assets().then(() => {
		if (token !== wrapper._render_token || wrapper.tutorial) return;
		wrapper.tutorial = new frappe_intelligence.ui.Tutorial({
			wrapper: wrapper.vue_host,
			page: wrapper.page,
			topic: route_topic(),
		});
	});
}
