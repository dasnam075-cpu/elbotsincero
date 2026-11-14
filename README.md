# 🤖 El Bot Sincero

Bot de trading **de código abierto** que opera **$100 reales** en Binance (spot, BTC/USDT) con una regla simple, y registra cada decisión — gane o pierda.

**Regla:** si el cierre diario de Bitcoin está **encima de la media móvil de 50 días**, el bot está comprado en BTC; si está **debajo**, se queda en USDT.

- Corre solo, una vez al día (19:07 hora de Lima), en GitHub Actions. No necesita una computadora prendida.
- Nunca usa más de 100 USDT, no repite órdenes, solo spot y sin apalancamiento.
- Cada decisión queda en [`registro/operaciones.csv`](registro/operaciones.csv).

> Experimento educativo. No es asesoría financiera ni una recomendación de inversión. No copies esto con dinero que no puedas perder.

Canal: **@elbotsincero** en YouTube, TikTok e Instagram.

---

## Cómo instalarlo (para el dueño del bot)

1. **Llave de API en Binance** (subcuenta del bot): permisos de *lectura* y *trading spot*; **sin retiros**, sin futuros.
2. **Secrets en GitHub:** *Settings → Secrets and variables → Actions → New repository secret*
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
3. **Prueba:** pestaña *Actions → El Bot Sincero → Run workflow* con `dry_run = 1`. Calcula todo y lo registra, pero no envía órdenes.
4. **Real:** desde ahí corre solo cada día. Para forzar una ejecución real: *Run workflow* con `dry_run = 0`.

Archivos: `bot.py` (el bot), `test_bot.py` (pruebas sin conexión: `python test_bot.py`), `.github/workflows/bot.yml` (horario).
