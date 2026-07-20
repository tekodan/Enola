#!/bin/bash
# Script para empaquetar todas tus configuraciones, credenciales y perfiles antes de la migración a NixOS.

set -e

BACKUP_DIR="/home/ronin/nixos_migration_backup"

# Limpiar respaldos previos si existen
if [ -d "$BACKUP_DIR" ]; then
  echo "[-] Eliminando directorio de respaldo previo..."
  rm -rf "$BACKUP_DIR"
fi

mkdir -p "$BACKUP_DIR"

echo "=== INICIANDO RESPALDO DE SEGURIDAD PARA NIXOS ==="

# 1. Credenciales SSH y llaves GPG
if [ -d "$HOME/.ssh" ]; then
  echo "[+] Respaldando llaves y configuraciones SSH..."
  cp -r "$HOME/.ssh" "$BACKUP_DIR/ssh"
fi

if [ -d "$HOME/.gnupg" ]; then
  echo "[+] Respaldando llaves GPG..."
  # Usamos rsync o cp con exclusión de sockets
  mkdir -p "$BACKUP_DIR/gnupg"
  find "$HOME/.gnupg" -type f -exec cp {} "$BACKUP_DIR/gnupg/" \;
fi

# 2. Historial e inicio de Zsh / Zim
echo "[+] Respaldando configuraciones de Zsh y Zim..."
mkdir -p "$BACKUP_DIR/shell"
[ -f "$HOME/.zsh_history" ] && cp "$HOME/.zsh_history" "$BACKUP_DIR/shell/"
[ -f "$HOME/.zimrc" ] && cp "$HOME/.zimrc" "$BACKUP_DIR/shell/"
[ -f "$HOME/.p10k.zsh" ] && cp "$HOME/.p10k.zsh" "$BACKUP_DIR/shell/"
[ -f "$HOME/.zsh_aliases" ] && cp "$HOME/.zsh_aliases" "$BACKUP_DIR/shell/"
[ -d "$HOME/.zim" ] && cp -r "$HOME/.zim" "$BACKUP_DIR/shell/zim"

# 3. Configuraciones de Editores y Terminales (.config)
echo "[+] Respaldando configuraciones de editores y terminales..."
mkdir -p "$BACKUP_DIR/config"
[ -d "$HOME/.config/nvim" ] && cp -r "$HOME/.config/nvim" "$BACKUP_DIR/config/"
[ -d "$HOME/.config/lazygit" ] && cp -r "$HOME/.config/lazygit" "$BACKUP_DIR/config/"
[ -d "$HOME/.config/warp-terminal" ] && cp -r "$HOME/.config/warp-terminal" "$BACKUP_DIR/config/"
[ -d "$HOME/.config/beekeeper-studio" ] && cp -r "$HOME/.config/beekeeper-studio" "$BACKUP_DIR/config/"
[ -d "$HOME/.config/opencode" ] && cp -r "$HOME/.config/opencode" "$BACKUP_DIR/config/"

# Configuración específica de VS Code
if [ -d "$HOME/.config/Code/User" ]; then
  mkdir -p "$BACKUP_DIR/config/Code/User"
  cp "$HOME/.config/Code/User/settings.json" "$BACKUP_DIR/config/Code/User/" 2>/dev/null || true
  cp "$HOME/.config/Code/User/keybindings.json" "$BACKUP_DIR/config/Code/User/" 2>/dev/null || true
fi

# Extensiones de VS Code
if [ -d "$HOME/.vscode/extensions" ]; then
  echo "[+] Respaldando extensiones de VS Code..."
  mkdir -p "$BACKUP_DIR/vscode"
  cp -r "$HOME/.vscode/extensions" "$BACKUP_DIR/vscode/"
fi

# 4. LM Studio
if [ -d "$HOME/.lmstudio" ]; then
  echo "[+] Respaldando configuraciones de LM Studio (excluyendo modelos pesados)..."
  mkdir -p "$BACKUP_DIR/lmstudio"
  # Respaldar archivos de configuración pero omitir binarios/modelos internos
  find "$HOME/.lmstudio" -maxdepth 2 -type f -exec cp {} "$BACKUP_DIR/lmstudio/" \;
fi

# 5. Scripts personales y utilidades de automatización
echo "[+] Respaldando scripts de usuario..."
[ -d "$HOME/scripts" ] && cp -r "$HOME/scripts" "$BACKUP_DIR/scripts"
[ -d "$HOME/Documents/scripts" ] && mkdir -p "$BACKUP_DIR/documents" && cp -r "$HOME/Documents/scripts" "$BACKUP_DIR/documents/"
[ -f "$HOME/Downloads/organize-downloads.sh" ] && mkdir -p "$BACKUP_DIR/downloads" && cp "$HOME/Downloads/organize-downloads.sh" "$BACKUP_DIR/downloads/"

echo "=================================================="
echo "¡Listo! Todo tu entorno de usuario ha sido copiado a:"
echo "  $BACKUP_DIR"
echo "Mueve esa carpeta a un disco USB o partición externa."
echo "Para restaurar en NixOS, consulta la guía definitiva."
echo "=================================================="
