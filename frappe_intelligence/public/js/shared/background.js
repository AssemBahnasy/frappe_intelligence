// Waiting for the result of a short background job (utils/background.py): the `fi_job` realtime
// event, or asking now and then in case it was missed while the socket reconnected.

const EVENT = "fi_job";
const CHECK_SECONDS = 10;
const GIVE_UP_SECONDS = 600;

export function job_result(job) {
	return new Promise((resolve, reject) => {
		const started = Date.now();
		const finish = (result) => {
			if (!result || result.pending) return;
			frappe.realtime.off(EVENT, on_event);
			clearInterval(timer);
			result.error ? reject(new Error(result.error)) : resolve(result.value);
		};
		const on_event = (e) => e.job === job && finish(e);
		const timer = setInterval(async () => {
			if (Date.now() - started > GIVE_UP_SECONDS * 1000) {
				finish({ error: __("This took too long. Please try again.") });
				return;
			}
			finish(
				await frappe
					.xcall("frappe_intelligence.api.jobs.job_result", { job })
					.catch(() => null)
			);
		}, CHECK_SECONDS * 1000);
		frappe.realtime.on(EVENT, on_event);
	});
}
