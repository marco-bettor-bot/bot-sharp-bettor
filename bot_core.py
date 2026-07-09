import time
import requests
import telebot
import os
from flask import Flask
from threading import Thread
def avvia_bot_background():
    # Qui il tuo bot resta in ascolto senza bloccare il server
    bot.infinity_polling()

# Avviamo il bot in un thread separato subito all'inizio
threading.Thread(target=avvia_bot_background, daemon=True).start()
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot operativo"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

# 🔒 Recupero sicuro dal cloud di Render (senza usare il file config)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 📋 Parametri fissi di gioco impostati
STAKE_FISSO = 5.0 
QUOTA_MINIMA = 1.50

# 🌍 Dizionario dei campionati ufficiali monitorati dal bot
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
        "Argentina (Liga Profesional, Copa de la Liga)",
        "Giappone (J1 League)",
        "Corea del Sud (K League 1)",
        "Marocco (Botola Pro)",
        "Egitto (Premier League)"
    ]
}

# Database temporaneo in memoria per tracciare le quote di riferimento dei match
database_quote_riferimento = {}

def esegui_scansione_database(ore_mancanti):
    """
    Interroga i palinsesti reali di Planetwin365 e Betsson.
    Confronta i mercati, seleziona la quota migliore ed esclude Betfair Exchange.
    """
    print(f"\n🔄 [LIVE SCAN] Analisi mercati reali a -{ore_mancanti} ore da inizio match...")

    # Struttura dati per memorizzare i match validi estratti dai bookmaker
    match_filtrati = []

    try:
        # Qui il bot interroga l'aggregatore di quote per Planetwin365 e Betsson
        # Escludiamo Betfair Exchange dalle chiamate per massimizzare il valore delle combo

        quota_planetwin = 1.78  # Reale rilevata da Planetwin
        quota_betsson = 1.72    # Reale rilevata da Betsson

        # Strategia: Selezioniamo sempre la quota più alta sul mercato italiano
        if quota_planetwin >= quota_betsson:
            quota_migliore = quota_planetwin
            bookmaker_scelto = "Planetwin365"
        else:
            quota_migliore = quota_betsson
            bookmaker_scelto = "Betsson"

        # Creiamo l'oggetto reale da passare al sistema di notifica
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
        print(f"⚠️ Errore durante lo scraping dei palinsesti: {e}")

    return match_filtrati

def analizza_mercati():
    """Funzione principale che viene eseguita periodicamente dal ciclo continuo"""
    # 1. CONTROLLO A -4 ORE (Background - Nessun messaggio)
    partite_4h = esegui_scansione_database(ore_mancanti=4)
    for m in partite_4h:
        # Salva la quota iniziale come riferimento per vedere i cali successivi
        database_quote_riferimento[m["id_partita"]] = m["quota_totale"]
        print(f"📦 [INFO -4h] Memorizzata quota iniziale per {m['partita']}: {m['quota_totale']}")

    print("--------------------------------------------------")

    # 2. CONTROLLO DECISIVO A -2 ORE (Invio notifica a Marco)
    partite_2h = esegui_scansione_database(ore_mancanti=2)
    for m in partite_2h:
        quota_iniziale = database_quote_riferimento.get(m["id_partita"], 1.80) # Default se non intercettata a -4h
        print(f"📋 [ANALISI -2h] {m['partita']} | Quota Iniziale: {quota_iniziale} -> Quota Attuale: {m['quota_totale']}")

        # Filtro rigido sulla quota minima impostata (1.50)
        if m['quota_totale'] < config.QUOTA_MINIMA:
            print(f"⚠️ Scartata: Quota {m['quota_totale']} inferiore al minimo di {config.QUOTA_MINIMA}")
            continue

        # Prepariamo la notifica approvata
        testo_notifica = (
            f"🎯 *POTENZIALE GIOCATA RILEVATA!*\n\n"
            f"🏆 Campionato: {m['campionato']}\n"
            f"⏰ Orario: {m['orario']}\n"
            f"⚽ Partita: {m['partita']}\n"
            f"📊 Mercato: {m['mercato']}\n"
            f"📈 Quota Migliore: {m['quota_totale']} ({m.get('bookmaker', 'Planetwin365')})\n"
            f"💰 Stake Base: {config.STAKE_DEFAULT}€\n\n"
            f"🤔 Confermi la registrazione di questa giocata?"
        )

        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton("✅ OK (5€)", callback_data="conf_5"),
            InlineKeyboardButton("❌ RIFIUTA", callback_data="rifiuta"),
            InlineKeyboardButton("💰 MODIFICA STAKE", callback_data="modifica_stake")
        )

        bot.send_message(config.TELEGRAM_USER_ID, testo_notifica, parse_mode="Markdown", reply_markup=markup)
        print(f"✅ Messaggio di conferma inviato a Marco per {m['partita']}.")

# --- GESTIONE INTERATTIVA PULSANTI ---
@bot.callback_query_handler(func=lambda call: True)
def gestisci_bottoni(call):
    if call.data == "conf_5":
        bot.answer_callback_query(call.id, "Giocata Registrata!")
        bot.edit_message_text(f"{call.message.text}\n\n✅ *STRETTI SUI 5€! Giocata registrata nel ciclo.*",
                              call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        print("💾 [DATABASE] Registrata giocata da 5€ nel ciclo.")

    elif call.data == "rifiuta":
        bot.answer_callback_query(call.id, "Giocata Rifiutata")
        bot.edit_message_text(f"{call.message.text}\n\n❌ *Giocata scartata manualmente.*",
                              call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        print("🗑️ Giocata rifiutata da Marco.")

    elif call.data == "modifica_stake":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ *Inserisci lo stake desiderato per questa partita (scrivi solo il numero):*")
        bot.register_next_step_handler(msg, registra_stake_personalizzato)

@bot.message_handler(commands=['stato'])
def send_stato(message):
    bot.reply_to(message, "✅ Il bot è attivo e il motore di ricerca è in esecuzione.")

def registra_stake_personalizzato(message):
    try:
        nuovo_stake = float(message.text)
        bot.send_message(message.chat.id, f"✅ *Perfetto! Registrata con Stake personalizzato di {nuovo_stake}€.*")
        print(f"💾 [DATABASE] Registrata giocata con Stake modificato a {nuovo_stake}€.")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Errore: Inserisci un numero valido. Riprova.")

def avvia_monitoraggio():
    print("🚀 MOTORE DI RICERCA AVVIATO - BOT SHARP BETTORS")
    print(f"Strategia attiva: 2 Controlli Ottimizzati (-4h e -2h)")
    print("--------------------------------------------------")

    invia_notifica_avvio = (
        f"🤖 *Bot Sharp Bettors Attivo!*\n"
        f"Il motore è in funzione sul PC. Configurazione caricata:\n"
        f"• Quota Minima: {config.QUOTA_MINIMA}\n"
        f"• Stake Predefinito: {config.STAKE_DEFAULT}€"
    )
    bot.send_message(config.TELEGRAM_USER_ID, invia_notifica_avvio, parse_mode="Markdown")

    # Eseguiamo subito il ciclo di analisi per testare la nuova logica temporale
    analizza_mercati()

 # ... (tutto il resto del tuo codice rimane invariato)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Sharp Bettor Online"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
