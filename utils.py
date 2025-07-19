from typing import Dict, Union
import re

SaveResult = Dict[str, Union[str, list[int]]]


def get_time_from_save_file(file_name: str) -> int:
    match = re.search(r"(?<!\d)(\d{10})(?!\d)", file_name)
    if match:
        return int(match.group(1))
    raise ValueError(f"no unix timestamp in file name found: {file_name}")
