#   configurator/ config.py

import json
import os
import datetime
from kivy.metrics import dp

from utils import save_json_with_format

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'user_settings.json')

# === 1. Données par défaut ===
    # ================================================================
    # ⚙️ CONFIGURATION MAÎTRESSE ET DOCUMENTATION DU CHAMP DE DONNÉES
    # ================================================================
DEFAULT_DATA = {
    "user_preferences": {
        "unit_distance": "mm",  # Abrégé d'appel interne: 'unit_distance'
        "unit_angle": "deg",    # Abrégé d'appel interne: 'unit_angle'
        "unit_speed": "rpm"     # Abrégé d'appel interne: 'unit_speed'
    },
    "units": {
        # 🚨 ATTENTION AVEC LE FIRMWARE MCU : 
        # Les registres int16/uint16 sont trop étroits pour stocker des microns bruts de grandes règles optiques !
        # Limites physiques : max 32 767 [int16_t] / 65 535 [uint16_t]. 
        # Le thread temps réel doit impérativement transiter par du int32_t (Long) pour éviter les débordements (Overflow).

        # 📏 DISTANCES : L'unité de référence absolue en RAM et dans les calculs est le micromètre (µm)
        "mm":    {"type": "unit_distance", "factor": 1000.0, "decimals": 3, "label": "mm", "long_name": "Millimètre"},
        "inch":  {"type": "unit_distance", "factor": 25400.508026, "decimals": 5, "label": "in", "long_name": "Pouce"},
        
        # 📐 ANGLES : L'unité de référence absolue dans les calculs est le millidegré (mdeg)
        "deg":   {"type": "unit_angle", "factor": 1000.0, "decimals": 2, "label": "°", "long_name": "Degré"},
        "rad":   {"type": "unit_angle", "factor": 57295.779513, "decimals": 4, "label": "rad", "long_name": "Radian"},
        "grade": {"type": "unit_angle", "factor": 900.0, "decimals": 2, "label": "gon", "long_name": "Grade (Gon)"},
        
        # 🔄 VITESSES : L'unité de référence absolue dans les calculs est le milli-tour par seconde (mtr/s)
        "rpm":   {"type": "unit_speed", "factor": 16.666667, "decimals": 1, "label": "rpm", "long_name": "Tours par minute"},
        "rps":   {"type": "unit_speed", "factor": 1000.0, "decimals": 3, "label": "tr/s", "long_name": "Tours par seconde"},
        "rad/s": {"type": "unit_speed", "factor": 159.15494309189535, "decimals": 4, "label": "rad/s", "long_name": "Radian par seconde"}
    },
    "axis": {
        # 🎛️ Chaîne cinématique des axes réels connectés aux règles optiques et capteurs physiques
        "vert":  {"screen": "X", "factor": 2, "numerator": 5, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "Diamètre transversale, absolu", "last_position_micron": -40},
        "hor":   {"screen": "Z", "factor": 1, "numerator": 5, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "Profondeur trainard, absolu", "last_position_micron": -210},
        "sup":   {"screen": "Y", "factor": 1, "numerator": 5, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "angle": 45000, "unit_angle": "unit_angle", "info": "Chariot porte-outil supérieur, absolu + angle de braquage", "last_position_micron": 1980},
        "s":     {"screen": "s", "factor": 1, "numerator": 360, "denominator": 32768, "type": "unit_angle", "unit": "unit_angle", "info": "Position angulaire absolue de la broche via encodeur Hall magnétique TLE5012B (ou MT6835)"},
        "r":     {"screen": "r", "factor": 1, "numerator": 5, "denominator": 1, "type": "unit_angle", "unit": "unit_angle", "info": "Servo motorisé couplé à la vis mère pour Electronic Gearing (Inutilisé / En développement)"},
        
        # 🧮 Axes de projection mathématique et de calculs géométriques relatifs
        "vert2": {"screen": "h", "factor": 1, "numerator": 5, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "X_relatif calculé par rapport au rayon de la pièce"},
        "hor2":  {"screen": "p", "factor": 1, "numerator": 1, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "Z_relatif de déplacement pièce"},
        "l":     {"screen": "l", "factor": 1, "numerator": 1, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "Longueur réelle du lacet de segment trigonométrique (h1'p1 / h2'p2)"},
        "alpha": {"screen": "α", "factor": 1, "numerator": 1, "denominator": 1, "type": "unit_angle", "unit": "unit_angle", "info": "Pente angulaire instantanée du segment CAO"},
        
        # 🚀 FUSION CINÉMATIQUE ACTIVE : Intègre le chariot supérieur motorisé pour l'assistance de trajectoire automatique
        "hor3":  {"screen": "diam", "factor": 2, "numerator": 1, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "X_règle + Y_moteur (Proj. Sinus) -> Diamètre réel absolu de la pièce"},
        "vert3": {"screen": "long", "factor": 1, "numerator": 1, "denominator": 1, "type": "unit_distance", "unit": "unit_distance", "info": "Z_règle + Y_moteur (Proj. Cosinus) -> Profondeur réelle absolue de la pièce"}
    },
    "shortcuts": {
        "toggle_mirror": "Ctrl+M"
    },
    "user_config": {
        "user_language": "fr",          # Choix de la langue active pour l'interface i18n
        "draw_profil_scale_dp": 0.008,  # Ratio pixel/micron pour le tracé CAO linéaire. TODO: Valider l'utilité au cours du chantier tracé.
        "ratio_tool_screen": [0.75,0.3],    # Ration d'écran pour le centrage sur burin
        "theme_name": "dark",           # Nom du thème graphique actif (sombre par défaut)
        "theme_path": "..."            # Emplacement des extensions et patchs de thèmes externes
    },
    "user_last_select": {
        # ⚙️ ÉTATS DES COMMANDE DE L'ASSISTANCE ACTIVE (V_7.2) : Mode d'intervention du moteur pas-à-pas Y
        "fao_y_mode_selected": "fillet",  # Modes supportés : 'fillet' (copieur de profil), 'joystick', 'constant' (avance fixe)
        "fao_r_mode_selected": "",        # Synchronisation de la vis mère (Electronic Gearing à la Provvedo/Bertelli)
        
        # 💾 Mémoire de fin de session pour la réouverture fluide de l'IHM
        "selected_part_idx": 4,           # Index de la pièce en cours d'usinage
        "selected_tool_ident": "199",     # Identifiant textuel de l'outil monté au dernier arrêt (Comparateur Maître par défaut)
        "vc_ref_mat_idx": 0,              # Index de la matière de référence choisie pour la Vitesse de Coupe
        "auto_vc": False,                 # Régulation automatisée ou manuelle de la Vitesse de Coupe (VC)
        "tactile_keyboard": True          # Activation du clavier virtuel Kivy pour les dalles tactiles d'atelier
    },
    "machine_config": {
        "rotate_ref_cutter": False,
        "cutters_not_homing_to_rotate": True,
        "index_multi_fix": [0, 18, 36, 54, 72, 90, 108, 126, 144, 162, 180, -162, -144, -126, -108, -90, -72, -54, -36, -18],  # Les 20 indexations physiques rigides du Multifix
        "has_coolant_pump": False,        # Déclaration matérielle de la présence d'une pompe à lubrifiant reliée au MCU
        "spindle_captor_type": "TLE5012B",# Type d'encodeur de broche : 'TLE5012B' (absolu SSI), 'INCREMENTAL', ou 'NONE'
        "y_motor_type": "STEPPER",        # Motorisation de l'axe supérieur correcteur : 'STEPPER', 'SERVO' ou 'NONE'
        "r_motor_type": "SERVO_INUTINISE" # Motorisation de l'axe de filetage de la vis mère
    }
}

