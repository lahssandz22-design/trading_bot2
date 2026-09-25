from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import os
import threading
import time
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests

# ==========================================
# 0. سيرفر وهمي لإرضاء منصة Render وتشغيل البوت مجاناً
# ==========================================


class SimpleHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Market Maker Bot is running successfully!")

  def do_HEAD(self):
    self.send_response(200)
    self.end_headers()


def run_server():
  port = int(os.environ.get("PORT", 10000))
  server = HTTPServer(("0.0.0.0", port), SimpleHandler)
  server.serve_forever()


server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# ==========================================
# 1. إعدادات البوت والمنصة والأمان
# ==========================================
TELEGRAM_BOT_TOKEN = "869642227:AAGNB88pBF_kJzEVBLzFQrBGv7yRG5f3Js4"
AUTHORIZED_CHAT_ID = "7895743860"

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "NEARUSDT",
    "MATICUSDT",
    "LTCUSDT",
    "UNIUSDT",
    "FILUSDT",
    "ATOMUSDT",
    "ETCUSDT",
    "XLMUSDT",
    "BCHUSDT",
    "APTUSDT",
    "SUIUSDT",
    "ARBUSDT",
    "OPUSDT",
    "INJUSDT",
    "RNDRUSDT",
    "TIAUSDT",
    "SEIUSDT",
    "FETUSDT",
    "AGIXUSDT",
    "RENDERUSDT",
    "PEPEUSDT",
    "SHIBUSDT",
    "FLOKIUSDT",
    "BONKUSDT",
    "WIFUSDT",
    "ARUSDT",
    "IMXUSDT",
    "SANDUSDT",
    "MANAUSDT",
    "AXSUSDT",
    "GALAUSDT",
    "CHZUSDT",
    "CRVUSDT",
    "AAVEUSDT",
    "MKRUSDT",
    "SNXUSDT",
    "COMPUSDT",
    "LDOUSDT",
    "RUNEUSDT",
    "KASUSDT",
    "STXUSDT",
    "ICPUSDT",
    "ALGOUSDT",
    "FTMUSDT",
    "HBARUSDT",
    "VETUSDT",
    "THETAUSDT",
    "EGLDUSDT",
    "EOSUSDT",
    "XTZUSDT",
    "KAVAUSDT",
    "ZILUSDT",
    "BATUSDT",
    "ENJUSDT",
    "ZRXUSDT",
    "IOSTUSDT",
    "ONTUSDT",
    "QTUMUSDT",
]

TIMEFRAME = "1h"
last_signals = {symbol: None for symbol in SYMBOLS}

active_trades = []
closed_trades = []


# ==========================================
# 2. دوال الاتصال وجلب البيانات والصور
# ==========================================
def send_telegram_alert(message):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": AUTHORIZED_CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }
  try:
    requests.post(url, data=payload, timeout=5)
  except Exception as e:
    print(f"خطأ في إرسال التلجرام: {e}")


def send_telegram_photo(photo_bytes, caption):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
  files = {"photo": ("stats.png", photo_bytes, "image/png")}
  data = {
      "chat_id": AUTHORIZED_CHAT_ID,
      "caption": caption,
      "parse_mode": "Markdown",
  }
  try:
    requests.post(url, data=data, files=files, timeout=10)
  except Exception as e:
    print(f"خطأ في إرسال الصورة للتلجرام: {e}")


def get_binance_klines(symbol, interval, limit=100):
  url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
  try:
    response = requests.get(url, timeout=5)
    data = response.json()
    if not isinstance(data, list):
      return None

    df = pd.DataFrame(
        data,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_av",
            "trades",
            "tb_base_av",
            "tb_quote_av",
            "ignore",
        ],
    )
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df
  except Exception:
    return None


def get_current_price(symbol):
  url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
  try:
    response = requests.get(url, timeout=3)
    return float(response.json()["price"])
  except:
    return None


