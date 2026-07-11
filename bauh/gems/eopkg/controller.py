import os
import re
import shutil
import subprocess
from typing import Set, Type, List, Tuple, Optional, Generator

from bauh.api.abstract.context import ApplicationContext
from bauh.api.abstract.controller import SoftwareManager, SearchResult, TransactionResult, \
    SoftwareAction, SettingsView, SettingsController, UpgradeRequirements, UpgradeRequirement
from bauh.api.abstract.disk import DiskCacheLoader
from bauh.api.abstract.handler import ProcessWatcher, TaskManager
from bauh.api.abstract.model import SoftwarePackage, PackageHistory, PackageUpdate
from bauh.api.abstract.view import MessageType
from bauh.commons.html import bold
from bauh.commons.system import SimpleProcess, ProcessHandler
from bauh.gems.eopkg.config import EopkgConfigManager
from bauh.gems.eopkg.model import EopkgPackage


class EopkgManager(SoftwareManager, SettingsController):

    def __init__(self, context: ApplicationContext):
        super(EopkgManager, self).__init__(context=context)
        self.i18n = context.i18n
        self.logger = context.logger
        self.enabled = True
        self.configman = EopkgConfigManager()

    def _execute_eopkg(self, args: List[str]) -> Tuple[bool, str]:
        """Executes an eopkg command and returns (success, output)."""
        cmd = ['eopkg'] + args + ['-N']
        try:
            env = os.environ.copy()
            env['LANG'] = 'en_US.UTF-8'
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env
            )
            # Remove ANSI color escape sequences
            clean_output = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', result.stdout)
            return result.returncode == 0, clean_output
        except Exception:
            return False, ""

    def search(self, words: str, disk_loader: Optional[DiskCacheLoader] = None,
               limit: int = -1, is_url: bool = False) -> SearchResult:
        self.logger.info(f"eopkg searching for: {words}")
        
        success, output = self._execute_eopkg(['search', words])
        installed_pkgs = []
        new_pkgs = []

        if success and output:
            lines = output.strip().split('\n')
            for line in lines:
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ''
                    
                    # We can't determine version/installed easily from just search output
                    # So we create a basic package
                    pkg = EopkgPackage(name=name, description=desc)
                    # For a real integration, we might want to cross-reference with list-installed
                    new_pkgs.append(pkg)

        # Cross reference to see if they are installed
        installed_res = self.read_installed()
        installed_names = {p.name for p in installed_res.installed}
        
        final_installed = []
        final_new = []
        for pkg in new_pkgs:
            if pkg.name in installed_names:
                pkg.installed = True
                final_installed.append(pkg)
            else:
                final_new.append(pkg)

        return SearchResult(installed=final_installed, new=final_new, total=len(final_installed) + len(final_new))

    def read_installed(self, disk_loader: Optional[DiskCacheLoader] = None, limit: int = -1,
                       only_apps: bool = False, pkg_types: Optional[Set[Type[SoftwarePackage]]] = None,
                       internet_available: bool = True) -> SearchResult:
        installed = []
        success, output = self._execute_eopkg(['list-installed'])
        
        if success and output:
            lines = output.strip().split('\n')
            for line in lines:
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ''
                    pkg = EopkgPackage(name=name, description=desc, installed=True)
                    installed.append(pkg)

        return SearchResult(installed=installed, new=None, total=len(installed))

    def install(self, pkg: EopkgPackage, root_password: Optional[str],
                disk_loader: Optional[DiskCacheLoader], watcher: ProcessWatcher) -> TransactionResult:
        handler = ProcessHandler(watcher)
        
        watcher.change_substatus(self.i18n.get('eopkg.installing', 'Instalando {}...').format(bold(pkg.name)))
        
        success, output = handler.handle_simple(
            SimpleProcess(['eopkg', 'install', '-y', '-N', pkg.name], root_password=root_password)
        )
        
        if success:
            pkg.installed = True
            return TransactionResult(success=True, installed=[pkg], removed=[])
        else:
            watcher.show_message(
                title=self.i18n.get('error', 'Error'),
                body=self.i18n.get('eopkg.install_error', 'Error al instalar {}.').format(bold(pkg.name)),
                type_=MessageType.ERROR
            )
            return TransactionResult.fail()

    def uninstall(self, pkg: EopkgPackage, root_password: Optional[str],
                  watcher: ProcessWatcher, disk_loader: Optional[DiskCacheLoader] = None) -> TransactionResult:
        handler = ProcessHandler(watcher)
        
        watcher.change_substatus(self.i18n.get('eopkg.removing', 'Desinstalando {}...').format(bold(pkg.name)))
        
        success, output = handler.handle_simple(
            SimpleProcess(['eopkg', 'remove', '-y', '-N', pkg.name], root_password=root_password)
        )
        
        if success:
            pkg.installed = False
            return TransactionResult(success=True, installed=[], removed=[pkg])
        else:
            watcher.show_message(
                title=self.i18n.get('error', 'Error'),
                body=self.i18n.get('eopkg.remove_error', 'Error al desinstalar {}.').format(bold(pkg.name)),
                type_=MessageType.ERROR
            )
            return TransactionResult.fail()

    def downgrade(self, pkg: SoftwarePackage, root_password: Optional[str],
                  handler: ProcessWatcher) -> bool:
        return False

    def upgrade(self, requirements: UpgradeRequirements, root_password: Optional[str],
                watcher: ProcessWatcher) -> bool:
        handler = ProcessHandler(watcher)
        success = True
        for req in (requirements.to_upgrade or []):
            pkg = req.pkg
            if isinstance(pkg, EopkgPackage):
                watcher.change_substatus(self.i18n.get('eopkg.upgrading', 'Actualizando {}...').format(bold(pkg.name)))
                res, _ = handler.handle_simple(
                    SimpleProcess(['eopkg', 'upgrade', '-y', '-N', pkg.name], root_password=root_password)
                )
                if not res:
                    success = False
        return success

    def get_managed_types(self) -> Set[Type[SoftwarePackage]]:
        return {EopkgPackage}

    def get_info(self, pkg: EopkgPackage) -> dict:
        info = {
            self.i18n.get('name', 'Name'): pkg.name,
            self.i18n.get('description', 'Description'): pkg.description or '—',
        }
        
        success, output = self._execute_eopkg(['info', pkg.name])
        if success and output:
            for line in output.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    info[key.strip()] = val.strip()
                    
        return info

    def get_history(self, pkg: SoftwarePackage) -> PackageHistory:
        return PackageHistory(pkg=pkg, history=[], pkg_status_idx=-1)

    def is_enabled(self) -> bool:
        return self.enabled

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def can_work(self) -> Tuple[bool, Optional[str]]:
        if not shutil.which('eopkg'):
            return False, self.i18n.get('eopkg.requires_eopkg',
                                         'El comando eopkg no está disponible en este sistema.')
        return True, None

    def requires_root(self, action: SoftwareAction, pkg: Optional[SoftwarePackage] = None) -> bool:
        # eopkg install, remove, and upgrade always require root privileges
        return action in (SoftwareAction.INSTALL, SoftwareAction.UNINSTALL, SoftwareAction.UPGRADE)

    def prepare(self, task_manager: Optional[TaskManager], root_password: Optional[str],
                internet_available: Optional[bool]):
        pass

    def list_updates(self, internet_available: bool) -> List[PackageUpdate]:
        updates = []
        if not internet_available:
            return updates

        success, output = self._execute_eopkg(['list-upgrades'])
        if success and output:
            for line in output.strip().split('\n'):
                line = line.strip()
                if not line or ':' in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    # Make sure it looks like a valid package name
                    if re.match(r'^[a-zA-Z0-9\-\+\._]+$', name):
                        version = parts[1]
                        updates.append(PackageUpdate(pkg_id=name, version=version, pkg_type='eopkg', name=name))
        return updates

    def list_warnings(self, internet_available: bool) -> Optional[List[str]]:
        return None

    def is_default_enabled(self) -> bool:
        return True

    def launch(self, pkg: SoftwarePackage):
        pass

    def get_screenshots(self, pkg: SoftwarePackage) -> Generator[str, None, None]:
        yield from ()

    def get_settings(self) -> Optional[Generator[SettingsView, None, None]]:
        return None
