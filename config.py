#   config.py

import json
import os
import datetime
from kivy.metrics import dp

from utils import save_json_with_format #, OLD_write_on_line, OLD_compact_dict_json

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'user_settings.json')

# === 1. Données par défaut ===
default_data = {
    "user_preferences": {
        "unit_distance": "mm",  # abrégé d'appel: 'dist'
        "unit_angle": "deg",    # abrégé d'appel: 'ang'
        "unit_speed": "rpm",    # abrégé d'appel: 'speed'
        "last_part": 0,
        "last_tool": 0
    },
    "units": {
    # ATTENTION AVEC MCU : int16/uint16 trop petit (max: 32 767[int16t] / 65 535[uint16t])
        # distances     unité de base = micromètre (µm)
        "mm":    {"type": "unit_distance", "factor": 1000.0, "decimals": 3, "label": "mm"},
        "inch":  {"type": "unit_distance", "factor": 25400.508026, "decimals": 5, "label": "in"},
        # angles        unité de base = millidegrés (mdeg)
        "deg":   {"type": "unit_angle", "factor": 1000.0, "decimals": 2, "label": "°"},
        "rad":   {"type": "unit_angle", "factor": 57295.779513, "decimals": 4, "label": "rad"},
        "grade": {"type": "unit_angle", "factor": 900.0, "decimals": 2, "label": "gon"},
        # vitesses      unité de base = milli-tr/s
        "rpm":   {"type": "unit_speed", "factor": 16.666667, "decimals": 1, "label": "rpm"},
        "rps":   {"type": "unit_speed", "factor": 1000.0, "decimals": 3, "label": "tr/s"},
        "rad/s": {"type": "unit_speed", "factor": 159.15494309189534, "decimals": 4, "label": "rad/s"}
    },
    "axis": {
        "vert": {"screen": "X", "factor": 2, "numerator": 5, "denumerator": 1, "type": "unit_distance", "info": "diamètre transversale, absolu"},
        "hor": {"screen": "Z", "factor": 1, "numerator": 5, "denumerator": 1, "type": "unit_distance", "info": "profondeur trainard, absolu"},
        "sup": {"screen": "Y", "factor": 1, "numerator": 5, "denumerator": 1, "type": "unit_distance", "angle": 45000, "info": "chariot porte outil, absolu + angle"},
        "s": {"screen": "s", "factor": 1, "numerator": 360, "denumerator": 32768, "type": "unit_angle", "info": "position de la broche avec  TLE5012B (ou MT6835)"},
        "r": {"screen": "r", "factor": 1, "numerator": 5, "denumerator": 1, "type": "unit_angle", "info": "Servo sur vise mère: Inutilisé pour l'instant"},
        "vert2": {"screen": "h", "factor": 1, "numerator": 5, "denumerator": 1, "type": "unit_distance", "info": "X_relatif au rayon"},
        "hor2": {"screen": "p", "factor": 1, "numerator": 1, "denumerator": 1, "type": "unit_distance", "info": "Z_relatif"},
        "l": {"screen": "l", "factor": 1, "numerator": 1, "denumerator": 1, "type": "unit_distance", "info": "Longeur du segment (h1'p1 / h2'p2)"},
        "alpha": {"screen": "α", "factor": 1, "numerator": 1, "denumerator": 1, "type": "unit_distance", "info": "Pente du segment"},
        "hor3": {"screen": "diam", "factor": 2, "numerator": 1, "denumerator": 1, "type": "unit_distance", "info": "X + Y en X (diamètre absolu)"},
        "vert3": {"screen": "long", "factor": 1, "numerator": 1, "denumerator": 1, "type": "unit_distance", "info": "Z + Y en Z (profondeur absolu)"}
    },
    "shortcuts": {
        "toggle_mirror": "Ctrl+M"
    },
    "user_config":{
        "user_langage": "fr",			# Langue définie par l'utilisateur
        "draw_profil_scale_dp": 0.005,	# Distance par défaut d'un point sur règles linéaire. TODO: contrôler si utilisé ?
        "theme_name": "dark",			# Thème définie par l'utilisateur
        "theme_path" : "..."			# Pour les future thème chargé comme patch
    }
}

# === 2. Fonction utilitaire de chargement ===
def load_json(path, default, format_array_key=None):
    if not os.path.exists(path):
        save_json(path, default)    # Savegarde avec mise en forme des lignes
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


