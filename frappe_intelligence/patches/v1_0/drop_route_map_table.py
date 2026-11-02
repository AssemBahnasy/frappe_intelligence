"""remove_route_map deleted the DocType; deleting a DocType keeps its table."""

import frappe


def execute():
	frappe.db.sql_ddl("DROP TABLE IF EXISTS `tabAI Route Map`")
