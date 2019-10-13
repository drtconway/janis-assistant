import os
from enum import Enum
from typing import Optional, List, Union
import ruamel.yaml

from janis_runner.engines.enginetypes import EngineType
from janis_core.utils.logger import Logger

from janis_runner.templates import from_template


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

        raise Exception(f"Couldn't determine default() for '{self.value}'")

    def resolve(self, include_default=False):
        return os.getenv(self.value, self.default() if include_default else None)


class JanisConfiguration:
    class Keys(HashableEnum):
        ConfigDir = "configDir"
        ExecutionDir = "executionDir"
        SearchPaths = "searchPaths"
        Engine = "engine"
        Environment = "environment"
        Cromwell = "cromwell"
        Template = "template"
        Recipes = "recipes"

    _managed = None  # type: JanisConfiguration

    _configpath = None

    @staticmethod
    def manager():
        """
        :return: JanisConfiguration
        """
        if not JanisConfiguration._managed:
            JanisConfiguration._managed = JanisConfiguration()
        return JanisConfiguration._managed

    @staticmethod
    def initial_configuration(potential_paths: Optional[Union[str, List[str]]]):

        paths_to_check = []
        if potential_paths:
            if isinstance(potential_paths, list):
                paths_to_check.extend(potential_paths)
            else:
                paths_to_check.append(potential_paths)

        default_path = EnvVariables.config_path.resolve(False)
        if default_path:
            paths_to_check.append(default_path)
        paths_to_check.append(EnvVariables.config_path.default())

        for p in paths_to_check:
            if p:
                p = os.path.expanduser(p)
            if not os.path.exists(p):
                continue

            with open(os.path.expanduser(p)) as cp:
                y = ruamel.yaml.safe_load(cp)
                JanisConfiguration._managed = JanisConfiguration(y)
                break

        if not JanisConfiguration._managed:
            JanisConfiguration._managed = JanisConfiguration()

        return JanisConfiguration._managed

    class JanisConfigurationEnvironment:
        class Keys(HashableEnum):
            Default = "default"

        def __init__(self, d: dict, default: dict):
            d = d if d else {}

            self.default = JanisConfiguration.get_value_for_key(
                d, self.Keys.Default, default
            )

    class JanisConfigurationTemplate:
        class Keys(HashableEnum):
            Id = "id"

        def __init__(self, d: dict, default: dict):
            self.id = JanisConfiguration.get_value_for_key(d, self.Keys.Id, default)

            # remove this id from the dictionary: https://stackoverflow.com/a/15411146/
            d.pop(self.Keys.Id.value, None)
            self.template = from_template(self.id, d)

    class JanisConfigurationCromwell:
        class Keys(HashableEnum):
            JarPath = "jar"
            ConfigPath = "configPath"

        def __init__(self, d: dict, default: dict):
            d = d if d else {}

            self.jarpath = JanisConfiguration.get_value_for_key(
                d, self.Keys.JarPath, default
            )
            self.configpath = JanisConfiguration.get_value_for_key(
                d, self.Keys.ConfigPath, default
            )

    class JanisConfigurationRecipes:
        class Keys(HashableEnum):
            Recipes = "recipes"
            RecipePaths = "paths"

        def __init__(self, d: dict, default: dict):
            d = d if d else {}

            self.recipes = JanisConfiguration.get_value_for_key(
                d, self.Keys.Recipes, default
            )
            rps = JanisConfiguration.get_value_for_key(
                d, self.Keys.RecipePaths, default
            )
            self.recipe_paths = rps if isinstance(rps, list) else [rps]

            self._loaded_recipes = False

        def load_recipes(self, force=False):
            if not force and (self._loaded_recipes or not self.recipe_paths):
                return

            import ruamel.yaml

            paths = []

            # Do the env first, then ones from the config can cascade over them
            from_env = EnvVariables.recipe_paths.resolve(True)
            if from_env:
                paths.extend(
                    from_env if isinstance(from_env, list) else from_env.split(",")
                )

            if self.recipe_paths:
                paths.extend(self.recipe_paths)

            for recipe_location in paths:
                try:
                    with open(recipe_location) as rl:
                        adr = ruamel.yaml.load(rl, Loader=ruamel.yaml.Loader)
                        self.recipes.update(adr)

                except Exception as e:
                    Logger.critical(f"Couldn't load recipe '{recipe_location}': {e}")

            self._loaded_recipes = True

        def get_recipe_for_key(self, key):

            self.load_recipes()

            if key is None:
                return {}
            if key in self.recipes:
                return self.recipes[key] or {}

            raise KeyError(
                f"Couldn't find recipe '{key}' in recipes, expected one of: {', '.join(self.recipes.keys())}"
            )

        def get_recipe_for_keys(self, keys: List[str]):

            self.load_recipes()

            if not keys:
                return {}

            rec = {}
            for key in keys:
                if key in self.recipes:
                    rec.update(self.recipes[key] or {})
                else:
                    Logger.critical("Couldn't find '{key}' in known recipes")

            return rec

    def __init__(self, d: dict = None):
        default = self.default()
        d = d if d else {}

        extra = "" if d is None else " from loaded config"
        Logger.log("Instantiating JanisConfiguration" + extra)

        self.configdir = self.get_value_for_key(
            d, JanisConfiguration.Keys.ConfigDir, default
        )
        self.dbpath = os.path.join(self.configdir, "janis.db")
        self.executiondir = self.get_value_for_key(
            d, JanisConfiguration.Keys.ExecutionDir, default
        )

        self.environment = JanisConfiguration.JanisConfigurationEnvironment(
            d.get(JanisConfiguration.Keys.Environment),
            default.get(JanisConfiguration.Keys.Environment),
        )

        self.engine = self.get_value_for_key(d, JanisConfiguration.Keys.Engine, default)
        self.cromwell = JanisConfiguration.JanisConfigurationCromwell(
            d.get(JanisConfiguration.Keys.Cromwell),
            default.get(JanisConfiguration.Keys.Cromwell),
        )

        self.template = JanisConfiguration.JanisConfigurationTemplate(
            d.get(JanisConfiguration.Keys.Template),
            default.get(JanisConfiguration.Keys.Template),
        )

        self.recipes = JanisConfiguration.JanisConfigurationRecipes(
            d.get(JanisConfiguration.Keys.Recipes),
            default.get(JanisConfiguration.Keys.Recipes),
        )

        sp = self.get_value_for_key(d, JanisConfiguration.Keys.SearchPaths, default)
        self.searchpaths = sp if isinstance(sp, list) else [sp]
        env_sp = EnvVariables.search_path.resolve(False)
        if env_sp and env_sp not in self.searchpaths:
            self.searchpaths.append(env_sp)

        JanisConfiguration._managed = self

    @staticmethod
    def get_value_for_key(d, key, default):
        val = d.get(key)
        if not val:
            return default.get(key) if default else None

        Logger.log(f"Got value '{val}' for key '{key}'")
        return val

    @staticmethod
    def from_path(path: Optional[str]):
        p = path or EnvVariables.config_path.resolve(True)
        if p:
            p = os.path.expanduser(p)
        if p and os.path.exists(p):
            with open(os.path.expanduser(p)) as cp:
                y = ruamel.yaml.load(cp, Loader=ruamel.yaml.Loader)
                return JanisConfiguration(y)

        return JanisConfiguration()

    @staticmethod
    def default():

        deflt = {
            JanisConfiguration.Keys.ConfigDir: EnvVariables.config_dir.resolve(True),
            JanisConfiguration.Keys.ExecutionDir: EnvVariables.exec_dir.resolve(True),
            JanisConfiguration.Keys.SearchPaths: [os.path.expanduser("~/janis/")],
            JanisConfiguration.Keys.Engine: EngineType.cromwell.value,
            JanisConfiguration.Keys.Cromwell: {
                # Resolved at runtime using "ConfigDir + cromwell-*.jar" else None, and then it's downloaded
                JanisConfiguration.JanisConfigurationCromwell.Keys.JarPath: None,
                JanisConfiguration.JanisConfigurationCromwell.Keys.ConfigPath: None,
            },
            JanisConfiguration.Keys.Template: {
                JanisConfiguration.JanisConfigurationTemplate.Keys.Id: "local"
            },
            JanisConfiguration.Keys.Recipes: {
                JanisConfiguration.JanisConfigurationRecipes.Keys.Recipes: {},
                JanisConfiguration.JanisConfigurationRecipes.Keys.RecipePaths: [],
            },
        }
        return stringify_dict_keys_or_return_value(deflt)


def stringify_dict_keys_or_return_value(d):
    if isinstance(d, list):
        return [stringify_dict_keys_or_return_value(dd) for dd in d]
    if not isinstance(d, dict):
        return d

    out = {}
    for k, v in d.items():
        out[str(k)] = stringify_dict_keys_or_return_value(v)
    return out
