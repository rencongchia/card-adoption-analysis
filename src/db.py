"""DuckDB helpers for the card-adoption-analysis pipeline.

Usage in a notebook:

    from src.db import get_conn, register_csv_tables, materialize_sql_file

    con = get_conn()
    register_csv_tables(con)
    df = materialize_sql_file(con, "sql/03_profit_per_transaction.sql")
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

CANONICAL_TABLES: tuple[str, ...] = ("card", "transaction", "cost_structure", "rates")


def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def register_csv_tables(
    con: duckdb.DuckDBPyConnection,
    processed_dir: Path = PROCESSED_DIR,
    tables: tuple[str, ...] = CANONICAL_TABLES,
) -> None:
    """Register CSV files in `processed_dir` as DuckDB views.

    Raises FileNotFoundError if any expected CSV is missing — typically
    because notebooks/01_validate.ipynb has not been run yet.
    """
    for tbl in tables:
        path = processed_dir / f"{tbl}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run notebooks/01_validate.ipynb first."
            )
        con.execute(
            f"CREATE OR REPLACE VIEW {tbl} AS "
            f"SELECT * FROM read_csv_auto('{path.as_posix()}')"
        )


def _model_name_from_path(sql_path: str | Path) -> str:
    """`sql/03_profit_per_transaction.sql` → `profit_per_transaction`."""
    stem = Path(sql_path).stem
    return stem.split("_", 1)[1] if "_" in stem and stem.split("_", 1)[0].isdigit() else stem


def materialize_sql_file(
    con: duckdb.DuckDBPyConnection,
    sql_path: str | Path,
    model_name: str | None = None,
) -> pd.DataFrame:
    """dbt-style helper: wrap the SELECT in `sql_path` as `CREATE OR REPLACE VIEW {model_name}`.

    Each .sql file should be a single SELECT (no trailing semicolon needed). The view is
    named after the file (`01_clean_transactions.sql` → `clean_transactions`) unless overridden.
    Returns the SELECT result as a DataFrame.
    """
    sql = Path(sql_path).read_text().strip().rstrip(";")
    name = model_name or _model_name_from_path(sql_path)
    con.execute(f"CREATE OR REPLACE VIEW {name} AS {sql}")
    return con.execute(f"SELECT * FROM {name}").df()
