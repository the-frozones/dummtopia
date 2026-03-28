#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DUMMTOPIA - Das Nasenspray Dealer Game
Ein Spiel über das Leben als Nasenspray-Dealer in einer Welt wo Nasenspray verboten ist.
"""

import os
import sys
import time
import random
import threading
import json
import math
import select
import tty
import termios
import locale as _locale_mod

# ─────────────────────────────────────────────────
#  LOCALIZATION SYSTEM
# ─────────────────────────────────────────────────

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCALE_DIR = os.path.join(_SCRIPT_DIR, "localization")
_FALLBACK_LOCALE = "de"
_ACTIVE_STRINGS = {}
_ACTIVE_LOCALE = _FALLBACK_LOCALE

def _detect_system_locale():
    """Auto-detect system locale, return 2-letter code like 'de', 'en', etc."""
    try:
        lang = _locale_mod.getdefaultlocale()[0]  # e.g. 'de_DE' or 'en_US'
        if lang:
            return lang.split("_")[0].lower()
    except Exception:
        pass
    # Fallback via env vars
    for ev in ("LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(ev, "")
        if val:
            return val.split("_")[0].split(".")[0].lower()
    return None

def _load_locale_file(code):
    path = os.path.join(_LOCALE_DIR, f"{code}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def init_localization(manual_locale=None):
    """
    Load localization strings. Priority:
    1. manual_locale (from settings)
    2. system locale
    3. fallback (de)
    Populates _ACTIVE_STRINGS and sets _ACTIVE_LOCALE.
    """
    global _ACTIVE_STRINGS, _ACTIVE_LOCALE

    candidates = []
    if manual_locale:
        candidates.append(manual_locale.lower())
    sys_locale = _detect_system_locale()
    if sys_locale:
        candidates.append(sys_locale)
    candidates.append(_FALLBACK_LOCALE)

    for code in candidates:
        data = _load_locale_file(code)
        if data:
            _ACTIVE_STRINGS = data
            _ACTIVE_LOCALE = code
            return

    # If no file found at all, ship an empty dict (game still runs with hardcoded fallback keys)
    _ACTIVE_STRINGS = {}
    _ACTIVE_LOCALE = _FALLBACK_LOCALE

def T(key, **kwargs):
    """Translate key. Falls back to key name if missing."""
    text = _ACTIVE_STRINGS.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

# ─────────────────────────────────────────────────
#  ITEM DEFINITIONS
# ─────────────────────────────────────────────────
NS_normal    = "Normales Nasenspray"
NP_normal    = 15

NS_premium   = "Premium Nasenspray"
NP_premium   = 35

NS_ultra     = "Ultra Nasenspray (Industrial)"
NP_ultra     = 75

NS_menthol   = "Menthol-Nasenspray"
NP_menthol   = 22

# ─────────────────────────────────────────────────
#  CHARACTER DEFINITIONS
# ─────────────────────────────────────────────────
#  selling_power: bonus multiplier vs male customers (base 1.0)
#  charisma:      bonus multiplier vs female customers & WTP increase chance
#  picky_bonus:   extra sell chance vs WTP < 4 customers (added to roll)
#  wtp_up_chance: base probability of raising WTP on special-price sale
#  win_bonus:     added to win_chance when delivering samples

CHARACTER_STATS = {
    "Philipp": {
        "selling_power": 1.25,   # better at selling to male customers
        "charisma":      0.80,   # weaker vs female
        "picky_bonus":   0.15,   # +15% chance vs WTP<4
        "wtp_up_chance": 0.05,   # low chance of raising WTP
        "win_bonus":     0.08,   # moderate win bonus
    },
    "Joseph": {
        "selling_power": 0.85,   # less raw selling power
        "charisma":      1.30,   # strong vs female, WTP increase
        "picky_bonus":  -0.05,   # slightly worse with stingy customers
        "wtp_up_chance": 0.20,   # higher chance of raising WTP
        "win_bonus":     0.15,   # better at winning over new customers
    },
}

# ─────────────────────────────────────────────────
#  CUSTOMER DEFINITIONS
#  gender: "m" = male, "f" = female  (affects which stat applies)
# ─────────────────────────────────────────────────

# --- Original regular customers ---
CPRO_Stefan    = "Ey Mann... *kratzt sich nervös am Kinn* ich brauch wieder wat. Du weißt schon. Das Zeug. Hast du noch?"
WTP_Stefan     = 5

CPRO_Johnathan = "*tippt dich auf die Schulter* Entschuldigung, äh... ich hab gehört du... verkaufst? Ähm. Nasenspray? Das klingt komisch ich weiß aber ich bin wirklich verstopft."
WTP_Johnathan  = 2

CPRO_Bob       = "*lehnt lässig an der Wand* Yo. Weißt du was ich brauche. Mach's kurz."
WTP_Bob        = 4

# --- 20 new regular customers ---
CPRO_Klaus     = "*schaut nervös um sich* Ich... ich brauch das Zeug. Meine Nase. Seit Wochen. Bitte."
WTP_Klaus      = 6

CPRO_Dieter    = "Yo Alter, Stefan hat mir von dir erzählt. Hast du noch was übrig? Ich zahl fair."
WTP_Dieter     = 5

CPRO_Hans      = "*hustet* Entschuldige die Störung. Kann man bei Ihnen... äh... das hier kaufen?"
WTP_Hans       = 3

CPRO_Marco     = "Ich hör du hast das beste Zeug in der Stadt. Stimmt das? Dann lass mal sehen."
WTP_Marco      = 7

CPRO_Tobias    = "*flüstert* Pssst. Du kennst doch das Ding. Ich brauch 'ne Einheit. Für heute Abend."
WTP_Tobias     = 5

CPRO_Felix     = "Alte Zeiten, Alter! Hab noch von damals. Du hast doch noch was, oder?"
WTP_Felix      = 6

CPRO_Patrick   = "*tippt auf sein Handy* Ich hab die Überweisung schon vorbereitet. Wie viel?"
WTP_Patrick    = 8

CPRO_Lukas     = "Mein Arzt hat gesagt ich soll aufhören. Aber mein Arzt weiß auch nicht wie sich das anfühlt."
WTP_Lukas      = 4

CPRO_Tim       = "*sieht aus wie er schon drei Tage nicht geschlafen hat* Bitte. Bitte sag mir du hast noch was."
WTP_Tim        = 3

CPRO_Nico      = "Ich bin neu in der Stadt. Jemand hat mir diese Adresse gegeben. Ich such was für... Erkältung."
WTP_Nico       = 2

CPRO_Fatima    = "*zieht ihren Schal hoch* Ich komm schnell wieder wenn du mir heute hilfst. Ich hab Geld."
WTP_Fatima     = 7

CPRO_Sandra    = "Hör zu, ich hab keine Zeit für Theater. Preis? Gut. Kaufe. Tschüss."
WTP_Sandra     = 6

CPRO_Melanie   = "*niesen* Ugh. Drei Wochen ohne. Du kannst dir nicht vorstellen wie das ist."
WTP_Melanie    = 5

CPRO_Jessica   = "Ich hab heute Morgen in deinen Kanal geguckt — du bist legit, oder? Ich kauf wenn der Preis stimmt."
WTP_Jessica    = 4

CPRO_Petra     = "*sehr leise* Mein Mann darf das nicht wissen. Bitte diskret. Ich zahle gut."
WTP_Petra      = 8

CPRO_Anna      = "Guten Tag. Äh. Ich... würde gern etwas erwerben. Wenn das möglich wäre?"
WTP_Anna       = 3

CPRO_Leonie    = "*schaut sich prüfend um* Okay. Ich bin rein. Was hast du heute?"
WTP_Leonie     = 6

CPRO_Sabine    = "Ich kenn Stefanie. Sie hat gesagt du bist die beste Adresse. Zeig mal was du hast."
WTP_Sabine     = 7

CPRO_Ralf      = "*Ralf schaut grimmig* Ich zahl nicht über Basispreis. Fertig. Willst du oder nicht?"
WTP_Ralf       = 3

CPRO_Gerhard   = "Ich muss ehrlich sein — ich hab das Zeug eigentlich für meinen Bruder. Er zahlt mir zurück. Wahrscheinlich."
WTP_Gerhard    = 4

# --- Original winnable customer ---
CPRO_Stefanie  = "*schnüffelt und wischt sich die Nase* Oh Gott... ich hab gehört du hast was dagegen? Ich bin seit einer Woche krank, ich kann nicht mehr atmen..."
WTP_Stefanie   = 9
WIN_CHANCE_Stefanie = 0.90

# --- 10 new buyable (winnable) customers ---
CPRO_Dr_Müller  = "*Arztkittel, sehr diskret* Meine Patienten fragen mich manchmal... privat... ob ich etwas empfehlen kann. Du verstehst? Diskretion vorausgesetzt."
WTP_Dr_Müller   = 9
WIN_CHANCE_Dr_Müller = 0.65

CPRO_Horst      = "*Bauarbeiter, direkt* Keine Scheiß-Erklärungen. Ich hab' die Nase voll — buchstäblich. Ich kauf wenn der Preis gut ist."
WTP_Horst       = 6
WIN_CHANCE_Horst = 0.70

CPRO_Claudia    = "*Anwältin, selbstsicher* Ich hab Recherche betrieben. Du hast die beste Verfügbarkeit in einem Umkreis von 3km. Ich möchte Stammkundin werden."
WTP_Claudia     = 8
WIN_CHANCE_Claudia = 0.75

CPRO_Erwin      = "*älterer Herr, schüchtern* Ich weiß das klingt verrückt. Aber meine Frau... seit sie das Spray nicht mehr bekommt... ich kann Ihnen nicht beschreiben."
WTP_Erwin       = 7
WIN_CHANCE_Erwin = 0.80

CPRO_Natascha   = "*Influencerin, sehr selbstbewusst* Ich poste natürlich nichts drüber. Aber ich brauch das regelmäßig. Und ich empfehle dich weiter wenn der Service stimmt."
WTP_Natascha    = 8
WIN_CHANCE_Natascha = 0.60

CPRO_Benjamin   = "*Student, leise* Ich hab von dir im Forum gelesen. Keine Namen natürlich. Ich... ich wollte einfach mal schauen."
WTP_Benjamin    = 3
WIN_CHANCE_Benjamin = 0.55

CPRO_Ingrid     = "*Rentnerin, sehr freundlich* Mein Sohn sagt ich soll das nicht kaufen. Aber mein Sohn sagt viele Dinge. Haben Sie etwas für eine ältere Dame?"
WTP_Ingrid      = 6
WIN_CHANCE_Ingrid = 0.85

CPRO_Markus     = "*Journalist, nervös* Ich schreibe eigentlich über den Schwarzmarkt. Aber... äh... rein journalistisch natürlich. Ein Sample wäre für... Recherche."
WTP_Markus      = 5
WIN_CHANCE_Markus = 0.50

CPRO_Yara       = "*Tänzerin, entspannt* Ich kenn das hier. Ich kenn das Spiel. Mach mir ein faires Angebot und ich bin regelmäßig."
WTP_Yara        = 7
WIN_CHANCE_Yara  = 0.72

CPRO_Dietmar    = "*Bodyguard, einschüchternd groß* Mein Chef schickt mich. Du weißt schon für wen. Guter Preis und wir kommen jede Woche."
WTP_Dietmar     = 9
WIN_CHANCE_Dietmar = 0.78

# ─────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def color(text, code):
    return f"\033[{code}m{text}\033[0m"

def red(t):    return color(t, "91")
def green(t):  return color(t, "92")
def yellow(t): return color(t, "93")
def blue(t):   return color(t, "94")
def cyan(t):   return color(t, "96")
def bold(t):   return color(t, "1")
def dim(t):    return color(t, "2")
def magenta(t):return color(t, "95")

def slow_print(text, delay=0.03):
    for ch in text:
        print(ch, end='', flush=True)
        time.sleep(delay)
    print()

def box(title, content_lines, width=55):
    import re
    out = []
    out.append("╔" + "═" * (width-2) + "╗")
    out.append("║" + f" {title} ".center(width-2) + "║")
    out.append("╠" + "═" * (width-2) + "╣")
    for line in content_lines:
        stripped = re.sub(r'\033\[[0-9;]*m', '', line)
        padding = width - 2 - len(stripped)
        out.append("║ " + line + " " * max(0, padding-2) + " ║")
    out.append("╚" + "═" * (width-2) + "╝")
    return "\n".join(out)

def getch_timeout(timeout=1.0):
    """Read a single char with timeout. Returns char or None."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            ch = sys.stdin.read(1)
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def input_line(prompt=""):
    """Normal line input (restores canonical mode)."""
    print(prompt, end='', flush=True)
    return input()