# === 3. Chargement des paramètres ===
SETTINGS = load_json(SETTINGS_FILE, default_data)
UNIT_SETTINGS = SETTINGS.get("units", {})
USER_SETTINGS = SETTINGS.get("user_preferences", {})
AXIS_CONFIG = SETTINGS.get("axis", [])
USER_CONFIG = SETTINGS.get("user_config", None)
USER_LANGAGE = USER_CONFIG.get("user_langage", None)

def save_json(path =SETTINGS_FILE, data = SETTINGS):
    keys_compacted = [("units", False), ("user_preferences", True), ("shortcuts", False), ("axis", False), ("user_config", False)]
    save_json_with_format(path, data, keys_compacted)


#> Partie name unit or type_unit
def get_unit_id(unit_type_or_id):
    """
    Retourne l'identifiant d'unité (ex: 'mm', 'deg', 'rpm') à partir :
      - d'un type abrégé ('dist', 'ang', 'speed') → selon les préférences utilisateur
      - d'un identifiant explicite (ex: 'mm', 'deg', 'rpm')
      - d'un label (ex: '°', 'rad', 'gon', 'tr/s', etc.)

    Args:
        unit_type_or_id (str): Type abrégé, identifiant ou label.

    Returns:
        str or None
    """
    key = unit_type_or_id.strip().lower() if unit_type_or_id is not None else unit_type_or_id


    # Direct match sur ID
    if key in UNIT_SETTINGS:
        return key

    # Préférences utilisateur (type abrégé)
    if key == "dist":
        return USER_SETTINGS.get("unit_distance", "mm")
    elif key == "ang":
        return USER_SETTINGS.get("unit_angle", "deg")
    elif key == "speed":
        return USER_SETTINGS.get("unit_speed", "rpm")
    
    # recherche sur le type -> retourne préférences utilisateur correspondant
    if USER_SETTINGS.get(key, None) is not None:
        return USER_SETTINGS.get(key)
    
    # Recherche par label
    for unit_id, config in UNIT_SETTINGS.items():
        if config.get("label", "").lower() == key:
            return unit_id

    # Extra alias possibles (Unicode, franglais, etc.)
    extra_labels = {
        "tr/s": "rps",
        "trs": "rps",
        "u/s": "rps",
        "gr": "grade",
        "grad": "grade",
        #"μm": "mm",
        #"um": "mm",   
        "tr/m": "rpm",
        "tr/min": "rpm",
        "t/m": "rpm",
        "u/min": "rpm",
        "min-1": "rpm",
    }
    if key in extra_labels:
        return extra_labels[key]

    return None  # Aucun match

def get_unit_type(unit_type_or_id):
    """
    Retourne le type d'unité (ex: 'unit_distance', 'unit_angle', ...) à partir :
      - d'un type abrégé ('dist', 'ang', 'speed') → selon les préférences utilisateur
      - d'un type d'unité (ex: 'unit_distance', 'unit_angle', unit_speed)
      - d'un identifiant explicite (ex: 'mm', 'deg', 'rpm')
      - d'un label (ex: '°', 'rad', 'gon', 'tr/s', etc.)
      - d'un Extre (voir liste get_unit_id())

    Args:
        unit_type_or_id (str): Type abrégé, Type, identifiant, label ou Extra.

    Returns:
        str or None
    """
    if unit_type_or_id is None:
        return None
    
    unit_id = get_unit_id(unit_type_or_id)

    if unit_id and unit_id in UNIT_SETTINGS:
        return UNIT_SETTINGS[unit_id].get("type")
    return None

def get_unit_property(unit_type_or_id, prop="label"):
    """
    Retourne une propriété d'une unité (label, factor, decimals, etc.)

    Args:
        unit_type_or_id (str): ID, label, ou abrégé (ex: "mm", "°", "dist")
        prop (str): Propriété à retourner (ex: "label", "factor", "type", etc.)

    Returns:
        Any or None: Valeur de la propriété demandée
    """
    unit_id = get_unit_id(unit_type_or_id)
    if not unit_id:
        return None
    cfg = UNIT_SETTINGS.get(unit_id)
    return cfg.get(prop) if cfg else None

