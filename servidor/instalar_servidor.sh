#!/usr/bin/env bash
# El Bot Sincero — instalación en un servidor Ubuntu (Oracle Cloud Always Free).
# Uso (en el servidor):  bash instalar_servidor.sh
set -euo pipefail

REPO="dasnam075-cpu/elbotsincero"
DIR="$HOME/elbotsincero"
ENVF="$HOME/.elbot.env"

echo "== 1/6 Probando si Binance acepta conexiones desde este servidor =="
code=$(curl -s -o /dev/null -w "%{http_code}" https://api.binance.com/api/v3/time || true)
echo "Respuesta de Binance: $code"
if [ "$code" != "200" ]; then
  echo "❌ Binance rechaza este servidor (código $code). No sigas: avisa a Claude."
  exit 1
fi
echo "✅ Binance responde desde aquí."

echo "== 2/6 Instalando Python y Git =="
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv git cron >/dev/null

echo "== 3/6 Datos privados (no se muestran en pantalla) =="
read -rsp "Pega tu BINANCE_API_KEY y presiona Enter: " BK; echo
read -rsp "Pega tu BINANCE_API_SECRET y presiona Enter: " BS; echo
read -rsp "Pega tu token de GitHub (para guardar el registro) y presiona Enter: " GT; echo
umask 077
cat > "$ENVF" <<EOF
BINANCE_API_KEY=$BK
BINANCE_API_SECRET=$BS
PRESUPUESTO_MAX=100
EOF
chmod 600 "$ENVF"

echo "== 4/6 Descargando el bot desde GitHub =="
rm -rf "$DIR"
git clone -q "https://x-access-token:${GT}@github.com/${REPO}.git" "$DIR"
git -C "$DIR" config user.name "elbotsincero-bot"
git -C "$DIR" config user.email "elbotsincero-bot@users.noreply.github.com"
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"

echo "== 5/6 Prueba en modo seguro (no envía órdenes) =="
( set -a; . "$ENVF"; set +a; cd "$DIR"; DRY_RUN=1 .venv/bin/python bot.py )
git -C "$DIR" checkout -q -- registro 2>/dev/null || true
git -C "$DIR" clean -qfd registro 2>/dev/null || true

echo "== 6/6 Programando la ejecución diaria (00:07 UTC = 19:07 Lima) =="
cp "$DIR/servidor/ejecutar_diario.sh" "$HOME/ejecutar_diario.sh"
chmod +x "$HOME/ejecutar_diario.sh"
( crontab -l 2>/dev/null | grep -v ejecutar_diario.sh; echo "7 0 * * * $HOME/ejecutar_diario.sh" ) | crontab -
sudo timedatectl set-timezone UTC 2>/dev/null || true

echo
echo "✅ Listo. El bot correrá solo cada día a las 19:07 (hora de Lima)."
echo "   Registro local: ~/elbot.log  ·  Registro público: github.com/${REPO}/blob/main/registro/operaciones.csv"
