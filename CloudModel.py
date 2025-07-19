from abc import ABC, abstractmethod
from typing import Optional

from savegame import Savegame


class CloudModel(ABC):
    @abstractmethod
    def upload_save(self, save: Savegame):
        pass

    @abstractmethod
    def get_latest_save(self) -> Optional[Savegame]:
        pass
