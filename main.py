import requests
import datetime
import pytz
from flask import Flask
import threading
import time
import logging
import os

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

API_KEY = "04e7128d2c962dcc02f6467c87d66afc"
BASE_URL = "https://v1.hockey.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

TELEGRAM_BOT_TOKEN = "7774934258:AAFf5ECLzRJeaNn-vqkFbVuNPs1pdO59JsU"
TELEGRAM_CHAT_ID = "-1002544321428"

TARGET_LEAGUES = ["Liiga", "DEL", "Extraliga", "AHL", "NHL"]

def get_today_matches():
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    params = {"date": today}
    url = f"{BASE_URL}/fixtures"
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10).json()
        fixtures = response.get("response", [])
        print(f"📅 API a retourné {len(fixtures)} matchs pour la date {today}")
        filtered = [
            match for match in fixtures
            if match['league']['name'] in TARGET_LEAGUES
        ]
        print(f"✅ Matchs après filtrage par ligues ciblées : {len(filtered)}")
        return filtered
    except Exception as e:
        print(f"Erreur API fixtures : {e}")
        return []

def get_odds(fixture_id):
    url = f"{BASE_URL}/odds"
    params = {"fixture": fixture_id}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10).json()
        for bookmaker in response.get("response", [{}])[0].get("bookmakers", []):
            if bookmaker['id'] == 21:  # Betclic
                return bookmaker.get("bets", [])
    except Exception as e:
        print(f"Erreur API odds : {e}")
    return []

def extract_bet(bets, home, away):
    for market in bets:
        if market['name'] == "Match Winner":
            for outcome in market['values']:
                odd = float(outcome['odd'])
                winner = home if outcome['value'] == "Home" else away if outcome['value'] == "Away" else "Nul"
                if 1.5 <= odd <= 2.5:
                    return {"pari": f"Vainqueur : {winner}", "cote": odd}
    return None

def detect_value_bet(match):
    fixture_id = match['fixture']['id']
    home = match['teams']['home']['name']
    away = match['teams']['away']['name']
    league = match['league']['name']
    country = match['league']['country']
    match_time = match['fixture']['date']

    print(f"🔍 Analyse du match : {home} vs {away} ({league})")

    bets = get_odds(fixture_id)
    bet = extract_bet(bets, home, away)
    if bet:
        return {
            "league": league,
            "country": country,
            "teams": f"{home} vs {away}",
            "time": match_time,
            **bet
        }
    return None

def construire_message(paris):
    jours_fr = {'Monday':'Lundi','Tuesday':'Mardi','Wednesday':'Mercredi','Thursday':'Jeudi','Friday':'Vendredi','Saturday':'Samedi','Sunday':'Dimanche'}
    mois_fr = {'January':'janvier','February':'février','March':'mars','April':'avril','May':'mai','June':'juin','July':'juillet','August':'août','September':'septembre','October':'octobre','November':'novembre','December':'décembre'}
    today = datetime.datetime.now()
    date_fr = f"{jours_fr[today.strftime('%A')]} {today.day} {mois_fr[today.strftime('%B')]} {today.year}"

    message = f"🔥 TES PARIS HOCKEY DU JOUR ({date_fr}) 🔥\n\n"
    for pari in paris:
        tz = pytz.timezone("Europe/Paris")
        match_datetime = datetime.datetime.fromisoformat(pari['time'][:19]).replace(tzinfo=datetime.timezone.utc).astimezone(tz)
        heure = match_datetime.strftime("%Hh%M")
        message += f"🗓️ {pari['teams']} ({pari['country']} - {pari['league']})\n"
        message += f"🕒 {heure}\n"
        message += f"🎯 {pari['pari']}\n"
        message += f"💸 Cote : {pari['cote']}\n\n"

    message += "Mise conseillée : 1 % de la bankroll par pari\n"
    message += "<i>Discipline, analyse et patience : les clés du succès.</i>\n\n"
    message += "Parie avec confiance sur Betclic : https://www.betclic.fr"
    return message

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def analyse_et_envoi():
    print("🚀 Démarrage de l'analyse hockey...")
    print("Test API: Appel API pour récupérer les matchs")
    matches = get_today_matches()[:25]
    paris_du_jour = []

    for match in matches:
        pari = detect_value_bet(match)
        time.sleep(1)
        if pari:
            paris_du_jour.append(pari)
        if len(paris_du_jour) == 2:
            break

    print(f"🎯 Nombre de paris sélectionnés : {len(paris_du_jour)}")

    if paris_du_jour:
        message = construire_message(paris_du_jour)
    else:
        message = "🚨 Aucun value bet hockey trouvé aujourd'hui."

    envoyer_telegram(message)

    matches = get_today_matches()[:25]
    paris_du_jour = []

    for match in matches:
        pari = detect_value_bet(match)
        time.sleep(1)
        if pari:
            paris_du_jour.append(pari)
        if len(paris_du_jour) == 2:
            break

    print(f"🎯 Nombre de paris sélectionnés : {len(paris_du_jour)}")

    if paris_du_jour:
        message = construire_message(paris_du_jour)
    else:
        message = "🚨 Aucun value bet hockey trouvé aujourd'hui."

    envoyer_telegram(message)

@app.route("/")
def main():
    threading.Thread(target=analyse_et_envoi).start()
    return {"status": "Analyse hockey en cours"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
