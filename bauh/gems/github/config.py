from bauh.commons.config import YAMLConfigManager
from bauh.gems.github import CONFIG_FILE, DEFAULT_REPOS_DIR


class GitHubConfigManager(YAMLConfigManager):

    def __init__(self):
        super(GitHubConfigManager, self).__init__(config_file_path=CONFIG_FILE)

    def get_default_config(self) -> dict:
        return {
            'repos_dir': DEFAULT_REPOS_DIR,
            'clone_only': False,
        }
