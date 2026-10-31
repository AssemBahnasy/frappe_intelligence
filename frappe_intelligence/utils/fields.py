"""Matching the field names the AI or an administrator wrote to a DocType's real fields."""

from __future__ import annotations


def writable_fieldname(meta, key: str) -> str | None:
	"""A writable field by name, or by label: models often use the labels they were shown."""
	label = key.strip().lower()
	df = meta.get_field(key) or next(
		(df for df in meta.fields if (df.label or "").strip().lower() == label), None
	)
	return df.fieldname if df and not df.read_only else None
