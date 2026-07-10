import json
import os
import re
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Set, Type, List, Tuple, Optional, Generator

from bauh.api.abstract.context import ApplicationContext
from bauh.api.abstract.controller import SoftwareManager, SearchResult, TransactionResult, \
    SoftwareAction, SettingsView, SettingsController, UpgradeRequirements, UpgradeRequirement
from bauh.api.abstract.disk import DiskCacheLoader
from bauh.api.abstract.handler import ProcessWatcher, TaskManager
from bauh.api.abstract.model import SoftwarePackage, PackageHistory, PackageUpdate, PackageSuggestion, \
    CustomSoftwareAction
from bauh.api.abstract.view import MessageType, FormComponent, SingleSelectComponent, \
    TextInputComponent, PanelComponent, FileChooserComponent
from bauh.commons import resource
from bauh.commons.html import bold
from bauh.commons.system import SystemProcess, new_subprocess, ProcessHandler, SimpleProcess
from bauh.gems.github import ROOT_DIR, DEFAULT_REPOS_DIR, get_icon_path
from bauh.gems.github.build_detector import detect_build_method, BuildMethod, requires_root as build_requires_root
from bauh.gems.github.config import GitHubConfigManager
from bauh.gems.github.model import GitHubPackage

RE_GITHUB_URL = re.compile(r'https?://github\.com/([^/]+)/([^/\s#?]+)/?.*')


