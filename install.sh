#!/usr/bin/env bash

set -e

# Cambiar al directorio donde está el script para que pipx encuentre pyproject.toml/setup.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# Colores para la interfaz
GREEN="\e[32m"
BLUE="\e[34m"
YELLOW="\e[33m"
RED="\e[31m"
BOLD="\e[1m"
RESET="\e[0m"

echo -e "${BLUE}${BOLD}==========================================================${RESET}"
echo -e "${GREEN}${BOLD}    Bauh - The Ultimate Linux App Manager                 ${RESET}"
echo -e "${YELLOW}${BOLD}    Fork Modernizado por The-Gekko 🦎𓆈                 ${RESET}"
echo -e "${BLUE}${BOLD}==========================================================${RESET}\n"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] Python 3 is required but not found.${RESET}"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[+] Detected Python version: ${PY_VERSION}${RESET}"

# Verificar si tiene habilitado Chaotic AUR
if [ -f /etc/pacman.conf ]; then
    if ! grep -qi "chaotic-aur" /etc/pacman.conf; then
        echo -e "${YELLOW}[!] ADVERTENCIA: No se encontró el repositorio [chaotic-aur] en /etc/pacman.conf.${RESET}"
        echo -e "${YELLOW}[!] Este fork está diseñado y optimizado específicamente para trabajar con Chaotic AUR.${RESET}"
        read -p "    ¿Deseas continuar con la instalación de todos modos? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}[*] Instalación abortada por el usuario.${RESET}"
            exit 1
        fi
    else
        echo -e "${GREEN}[+] Repositorio Chaotic AUR detectado en el sistema.${RESET}"
    fi
fi

# Ensure pipx is installed
if ! command -v pipx &> /dev/null; then
    echo -e "${YELLOW}[*] pipx no está instalado. pipx es necesario para aislar las dependencias de forma segura.${RESET}"
    echo -e "${YELLOW}[*] Intentando instalar pipx automáticamente...${RESET}"
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y pipx
    elif command -v pacman &> /dev/null; then
        # En Arch Linux el paquete se llama python-pipx
        sudo pacman -S --noconfirm python-pipx
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y pipx
    else
        echo -e "${RED}[!] Gestor de paquetes no soportado automáticamente. Por favor instala 'pipx' manualmente y vuelve a ejecutar este script.${RESET}"
        exit 1
    fi
    pipx ensurepath
fi

if command -v ~/.local/bin/bauh &> /dev/null || command -v bauh &> /dev/null; then
    echo -e "${YELLOW}[?] Bauh ya parece estar instalado en tu sistema.${RESET}"
    read -p "    ¿Deseas actualizarlo/reinstalarlo con los nuevos cambios? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}[*] Instalación cancelada. ¡Disfruta de Bauh!${RESET}"
        exit 0
    fi
    echo -e "${BLUE}[+] Actualizando Bauh a través de pipx...${RESET}"
else
    echo -e "${BLUE}[+] Instalando Bauh a través de pipx...${RESET}"
fi

pipx install --force .

echo -e "${BLUE}[+] Copiando icono de la aplicación...${RESET}"
mkdir -p ~/.local/share/icons/hicolor/scalable/apps/
cp "$SCRIPT_DIR/bauh/view/resources/img/logo.svg" ~/.local/share/icons/hicolor/scalable/apps/bauh.svg
cp "$SCRIPT_DIR/bauh/view/resources/img/logo.svg" ~/.local/share/icons/bauh.svg

echo -e "${BLUE}[+] Creando acceso directo en el escritorio (Desktop Entry)...${RESET}"
mkdir -p ~/.local/share/applications/
cat <<EOF > ~/.local/share/applications/bauh.desktop
[Desktop Entry]
Name=Bauh Fork The-Gekko
Comment=Manage your Linux applications
Exec=$HOME/.local/bin/bauh
Icon=bauh
Terminal=false
Type=Application
Categories=System;Settings;PackageManager;
EOF

# Actualizar base de datos de escritorios e iconos para Gnome
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database ~/.local/share/applications/
fi
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t ~/.local/share/icons/ &> /dev/null || true
fi


echo -e "\n${GREEN}${BOLD}==========================================================${RESET}"
echo -e "${GREEN}${BOLD}    ¡Instalación Completada con Éxito! 🚀                 ${RESET}"
echo -e "${GREEN}${BOLD}==========================================================${RESET}"
echo -e "${YELLOW}Nota:${RESET} Ahora puedes ejecutar Bauh desde el menú de aplicaciones de tu sistema."
echo -e "O simplemente escribiendo ${BOLD}'bauh'${RESET} en tu terminal."
echo -e "Si el comando 'bauh' no se encuentra, es posible que necesites reiniciar tu terminal.\n"