def get_all_units_for_type(unit_type, with_labels=False):
    """
    Retourne la liste des identifiants d'unités correspondant à un type donné.
    Si l'entrée est un ID d'unité ou un label (ex: 'mm', 'deg', 'tr/min'),
    on déduit automatiquement son type via `get_unit_type`.

    Args:
        unit_type (str): Type exact (ex: 'unit_angle') ou nom d'unité.
        with_labels (bool): Si True, retourne une liste de tuples (id, label).

    Returns:
        list[str] ou list[tuple[str, str]]: Liste des IDs ou des (ID, label).
    """
    def build_result_list(type_str):
        result = []
        for uid, info in UNIT_SETTINGS.items():
            if info.get("type") == type_str:
                result.append((uid, info.get("label", uid)) if with_labels else uid)
        return result

    # Étape 1 : tentative directe
    result = build_result_list(unit_type)
    if result:
        return result

    # Étape 2 : fallback via déduction du type
    next_type = get_unit_type(unit_type)
    if not next_type:
        return []

    return build_result_list(next_type)

#> Partie convertion d'unités
def get_unit_config(unit_type_or_id):
    """
    Retourne la configuration d'une unité à partir de son identifiant ou de son type,
    et inclut également l'ID de l'unité dans le retour.

    Args:
        unit_type_or_id (str): Type abrégé ('dist', 'ang', 'speed') ou identifiant d’unité.

    Returns:
        dict: Dictionnaire de configuration contenant :
              {
                  "unit_id": str,
                  "type": str,
                  "factor": float,
                  "decimals": int,
                  "label": str
              }

    Raises:
        ValueError: si l’unité est inconnue.
    """
    #if unit_id and unit_id in USER_SETTINGS[""]:
    '''    
    if unit_type_or_id == "dist" or unit_type_or_id == "unit_distance":
        unit_id = USER_SETTINGS.get("unit_distance", "mm")
    elif unit_type_or_id == "ang" or unit_type_or_id == "unit_angle":
        unit_id = USER_SETTINGS.get("unit_angle", "deg")
    elif unit_type_or_id == "speed" or unit_type_or_id == "unit_speed":
        unit_id = USER_SETTINGS.get("unit_speed", "rpm")
    else:
        unit_id = unit_type_or_id
    '''
    unit_id = get_unit_id(unit_type_or_id)


    cfg = UNIT_SETTINGS.get(unit_id)
    if not cfg:
        raise ValueError(f"Unité inconnue : {unit_id}")
    # Retourner la configuration 
    return {
        "unit_id": unit_id,
        "type": cfg.get("type"),
        "factor": cfg.get("factor"),
        "decimals": cfg.get("decimals"),
        "label": cfg.get("label")
    }

def switch_unit(value, last_unit_id, new_unit_id):
    """
    Convertit une valeur d'une unité (last_unit_id) vers une autre (new_unit_id).

    Args:
        value (str | float | int): La valeur à convertir, sous forme de nombre ou chaîne.
        last_unit_id (str): L'identifiant de l'unité actuelle (ex: "mm", "rpm").
        new_unit_id (str): L'identifiant de la nouvelle unité vers laquelle convertir (ex: "in", "tr/s").

    Returns:
        list: [valeur_convertie, new_unit_id, new_unit_label]
        str: "erreur" en cas d'erreur
    """
    # Si la valeur est un nombre, utiliser directement la valeur
    if isinstance(value, (int, float)):
        val = value
        last_unit_conf = get_unit_config(last_unit_id)
    else:
        # Si la valeur est une chaîne (par exemple "12.5mm"), la parser
        val_list = parse_user_input(value, last_unit_id)
        if isinstance(val_list, str):
            return "erreur"  # Si erreur de parsing, retourner "erreur"
        val = val_list[0]
        last_unit_conf = get_unit_config(val_list[1])  # Config de l'unité d'origine

    # Config de l'unité cible
    new_unit_conf = get_unit_config(new_unit_id)

    # Facteurs de conversion
    factor_in = last_unit_conf["factor"]
    factor_out = new_unit_conf["factor"]

    # Conversion de la valeur
    converted_value = val * factor_out / factor_in

    # Retourner la valeur convertie avec l'ID et le label de la nouvelle unité
    return [converted_value, new_unit_conf["unit_id"], new_unit_conf["label"]]