class GitHubManager(SoftwareManager, SettingsController):

    def __init__(self, context: ApplicationContext):
        super(GitHubManager, self).__init__(context=context)
        self.i18n = context.i18n
        self.http_client = context.http_client
        self.logger = context.logger
        self.enabled = True
        self.configman = GitHubConfigManager()

    def _get_repos_dir(self) -> str:
        config = self.configman.get_config()
        repos_dir = config.get('repos_dir', DEFAULT_REPOS_DIR)
        return os.path.expanduser(repos_dir)

    def _is_clone_only(self) -> bool:
        config = self.configman.get_config()
        return bool(config.get('clone_only', False))

    def _parse_github_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Parses a GitHub URL and returns (owner, repo_name) or None."""
        match = RE_GITHUB_URL.match(url.strip())
        if match:
            owner = match.group(1)
            repo = match.group(2)
            # Remove .git suffix if present
            if repo.endswith('.git'):
                repo = repo[:-4]
            return owner, repo
        return None

    def _fetch_repo_info(self, owner: str, repo_name: str) -> Optional[dict]:
        """Fetches repository info from the GitHub API."""
        try:
            url = f'https://api.github.com/repos/{owner}/{repo_name}'
            resp = self.http_client.get(url)
            if resp and resp.status_code == 200:
                return resp.json()
        except Exception:
            self.logger.error(f"Failed to fetch GitHub repo info for {owner}/{repo_name}")
            import logging; logging.error("Exception occurred", exc_info=True)
        return None

    def _search_github_api(self, query: str, limit: int = 20) -> List[dict]:
        """Searches the GitHub API for repositories matching a query."""
        try:
            url = f'https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={limit}'
            resp = self.http_client.get(url)
            if resp and resp.status_code == 200:
                data = resp.json()
                return data.get('items', [])
        except Exception:
            self.logger.error(f"GitHub API search failed for query: {query}")
            import logging; logging.error("Exception occurred", exc_info=True)
        return []

    def _api_to_package(self, api_data: dict, installed: bool = False, clone_path: str = None) -> GitHubPackage:
        """Converts a GitHub API response dict into a GitHubPackage."""
        owner = api_data.get('owner', {}).get('login', '')
        repo_name = api_data.get('name', '')
        return GitHubPackage(
            name=repo_name,
            description=api_data.get('description') or self.i18n.get('github.no_description', 'Sin descripción'),
            version=api_data.get('default_branch', 'main'),
            repo_url=api_data.get('html_url', f'https://github.com/{owner}/{repo_name}'),
            owner=owner,
            repo_name=repo_name,
            stars=api_data.get('stargazers_count', 0),
            clone_path=clone_path,
            cloned=installed,
            installed=installed,
            license=api_data.get('license', {}).get('spdx_id') if api_data.get('license') else None,
            default_branch=api_data.get('default_branch', 'main'),
            language=api_data.get('language'),
        )

    def search(self, words: str, disk_loader: Optional[DiskCacheLoader] = None,
               limit: int = -1, is_url: bool = False) -> SearchResult:
        self.logger.info(f"GitHub gem searching for: {words}")

        installed_pkgs = []
        new_pkgs = []

        # Check if the search is a GitHub URL
        parsed = self._parse_github_url(words)
        if parsed:
            owner, repo_name = parsed
            api_data = self._fetch_repo_info(owner, repo_name)

            if api_data:
                repos_dir = self._get_repos_dir()
                clone_path = f'{repos_dir}/{repo_name}'
                is_cloned = os.path.isdir(clone_path)

                pkg = self._api_to_package(api_data, installed=is_cloned, clone_path=clone_path)

                if is_cloned:
                    method, _ = detect_build_method(clone_path)
                    pkg.build_method = method.value
                    installed_pkgs.append(pkg)
                else:
                    new_pkgs.append(pkg)

            return SearchResult(installed=installed_pkgs, new=new_pkgs, total=len(installed_pkgs) + len(new_pkgs))

        # Regular text search via GitHub API
        search_limit = limit if limit > 0 else 20
        api_results = self._search_github_api(words, search_limit)

        repos_dir = self._get_repos_dir()
        for item in api_results:
            repo_name = item.get('name', '')
            clone_path = f'{repos_dir}/{repo_name}'
            is_cloned = os.path.isdir(clone_path)
            pkg = self._api_to_package(item, installed=is_cloned, clone_path=clone_path)

            if is_cloned:
                method, _ = detect_build_method(clone_path)
                pkg.build_method = method.value
                installed_pkgs.append(pkg)
            else:
                new_pkgs.append(pkg)

        return SearchResult(installed=installed_pkgs, new=new_pkgs, total=len(installed_pkgs) + len(new_pkgs))

    def read_installed(self, disk_loader: Optional[DiskCacheLoader] = None, limit: int = -1,
                       only_apps: bool = False, pkg_types: Optional[Set[Type[SoftwarePackage]]] = None,
                       internet_available: bool = True) -> SearchResult:
        """Scans the repos directory for cloned repositories."""
        installed = []
        repos_dir = self._get_repos_dir()

        if os.path.isdir(repos_dir):
            for entry in os.scandir(repos_dir):
                if entry.is_dir() and not entry.name.startswith('.'):
                    # Check if it's actually a git repository
                    git_dir = os.path.join(entry.path, '.git')
                    if os.path.isdir(git_dir):
                        # Try to read the remote URL
                        repo_url = self._get_remote_url(entry.path)
                        owner, repo_name = '', entry.name
                        if repo_url:
                            parsed = self._parse_github_url(repo_url)
                            if parsed:
                                owner, repo_name = parsed

                        method, _ = detect_build_method(entry.path)

                        pkg = GitHubPackage(
                            name=repo_name,
                            description=f'Repositorio clonado: {owner}/{repo_name}',
                            version=self._get_current_branch(entry.path),
                            repo_url=repo_url or f'https://github.com/{owner}/{repo_name}',
                            owner=owner,
                            repo_name=repo_name,
                            clone_path=entry.path,
                            cloned=True,
                            installed=True,
                            build_method=method.value,
                        )
                        installed.append(pkg)

        return SearchResult(installed=installed, new=None, total=len(installed))

    def _get_remote_url(self, repo_path: str) -> Optional[str]:
        """Gets the remote origin URL from a git repo."""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=repo_path, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Convert SSH URLs to HTTPS
                if url.startswith('git@github.com:'):
                    url = url.replace('git@github.com:', 'https://github.com/')
                    if url.endswith('.git'):
                        url = url[:-4]
                return url
        except Exception:
            pass
        return None

    def _get_current_branch(self, repo_path: str) -> str:
        """Gets the current branch of a git repo."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_path, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return 'unknown'

    def install(self, pkg: GitHubPackage, root_password: Optional[str],
                disk_loader: Optional[DiskCacheLoader], watcher: ProcessWatcher) -> TransactionResult:
        handler = ProcessHandler(watcher)
        repos_dir = self._get_repos_dir()
        Path(repos_dir).mkdir(parents=True, exist_ok=True)

        clone_path = f'{repos_dir}/{pkg.repo_name}'
        pkg.clone_path = clone_path

        # Step 1: Clone the repository
        watcher.change_substatus(self.i18n.get('github.cloning', 'Clonando repositorio: {}').format(bold(pkg.repo_url)))

        if os.path.isdir(clone_path):
            # Already cloned, pull updates instead
            self.logger.info(f"Repository already exists at {clone_path}, pulling updates")
            success, output = handler.handle_simple(
                SimpleProcess(['git', 'pull'], cwd=clone_path)
            )
        else:
            success, output = handler.handle_simple(
                SimpleProcess(['git', 'clone', pkg.repo_url, clone_path])
            )

        if not success:
            watcher.show_message(
                title=self.i18n.get('github.clone_error', 'Error al clonar'),
                body=self.i18n.get('github.clone_error.body',
                                    'No se pudo clonar el repositorio {}. Verifica la URL y tu conexión a internet.').format(
                    bold(pkg.repo_url)),
                type_=MessageType.ERROR
            )
            return TransactionResult.fail()

        pkg.cloned = True

        # Step 2: Detect build method
        method, build_cmd = detect_build_method(clone_path)
        pkg.build_method = method.value

        watcher.change_substatus(
            self.i18n.get('github.build_detected', 'Método de build detectado: {}').format(bold(method.value))
        )

        # Step 3: If clone_only mode, stop here
        if self._is_clone_only():
            self.logger.info(f"Clone-only mode: skipping build for {pkg.repo_name}")
            watcher.change_substatus(
                self.i18n.get('github.clone_only_done', 'Repositorio clonado exitosamente (modo solo clonar)')
            )
            return TransactionResult(success=True, installed=[pkg], removed=[])

        from bauh.gems.github.build_detector import SAFE_METHODS

        # Step 4: Build and install if a method was detected
        if method == BuildMethod.UNKNOWN or method not in SAFE_METHODS:
            watcher.show_message(
                title=self.i18n.get('github.unsafe_build', 'Instalación manual requerida'),
                body=self.i18n.get('github.unsafe_build.body',
                                    'El repositorio usa {}. Por seguridad, Bauh solo instala automáticamente repositorios con PKGBUILD, Python o Cargo. '
                                    'El repositorio ha sido clonado en {}. '
                                    'Por favor, instala las dependencias manualmente y compílalo bajo tu propio riesgo.').format(
                    bold(method.value), bold(clone_path)),
                type_=MessageType.WARNING
            )
            return TransactionResult(success=True, installed=[pkg], removed=[])

        watcher.change_substatus(
            self.i18n.get('github.building', 'Construyendo {} con {}...').format(
                bold(pkg.repo_name), bold(method.value))
        )

        # Execute the build command
        build_success, build_output = handler.handle_simple(
            SimpleProcess(['bash', '-c', build_cmd], cwd=clone_path, root_password=root_password)
        )

        if not build_success:
            watcher.show_message(
                title=self.i18n.get('github.build_error', 'Error de construcción'),
                body=self.i18n.get('github.build_error.body',
                                    'Falló la construcción de {}. El repositorio sigue clonado en {}.\n\n'
                                    'Detalles del error:\n{}').format(
                    bold(pkg.repo_name), bold(clone_path), build_output),
                type_=MessageType.ERROR
            )
            return TransactionResult(success=True, installed=[pkg], removed=[])

        pkg.built = True
        self.logger.info(f"Successfully built and installed {pkg.repo_name}")

        return TransactionResult(success=True, installed=[pkg], removed=[])

    def uninstall(self, pkg: GitHubPackage, root_password: Optional[str],
                  watcher: ProcessWatcher, disk_loader: Optional[DiskCacheLoader] = None) -> TransactionResult:
        handler = ProcessHandler(watcher)

        if pkg.clone_path and os.path.isdir(pkg.clone_path):
            watcher.change_substatus(
                self.i18n.get('github.removing', 'Eliminando repositorio: {}').format(bold(pkg.repo_name or pkg.name))
            )
            try:
                shutil.rmtree(pkg.clone_path)
                self.logger.info(f"Removed cloned repository: {pkg.clone_path}")
            except Exception:
                watcher.show_message(
                    title=self.i18n.get('error', 'Error'),
                    body=self.i18n.get('github.remove_error',
                                        'No se pudo eliminar la carpeta {}').format(bold(pkg.clone_path)),
                    type_=MessageType.ERROR
                )
                return TransactionResult.fail()

        return TransactionResult(success=True, installed=[], removed=[pkg])

    def downgrade(self, pkg: SoftwarePackage, root_password: Optional[str],
                  handler: ProcessWatcher) -> bool:
        return False

    def upgrade(self, requirements: UpgradeRequirements, root_password: Optional[str],
                watcher: ProcessWatcher) -> bool:
        """Pulls latest changes for each repo."""
        handler = ProcessHandler(watcher)
        for req in (requirements.to_upgrade or []):
            pkg = req.pkg
            if isinstance(pkg, GitHubPackage) and pkg.clone_path and os.path.isdir(pkg.clone_path):
                watcher.change_substatus(
                    self.i18n.get('github.pulling', 'Actualizando {}...').format(bold(pkg.repo_name))
                )
                handler.handle_simple(SimpleProcess(['git', 'pull'], cwd=pkg.clone_path))
        return True

    def get_managed_types(self) -> Set[Type[SoftwarePackage]]:
        return {GitHubPackage}

    def get_info(self, pkg: GitHubPackage) -> dict:
        info = {
            self.i18n.get('github.info.name', 'Nombre'): pkg.name,
            self.i18n.get('github.info.owner', 'Propietario'): pkg.owner or '—',
            self.i18n.get('github.info.url', 'URL'): pkg.repo_url or '—',
            self.i18n.get('github.info.stars', 'Estrellas'): str(pkg.stars) if pkg.stars else '—',
            self.i18n.get('github.info.language', 'Lenguaje'): pkg.language or '—',
            self.i18n.get('github.info.license', 'Licencia'): pkg.license or '—',
            self.i18n.get('github.info.branch', 'Rama'): pkg.version or pkg.default_branch or '—',
            self.i18n.get('github.info.build', 'Método de Build'): pkg.build_method or '—',
            self.i18n.get('github.info.cloned', 'Clonado'): self.i18n.get('yes', 'Sí') if pkg.cloned else self.i18n.get('no', 'No'),
            self.i18n.get('github.info.built', 'Construido'): self.i18n.get('yes', 'Sí') if pkg.built else self.i18n.get('no', 'No'),
            self.i18n.get('github.info.path', 'Ruta Local'): pkg.clone_path or '—',
        }
        return info

    def get_history(self, pkg: SoftwarePackage) -> PackageHistory:
        return PackageHistory(pkg=pkg, history=[], pkg_status_idx=-1)

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def can_work(self) -> Tuple[bool, Optional[str]]:
        if not shutil.which('git'):
            return False, self.i18n.get('github.requires_git',
                                         'Se requiere git para utilizar este módulo. Instálalo con: sudo pacman -S git')
        return True, None

    def requires_root(self, action: SoftwareAction, pkg: Optional[SoftwarePackage] = None) -> bool:
        if action == SoftwareAction.INSTALL and isinstance(pkg, GitHubPackage):
            if pkg.clone_path and os.path.isdir(pkg.clone_path):
                method, _ = detect_build_method(pkg.clone_path)
                return build_requires_root(method)
        return False

    def prepare(self, task_manager: Optional[TaskManager], root_password: Optional[str],
                internet_available: Optional[bool]):
        repos_dir = self._get_repos_dir()
        Path(repos_dir).mkdir(parents=True, exist_ok=True)

        # Check if gh CLI is available (optional, for enhanced features)
        if shutil.which('gh'):
            self.logger.info("GitHub CLI (gh) detected. Enhanced GitHub features available.")
        else:
            self.logger.info("GitHub CLI (gh) not found. Using basic git for cloning.")

    def list_updates(self, internet_available: bool) -> List[PackageUpdate]:
        return []

    def list_warnings(self, internet_available: bool) -> Optional[List[str]]:
        if not internet_available:
            return [self.i18n.get('github.no_internet', 'Se requiere internet para buscar repositorios en GitHub')]
        return None

    def is_default_enabled(self) -> bool:
        return True

    def launch(self, pkg: SoftwarePackage):
        # Open the clone directory in the file manager
        if isinstance(pkg, GitHubPackage) and pkg.clone_path and os.path.isdir(pkg.clone_path):
            subprocess.Popen(['xdg-open', pkg.clone_path])

    def get_screenshots(self, pkg: SoftwarePackage) -> Generator[str, None, None]:
        yield from ()

    def get_settings(self) -> Optional[Generator[SettingsView, None, None]]:
        return None