# ─────────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────────

DEFAULT_STATE = {
    "first_launch": True,
    "dealer_name": "Philipp",
    "character": "Philipp",          # "Philipp" or "Joseph"
    "balance": 50.0,
    "rebirth_points": 0,
    "rebirth_count": 0,
    "level": 1,
    "xp": 0,
    "inventory": ["normal", "normal"],
    "hidden_stash": [],
    "custom_prices": {},
    "customer_ratings": {},
    "unlocked_customers": [
        "Stefan", "Johnathan", "Bob",
        "Klaus", "Dieter", "Hans", "Marco", "Tobias", "Felix", "Patrick",
        "Lukas", "Tim", "Nico", "Fatima", "Sandra", "Melanie", "Jessica",
        "Petra", "Anna", "Leonie", "Sabine", "Ralf", "Gerhard",
    ],
    "winnable_customers": [
        "Stefanie",
        "Dr_Müller", "Horst", "Claudia", "Erwin", "Natascha",
        "Benjamin", "Ingrid", "Markus", "Yara", "Dietmar",
    ],
    "won_customers": [],
    "pending_samples": [],
    "settings": {
        "police_interval_min": 60,
        "police_interval_max": 120,
        "day_length_seconds": 1200,
        "news_notifications": True,
        "locale": None,              # None = auto-detect
    },
    "total_sales": 0,
    "total_busted": 0,
    "session_day": 1,
    "loan_amount": 0.0,
    "loan_deadline": None,
    "ingame_start_real": None,
    "ingame_day_notified": 0,
}

SPRAY_DATA = {
    "normal":  {"name": NS_normal,  "base_price": NP_normal},
    "premium": {"name": NS_premium, "base_price": NP_premium},
    "ultra":   {"name": NS_ultra,   "base_price": NP_ultra},
    "menthol": {"name": NS_menthol, "base_price": NP_menthol},
}

CUSTOMER_DATA = {
    # Regular customers — gender: m=male, f=female
    "Stefan":    {"prompt": CPRO_Stefan,    "wtp": WTP_Stefan,    "winnable": False, "gender": "m"},
    "Johnathan": {"prompt": CPRO_Johnathan, "wtp": WTP_Johnathan, "winnable": False, "gender": "m"},
    "Bob":       {"prompt": CPRO_Bob,       "wtp": WTP_Bob,       "winnable": False, "gender": "m"},
    "Klaus":     {"prompt": CPRO_Klaus,     "wtp": WTP_Klaus,     "winnable": False, "gender": "m"},
    "Dieter":    {"prompt": CPRO_Dieter,    "wtp": WTP_Dieter,    "winnable": False, "gender": "m"},
    "Hans":      {"prompt": CPRO_Hans,      "wtp": WTP_Hans,      "winnable": False, "gender": "m"},
    "Marco":     {"prompt": CPRO_Marco,     "wtp": WTP_Marco,     "winnable": False, "gender": "m"},
    "Tobias":    {"prompt": CPRO_Tobias,    "wtp": WTP_Tobias,    "winnable": False, "gender": "m"},
    "Felix":     {"prompt": CPRO_Felix,     "wtp": WTP_Felix,     "winnable": False, "gender": "m"},
    "Patrick":   {"prompt": CPRO_Patrick,   "wtp": WTP_Patrick,   "winnable": False, "gender": "m"},
    "Lukas":     {"prompt": CPRO_Lukas,     "wtp": WTP_Lukas,     "winnable": False, "gender": "m"},
    "Tim":       {"prompt": CPRO_Tim,       "wtp": WTP_Tim,       "winnable": False, "gender": "m"},
    "Nico":      {"prompt": CPRO_Nico,      "wtp": WTP_Nico,      "winnable": False, "gender": "m"},
    "Fatima":    {"prompt": CPRO_Fatima,    "wtp": WTP_Fatima,    "winnable": False, "gender": "f"},
    "Sandra":    {"prompt": CPRO_Sandra,    "wtp": WTP_Sandra,    "winnable": False, "gender": "f"},
    "Melanie":   {"prompt": CPRO_Melanie,   "wtp": WTP_Melanie,   "winnable": False, "gender": "f"},
    "Jessica":   {"prompt": CPRO_Jessica,   "wtp": WTP_Jessica,   "winnable": False, "gender": "f"},
    "Petra":     {"prompt": CPRO_Petra,     "wtp": WTP_Petra,     "winnable": False, "gender": "f"},
    "Anna":      {"prompt": CPRO_Anna,      "wtp": WTP_Anna,      "winnable": False, "gender": "f"},
    "Leonie":    {"prompt": CPRO_Leonie,    "wtp": WTP_Leonie,    "winnable": False, "gender": "f"},
    "Sabine":    {"prompt": CPRO_Sabine,    "wtp": WTP_Sabine,    "winnable": False, "gender": "f"},
    "Ralf":      {"prompt": CPRO_Ralf,      "wtp": WTP_Ralf,      "winnable": False, "gender": "m"},
    "Gerhard":   {"prompt": CPRO_Gerhard,   "wtp": WTP_Gerhard,   "winnable": False, "gender": "m"},

    # Winnable customers
    "Stefanie":  {"prompt": CPRO_Stefanie, "wtp": WTP_Stefanie, "winnable": True,
                  "win_chance": WIN_CHANCE_Stefanie, "state": "krank - braucht dringend Nasenspray", "gender": "f"},
    "Dr_Müller": {"prompt": CPRO_Dr_Müller,  "wtp": WTP_Dr_Müller,  "winnable": True,
                  "win_chance": WIN_CHANCE_Dr_Müller,  "state": "diskret — Stammkunde werden?", "gender": "m"},
    "Horst":     {"prompt": CPRO_Horst,      "wtp": WTP_Horst,      "winnable": True,
                  "win_chance": WIN_CHANCE_Horst,      "state": "direkter Typ — will guten Preis", "gender": "m"},
    "Claudia":   {"prompt": CPRO_Claudia,    "wtp": WTP_Claudia,    "winnable": True,
                  "win_chance": WIN_CHANCE_Claudia,    "state": "Anwältin — will Stammkundin werden", "gender": "f"},
    "Erwin":     {"prompt": CPRO_Erwin,      "wtp": WTP_Erwin,      "winnable": True,
                  "win_chance": WIN_CHANCE_Erwin,      "state": "für seine Frau — verzweifelt", "gender": "m"},
    "Natascha":  {"prompt": CPRO_Natascha,   "wtp": WTP_Natascha,   "winnable": True,
                  "win_chance": WIN_CHANCE_Natascha,   "state": "Influencerin — will diskret bleiben", "gender": "f"},
    "Benjamin":  {"prompt": CPRO_Benjamin,   "wtp": WTP_Benjamin,   "winnable": True,
                  "win_chance": WIN_CHANCE_Benjamin,   "state": "neugieriger Student", "gender": "m"},
    "Ingrid":    {"prompt": CPRO_Ingrid,     "wtp": WTP_Ingrid,     "winnable": True,
                  "win_chance": WIN_CHANCE_Ingrid,     "state": "Rentnerin — freundlich aber bestimmt", "gender": "f"},
    "Markus":    {"prompt": CPRO_Markus,     "wtp": WTP_Markus,     "winnable": True,
                  "win_chance": WIN_CHANCE_Markus,     "state": "Journalist — angeblich für Recherche", "gender": "m"},
    "Yara":      {"prompt": CPRO_Yara,       "wtp": WTP_Yara,       "winnable": True,
                  "win_chance": WIN_CHANCE_Yara,       "state": "Tänzerin — will Stammkundin werden", "gender": "f"},
    "Dietmar":   {"prompt": CPRO_Dietmar,    "wtp": WTP_Dietmar,    "winnable": True,
                  "win_chance": WIN_CHANCE_Dietmar,    "state": "Bodyguard — kauft für seinen Boss", "gender": "m"},
}

