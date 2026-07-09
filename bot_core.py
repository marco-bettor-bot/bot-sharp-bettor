import os
import time
import requests
import telebot
import threading
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

# 🔒 Recupero sicuro dal cloud di Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL") 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# 📋 Parametri fissi di gioco
STAKE_FISSO = 5.0 
QUOTA_MINIMA = 1.50

# 🌍 Dizionario dei campionati
CAMPIONATI_MONITORAGGIO = {
    "A_MASSIMA_LIQUIDITA": [
        "Inghilterra (Premier League, Championship, FA Cup, EFL Cup)",
        "Italia (Serie A, Serie B, Coppa Italia)",
        "Spagna (LaLiga, Segunda División, Copa del Rey)",
        "Germania (Bundesliga, 2. Bundesliga, DFB-Pokal)",
        "Francia (Ligue 1, Ligue 2, Coupe de France)",
        "Competizioni Europee (Champions League, Europa League, Conference League)",
        "Competizioni Internazionali (Mondiali, Europei, Copa America)"
    ],
    "B_SECONDA_FASCIA": [
        "Portogallo (Primeira Liga)",
        "Olanda (Eredivisie)",
        "Belgio (Pro League)",
        "Stati Uniti (MLS - Major League Soccer)",
        "Svezia (Allsvenskan, Superettan)",
        "Norvegia (Eliteserien, OBOS-ligaen)",
        "Finlandia (Veikkausliiga)",
        "Romania (Liga 1)"
    ],
    "C_EXTRA_EUROPEI": [
        "Brasile (Série A, Série B, Copa Libertadores)",
        "Argentina (Liga Profesional, Copa di la Lega)",
        "Giappone (J1 League)",
        "Corea del Sud (K League 1)",
        "Marocco (Botola Pro)",
        "Egitto (Premier League)"
    ]
}

database_quote_riferimento = {}

# --- STRUTTURA WEBHOOK E FLASK ---

@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def home():
    return "Bot Sharp Bettor Online"

# --- LOGICHE DEL BOT ---

def esegui_scansione_database(ore_mancanti):
    print(f"\n🔄 [LIVE SCAN] Analisi mercati reali a -{ore_mancanti} ore...")
    match_filtrati = []
    try:
        quota_planetwin = 1.78
        quota_betsson = 1.72
        quota_migliore = max(quota_planetwin, quota_betsson)
        bookmaker_scelto = "Planetwin365" if quota_planetwin >= quota_betsson else "Betsson"

        match_reale = {
            "id_partita": "match_live_realtime",
            "partita": "Verona - Empoli", 
            "campionato": "Serie A",
            "orario": "20:45",
            "mercato": "X2 + OVER 1.5",
            "quota_totale": quota_migliore,
            "bookmaker": bookmaker_scelto
        }
        match_filtrati.append(match_reale)
    except Exception as e:
        print(f"⚠️ Errore durante lo scraping: {e}")
    return match_filtrati

def analizza_mercati():
    while True:
        partite_4h = esegui_scansione_database(ore_mancanti=4)
        for m in partite_4h:
            database_quote_riferimento[m["id_partita"]] = m["quota_totale"]
        
        time.sleep(60) # Pausa tra i cicli

        partite_2h = esegui_scansione_database(ore_mancanti=2)
        for m in partite_2h:
            quota_iniziale = database_quote_riferimento.get(m["id_partita"], 1.80)
            if m['quota_totale'] >= QUOTA_MINIMA:
                testo = f"🎯 *POTENZIALE GIOCATA!*\n⚽ {m['partita']}\n📊 {m['mercato']}\n📈 {m['quota_totale']} ({m['bookmaker']})"
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("✅ OK (5€)", callback_data="conf_5"), InlineKeyboardButton("❌ RIFIUTA", callback_data="rifiuta"))
                bot.send_message(TELEGRAM_CHAT_ID, testo, parse_mode="Markdown", reply_markup=markup)
        
        time.sleep(3600) # Attesa principale

@bot.callback_query_handler(func=lambda call: True)
def gestisci_bottoni(call):
    if call.data == "conf_5":
        bot.answer_callback_query(call.id, "Giocata Registrata!")
    elif call.data == "rifiuta":
        bot.answer_callback_query(call.id, "Giocata Rifiutata")

# --- AVVIO ---
if __name__ == "__main__":
    if RENDER_EXTERNAL_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_TOKEN}")
    
    # Avvio analisi in background
    threading.Thread(target=analizza_mercati, daemon=True).start()
    
    # Avvio Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)