# === 2. Fonction utilitaire de chargement ===

def init_json(path=SETTINGS_FILE, data=DEFAULT_DATA):
    """ Calcule et injecte le dictionnaire d'usine initial sur le disque dur. """
    # 🟢 AJOUTÉ : On compacte 'index_multi_fix' sur une seule ligne horizontale 
    # pour éviter que les 20 crans Multifix ne prennent 20 lignes à la verticale !
    keys_compacted = [
        ("units", False), 
        ("user_preferences", True), 
        ("shortcuts", False), 
        ("axis", False), 
        ("user_config", False),
        ("index_multi_fix", True)  # 🎯 Force les 20 crans Multifix sur une seule ligne compacte
    ]
    save_json_with_format(path, data, keys_compacted)

def load_json(path, default):
    """Lit la configuration en RAM ou restaure l'usine en cas de fichier absent/corrompu."""
    if not os.path.exists(path):
        init_json(path, default)    # Sauvegarde initiale avec mise en forme propre des lignes
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ [IHM Config] user_settings.json corrompu. Restauration des valeurs d'usine.")
        return default

def save_json(path=SETTINGS_FILE, data=None):
    """ Sauvegarde les modifications de l'opérateur en cours de route. """
    if data is None:
        data = SETTINGS
    
    # 🟢 ALIGNÉ : Rigoureusement la même charte de formatage pour l'écriture de session
    keys_compacted = [
        ("units", False), 
        ("user_preferences", True), 
        ("shortcuts", False), 
        ("axis", False), 
        ("user_config", False),
        ("index_multi_fix", True)  # 🎯 Reste compact et lisible à chaque sauvegarde
    ]
    save_json_with_format(path, data, keys_compacted)

