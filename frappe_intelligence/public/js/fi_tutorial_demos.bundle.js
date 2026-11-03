// Loaded only by the demo recorder (tutorial/recorder.cjs), never by the desk.
import { DEMOS } from "./tutorial/demos";
import { Stage } from "./tutorial/stage";

frappe.provide("frappe_intelligence.tutorial");
frappe_intelligence.tutorial.DEMOS = DEMOS;
frappe_intelligence.tutorial.Stage = Stage;
