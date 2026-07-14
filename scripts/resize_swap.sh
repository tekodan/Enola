#!/bin/bash
# Script para redimensionar /swapfile de forma segura.
# Debe ejecutarse con privilegios de root (sudo).

set -e

# Tamaño deseado. Con 64GB de RAM física, 16G o 8G de swap es más que suficiente.
NEW_SIZE="16G"

if [ "$EUID" -ne 0 ]; then
  echo "Por favor, ejecuta este script usando sudo:"
  echo "  sudo bash scripts/resize_swap.sh"
  exit 1
fi

echo "=== Redimensionando /swapfile a $NEW_SIZE ==="

if swapon --show | grep -q "/swapfile"; then
  echo "1. Desactivando swap temporalmente (esto puede tardar unos momentos)..."
  swapoff /swapfile
else
  echo "1. /swapfile ya está desactivado."
fi

echo "2. Eliminando el archivo de swap anterior..."
rm -f /swapfile

echo "3. Creando nuevo /swapfile de $NEW_SIZE..."
if fallocate -l "$NEW_SIZE" /swapfile; then
  echo "   [OK] fallocate completado."
else
  echo "   [!] fallocate falló, reintentando con dd (esto puede tardar)..."
  dd if=/dev/zero of=/swapfile bs=1M count=16384 status=progress
fi

echo "4. Ajustando permisos a 0600..."
chmod 600 /swapfile

echo "5. Creando estructura de swap..."
mkswap /swapfile

echo "6. Reactivando /swapfile..."
swapon /swapfile

echo "=== ¡Listo! Estado actual de Swap ==="
swapon --show
free -h
