from config import MODULES
from config import NET_CONF as config
import os
import importlib

class ModuleLoader:    
    def load_all(self, module_refs: list) -> list:
        module_dir = MODULES['MODULE_DIR']
        mod_list = os.listdir(module_dir)
        output = []
        for mod in mod_list:
            relative_mod_path = f"{module_dir}{os.sep}{mod}"
            if os.path.isfile(os.path.abspath(relative_mod_path)) and mod.startswith("mod"):
                mod_name = mod.split(".")[0]
                if mod_name in MODULES['ENABLED']:
                    output.append(mod_name)
                    m = importlib.import_module(f"modules.{mod_name}")
                    module_refs[mod_name] = m
        return output
                