"""Pruebas sin conexión: simula Binance para verificar la lógica del bot."""
import datetime as dt, shutil
import bot

class Fake:
    def __init__(self, closes, usdt, btc, price):
        self.closes, self.usdt, self.btc, self.price, self.orders = closes, usdt, btc, price, []
    def fetch_ohlcv(self, s, timeframe, limit):
        base = int(dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
        return [[base + i * 86_400_000, 0, 0, 0, c, 0] for i, c in enumerate(self.closes)]
    def fetch_balance(self): return {"USDT": {"free": self.usdt}, "BTC": {"free": self.btc}}
    def fetch_ticker(self, s): return {"last": self.price}
    def amount_to_precision(self, s, a): return f"{int(a * 1e5) / 1e5:.5f}"
    def create_market_buy_order_with_cost(self, s, cost):
        q = cost / self.price * 0.999; self.usdt -= cost; self.btc += q
        self.orders.append(("BUY", cost)); return {"average": self.price, "filled": q}
    def create_market_sell_order(self, s, q):
        self.btc -= q; self.usdt += q * self.price * 0.999
        self.orders.append(("SELL", q)); return {"average": self.price, "cost": q * self.price}

def reset():
    shutil.rmtree(bot.REGISTRO, ignore_errors=True)

def ahora(n):  # momento justo después de que cierra la vela n-1
    return dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc) + dt.timedelta(days=n, minutes=7)

# 1) Tendencia bajista -> FUERA, con USDT: no compra
reset(); f = Fake([100 - i * 0.5 for i in range(61)], 100, 0, 70)
r = bot.ejecutar(f, ahora=ahora(60)); assert r["senal"] == "FUERA" and r["accion"] == "MANTENER" and not f.orders

# 2) Tendencia alcista con USDT -> COMPRA usando máx. 100 aunque haya 150
reset(); f = Fake([50 + i for i in range(61)], 150, 0, 110)
r = bot.ejecutar(f, ahora=ahora(60)); assert r["accion"] == "COMPRA" and f.orders == [("BUY", 99.5)], f.orders
# 2b) Misma vela otra vez -> no repite
assert bot.ejecutar(f, ahora=ahora(60)) is None and len(f.orders) == 1
# 2c) Día siguiente sigue alcista y ya tiene BTC -> MANTENER
f.closes.append(112); r = bot.ejecutar(f, ahora=ahora(61)); assert r["accion"] == "MANTENER" and len(f.orders) == 1

# 3) Con BTC y cruce a la baja -> VENTA de todo
reset(); f = Fake([100] * 59 + [80], 0, 0.5, 80)
r = bot.ejecutar(f, ahora=ahora(60)); assert r["accion"] == "VENTA" and f.orders[0][0] == "SELL"

# 4) La vela en curso (no cerrada) se ignora
reset(); f = Fake([100 - i * 0.5 for i in range(60)] + [500], 100, 0, 500)
r = bot.ejecutar(f, ahora=ahora(60)); assert r["senal"] == "FUERA" and not f.orders

# 5) Modo prueba: calcula pero no envía órdenes ni bloquea la vela
reset(); f = Fake([50 + i for i in range(61)], 100, 0, 110)
r = bot.ejecutar(f, ahora=ahora(60), dry_run=True); assert r["accion"] == "COMPRA" and not f.orders and r["modo"] == "PRUEBA"
r = bot.ejecutar(f, ahora=ahora(60)); assert r["accion"] == "COMPRA" and len(f.orders) == 1

# 6) Saldo menor al mínimo -> no opera
reset(); f = Fake([50 + i for i in range(61)], 4, 0, 110)
r = bot.ejecutar(f, ahora=ahora(60)); assert r["accion"] == "MANTENER" and not f.orders
reset(); print("Todas las pruebas pasaron")
