import gzip
import json
import time
import os
from utils import SaveResult


class Savegame:
    def __init__(self, save_result: SaveResult):
        self.save_result = save_result
        self.file_name = str(save_result.get("fileName", "unknown"))

        save_content = save_result.get("save")
        assert isinstance(
            save_content, list
        ), f"save_content is of type {type(save_content)}, expected list"

        self.save_data_bytes = save_content
        save_bytes = bytes(save_content)

        try:
            decompressed_content = gzip.decompress(save_bytes)
            self.save_data_json = json.loads(decompressed_content.decode("utf-8"))

            player_save = json.loads(self.save_data_json["data"]["PlayerSave"])
            self.player_data = player_save["data"]

            self.last_save = self.player_data["lastSave"]
            self.identifier = self.player_data.get("identifier", "unknown")
            self.total_playtime = self.player_data["totalPlaytime"]

        except (json.JSONDecodeError, KeyError, gzip.BadGzipFile) as e:
            raise ValueError(f"Error parsing save file: {e}")

    @classmethod
    def from_file(cls, file_path: str) -> "Savegame":
        file_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            file_content = f.read()

        save_result = {"fileName": file_name, "save": list(file_content)}
        return cls(save_result)

    @property
    def progression_timestamp(self) -> int:
        return self.last_save

    @property
    def last_save_readable(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_save / 1000))

    def save_to_file(self, file_path: str):
        save_bytes = bytes(self.save_data_bytes)
        with open(file_path, "wb") as f:
            f.write(save_bytes)

    def to_save_result(self) -> SaveResult:
        return self.save_result

    def __str__(self) -> str:
        return f"Savegame({self.file_name}, lastSave={self.last_save_readable}, id={self.identifier})"

    def __repr__(self) -> str:
        return self.__str__()
