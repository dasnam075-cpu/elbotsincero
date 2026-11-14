"""
El Bot Sincero — bot de media móvil de 50 días (BTC/USDT, Binance spot).

Regla (la misma del Día 2):
  - Si el último cierre diario está ENCIMA de la media de 50 días -> estar comprado en BTC.
  - Si está DEBAJO -> estar en USDT.

Protecciones:
  - Nunca usa más de PRESUPUESTO_MAX USDT, aunque haya más saldo.
  - Solo opera una vez por vela diaria (no repite órdenes si se ejecuta dos veces).
  - Solo spot, sin apalancamiento. Ignora saldos menores al mínimo de Binance.
  - Modo prueba (DRY_RUN=1): calcula todo y lo registra, pero no envía órdenes.

Variables de entorno:
  BINANCE_API_KEY, BINANCE_API_SECRET  (en GitHub: Settings -> Secrets -> Actions)
  DRY_RUN=1          -> no envía órdenes (por defecto 0)
  PRESUPUESTO_MAX    -> USDT máximos que puede usar el bot (por defecto 100)
"""
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

SIMBOLO = "BTC/USDT"
VENTANA = 50
MIN_ORDEN_USDT = 6.0          # Binance exige ~5 USDT por orden; dejamos margen
REGISTRO = Path(__file__).parent / "registro"
CSV = REGISTRO / "operaciones.csv"
ESTADO = REGISTRO / "estado.json"
COLUMNAS = ["fecha_utc", "vela", "cierre", "media50", "senal", "accion", "precio_ejec",
            "btc_movido", "usdt_movido", "saldo_usdt", "saldo_btc", "valor_total_usdt", "modo"]


def crear_exchange():
    import ccxt
    return ccxt.binance({
        "apiKey": os.environ.get("BINANCE_API_KEY", ""),
        "secret": os.environ.get("BINANCE_API_SECRET", ""),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })


def velas_cerradas(ex, ahora_ms):
    """Devuelve [(fecha, cierre)] solo de velas diarias ya cerradas."""
    velas = ex.fetch_ohlcv(SIMBOLO, timeframe="1d", limit=VENTANA + 10)
    dia = 86_400_000
    cerradas = [v for v in velas if v[0] + dia <= ahora_ms]
    return [(dt.datetime.fromtimestamp(v[0] / 1000, dt.timezone.utc).date().isoformat(), float(v[4]))
            for v in cerradas]


def leer_estado():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {}


def guardar(fila, estado):
    REGISTRO.mkdir(exist_ok=True)
    nuevo = not CSV.exists()
    with CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        if nuevo:
            w.writeheader()
        w.writerow(fila)
    ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")


def ejecutar(ex, ahora=None, dry_run=False, presupuesto=100.0):
    ahora = ahora or dt.datetime.now(dt.timezone.utc)
    ahora_ms = int(ahora.timestamp() * 1000)
    estado = leer_estado()

    velas = velas_cerradas(ex, ahora_ms)
    if len(velas) < VENTANA:
        raise RuntimeError(f"Solo hay {len(velas)} velas cerradas; se necesitan {VENTANA}.")
    fecha_vela, cierre = velas[-1]
    media = sum(c for _, c in velas[-VENTANA:]) / VENTANA
    senal = "DENTRO" if cierre > media else "FUERA"

    if estado.get("ultima_vela") == fecha_vela:
        print(f"Vela {fecha_vela} ya procesada ({estado.get('ultima_accion')}). No hago nada.")
        return None

    saldo = ex.fetch_balance()
    usdt = float(saldo.get("USDT", {}).get("free", 0) or 0)
    btc = float(saldo.get("BTC", {}).get("free", 0) or 0)
    precio = float(ex.fetch_ticker(SIMBOLO)["last"])
    valor_btc = btc * precio

    accion, precio_ejec, btc_mov, usdt_mov = "MANTENER", "", "", ""
    if senal == "DENTRO" and valor_btc < MIN_ORDEN_USDT:
        gasto = round(min(usdt, presupuesto) * 0.995, 2)   # 0,5 % de colchón para comisión
        if gasto >= MIN_ORDEN_USDT:
            accion = "COMPRA"
            if not dry_run:
                orden = ex.create_market_buy_order_with_cost(SIMBOLO, gasto)
                precio_ejec = orden.get("average") or orden.get("price") or precio
                btc_mov = orden.get("filled", "")
            usdt_mov = gasto
    elif senal == "FUERA" and valor_btc >= MIN_ORDEN_USDT:
        cantidad = float(ex.amount_to_precision(SIMBOLO, btc))
        if cantidad * precio >= MIN_ORDEN_USDT:
            accion = "VENTA"
            if not dry_run:
                orden = ex.create_market_sell_order(SIMBOLO, cantidad)
                precio_ejec = orden.get("average") or orden.get("price") or precio
                usdt_mov = orden.get("cost", "")
            btc_mov = cantidad

    if accion != "MANTENER" and not dry_run:
        saldo = ex.fetch_balance()
        usdt = float(saldo.get("USDT", {}).get("free", 0) or 0)
        btc = float(saldo.get("BTC", {}).get("free", 0) or 0)

    fila = {
        "fecha_utc": ahora.strftime("%Y-%m-%d %H:%M"), "vela": fecha_vela,
        "cierre": round(cierre, 2), "media50": round(media, 2), "senal": senal, "accion": accion,
        "precio_ejec": precio_ejec, "btc_movido": btc_mov, "usdt_movido": usdt_mov,
        "saldo_usdt": round(usdt, 2), "saldo_btc": round(btc, 8),
        "valor_total_usdt": round(usdt + btc * precio, 2), "modo": "PRUEBA" if dry_run else "REAL",
    }
    estado.update({"ultima_vela": fecha_vela, "ultima_accion": accion,
                   "posicion": "BTC" if (accion == "COMPRA" or (accion == "MANTENER" and valor_btc >= MIN_ORDEN_USDT)) else "USDT"})
    if dry_run:
        estado.pop("ultima_vela")   # en modo prueba no bloquea la ejecución real del día
    guardar(fila, estado)
    print(json.dumps(fila, ensure_ascii=False, indent=2))
    return fila


if __name__ == "__main__":
    dry = os.environ.get("DRY_RUN", "0") == "1"
    tope = float(os.environ.get("PRESUPUESTO_MAX", "100"))
    if not dry and not (os.environ.get("BINANCE_API_KEY") and os.environ.get("BINANCE_API_SECRET")):
        sys.exit("Faltan BINANCE_API_KEY / BINANCE_API_SECRET.")
    ejecutar(crear_exchange(), dry_run=dry, presupuesto=tope)