def format_unit(value_base, unit_type_or_id='dist', with_unit=False):
    """
    Convertit une valeur de base (µm, µrad ou milli-tr/s) en unité utilisateur ou explicite, avec formatage.

    Args:
        value_base (float): valeur en base (µm ou µrad)
        unit_type_or_id (str): 'dist', 'ang', 'speed' ou identifiant explicite
        with_unit (bool): si True, retourne [valeur_str, unité]; sinon, retourne une string complète

    Returns:
        str | list: "123.456 mm" ou ["123.456", "mm"] — selon le paramètre `with_unit`
    """
    cfg = get_unit_config(unit_type_or_id)

    factor = cfg.get("factor", 1)
    decimals = cfg.get("decimals", 3)
    label = cfg.get("label", "Erreur")

    value_disp = value_base / factor
    formatted = f"{value_disp:.{decimals}f}"

    return [formatted, label] if with_unit else formatted

def parse_user_input_calc(input_str, default_unit_type_or_id='dist', last_val=0, last_unit=None):
    if last_unit is None:
        last_unit = default_unit_type_or_id
        
    # Vérifier si l'entrée commence par un opérateur suivi de '=' (+=, -=, *=, =/)

    #Avant le contrôle peut-être supprimer les espaces (seulement avant le premier caractère)

    if input_str.startswith(('+=', '=+', '-=', '=-', '*=', '=*', '/=', '=/')):
        # Extraire l'opérateur et la valeur
        operator = input_str[:2]
        value_str = input_str[2:].strip()

        # Récupérer la valeur numérique et l'unité
        calc_val = parse_user_input(value_str, default_unit_type_or_id)
        origin_val = parse_user_input(last_val, last_unit)

        if isinstance(calc_val, str) and calc_val in ['invalid_format', 'invalid_unit']:
            return calc_val  # Si l'entrée est invalide, renvoyer l'erreur
        if isinstance(origin_val, str):
            return origin_val  # Si l'entrée est invalide, renvoyer l'erreur

        calc_float, calc_id, unit_label = calc_val
        origin_float, origin_id, _ = origin_val

        val_float = calc_float
        if calc_id != origin_id: # mise à la nouvelle l'échelle 
            factor_out = get_unit_property(calc_id, "factor")
            factor_in = get_unit_property(origin_id, "factor")
            last_float = origin_float / factor_in * factor_out
        else:
            last_float = origin_float

        # Appliquer l'opération en fonction de l'opérateur
        if operator == '+=':
            last_float += val_float
        elif operator == '-=':
            last_float -= val_float
        elif operator == '*=':
            last_float *= val_float
        elif operator == '=/':
            if val_float == 0:
                return 'invalid_format'  # Empêcher la division par zéro
            last_float /= val_float

        # Retourner la nouvelle valeur dans la nouvelle l'unité
        return [last_float, calc_id, unit_label]

    else:
        # Si l'entrée ne commence pas par un opérateur, c'est une nouvelle valeur à traiter normalement
        return  parse_user_input(input_str, default_unit_type_or_id)

def parse_user_input(input_str, default_unit_type_or_id='dist'):
    """
    Analyse une saisie utilisateur et retourne la valeur, l'unité détectée et son label.

    Args:
        input_str (str): Saisie utilisateur, ex: "12.5mm", "10 °", "1.2in"
        default_unit_type_or_id (str): Type ou ID d'unité par défaut (ex: 'dist', 'mm')

    Returns:
        list: [val_float, unit_id, unit_label] → ex: [1.25, 'inch', 'in']
        str: 'invalid_unit' ou 'invalid_format' en cas d'échec
    """
    import re

    # Nettoyage
    cleaned = input_str.strip().lower().replace(",", ".")

    # Regex pour séparer valeur et unité
    match = re.match(r"^([-+]?\d*\.?\d+)\s*([^\d\s]*)$", cleaned)
    if not match:
        return 'invalid_format'

    val_str, unit_str = match.groups()

    try:
        val_float = float(val_str)
    except ValueError:
        return 'invalid_format'

    # Identification de l’unité
    unit_id = get_unit_id(unit_str) if unit_str else get_unit_id(default_unit_type_or_id)
    if unit_id is None:
        return 'invalid_unit'

    unit_label = get_unit_property(unit_id, "label") or unit_id

    return [val_float, unit_id, unit_label]

#< END Partie convertion d'unités

#> Partie configurations utilisateur
def get_scale_profil_screen():
    scale_px = USER_CONFIG.get("draw_profil_scale_dp", 0.005)/ dp(1)
    return scale_px
#< END configurations utilisateur

LOG_FILE = "log.txt"

def log_message(message: str) -> None:
    """Écrit un message horodaté dans le fichier log.txt."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {message}\n")