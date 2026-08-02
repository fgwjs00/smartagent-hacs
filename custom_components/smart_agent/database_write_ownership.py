"""HA-local write ownership and schema migration safety contracts."""
from __future__ import annotations

import logging
import re
import sqlite3


_LOGGER = logging.getLogger(__name__)

_VALID_MIGRATION_TABLES = frozenset({"events", "devices", "habits", "rules", "action_results", "ai_scenes", "action_transactions", "room_topology"})

# Add-on Core owns business writes. HA keeps compatibility tables readable until
# a separately evidenced migration and rollback plan permits their retirement.
BUSINESS_TABLE_OWNERSHIP = {
    table: {
        "SELECT": ("ha", "addon"),
        "INSERT": "addon",
        "UPDATE": "addon",
        "DELETE": "addon",
    }
    for table in ("devices", "habits", "rules", "ai_scenes")
}
HA_COMPATIBILITY_WRITE_COLUMNS = {
    "devices": frozenset({"ha_unique_id", "ha_device_id", "entity_id", "updated"}),
    "ai_scenes": frozenset({"ha_entity_id", "updated"}),
}


HA_LOCAL_WRITE_TABLES = frozenset({"events"})


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL comments without interpreting parameter values."""
    text = str(sql or "")
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"--[^\r\n]*(?:\r?\n|$)", " ", text)
    return " ".join(text.strip().split())


def _top_level_statement(sql: str) -> str:
    """Return the top-level statement after optional CTE declarations."""
    normalized = _strip_sql_comments(sql)
    if not re.match(r"^WITH\b", normalized, re.IGNORECASE):
        return normalized
    depth = 0
    quote = ""
    index = 0
    while index < len(normalized):
        char = normalized[index]
        if quote:
            if quote == "]":
                if char == "]":
                    quote = ""
            elif char == quote:
                if index + 1 < len(normalized) and normalized[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"', chr(96)}:
            quote = char
            index += 1
            continue
        if char == "[":
            quote = "]"
            index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0 and (char.isalpha() or char == "_"):
            end = index + 1
            while end < len(normalized) and (normalized[end].isalnum() or normalized[end] == "_"):
                end += 1
            token = normalized[index:end].upper()
            if token in {"INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP"}:
                return normalized[index:]
            index = end
            continue
        index += 1
    return normalized


def classify_ha_local_write(sql: str) -> tuple[str, str, frozenset[str]]:
    """Classify one HA-local write, including CTE/comment/DDL prefixes."""
    normalized = _top_level_statement(sql)
    operation_match = re.match(
        r"^(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP)\b",
        normalized,
        re.IGNORECASE,
    )
    if operation_match is None:
        return "", "", frozenset()
    operation = operation_match.group(1).upper()
    raw_columns = ""
    if operation in {"INSERT", "REPLACE"}:
        match = re.match(
            r"^(?:INSERT|REPLACE)(?:\s+OR\s+\w+)?\s+INTO\s+([^\s(]+)\s*(?:\(([^)]*)\))?",
            normalized,
            re.IGNORECASE,
        )
        raw_columns = match.group(2) if match else ""
    elif operation == "UPDATE":
        match = re.match(
            r"^UPDATE(?:\s+OR\s+\w+)?\s+([^\s]+)\s+SET\s+(.+?)(?:\s+WHERE\b|$)",
            normalized,
            re.IGNORECASE,
        )
        raw_columns = match.group(2) if match else ""
    elif operation == "DELETE":
        match = re.match(r"^DELETE\s+FROM\s+([^\s]+)", normalized, re.IGNORECASE)
    elif operation == "ALTER":
        match = re.match(r"^ALTER\s+TABLE\s+([^\s]+)", normalized, re.IGNORECASE)
    elif operation == "DROP":
        match = re.match(r"^DROP\s+TABLE(?:\s+IF\s+EXISTS)?\s+([^\s]+)", normalized, re.IGNORECASE)
    else:
        match = re.match(r"^CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([^\s(]+)", normalized, re.IGNORECASE)
    if match is None:
        return "", operation, frozenset()
    strip_chars = chr(96) + '"[]'
    table = match.group(1).strip(strip_chars).rsplit(".", 1)[-1].lower()
    columns = frozenset(
        part.split("=", 1)[0].strip().strip(strip_chars).rsplit(".", 1)[-1].lower()
        for part in raw_columns.split(",")
        if part.strip()
    )
    return table, operation, columns


def ha_local_write_allowed(sql: str) -> bool:
    """Fail closed except for explicit HA projection and compatibility writes."""
    table, operation, columns = classify_ha_local_write(sql)
    if not operation or not table:
        return False
    if table in HA_LOCAL_WRITE_TABLES:
        return operation in {"INSERT", "UPDATE", "DELETE", "REPLACE"}
    if table not in BUSINESS_TABLE_OWNERSHIP:
        return False
    allowed_columns = HA_COMPATIBILITY_WRITE_COLUMNS.get(table, frozenset())
    required_mapping = {
        "devices": frozenset({"ha_unique_id", "ha_device_id", "entity_id"}),
        "ai_scenes": frozenset({"ha_entity_id"}),
    }.get(table, frozenset())
    return bool(
        operation == "UPDATE"
        and columns
        and columns <= allowed_columns
        and columns & required_mapping
    )

def _safe_add_column(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    table_name = (table or "").strip()
    col_def = (column_def or "").strip()

    if table_name not in _VALID_MIGRATION_TABLES:
        raise ValueError(f"invalid migration table: {table_name}")
    if not col_def:
        raise ValueError("invalid empty column definition")
    upper_col_def = col_def.upper()
    if ";" in col_def or "--" in col_def or "/*" in col_def or "DROP TABLE" in upper_col_def:
        raise ValueError(f"invalid column definition: {col_def}")

    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            _LOGGER.error("[DB] migration failed: ALTER TABLE %s ADD COLUMN %s: %s", table_name, col_def, exc)
            raise
