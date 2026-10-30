"""
Data Access Layer (DAL) for SQLite storage and export operations.
Enforces foreign keys, optimizes batch operations, and exports data to CSV/JSON/SQL.
"""

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from src.config import WORKSPACE_DIR

DEFAULT_SCHEMA_PATH = WORKSPACE_DIR / "schema.sql"

TABLE_NAMES = [
    "learners",
    "courses",
    "skills",
    "skill_prerequisites",
    "content_items",
    "content_skills",
    "attempts",
    "assessment_results",
    "learning_paths",
    "recommendations",
]


def get_db_connection(db_path: Union[str, Path]) -> sqlite3.Connection:
    """
    Creates and configures a SQLite connection with foreign keys strictly enabled.
    """
    path_str = str(db_path)
    conn = sqlite3.connect(path_str)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(db_path: Union[str, Path], schema_path: Optional[Union[str, Path]] = None) -> None:
    """Initializes tables, constraints, and indexes from schema.sql."""
    schema_file = Path(schema_path or DEFAULT_SCHEMA_PATH)
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.executescript(schema_sql)
    finally:
        conn.close()


def insert_batch(
    conn: sqlite3.Connection,
    table_name: str,
    columns: List[str],
    rows: Iterable[Union[Tuple, List]],
    chunk_size: int = 10_000,
) -> int:
    """Efficiently inserts rows in parameterized chunks within a transaction."""
    placeholders = ", ".join(["?"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"

    total_inserted = 0
    buffer: List[Tuple] = []

    with conn:
        for row in rows:
            buffer.append(tuple(row))
            if len(buffer) >= chunk_size:
                conn.executemany(sql, buffer)
                total_inserted += len(buffer)
                buffer.clear()

        if buffer:
            conn.executemany(sql, buffer)
            total_inserted += len(buffer)
            buffer.clear()

    return total_inserted


def get_table_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    """Returns row counts for all platform tables."""
    counts = {}
    cursor = conn.cursor()
    for table in TABLE_NAMES:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    return counts


def export_to_csv(conn: sqlite3.Connection, export_dir: Union[str, Path]) -> Dict[str, str]:
    """Exports each table to standard RFC 4180 CSV format."""
    out_dir = Path(export_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exported_files = {}

    cursor = conn.cursor()
    for table in TABLE_NAMES:
        csv_path = out_dir / f"{table}.csv"
        cursor.execute(f"SELECT * FROM {table}")
        col_names = [description[0] for description in cursor.description]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            while True:
                rows = cursor.fetchmany(5000)
                if not rows:
                    break
                writer.writerows(rows)

        exported_files[table] = str(csv_path)

    return exported_files


def export_to_json(conn: sqlite3.Connection, export_dir: Union[str, Path]) -> Dict[str, str]:
    """Exports each table to line-delimited and structured JSON format."""
    out_dir = Path(export_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exported_files = {}

    cursor = conn.cursor()
    for table in TABLE_NAMES:
        json_path = out_dir / f"{table}.json"
        cursor.execute(f"SELECT * FROM {table}")
        col_names = [description[0] for description in cursor.description]

        records = []
        while True:
            rows = cursor.fetchmany(5000)
            if not rows:
                break
            for row in rows:
                records.append(dict(zip(col_names, row)))

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        exported_files[table] = str(json_path)

    return exported_files


def export_to_sql(conn: sqlite3.Connection, output_file: Union[str, Path]) -> str:
    """Dumps complete database schema and data as valid executable SQL."""
    out_file = Path(output_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")

    return str(out_file)
