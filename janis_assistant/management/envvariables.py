from enum import Enum
from os import getenv


class HashableEnum(str, Enum):
    def __str__(self):
        return self.value

    def to_yaml(self):
        return self.value

    pass
    # def __hash__(self):
    #     return self.value.__hash__()


class EnvVariables(HashableEnum):
    config_path = "JANIS_CONFIGPATH"
    config_dir = "JANIS_CONFIGDIR"
    exec_dir = "JANIS_EXCECUTIONDIR"
    search_path = "JANIS_SEARCHPATH"
    recipe_paths = "JANIS_RECIPEPATHS"
    recipe_directory = "JANIS_RECIPEDIRECTORY"  # secretly comma separated

    cromwelljar = "JANIS_CROMWELLJAR"

    def __str__(self):
        return self.value

    def default(self):
        import os

        if self == EnvVariables.config_dir:
            return os.path.join(os.getenv("HOME"), ".janis/")
        elif self == EnvVariables.exec_dir:
            return os.path.join(os.getenv("HOME"), "janis/execution/")
        elif self == EnvVariables.config_path:
            return os.path.join(os.getenv("HOME"), ".janis/janis.conf")
        elif self == EnvVariables.recipe_paths:
            return []
        elif self == EnvVariables.recipe_directory:
            return []

        raise Exception(f"Couldn't determine default() for '{self.value}'")

    def resolve(self, include_default=False):
        value = getenv(self.value, self.default() if include_default else None)
        if self == EnvVariables.recipe_paths:
            return value.split(",") if value else None
        if self == EnvVariables.recipe_directory:
            return value.split(",") if value else None
        return value