# ==========================================
# 3. توليد صورة إحصائيات آخر الصفقات
# ==========================================
def generate_stats_image():
  if not closed_trades:
    return None

  recent = closed_trades[-20:]
  wins = sum(1 for t in recent if t["result"] == "WIN")
  losses = len(recent) - wins
  win_rate = (wins / len(recent)) * 100 if len(recent) > 0 else 0

  fig, ax = plt.subplots(figsize=(8, 6), facecolor="#1e1e1e")
  ax.set_facecolor("#1e1e1e")

  ax.axis("off")
  title_text = (
      f"تقرير أداء الصفقات (آخر {len(recent)} صفقات)\nنسبة النجاح:"
      f" {win_rate:.1f}% (ربح: {wins} | خسارة: {losses})"
  )
  ax.text(
      0.5,
      0.92,
      title_text,
      color="white",
      fontsize=14,
      fontweight="bold",
      ha="center",
      transform=ax.transAxes,
  )

  table_data = []
  for t in recent:
    res_text = "رابحة" if t["result"] == "WIN" else "خاسرة"
    table_data.append([t["symbol"], t["type"], f"{t['entry']:.2f}", res_text])

  columns = ["الزوج", "النوع", "سعر الدخول", "النتيجة"]
  table = ax.table(
      cellText=table_data, colLabels=columns, loc="center", cellLoc="center"
  )

  table.auto_set_font_size(False)
  table.set_fontsize(10)
  table.scale(1, 1.3)

  for key, cell in table.get_celld().items():
    cell.set_text_props(color="white")
    if key[0] == 0:
      cell.set_facecolor("#333333")
      cell.set_text_props(weight="bold")
    else:
      cell.set_facecolor("#2a2a2a")

  plt.tight_layout()
  buf = io.BytesIO()
  plt.savefig(
      buf, format="png", dpi=150, facecolor=fig.get_facecolor(), edgecolor="none"
  )
  buf.seek(0)
  plt.close(fig)
  return buf.getvalue()


# ==========================================
# 4. خوارزمية صانع السوق وتتبع الصفقات
# ==========================================
def analyze_market_maker_model(symbol):
  df = get_binance_klines(symbol, TIMEFRAME, limit=60)
  if df is None or len(df) < 45:
    return

  lookback = 40
  recent_high = df["high"].iloc[-lookback:-1].max()
  recent_low = df["low"].iloc[-lookback:-1].min()
  equilibrium = (recent_high + recent_low) / 2

  current_close = df["close"].iloc[-2]
  current_low = df["low"].iloc[-2]
  current_high = df["high"].iloc[-2]

  signal_type = None

  if current_close < equilibrium and current_low < recent_low:
    signal_type = "MM_BUY"
  elif current_close > equilibrium and current_high > recent_high:
    signal_type = "MM_SELL"

  if signal_type and last_signals.get(symbol) != signal_type:
    last_signals[symbol] = signal_type
    entry_price = current_close

    if signal_type == "MM_BUY":
      tp = entry_price * 1.015
      sl = entry_price * 0.9925
    else:
      tp = entry_price * 0.985
      sl = entry_price * 1.0075

    active_trades.append({
        "symbol": symbol,
        "type": "شراء (BUY)" if signal_type == "MM_BUY" else "بيع (SELL)",
        "entry": entry_price,
        "tp": tp,
        "sl": sl,
    })

    msg = (
        f"إشارة جديدة وفق نموذج صانع السوق\n\n"
        f"• الأصل: {symbol}\n"
        f"• النوع: {'شراء' if signal_type == 'MM_BUY' else 'بيع'}\n"
        f"• سعر الدخول: {entry_price:,.4f}\n"
        f"• الهدف: {tp:,.4f}\n"
        f"• وقف الخسارة: {sl:,.4f}"
    )
    send_telegram_alert(msg)


def track_open_trades():
  if not active_trades:
    return

  for trade in active_trades[:]:
    current_price = get_current_price(trade["symbol"])
    if not current_price:
      continue

    is_buy = "شراء" in trade["type"]
    closed = False
    result = None

    if is_buy:
      if current_price >= trade["tp"]:
        closed, result = True, "WIN"
      elif current_price <= trade["sl"]:
        closed, result = True, "LOSS"
    else:
      if current_price <= trade["tp"]:
        closed, result = True, "WIN"
      elif current_price >= trade["sl"]:
        closed, result = True, "LOSS"

    if closed:
      trade["result"] = result
      closed_trades.append(trade)
      active_trades.remove(trade)

      res_icon = "رابحة" if result == "WIN" else "خاسرة"
      msg = (
          f"تحديث نتيجة صفقة مغلقة\n\n"
          f"• الأصل: {trade['symbol']}\n"
          f"• النوع: {trade['type']}\n"
          f"• سعر الدخول: {trade['entry']:,.4f}\n"
          f"• سعر الخروج: {current_price:,.4f}\n"
          f"• النتيجة: {res_icon}"
      )
      send_telegram_alert(msg)

      photo = generate_stats_image()
      if photo:
        send_telegram_photo(photo, "إحصائيات أداء الصفقات الحالية")


# ==========================================
# 5. حلقة التشغيل المستمر
# ==========================================
def run_bot():
  print("تم تشغيل البوت بنجاح...")
  send_telegram_alert("تم تشغيل بوت صانع السوق بنجاح وحماية خاصة")

  while True:
    print("جاري فحص الأسواق...")
    with ThreadPoolExecutor(max_workers=10) as executor:
      executor.map(analyze_market_maker_model, SYMBOLS)

    track_open_trades()
    time.sleep(60)


if __name__ == "__main__":
  run_bot()
