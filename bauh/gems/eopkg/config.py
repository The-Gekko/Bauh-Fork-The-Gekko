from bauh.commons.config import YAMLConfigManager
from bauh.gems.eopkg import CONFIG_FILE


class EopkgConfigManager(YAMLConfigManager):

    def __init__(self):
        super(EopkgConfigManager, self).__init__(config_file_path=CONFIG_FILE)

    def get_default_config(self) -> dict:
        return {
            'search_limit': 50,
        }