# =====================================================================
# === 3. Chargement et Fixation des variables actives en RAM ==========
# =====================================================================

SETTINGS = load_json(SETTINGS_FILE, DEFAULT_DATA)   # C'est CETTE variable globale 'SETTINGS' qui est lue et modifiée par toute l'IHM !

UNIT_SETTINGS = SETTINGS.get("units", {})
USER_PREFERENCES = SETTINGS.get("user_preferences", {}) # Raccordé proprement aux préférences
AXIS_CONFIG = SETTINGS.get("axis", {})                  # Changé [] en {} car 'axis' est un dictionnaire !
USER_CONFIG = SETTINGS.get("user_config", {})           # Changé None en {} pour éviter les crashs de lecture .get()
USER_LAST_SELECT = SETTINGS.get("user_last_select", {}) # Tiroir de session FAO !
MACHINE_CONFIG = SETTINGS.get("machine_config", {})     # Tiroir matériel moteur/pompe !
# Extraction sécurisée de la langue
user_language = USER_CONFIG.get("user_language", "fr")


# =====================================================================
# === 4. Partie conversion d'unités et configurations utilisateur =====
# =====================================================================

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
        return USER_PREFERENCES.get("unit_distance", "mm")
    elif key == "ang":
        return USER_PREFERENCES.get("unit_angle", "deg")
    elif key == "speed":
        return USER_PREFERENCES.get("unit_speed", "rpm")
    
    # recherche sur le type -> retourne préférences utilisateur correspondant
    if USER_PREFERENCES.get(key, None) is not None:
        return USER_PREFERENCES.get(key)
    
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

def get_all_units_for_type(unit_type, with_labels=False, with_long_names=False):
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
                # 🎯 Cas 1 : On demande la version enrichie (Notre Popup)
                if with_labels and with_long_names:
                    label_court = info.get("label", uid)
                    nom_long = info.get("long_name", "Inconnu")
                    result.append((uid, f"{label_court} ({nom_long})"))
                
                # 🎯 Cas 2 : Comportement historique (Label court seul)
                elif with_labels:
                    result.append((uid, info.get("label", uid)))
                
                # 🎯 Cas 3 : Uniquement le nom long en label si besoin futur
                elif with_long_names:
                    result.append((uid, info.get("long_name", "Inconnu")))
                
                # 🎯 Cas 4 : Par défaut, juste une liste d'ID bruts
                else:
                    result.append(uid)
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
                  "label": str,
                  "long_name": str
              }

    Raises:
        ValueError: si l'unité est inconnue.
    """
    
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
        "label": cfg.get("label"),
        "long_name": cfg.get("long_name", "Inconnu")
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

    # Facteurs de conversion (ex: nombre de microns ou millièmes de tours par unité)
    factor_in = last_unit_conf["factor"]
    factor_out = new_unit_conf["factor"]

    # 🎯 LA FORMULE CORRIGÉE ET SÉCURISÉE :
    # 1. (val * factor_in) descend la valeur vers votre base entière universelle (microns ou millièmes de tr/s)
    # 2. / factor_out remonte cette base vers l'unité d'affichage cible demandée
    converted_value = val * factor_in / factor_out

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
# N'est pas utilisé pour l'instant, ajouter l'appel à [log_message()] pour 
# les problèmes à surveiller (comme les redémarrages après crachs)
def log_message(message: str) -> None:
    """Écrit un message horodaté dans le fichier log.txt."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now}] {message}\n")



