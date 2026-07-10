import os
from enum import Enum
from typing import Optional, Tuple


class BuildMethod(Enum):
    PKGBUILD = 'PKGBUILD'
    MAKEFILE = 'Makefile'
    INSTALL_SCRIPT = 'install.sh'
    PYTHON_SETUP = 'Python (pip)'
    CARGO = 'Cargo (Rust)'
    MESON = 'Meson'
    CMAKE = 'CMake'
    UNKNOWN = 'Desconocido'


# Maps build methods to the commands required to build and install.
# Unsafe methods (that require sudo make install without pacman) are set to None.
BUILD_COMMANDS = {
    BuildMethod.PKGBUILD: ('makepkg -si --noconfirm', True),
    BuildMethod.MAKEFILE: (None, False),
    BuildMethod.INSTALL_SCRIPT: (None, False),
    BuildMethod.PYTHON_SETUP: ('pip install --user .', False),
    BuildMethod.CARGO: ('cargo build --release && cargo install --path .', False),
    BuildMethod.MESON: (None, False),
    BuildMethod.CMAKE: (None, False),
}

# Only these methods are safe to auto-build without risking system stability
SAFE_METHODS = {BuildMethod.PKGBUILD, BuildMethod.PYTHON_SETUP, BuildMethod.CARGO}

# Maps build methods to their uninstall commands (if applicable)
UNINSTALL_COMMANDS = {
    BuildMethod.PKGBUILD: None,  # pacman -R handles this
    BuildMethod.MAKEFILE: 'sudo make uninstall',
    BuildMethod.INSTALL_SCRIPT: None,
    BuildMethod.PYTHON_SETUP: None,  # pip uninstall <name>
    BuildMethod.CARGO: 'cargo uninstall',
    BuildMethod.MESON: 'sudo ninja -C build uninstall',
    BuildMethod.CMAKE: None,
}


def detect_build_method(repo_path: str) -> Tuple[BuildMethod, Optional[str]]:
    """
    Analyzes the root directory of a cloned repository and returns the detected
    build method along with the command string to execute.

    Returns a tuple of (BuildMethod, command_string or None).
    """
    if not os.path.isdir(repo_path):
        return BuildMethod.UNKNOWN, None

    root_files = set(os.listdir(repo_path))

    # Priority order: PKGBUILD is the best for Arch Linux
    if 'PKGBUILD' in root_files:
        return BuildMethod.PKGBUILD, BUILD_COMMANDS[BuildMethod.PKGBUILD][0]

    if 'Makefile' in root_files or 'makefile' in root_files or 'GNUmakefile' in root_files:
        return BuildMethod.MAKEFILE, BUILD_COMMANDS[BuildMethod.MAKEFILE][0]

    if 'install.sh' in root_files or 'setup.sh' in root_files:
        return BuildMethod.INSTALL_SCRIPT, BUILD_COMMANDS[BuildMethod.INSTALL_SCRIPT][0]

    if 'setup.py' in root_files or 'pyproject.toml' in root_files:
        return BuildMethod.PYTHON_SETUP, BUILD_COMMANDS[BuildMethod.PYTHON_SETUP][0]

    if 'Cargo.toml' in root_files:
        return BuildMethod.CARGO, BUILD_COMMANDS[BuildMethod.CARGO][0]

    if 'meson.build' in root_files:
        return BuildMethod.MESON, BUILD_COMMANDS[BuildMethod.MESON][0]

    if 'CMakeLists.txt' in root_files:
        return BuildMethod.CMAKE, BUILD_COMMANDS[BuildMethod.CMAKE][0]

    return BuildMethod.UNKNOWN, None


def requires_root(method: BuildMethod) -> bool:
    """Returns True if the build method requires root/sudo to install."""
    if method in BUILD_COMMANDS:
        return BUILD_COMMANDS[method][1]
    return False
