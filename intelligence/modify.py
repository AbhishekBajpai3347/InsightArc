# -*- coding: utf-8 -*-
"""
Re-export modification functions from data.modify for backwards compatibility.
"""

from data.modify import (
    delete_column,
    rename_column,
    select_columns,
    drop_rows,
    update_value,
    add_column,
    fill_column,
)

__all__ = [
    "delete_column",
    "rename_column",
    "select_columns",
    "drop_rows",
    "update_value",
    "add_column",
    "fill_column",
]
