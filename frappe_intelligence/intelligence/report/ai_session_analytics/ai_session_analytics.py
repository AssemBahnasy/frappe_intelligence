"""AI Session Analytics — Script Report.

Columns
-------
workflow         Workflow key
total_sessions   All sessions ever created for the workflow
active           Currently active
completed        Reached Completed status
abandoned        Marked Abandoned (idle >7 days via daily task)
avg_turns        Average turn count across all sessions
"""

import frappe


def execute(filters=None):
    columns = _get_columns()
    data = _get_data(filters or {})
    return columns, data


def _get_columns():
    return [
        {
            "fieldname": "workflow",
            "label": "Workflow",
            "fieldtype": "Link",
            "options": "AI Workflow",
            "width": 180,
        },
        {
            "fieldname": "total_sessions",
            "label": "Total Sessions",
            "fieldtype": "Int",
            "width": 130,
        },
        {
            "fieldname": "active",
            "label": "Active",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "fieldname": "completed",
            "label": "Completed",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "fieldname": "abandoned",
            "label": "Abandoned",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "fieldname": "avg_turns",
            "label": "Avg Turns",
            "fieldtype": "Float",
            "precision": 1,
            "width": 110,
        },
    ]


def _get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    workflow_filter = filters.get("workflow")

    conditions = ""
    values = {}

    if from_date:
        conditions += " AND s.creation >= %(from_date)s"
        values["from_date"] = from_date
    if to_date:
        conditions += " AND s.creation <= %(to_date)s"
        values["to_date"] = to_date
    if workflow_filter:
        conditions += " AND s.workflow = %(workflow)s"
        values["workflow"] = workflow_filter

    rows = frappe.db.sql(
        f"""
        SELECT
            s.workflow,
            COUNT(*) AS total_sessions,
            SUM(CASE WHEN s.status = 'Active'    THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN s.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN s.status = 'Abandoned' THEN 1 ELSE 0 END) AS abandoned,
            ROUND(AVG(tc.turn_count), 1) AS avg_turns
        FROM `tabAI Conversation` s
        LEFT JOIN (
            SELECT parent, COUNT(*) AS turn_count
            FROM `tabAI Conversation Message`
            WHERE parenttype = 'AI Conversation' AND role IN ('user', 'assistant')
            GROUP BY parent
        ) tc ON tc.parent = s.name
        WHERE s.mode = 'Workflow' {conditions}
        GROUP BY s.workflow
        ORDER BY total_sessions DESC
        """,
        values=values,
        as_dict=True,
    )

    return rows
