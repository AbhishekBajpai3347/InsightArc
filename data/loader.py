# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.expand_frame_repr", False)
pd.set_option("display.max_colwidth", None)

LOADERS = {
    ".csv": pd.read_csv,
    ".xlsx": pd.read_excel,
    ".xls": pd.read_excel,
    ".json": pd.read_json,
    ".pickle": pd.read_pickle,
    ".pkl": pd.read_pickle,
    ".xml": pd.read_xml,
}


import io
from typing import Union

def load_dataset(file_path: Union[str, Path, io.BytesIO, io.StringIO], filename: str | None = None) -> pd.DataFrame:
    if isinstance(file_path, (io.BytesIO, io.StringIO)):
        if not filename:
            raise ValueError("filename must be provided when passing a buffer")
        file_type = Path(filename).suffix.lower()
        if file_type not in LOADERS:
            valid_types = ", ".join(sorted(LOADERS.keys()))
            raise ValueError(
                f"Unsupported file type: {file_type}\n"
                f"Supported types are: {valid_types}"
            )
        loader = LOADERS[file_type]
        return loader(file_path)

    path = Path(file_path)
    # Check whether the file exists
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    # Get file extension
    file_type = path.suffix.lower()

    # Check whether the extension is supported
    if file_type not in LOADERS:
        valid_types = ", ".join(sorted(LOADERS.keys()))
        raise ValueError(
            f"Unsupported file type: {file_type}\n"
            f"Supported types are: {valid_types}"
        )

    # Load and return the dataset
    loader = LOADERS[file_type]

    return loader(path)
