import os
from pathlib import Path

from bauh import __app_name__
from bauh.api.paths import CONFIG_DIR, TEMP_DIR, CACHE_DIR, SHARED_FILES_DIR
from bauh.commons import resource

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_SHARED_DIR = f'{SHARED_FILES_DIR}/github'
DEFAULT_REPOS_DIR = f'{Path.home()}/BauhRepos'
CONFIG_FILE = f'{CONFIG_DIR}/github.yml'
GITHUB_CACHE_DIR = f'{CACHE_DIR}/github'
DOWNLOAD_DIR = f'{TEMP_DIR}/github/download'


def get_icon_path() -> str:
    return resource.get_path('img/github.svg', ROOT_DIR)