# ─────────────────────────────────────────────────
#  SAVE / LOAD
# ─────────────────────────────────────────────────

SAVE_FILE = os.path.expanduser("~/Documents/.dummtopia_save.json")

def save_game(state):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        # Make sure settings sub-dict gets merged too
        merged_settings = dict(DEFAULT_STATE["settings"])
        merged_settings.update(data.get("settings", {}))
        merged["settings"] = merged_settings
        return merged
    return dict(DEFAULT_STATE)

# ─────────────────────────────────────────────────
#  IN-GAME TIME SYSTEM
# ─────────────────────────────────────────────────

INGAME_WEEK_DAYS = 7

def ingame_start_if_needed(state):
    if not state.get("ingame_start_real"):
        state["ingame_start_real"] = time.time()
        state["ingame_day_notified"] = 0
        save_game(state)

def get_ingame_time(state):
    start = state.get("ingame_start_real")
    if not start:
        return 1, 8, 0
    day_len = state["settings"]["day_length_seconds"]
    elapsed = time.time() - start
    total_ingame_days = int(elapsed // day_len)
    day = (total_ingame_days % INGAME_WEEK_DAYS) + 1
    day_progress = (elapsed % day_len) / day_len
    ingame_hour = int(day_progress * 24)
    ingame_minute = int((day_progress * 24 * 60) % 60)
    return day, ingame_hour, ingame_minute

def get_ingame_day(state):
    d, _, _ = get_ingame_time(state)
    return d

INGAME_WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

INGAME_NEWS_POOL = [
    ["Dummtopia Polizeibericht: Erhöhte Streifenaktivität in der Innenstadt.",
     "Marktgerücht: Neue Lieferung 'Frischer Ware' soll morgen ankommen.",
     "Anwohner klagen über mysteriöse Sniffgeräusche in der Unterführung."],
    ["Bürgermeister kündigt 'Null-Toleranz gegen Nasenspray' an.",
     "Schwarzmarkt-Preis für Premium-Ware um 12% gestiegen.",
     "Zeuge berichtet: Mann mit Plastiktüte rannte verdächtig schnell."],
    ["Lokale Drogenrazzia: Polizei findet nur Erkältungssalbe.",
     "Insider-Tipp: Neue Kunden sollen heute die Stadt betreten.",
     "Wettervorhersage: Trocken und klar — ideal für Straßengeschäfte."],
    ["Mafiabosse treffen sich im Restaurant 'La Nase'.",
     "Gerücht: Korrupter Beamter soll befördert worden sein.",
     "Nasenspray-Abhängige berichten von neuer 'Ultra'-Variante."],
    ["Polizei verstärkt Patrouillen nach anonymem Hinweis.",
     "Schwarzmarktbericht: Mentholware ist heute heiß begehrt.",
     "Stadtrat debattiert über Entkriminalisierung von Nasenspray."],
    ["Wochenend-Rushhour auf dem Schwarzmarkt erwartet.",
     "Stammkunde Stefan wurde zuletzt in der Nähe der Brücke gesehen.",
     "Mafia-Kredit-Zinsen bleiben diese Woche 'gnädig', heißt es."],
    ["Sonntagsruhe? Nicht für Dealer. Kunden sind aktiver als je zuvor.",
     "Ende der Woche: Zeit, Schulden zu begleichen.",
     "Stadtmagazin: 'Das geheime Leben der Nasenspray-Dealer von Dummtopia'"],
]

def get_ingame_news(state):
    day = get_ingame_day(state)
    idx = (day - 1) % len(INGAME_NEWS_POOL)
    return INGAME_NEWS_POOL[idx]

def check_and_show_news(state):
    if not state["settings"].get("news_notifications", True):
        return state
    day = get_ingame_day(state)
    last_notified = state.get("ingame_day_notified", 0)
    if day != last_notified:
        state["ingame_day_notified"] = day
        save_game(state)
        _show_news_popup(state, day)
    return state

def _show_news_popup(state, day):
    clear()
    weekday = INGAME_WEEKDAYS[(day - 1) % 7]
    print()
    print(cyan(bold(f"  ╔══════════════════════════════════════════════════╗")))
    print(cyan(bold(f"  ║     {T('news_header', weekday=weekday, day=day):<42} ║")))
    print(cyan(bold(f"  ╚══════════════════════════════════════════════════╝")))
    print()
    news = get_ingame_news(state)
    for n in news:
        slow_print(f"  • {yellow(n)}", 0.015)
    print()
    print(dim(f"  {T('news_settings_hint')}"))
    print()
    input(dim(f"  {T('news_continue')}"))

def format_clock_line(state):
    d, ih, im = get_ingame_time(state)
    weekday = INGAME_WEEKDAYS[(d - 1) % 7]
    real_now = time.strftime("%H:%M:%S")
    real_date = time.strftime("%d.%m.%Y")
    ingame_str = f"{weekday}. {ih:02d}:{im:02d} Uhr"
    line1 = dim(f"  {T('realtime_label', time=bold(real_now), date=real_date)}")
    line2 = cyan(f"  {T('ingame_label', time=bold(ingame_str), day=d)}")
    return line1 + "\n" + line2

# ─────────────────────────────────────────────────
#  SELL CHANCE CALCULATOR (character-aware)
# ─────────────────────────────────────────────────

def sell_chance(base_price, set_price, wtp):
    """Base sell chance, 0-1."""
    ratio = set_price / base_price
    tolerance = 0.05 + (wtp / 10) * 0.5
    threshold = 1.0 + tolerance
    if ratio <= threshold:
        return 0.95
    penalty = (ratio - threshold) * 1.5
    chance = max(0.05, 0.95 - penalty)
    return round(chance, 2)

def sell_chance_character(base_price, set_price, wtp, character, gender, custom_offer=False):
    """
    Adjusted sell chance based on character stats and customer gender.
    selling_power boosts male customers.
    charisma boosts female customers.
    picky_bonus applies when WTP < 4.
    """
    base = sell_chance(base_price, set_price, wtp)
    stats = CHARACTER_STATS.get(character, CHARACTER_STATS["Philipp"])

    if gender == "m":
        modifier = (stats["selling_power"] - 1.0) * 0.3   # scale it down so it's not OP
    else:
        modifier = (stats["charisma"] - 1.0) * 0.3

    if wtp < 4:
        modifier += stats["picky_bonus"]

    result = min(0.97, max(0.04, base + modifier))
    return round(result, 2)

# ─────────────────────────────────────────────────
#  CHARACTER SELECTION SCREEN
# ─────────────────────────────────────────────────

def choose_character(state):
    clear()
    print()
    print(cyan(bold(f"  ╔══════════════════════════════════════════════════════╗")))
    print(cyan(bold(f"  ║           {T('char_select_title').center(42)}║")))
    print(cyan(bold(f"  ╚══════════════════════════════════════════════════════╝")))
    print()
    slow_print(dim(f"  {T('char_select_prompt')}"), 0.015)
    print()

    chars = [
        ("1", "Philipp", "char_philipp_name", "char_philipp_desc"),
        ("2", "Joseph",  "char_joseph_name",  "char_joseph_desc"),
    ]
    for key, char_id, name_key, desc_key in chars:
        print(f"  [{cyan(key)}] {bold(yellow(T(name_key)))}")
        print(f"      {dim(T(desc_key))}")
        print()

    print(dim(f"  ℹ  {T('char_select_hint')}"))
    print()

    while True:
        ch = getch_timeout(60)
        if ch == '1':
            state["character"] = "Philipp"
            state["dealer_name"] = "Philipp"
            break
        elif ch == '2':
            state["character"] = "Joseph"
            state["dealer_name"] = "Joseph"
            break

    print(green(f"\n  ✓ Du spielst als {bold(state['dealer_name'])}!"))
    time.sleep(1.2)

# ─────────────────────────────────────────────────
#  FIRST LAUNCH
# ─────────────────────────────────────────────────

def first_launch(state):
    clear()
    print("\n" * 2)
    print(cyan(bold("╔══════════════════════════════════════════════════════╗")))
    print(cyan(bold(f"║              {T('welcome_title_1').center(40)}║")))
    print(cyan(bold(f"║              {T('welcome_title_2').center(40)}║")))
    print(cyan(bold("╚══════════════════════════════════════════════════════╝")))
    print()
    time.sleep(0.5)
    slow_print(dim(T("welcome_lore_1")), 0.025)
    time.sleep(0.3)
    slow_print(dim(T("welcome_lore_2")), 0.025)
    time.sleep(0.3)
    slow_print(dim(T("welcome_lore_3")), 0.025)
    time.sleep(0.6)
    print()
    slow_print(red(bold(T("welcome_warning"))), 0.04)
    print()
    time.sleep(0.3)

    slow_print(dim(T("controls_title")), 0.01)
    controls = [
        ("s → e",   T("controls_rename")),
        ("s → s → e", T("controls_settings")),
        ("t",       T("controls_system")),
        ("q",       T("controls_quit")),
    ]
    for k, v in controls:
        print(f"  {cyan(k):<20} {dim(v)}")
    print()
    input(dim(f"[ {T('welcome_enter')} ]"))

    # Character selection
    choose_character(state)

    state["first_launch"] = False
    save_game(state)

# ─────────────────────────────────────────────────
#  MAIN MENU
# ─────────────────────────────────────────────────

def main_menu(state):
    ingame_start_if_needed(state)
    state = check_and_show_news(state)
    clear()
    name = state["dealer_name"]
    char = state.get("character", "Philipp")
    bal  = state["balance"]
    lvl  = state["level"]

    print()
    print(format_clock_line(state))
    print()
    print(cyan(bold(f"  DUMMTOPIA  ·  Level {lvl}")))
    print(dim(f"  Dealer: {name} [{char}]  |  {green('€'+str(round(bal,2)))}"))
    if state["rebirth_count"] > 0:
        print(dim(f"  Rebirths: {state['rebirth_count']}  |  RP: {magenta(str(state['rebirth_points']))}"))
    if state.get("loan_amount", 0) > 0:
        deadline = state.get("loan_deadline")
        remaining = max(0, int(deadline - time.time())) if deadline else 0
        hrs = remaining // 3600
        mins = (remaining % 3600) // 60
        secs = remaining % 60
        print(red(bold(f"  ⚠  MAFIA-SCHULDEN: €{round(state['loan_amount'],2)}  |  Zeit: {hrs:02d}:{mins:02d}:{secs:02d}")))
    print()

    options = [
        ("1", T("menu_serve"),     "green"),
        ("2", T("menu_shop"),      "cyan"),
        ("3", T("menu_prices"),    "yellow"),
        ("4", T("menu_inventory"), "cyan"),
        ("5", T("menu_level"),     "magenta"),
    ]
    if lvl >= 2:
        options.append(("6", T("menu_customer_shop"), "cyan"))
        options.append(("7", T("menu_phone"),         "yellow"))
    if lvl >= 3:
        options.append(("8", T("menu_distraction"),   "cyan"))
    if state["rebirth_points"] > 0 or state["rebirth_count"] > 0:
        options.append(("R", T("menu_rebirth"),       "magenta"))

    options.append(("9", T("menu_settings"), "dim"))
    options.append(("M", T("menu_mafia"),    "red"))
    options.append(("q", T("menu_quit"),     "red"))

    for key, label, col in options:
        c = {"green": green, "cyan": cyan, "yellow": yellow,
             "magenta": magenta, "dim": dim, "red": red}.get(col, str)
        print(f"  [{cyan(key)}] {c(label)}")

    print()

    ch = get_menu_input(state)
    return ch

def get_menu_input(state):
    """Returns a single action string."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    if ch == 's':
        ch2 = getch_timeout(1.0)
        if ch2 == 'e':
            return 'rename'
        elif ch2 == 's':
            ch3 = getch_timeout(1.0)
            if ch3 == 'e':
                return 'game_settings'
        return 'menu'
    return ch

# ─────────────────────────────────────────────────
#  RENAME
# ─────────────────────────────────────────────────

def rename_dealer(state):
    clear()
    print(cyan(bold(f"\n  === {T('rename_title')} ===")))
    print(dim(f"  {T('rename_current', name=state['dealer_name'])}"))
    print()
    new_name = input(f"  {T('rename_prompt')}").strip()
    if new_name:
        state["dealer_name"] = new_name
        save_game(state)
        print(green(f"  {T('rename_ok', name=bold(new_name))}"))
    else:
        print(dim(f"  {T('rename_abort')}"))
    time.sleep(1.2)

# ─────────────────────────────────────────────────
#  INVENTORY DISPLAY
# ─────────────────────────────────────────────────

def show_inventory(state, pause=True):
    clear()
    print(cyan(bold(f"\n  === {T('inv_title')} ===")))
    inv = state["inventory"]
    if not inv:
        print(red(f"  {T('inv_empty')}"))
    else:
        counts = {}
        for k in inv:
            counts[k] = counts.get(k, 0) + 1
        for k, cnt in counts.items():
            d = SPRAY_DATA.get(k, {})
            name = d.get("name", k)
            base = d.get("base_price", 0)
            custom = state["custom_prices"].get(k, base)
            chance = sell_chance(base, custom, 5) * 100
            print(f"  [{cyan(k[0].upper())}] {name}")
            print(f"      Anzahl: {cnt}  |  Basispreis: €{base}  |  Dein Preis: {yellow('€'+str(round(custom,2)))}  |  Ø Chance: {round(chance)}%")
    print()
    if state["hidden_stash"]:
        print(dim(f"  {T('inv_stash', items=', '.join(state['hidden_stash']))}"))
    if pause:
        input(dim(T("inv_enter")))

# ─────────────────────────────────────────────────
#  PRICE SETTINGS
# ─────────────────────────────────────────────────

def price_settings(state):
    clear()
    print(cyan(bold(f"\n  === {T('price_title')} ===")))
    sprays = list(SPRAY_DATA.keys())
    for i, k in enumerate(sprays):
        d = SPRAY_DATA[k]
        custom = state["custom_prices"].get(k, d["base_price"])
        print(f"  [{i+1}] {d['name']} | Basis: €{d['base_price']} | Aktuell: {yellow('€'+str(round(custom,2)))}")
    print(f"  [0] Zurück")
    print()
    choice = input("  Auswahl: ").strip()
    if choice == '0' or not choice.isdigit():
        return
    idx = int(choice) - 1
    if 0 <= idx < len(sprays):
        key = sprays[idx]
        d = SPRAY_DATA[key]
        print()
        try:
            new_price = float(input(f"  {T('price_new_prompt', name=d['name'], base=d['base_price'])}").strip())
        except ValueError:
            print(red(f"  {T('price_invalid')}"))
            time.sleep(1)
            return
        print()
        print(dim(f"  {T('price_chances')}"))
        for wtp in [2, 5, 9]:
            c = sell_chance(d["base_price"], new_price, wtp) * 100
            print(f"    WTP {wtp}: {round(c)}%")
        print()
        confirm = input(yellow(f"  {T('price_set_prompt')}")).strip().lower()
        if confirm == 'j':
            state["custom_prices"][key] = new_price
            save_game(state)
            print(green(f"  {T('price_set_ok')}"))
        else:
            print(dim(f"  {T('price_abort')}"))
        time.sleep(1.2)

# ─────────────────────────────────────────────────
#  NS SHOP
# ─────────────────────────────────────────────────

def ns_shop(state):
    clear()
    print(cyan(bold(f"\n  === {T('shop_title')} ===")))
    print(dim(f"  {T('shop_balance')}{green('€'+str(round(state['balance'],2)))}"))
    print()

    available = []
    if state["level"] >= 1:
        available = ["normal", "menthol"]
    if state["level"] >= 2:
        available.append("premium")
    if state["level"] >= 3:
        available.append("ultra")

    for i, k in enumerate(available):
        d = SPRAY_DATA[k]
        print(f"  [{i+1}] {d['name']} — €{d['base_price']}")
    print(f"  [0] Zurück")
    print()
    choice = input(f"  {T('shop_buy_prompt')}").strip()
    if choice == '0' or not choice.isdigit():
        return
    idx = int(choice) - 1
    if 0 <= idx < len(available):
        key = available[idx]
        d = SPRAY_DATA[key]
        try:
            qty = int(input(f"  {T('shop_qty_prompt', name=d['name'])}").strip())
        except ValueError:
            return
        cost = d["base_price"] * qty
        if cost > state["balance"]:
            print(red(f"  {T('shop_not_enough', cost=cost)}"))
        else:
            state["balance"] -= cost
            state["inventory"].extend([key] * qty)
            save_game(state)
            print(green(f"  {T('shop_bought', qty=qty, name=d['name'], cost=round(cost,2))}"))
    time.sleep(1.5)

# ─────────────────────────────────────────────────
#  LEVEL UPGRADE
# ─────────────────────────────────────────────────

def level_upgrade(state):
    clear()
    lvl = state["level"]
    bal = state["balance"]
    ratings = list(state["customer_ratings"].values())
    avg_rating = (sum(ratings) / len(ratings)) if ratings else 3.0

    upgrade_cost = round(100 * (lvl ** 1.8) * (1 / max(avg_rating, 0.5)), 2)

    if state["rebirth_count"] > 0:
        upgrade_cost = round(upgrade_cost * 0.7, 2)

    max_level = 3
    if lvl >= max_level:
        print(cyan(f"\n  {T('level_max')}"))
        print(dim(f"  {T('level_rebirth_hint')}"))
        print()
        rb = input(yellow(f"  {T('level_rebirth_prompt')}")).strip().lower()
        if rb == 'j':
            state["rebirth_points"] += 3
            state["rebirth_count"] += 1
            state["level"] = 1
            state["balance"] = 50.0
            state["inventory"] = ["normal", "normal"]
            state["custom_prices"] = {}
            save_game(state)
            print(magenta(bold(f"\n  {T('level_rebirth_done', n=state['rebirth_count'])}")))
        time.sleep(2)
        return

    print(cyan(bold(f"\n  === {T('level_title')} ===")))
    print(dim(f"  {T('level_current', cur=lvl, next=lvl+1)}"))
    print(dim(f"  {T('level_avg_rating', rating=round(avg_rating,1))}"))
    print(dim(f"  {T('level_cost', cost=upgrade_cost)}"))
    print()
    if lvl+1 == 2:
        print(dim("  Freischaltet: Kunden Shop, Telefon System"))
    elif lvl+1 == 3:
        print(dim("  Freischaltet: Ablenkung Shop, Ultra Nasenspray"))
    print()

    if bal < upgrade_cost:
        print(red(f"  {T('level_not_enough', missing=round(upgrade_cost-bal,2))}"))
        time.sleep(1.5)
        return

    confirm = input(yellow(f"  {T('level_upgrade_prompt')}")).strip().lower()
    if confirm == 'j':
        state["balance"] -= upgrade_cost
        state["level"] += 1
        save_game(state)
        print(green(bold(f"\n  {T('level_upgraded', lvl=state['level'])}")))
    time.sleep(1.5)

# ─────────────────────────────────────────────────
#  CUSTOMER SHOP
# ─────────────────────────────────────────────────

def customer_shop(state):
    if state["level"] < 2:
        print(red("  Level 2 benötigt."))
        time.sleep(1)
        return
    clear()
    print(cyan(bold(f"\n  === {T('customer_shop_title')} ===")))
    print(dim(f"  {T('customer_shop_hint')}"))
    print()
    winnable = state["winnable_customers"]
    already_won = state["won_customers"]
    pending = state["pending_samples"]

    available = [c for c in winnable if c not in already_won and c not in pending]
    if not available:
        print(dim(f"  {T('customer_shop_none')}"))
        time.sleep(1.5)
        return

    for i, name in enumerate(available):
        d = CUSTOMER_DATA[name]
        status = d.get("state", "Unbekannt")
        print(f"  [{i+1}] {bold(name)} | Status: {dim(status)} | WTP: {'★'*d['wtp']}")

    print(f"  [0] Zurück")
    print()
    choice = input("  Auswahl: ").strip()
    if choice == '0' or not choice.isdigit():
        return
    idx = int(choice) - 1
    if 0 <= idx < len(available):
        name = available[idx]
        cost = 20 + CUSTOMER_DATA[name]["wtp"] * 5
        print(f"\n  {T('customer_shop_contact_cost', cost=cost)}")
        confirm = input(yellow(f"  {T('customer_shop_contact_prompt')}")).strip().lower()
        if confirm == 'j':
            if state["balance"] < cost:
                print(red(f"  {T('customer_shop_not_enough')}"))
            else:
                state["balance"] -= cost
                state["pending_samples"].append(name)
                save_game(state)
                print(green(f"  {T('customer_shop_pending', name=name)}"))
        time.sleep(1.5)

# ─────────────────────────────────────────────────
#  DISTRACTION SHOP
# ─────────────────────────────────────────────────

def distraction_shop(state):
    if state["level"] < 3:
        print(red("  Level 3 benötigt."))
        time.sleep(1)
        return
    clear()
    print(cyan(bold(f"\n  === {T('distraction_shop_title')} ===")))
    options = [
        ("Dummy-Kiosk",    150, 30,  "polizei_min"),
        ("Fake-Marktstand",300, 60,  "polizei_max"),
        ("Bestechung",     500, 120, "both"),
    ]
    settings = state["settings"]
    for i, (name, cost, bonus, key) in enumerate(options):
        if key == "both":
            desc = f"+120s auf beide Intervalle"
        else:
            kk = "min" if "min" in key else "max"
            desc = f"+{bonus}s auf Polizei {kk}-Intervall"
        print(f"  [{i+1}] {name} — {yellow('€'+str(cost))} — {dim(desc)}")
    print(f"  [0] Zurück")
    print()
    choice = input("  Auswahl: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        idx = int(choice) - 1
        name, cost, bonus, key = options[idx]
        if state["balance"] < cost:
            print(red("  Nicht genug Geld."))
        else:
            state["balance"] -= cost
            if key == "both":
                state["settings"]["police_interval_min"] += bonus
                state["settings"]["police_interval_max"] += bonus
            elif "min" in key:
                state["settings"]["police_interval_min"] += bonus
            else:
                state["settings"]["police_interval_max"] += bonus
            save_game(state)
            print(green(f"  ✓ {name} gekauft! Polizei-Intervall erhöht."))
    time.sleep(1.5)

# ─────────────────────────────────────────────────
#  REBIRTH SHOP
# ─────────────────────────────────────────────────

def rebirth_shop(state):
    clear()
    rp = state["rebirth_points"]
    print(magenta(bold(f"\n  === {T('rebirth_shop_title', rp=rp)} ===")))
    options = [
        (1, "Goldene Nase",         "Alle Preise -10%"),
        (2, "VIP-Liste",             "+2 WTP für alle Kunden"),
        (3, "Korrupter Polizist",    "Polizei ignoriert dich einmal"),
        (5, "Schwarzmarkt-Kontakt", "Unlocks Ultra Nasenspray sofort"),
    ]
    for cost, name, desc in options:
        avail = green("✓") if rp >= cost else red("✗")
        print(f"  {avail} [{cost} RP] {bold(name)} — {dim(desc)}")
    print(f"\n  [0] Zurück")
    print()
    choice = input(f"  {T('rebirth_spend_prompt')}").strip()
    if choice == '0':
        return
    for cost, name, desc in options:
        if choice.lower() in name.lower():
            if rp < cost:
                print(red("  Nicht genug RP."))
            else:
                state["rebirth_points"] -= cost
                apply_rebirth_perk(state, name)
                save_game(state)
                print(green(f"  ✓ {name} aktiviert!"))
            break
    time.sleep(1.5)

def apply_rebirth_perk(state, name):
    if "Goldene" in name:
        for k in SPRAY_DATA:
            base = SPRAY_DATA[k]["base_price"]
            current = state["custom_prices"].get(k, base)
            state["custom_prices"][k] = round(current * 0.9, 2)
    elif "VIP" in name:
        state.setdefault("wtp_bonus", 0)
        state["wtp_bonus"] = state.get("wtp_bonus", 0) + 2
    elif "Korrupt" in name:
        state["police_skip"] = state.get("police_skip", 0) + 1
    elif "Schwarzmarkt" in name:
        state["level"] = max(state["level"], 3)

# ─────────────────────────────────────────────────
#  SYSTEM SETTINGS
# ─────────────────────────────────────────────────

def settings_menu(state):
    while True:
        clear()
        s = state["settings"]
        print(cyan(bold(f"\n  === {T('settings_title')} ===")))
        print(dim(f"  Gespeichert in: {SAVE_FILE}"))
        print(dim(f"  Sprache/Locale: {_ACTIVE_LOCALE}  (auto erkannt — manuell via [8])"))
        print()
        print(cyan("  ── Spieleinstellungen ──────────────────"))
        print(f"  [1] {T('settings_rename'):<28} (aktuell: {bold(state['dealer_name'])})")
        print(f"  [2] {T('settings_reset_prices')}")
        print()
        print(cyan("  ── Systemeinstellungen ─────────────────"))
        print(f"  [3] {T('settings_police_min'):<28} (aktuell: {yellow(str(s['police_interval_min'])+'s')})")
        print(f"  [4] {T('settings_police_max'):<28} (aktuell: {yellow(str(s['police_interval_max'])+'s')})")
        print(f"  [5] {T('settings_day_length'):<28} (aktuell: {yellow(str(s['day_length_seconds'])+'s')})")
        news_status = green(T("settings_news_on")) if s.get("news_notifications", True) else red(T("settings_news_off"))
        print(f"  [7] {T('settings_news'):<28} (aktuell: {news_status})")
        print(f"  [8] Sprache/Locale manuell setzen (aktuell: {cyan(_ACTIVE_LOCALE)})")
        print()
        print(cyan("  ── Gefährlich ──────────────────────────"))
        print(f"  [6] {red(T('settings_delete'))}")
        print(f"  [0] {T('settings_back')}")
        print()
        choice = input("  Auswahl: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            rename_dealer(state)
        elif choice == '2':
            confirm = input(yellow(f"  {T('settings_prices_reset_prompt')}")).strip().lower()
            if confirm == 'j':
                state["custom_prices"] = {}
                save_game(state)
                print(green(f"  {T('settings_prices_reset_ok')}"))
                time.sleep(1)
        elif choice == '3':
            v = input(f"  Neuer Min-Wert in Sekunden (aktuell {s['police_interval_min']}s): ").strip()
            if v.isdigit():
                state["settings"]["police_interval_min"] = int(v)
                save_game(state)
                print(green(f"  ✓ Gesetzt auf {v}s"))
                time.sleep(0.8)
        elif choice == '4':
            v = input(f"  Neuer Max-Wert in Sekunden (aktuell {s['police_interval_max']}s): ").strip()
            if v.isdigit():
                state["settings"]["police_interval_max"] = int(v)
                save_game(state)
                print(green(f"  ✓ Gesetzt auf {v}s"))
                time.sleep(0.8)
        elif choice == '5':
            v = input(f"  Tageslänge in Sekunden (aktuell {s['day_length_seconds']}s): ").strip()
            if v.isdigit():
                state["settings"]["day_length_seconds"] = int(v)
                save_game(state)
                print(green(f"  ✓ Gesetzt auf {v}s"))
                time.sleep(0.8)
        elif choice == '7':
            current = state["settings"].get("news_notifications", True)
            state["settings"]["news_notifications"] = not current
            save_game(state)
            status = green(T("settings_news_on")) if state["settings"]["news_notifications"] else red(T("settings_news_off"))
            print(green(f"  ✓ Nachrichten jetzt: {status}"))
            time.sleep(0.8)
        elif choice == '8':
            lc = input(f"  Locale-Code eingeben (z.B. 'de', 'en', leer = auto): ").strip().lower()
            state["settings"]["locale"] = lc if lc else None
            save_game(state)
            init_localization(state["settings"].get("locale"))
            print(green(f"  ✓ Locale gesetzt auf: {_ACTIVE_LOCALE}"))
            time.sleep(1)
        elif choice == '6':
            confirm = input(red(f"  {T('settings_delete_confirm')}")).strip()
            if confirm == 'JA':
                if os.path.exists(SAVE_FILE):
                    os.remove(SAVE_FILE)
                print(red(f"  {T('settings_deleted')}"))
                time.sleep(2)
                sys.exit(0)

# ─────────────────────────────────────────────────
#  SERVE MODE
# ─────────────────────────────────────────────────

# Police blackout window constants (seconds)
_PRE_POLICE_BLACKOUT  = 20   # no customers in last 20s before police
_POST_POLICE_BLACKOUT = 10   # no customers in first 10s after inspection ends

class ServeMode:
    def __init__(self, state):
        self.state = state
        self.running = True
        self.under_inspection = False
        self.inspection_end = 0
        self.inspection_ended_at = 0   # tracks when inspection last ended
        self.next_police = 0
        self.next_customer = 0
        self.message_log = []
        self.wtp_bonus = state.get("wtp_bonus", 0)
        self.character = state.get("character", "Philipp")
        self._schedule_police()
        self._schedule_customer()

    def _schedule_police(self):
        s = self.state["settings"]
        delay = random.randint(s["police_interval_min"], s["police_interval_max"])
        self.next_police = time.time() + delay

    def _schedule_customer(self):
        self.next_customer = time.time() + random.randint(15, 45)

    def _in_customer_blackout(self):
        """Returns True if it's too close to a police event to spawn customers."""
        now = time.time()
        # Pre-police blackout: last 20s before police arrives
        police_in = self.next_police - now
        if 0 < police_in <= _PRE_POLICE_BLACKOUT:
            return True
        # Post-inspection blackout: first 10s after inspection ended
        if self.inspection_ended_at > 0 and (now - self.inspection_ended_at) < _POST_POLICE_BLACKOUT:
            return True
        return False

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.message_log.append(f"[{dim(ts)}] {msg}")
        if len(self.message_log) > 8:
            self.message_log.pop(0)

    def render(self):
        clear()
        state = self.state
        bal   = round(state["balance"], 2)
        inv   = state["inventory"]
        lvl   = state["level"]

        print()
        print(format_clock_line(state))
        print()
        print(cyan(bold(f"  {T('serve_header', lvl=lvl)}")))
        print(dim(f"  Dealer: {state['dealer_name']} [{self.character}]  |  {green('€'+str(bal))}"))

        now = time.time()
        if not self.under_inspection:
            police_in = max(0, int(self.next_police - now))
            police_str = red(str(police_in)+'s') if police_in < 20 else str(police_in)+'s'
            print(dim(f"  {T('serve_police_in', sec=police_str)}"))
        else:
            inspection_left = max(0, int(self.inspection_end - now))
            print(red(bold(f"  {T('serve_razzia', sec=inspection_left)}")))

        counts = {}
        for k in inv:
            counts[k] = counts.get(k, 0) + 1
        inv_str = f"  {T('serve_inventory')}" + (", ".join(f"{SPRAY_DATA[k]['name']} x{v}" for k, v in counts.items()) if counts else red(T("serve_empty_inv")))
        print(inv_str)

        if state["pending_samples"]:
            for i, name in enumerate(state["pending_samples"]):
                print(yellow(f"  📱 [{i+1}] Probe liefern → {bold(name)}  (Taste: {name[0].upper()})"))
        if state["pending_samples"]:
            print(dim(f"  {T('sample_deliver_hint')}"))

        print()
        for line in self.message_log[-5:]:
            print(f"  {line}")

        print()
        if self.under_inspection:
            print(dim(f"  {T('serve_razzia_hint')}"))
        else:
            print(dim(f"  {T('serve_quit_hint')}"))

    def police_qte(self):
        """Hide inventory QTE."""
        self.under_inspection = True
        inv = list(self.state["inventory"])

        if not inv:
            self.log(dim(T("police_nothing")))
            inspection_dur = random.randint(5, 15)
            self.inspection_end = time.time() + inspection_dur
            self._schedule_police()
            return

        if self.state.get("police_skip", 0) > 0:
            self.state["police_skip"] -= 1
            self.log(green(T("police_corrupt")))
            inspection_dur = random.randint(10, 20)
            self.inspection_end = time.time() + inspection_dur
            self._schedule_police()
            return

        clear()
        print()
        print(red(bold(f"  {T('police_warning')}")))
        print()

        letters = [k[0].upper() for k in inv]
        random.shuffle(letters)

        remaining = list(letters)
        stash = list(inv)
        failed = False

        print(dim(f"  {T('police_hide_hint')}"))
        print(f"  {' '.join(cyan(l) for l in remaining)}")
        print()

        for i, letter in enumerate(letters):
            print(f"  {T('police_hide_item', letter=yellow(letter))}")
            ch = getch_timeout(2.0)
            if ch is None or ch.upper() != letter:
                failed = True
                break
            for k in stash:
                if k[0].upper() == letter:
                    stash.remove(k)
                    self.state["hidden_stash"].append(k)
                    self.state["inventory"].remove(k)
                    remaining.remove(letter)
                    print(green(f"  {T('police_hidden_ok', name=SPRAY_DATA[k]['name'])}"))
                    if remaining:
                        print(f"  {T('police_remaining', letters=' '.join(cyan(l) for l in remaining))}")
                    break

        if failed:
            exposed = len(self.state["inventory"])
            if exposed > 0:
                print()
                print(red(bold(f"  {T('police_caught')}")))
                self._apply_bust()
            else:
                print(green(f"  {T('police_all_hidden_close')}"))
        else:
            print(green(f"\n  {T('police_all_hidden')}"))

        inspection_dur = random.randint(30, 60)
        self.inspection_end = time.time() + inspection_dur
        self._schedule_police()
        time.sleep(2)

    def _apply_bust(self):
        state = self.state
        bal = state["balance"]
        lvl = state["level"]
        bail = round(min(bal * 0.4, 50 + lvl * 30 + bal * 0.15), 2)
        bail = max(20.0, bail)

        print(red(T("police_bail", bail=bail)))
        state["balance"] = max(0, state["balance"] - bail)
        state["total_busted"] += 1
        exposed = list(state["inventory"])
        state["inventory"] = []
        print(red(f"  {T('police_bust_inv', items=', '.join(SPRAY_DATA[k]['name'] for k in exposed))}"))
        save_game(state)
        time.sleep(3)

    def post_inspection_retrieval(self):
        """After inspection ends, take stash back."""
        if self.state["hidden_stash"]:
            self.state["inventory"].extend(self.state["hidden_stash"])
            self.state["hidden_stash"] = []
            save_game(self.state)
            self.log(green(T("police_stash_back")))
        self.inspection_ended_at = time.time()

    def customer_visit(self, target=None):
        state = self.state
        inv = state["inventory"]

        available_customers = list(state["unlocked_customers"]) + list(state["won_customers"])
        if not available_customers:
            return

        if target and (target in available_customers or target in state["pending_samples"]):
            name = target
        else:
            name = random.choice(available_customers)
        cdata = CUSTOMER_DATA[name]
        wtp = min(10, cdata["wtp"] + self.wtp_bonus)
        gender = cdata.get("gender", "m")

        clear()

        if self.under_inspection:
            print()
            print(dim(f"  {name} kommt näher..."))
            print(cyan(f'  "{name}: {T("customer_busy")}"'))
            self.log(dim(T("customer_left_razzia", name=name)))
            time.sleep(2.5)
            return

        print()
        print(cyan(bold(f"  === {T('customer_header', name=name)} ===")))
        print()
        print(cyan(f'  "{cdata["prompt"]}"'))
        print()
        time.sleep(5)

        # Pending sample delivery
        if name in state["pending_samples"]:
            deliver = input(yellow(f"  {T('sample_deliver_prompt', name=name)}")).strip().lower()
            if deliver == 'j':
                state["pending_samples"].remove(name)
                stats = CHARACTER_STATS.get(self.character, CHARACTER_STATS["Philipp"])
                win_chance = CUSTOMER_DATA[name].get("win_chance", 0.5)
                # Character win bonus (charisma for female, selling_power otherwise)
                if gender == "f":
                    win_chance = min(0.97, win_chance + stats["win_bonus"] * (stats["charisma"] / 1.0))
                else:
                    win_chance = min(0.97, win_chance + stats["win_bonus"])
                if random.random() < win_chance:
                    state["won_customers"].append(name)
                    self.log(green(T("sample_won_log", name=name)))
                    print(green(f"\n  {T('sample_won', name=name)}"))
                else:
                    self.log(yellow(T("sample_rejected_log", name=name)))
                    print(yellow(f"  {T('sample_rejected', name=name)}"))
                save_game(state)
                time.sleep(2.5)
                return

        if not inv:
            print(red(f"  {T('customer_no_inv')}"))
            self.log(dim(T("customer_left_no_inv", name=name)))
            time.sleep(2)
            return

        print(dim(f"  {T('customer_dealer_offers')}"))
        counts = {}
        for k in inv:
            counts[k] = counts.get(k, 0) + 1

        items_to_offer = list(counts.items())
        for k, cnt in items_to_offer:
            d = SPRAY_DATA[k]
            price = state["custom_prices"].get(k, d["base_price"])
            print(f"    {yellow('€'+str(round(price,2)))} für {d['name']} (x{cnt})")

        print()

        custom_offer = None
        if wtp < 4:
            print(yellow(f"  {T('customer_low_wtp', name=name, wtp=wtp)}"))
            special = input(f"  {T('customer_special_price_prompt')}").strip()
            if special:
                try:
                    custom_offer = float(special)
                except ValueError:
                    pass

        if not items_to_offer:
            return
        spray_key, _ = items_to_offer[0]
        d = SPRAY_DATA[spray_key]
        base_price = d["base_price"]
        sell_price = custom_offer if custom_offer else state["custom_prices"].get(spray_key, base_price)

        chance = sell_chance_character(base_price, sell_price, wtp, self.character, gender, custom_offer=bool(custom_offer))

        if random.random() < chance:
            state["inventory"].remove(spray_key)
            state["balance"] += sell_price
            state["total_sales"] += 1
            rating = round(random.uniform(3.5, 5.0) if sell_price <= base_price * 1.2 else random.uniform(2.0, 3.5), 1)
            prev = state["customer_ratings"].get(name, rating)
            state["customer_ratings"][name] = round((prev + rating) / 2, 1)

            # WTP bump — character-aware
            stats = CHARACTER_STATS.get(self.character, CHARACTER_STATS["Philipp"])
            wtp_up_prob = stats["wtp_up_chance"]
            if gender == "f":
                wtp_up_prob *= stats["charisma"]
            if custom_offer and random.random() < wtp_up_prob:
                CUSTOMER_DATA[name]["wtp"] = min(10, CUSTOMER_DATA[name]["wtp"] + 1)
                self.log(yellow(T("customer_wtp_up", name=name)))

            save_game(state)
            self.log(green(T("customer_sold_log", name=name, item=d["name"], price=round(sell_price,2))))
            print()
            print(green(bold(f"  {T('customer_sale_ok', price=round(sell_price,2))}")))
        else:
            self.log(dim(T("customer_rejected_log", name=name)))
            print()
            print(red(f"  {T('customer_sale_fail', name=name)}"))

        time.sleep(5)

    def run(self):
        self.log(green(T("serve_started")))

        while self.running:
            now = time.time()
            self.render()

            # Check inspection end
            if self.under_inspection and now >= self.inspection_end:
                self.under_inspection = False
                self.post_inspection_retrieval()

            # Police trigger
            if not self.under_inspection and now >= self.next_police:
                self.log(red(T("police_coming")))
                self.render()
                time.sleep(0.5)
                self.police_qte()
                continue

            ch = getch_timeout(1.0)
            if ch == 'q':
                self.running = False
                break

            # Sample delivery shortcut
            if ch and self.state["pending_samples"]:
                matched = None
                for pname in list(self.state["pending_samples"]):
                    if ch.upper() == pname[0].upper():
                        matched = pname
                        break
                if matched:
                    self._schedule_customer()
                    self.customer_visit(target=matched)
                    continue

            now = time.time()

            # Customer trigger — respect blackout window
            if not self.under_inspection and now >= self.next_customer:
                self._schedule_customer()
                if self._in_customer_blackout():
                    self.log(dim("(Kein Kunde — zu nah an der Polizei-Patrouille)"))
                    continue
                self.customer_visit()
                continue

        print(green(T("serve_ended")))
        save_game(self.state)
        time.sleep(1)


# ─────────────────────────────────────────────────
#  MAFIA LOAN SYSTEM
# ─────────────────────────────────────────────────

MAX_LOAN = 100.0

def get_loan_deadline_seconds(state):
    return 7 * state["settings"]["day_length_seconds"]

def mafia_loan(state):
    clear()
    print()
    print(red(bold("  ╔══════════════════════════════════════╗")))
    print(red(bold(f"  ║        {T('mafia_title_1').center(30)}║")))
    print(red(bold(f"  ║    {T('mafia_title_2').center(34)}║")))
    print(red(bold("  ╚══════════════════════════════════════╝")))
    print()

    active_loan = state.get("loan_amount", 0)

    if active_loan > 0:
        deadline = state.get("loan_deadline", 0)
        remaining = max(0, int(deadline - time.time()))
        hrs  = remaining // 3600
        mins = (remaining % 3600) // 60
        secs = remaining % 60
        print(red(f"  Du hast bereits eine offene Schuld von {bold('€'+str(round(active_loan,2)))}"))
        print(red(f"  Verbleibende Zeit: {hrs:02d}:{mins:02d}:{secs:02d}"))
        print(dim(f"  Dein Kontostand: {green('€'+str(round(state['balance'],2)))}"))
        print()
        print(dim("  [1] Schuld vollständig zurückzahlen"))
        print(dim("  [2] Teilbetrag zurückzahlen"))
        print(dim("  [0] Zurück (und beten)"))
        print()
        choice = input("  Auswahl: ").strip()
        if choice == '1':
            _mafia_repay(state)
        elif choice == '2':
            _mafia_repay_partial(state)
        return

    print(dim("  *Ein Mann in einem schwarzen Anzug lehnt sich über deinen Tisch.*"))
    print()
    slow_print(cyan(f'  {T("mafia_greet_1")}'), 0.03)
    slow_print(cyan(f'  {T("mafia_greet_2")}'), 0.03)
    slow_print(cyan(f'  {T("mafia_greet_3")}'), 0.03)
    print()

    try:
        amount_str = input(yellow(f"  {T('mafia_amount_prompt', max=MAX_LOAN)}")).strip()
        amount = float(amount_str)
    except ValueError:
        print(dim(f"  {T('mafia_abort')}"))
        time.sleep(1)
        return

    if amount <= 0:
        print(dim(f'  {T("mafia_wise")}'))
        time.sleep(2)
        return

    amount = min(round(amount, 2), MAX_LOAN)
    print()
    print(yellow(f"  {T('mafia_borrow', amount=amount)}"))
    ingame_days = 7
    real_hours = round(get_loan_deadline_seconds(state) / 3600, 1)
    print(red(f"  {T('mafia_deadline', days=ingame_days, hours=real_hours)}"))
    print(red(f"  {T('mafia_gameover_hint')}"))
    print()
    confirm = input(yellow(f"  {T('mafia_confirm')}")).strip().lower()
    if confirm != 'j':
        print(dim(f"  {T('mafia_abort')}"))
        time.sleep(1)
        return

    state["loan_amount"] = amount
    state["loan_deadline"] = time.time() + get_loan_deadline_seconds(state)
    state["balance"] += amount
    save_game(state)
    print()
    print(green(f"  {T('mafia_borrowed', amount=amount)}"))
    slow_print(cyan(f'  {T("mafia_goodbye_1")}'), 0.02)
    slow_print(cyan(f'  {T("mafia_goodbye_2")}'), 0.03)
    time.sleep(3)

def _mafia_repay(state):
    amount = round(state.get("loan_amount", 0), 2)
    if amount <= 0:
        print(dim("  Keine Schulden."))
        time.sleep(1)
        return

    if state["balance"] < amount:
        shortage = round(amount - state["balance"], 2)
        print(red(f"  ✗ Du hast nicht genug. Dir fehlen €{shortage}."))
        print(dim("  Viel Glück..."))
        time.sleep(2)
        return

    state["balance"] -= amount
    state["loan_amount"] = 0.0
    state["loan_deadline"] = None
    save_game(state)
    print(green(f"  ✓ €{amount} zurückgezahlt. Du bist frei."))
    slow_print(cyan('  *Er nickt.* "Pleasure doing business."'), 0.03)
    time.sleep(2.5)

def _mafia_repay_partial(state):
    total_debt = round(state.get("loan_amount", 0), 2)
    if total_debt <= 0:
        print(dim("  Keine Schulden."))
        time.sleep(1)
        return

    print()
    print(red(f"  Gesamtschuld: €{total_debt}"))
    print(dim(f"  Dein Kontostand: {green('€'+str(round(state['balance'],2)))}"))
    print()
    slow_print(cyan('  *Er zieht eine Augenbraue hoch.* "Teilzahlung? Na gut.'), 0.025)
    slow_print(cyan('   Aber der Rest — den erwarte ich pünktlich."'), 0.025)
    print()

    try:
        pay_str = input(yellow(f"  Wie viel willst du zurückzahlen? (max €{total_debt}): €")).strip()
        pay = round(float(pay_str), 2)
    except ValueError:
        print(dim("  Abgebrochen."))
        time.sleep(1)
        return

    if pay <= 0:
        print(dim("  Abgebrochen."))
        time.sleep(1)
        return

    pay = min(pay, total_debt)

    if state["balance"] < pay:
        shortage = round(pay - state["balance"], 2)
        print(red(f"  ✗ Nicht genug Geld. Dir fehlen €{shortage}."))
        time.sleep(2)
        return

    state["balance"] -= pay
    new_debt = round(total_debt - pay, 2)
    state["loan_amount"] = new_debt

    if new_debt <= 0:
        state["loan_amount"] = 0.0
        state["loan_deadline"] = None
        print(green(f"  ✓ Alles bezahlt! Du bist schuldenfrei."))
        slow_print(cyan('  *Er nickt langsam.* "Respekt. Bis zum nächsten Mal."'), 0.03)
    else:
        print(green(f"  ✓ €{pay} bezahlt. Verbleibende Schuld: {red('€'+str(new_debt))}"))
        slow_print(cyan(f'  *Er zählt das Geld.* "Noch €{new_debt}. Vergiss das nicht."'), 0.03)

    save_game(state)
    time.sleep(2.5)

def check_mafia_deadline(state):
    if state.get("loan_amount", 0) <= 0:
        return False, state
    deadline = state.get("loan_deadline")
    if deadline and time.time() > deadline:
        new_state = _mafia_death(state)
        return True, new_state
    return False, state

def _mafia_death(state):
    clear()
    print()
    time.sleep(0.5)
    print(red(bold("  ════════════════════════════════════════")))
    print()
    slow_print(red(bold(f"  {T('mafia_death_time')}")), 0.05)
    time.sleep(0.4)
    slow_print(red(f"  {T('mafia_death_knock_1')}"), 0.04)
    time.sleep(0.6)
    slow_print(red(f"  {T('mafia_death_knock_2')}"), 0.08)
    time.sleep(0.8)
    slow_print(red(f"  {T('mafia_death_knock_3')}"), 0.08)
    time.sleep(1)
    print()
    slow_print(red(bold(f'  {T("mafia_death_shout")}')), 0.06)
    time.sleep(1.5)
    print()
    slow_print(dim(f"  {T('mafia_death_desc_1')}"), 0.03)
    time.sleep(0.5)
    slow_print(dim(f"  {T('mafia_death_desc_2', name=state.get('dealer_name', 'Der Dealer'))}"), 0.03)
    time.sleep(1)
    print()
    print(red(bold(f"  {T('mafia_gameover')}")))
    print(red(f"  {T('mafia_gameover_reset')}"))
    print()
    time.sleep(3)
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    input(dim(f"  {T('mafia_enter_restart')}"))
    new_state = dict(DEFAULT_STATE)
    save_game(new_state)
    return new_state


# ─────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────

def main():
    state = load_game()
    # Init localization from saved settings (or auto-detect)
    init_localization(state["settings"].get("locale"))

    if state.get("first_launch", True):
        first_launch(state)

    ingame_start_if_needed(state)

    while True:
        dead, state = check_mafia_deadline(state)
        if dead:
            continue

        action = main_menu(state)

        if action == '1':
            sm = ServeMode(state)
            sm.run()
        elif action == '2':
            ns_shop(state)
        elif action == '3':
            price_settings(state)
        elif action == '4':
            show_inventory(state)
        elif action == '5':
            level_upgrade(state)
        elif action == '6' and state["level"] >= 2:
            customer_shop(state)
        elif action == '7' and state["level"] >= 2:
            print(cyan(f"\n  {T('phone_hint')}"))
            time.sleep(1.5)
        elif action == '8' and state["level"] >= 3:
            distraction_shop(state)
        elif action in ('r', 'R'):
            rebirth_shop(state)
        elif action in ('m', 'M'):
            mafia_loan(state)
        elif action in ('9', 'rename', 'game_settings', 't'):
            settings_menu(state)
        elif action == 'q':
            clear()
            print(dim(T("bye")))
            print()
            save_game(state)
            sys.exit(0)

if __name__ == "__main__":
    main()
