import os
import glob
from typing import Optional
from CloudModel import CloudModel
from savegame import Savegame
from utils import get_time_from_save_file


class LocalSaveServer(CloudModel):
    """
    CloudModel implementation using local filesystem for save storage.
    """

    def __init__(self, save_path: str) -> None:
        """
        Initialize local save model.

        Args:
            save_path: Local directory path for save files
        """
        super().__init__()
        self.save_path = save_path
        self._ensure_save_directory()

    def _ensure_save_directory(self):
        """Ensure the save directory exists."""
        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path)
                print(f"Created save directory: {self.save_path}")
            except Exception as e:
                print(f"Failed to create save directory {self.save_path}: {e}")
                raise

    def upload_save(self, save: Savegame):
        """
        Save a Savegame to the local directory.

        Args:
            save: Savegame object to save
        """
        file_name = save.file_name
        save_content = save.save_data_bytes
        assert isinstance(
            save_content, list
        ), f"save_content is of type {type(save_content)}"

        file_path = os.path.join(self.save_path, file_name)

        try:
            print(f"Saving game to: {file_path}")
            save_bytes = bytes(save_content)
            with open(file_path, "wb") as f:
                f.write(save_bytes)
            print(f"Successfully saved {file_name} ({len(save_bytes)} bytes)")

        except Exception as e:
            print(f"Failed to save file: {e}")
            raise

    def get_latest_save(self) -> Optional[Savegame]:
        """
        Retrieve the latest save file from the local directory.

        Returns:
            Savegame object, or None if no saves found
        """
        try:
            # get all save files from save dir
            file_pattern = os.path.join(self.save_path, "bitburnerSave_*.json*")
            list_of_files = glob.glob(file_pattern)

            if not list_of_files:
                print("No Bitburner save files found in local directory.")
                return None

            latest_file_path = max(
                list_of_files, key=lambda f: get_time_from_save_file(f)
            )
            latest_file_name = os.path.basename(latest_file_path)

            print(f"Loading latest save: {latest_file_name} ...")

            return Savegame.from_file(latest_file_path)

        except Exception as e:
            print(f"Failed to retrieve latest save: {e}")
            return None
