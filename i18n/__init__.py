import json
import os
from copy import deepcopy

from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock  # Importer la classe Clock
#from kivy.app import App

DEFAULT_FILE = os.path.join(os.path.dirname(__file__), 'def_fallback.json')
LOG_LANGUAGE_FILE = os.path.join(os.path.dirname(__file__), "log_language.json") # "log_language.json"  # Nom du fichier log

PLUGIN_TRANSLATIONS= {
    #Exemple:plugin_id: {"name": "nom_identifiant_du_plugin","lang": {"en":{dictionnaire englais},"fr":{dictionnaire francais}, ...}},
    }

def load_json_log(path):
    default_log_language = {
        "INFORMATION": {"message": "You need to add an object for each language you want to use.",
            "ne_pas_supprimer":"missing_languages, c'est pour les langues manquantes ou corrompues"
        },
        "missing_languages": {},  # Dictionnaire pour les langues manquantes ou corrompues
        "en": {},   # ensuite dictionnaire pour les langues inclusent (un dict par langue)
        "fr": {}
    }
    if not os.path.exists(path):
        # Si le fichier n'existe pas, crée-le avec les données par défaut
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default_log_language, f, indent=4, ensure_ascii=False)
        print(f"Created {path} with default content.")
        return default_log_language
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_log_language

# Variables globales
error_message_buffer = []  # Pour accumuler les erreurs
popup_timer = None  # Timer pour afficher le pop-up après un délai
_current_lang = "fr"
_plug_lang = "fr"
_translations = {}
LOG_LANGUAGE = load_json_log(LOG_LANGUAGE_FILE)
MAX_ERROR_LOG = 10  # nombre d'écritures maximum pour chaque section du log


def def_fallback_json():
    global _current_lang, _translations
    fallback_language_create = {
        "not_your_language_existing": "The selected language does not exist.",
        "you_select_language": "Please select another language from the list below.",
        "not_language_dictionaries": "No language dictionaries available.",
        "reload_software_for_language": "You must add the language dictionaries or reinstall the software.",
        "corrupted_language": "The language you have chosen is too corrupted to be used."
    }
    _current_lang = "fallback"  # Définit la langue de secours (fallback)
    _translations = fallback_language_create  # Applique le dictionnaire de la langue de secours

def save_json_log(path, data):
    """Sauvegarde le fichier log après modification."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Updated {path} with new error.")


def set_language(lang_code):
    """Change la langue actuelle (ex: 'fr', 'en')"""
    global _current_lang, _plug_lang, _translations

    if lang_code == "fallback":
        def_fallback_json()  # Charge la langue de secours (fallback)
        return

    _plug_lang = lang_code  # Langue à utiliser pour tous les plugins

    lang_file = os.path.join(os.path.dirname(__file__), f"{lang_code}.json")
    if os.path.exists(lang_file):
        with open(lang_file, "r", encoding="utf-8") as f:
            _translations = json.load(f)
        _current_lang = lang_code
    else:
        add_translation_error(lang_code, "None", "Language is missing or corrupted.")
        def_fallback_json()  # Charge la langue de secours (fallback)

def tr(key, plugin_id=None):
    """Retourne la traduction telle qu'elle est écrite dans le fichier JSON"""
    global _current_lang, _plug_lang
    plug_lang = _plug_lang    # plug_lang = copy(_plug_lang) -> copy inutile ici (pas d'effet de bord)
    raiponce = None
    if plugin_id is not None:

        plugin_entry = PLUGIN_TRANSLATIONS.get(plugin_id, {})
        plugin_name = plugin_entry.get("name", plugin_id)
        langs = plugin_entry.get("lang", {})

        # Tentative 1 : langue actuelle
        lang_dict = langs.get(plug_lang)

        # Tentative 2 : première langue disponible
        if lang_dict is None and langs:
            add_translation_error(plug_lang, key, "Language is missing or corrupted.", plugin_id=plugin_id, plugin_name=plugin_name)
            # Prend la première langue définie dans le dict (ordre garanti depuis Python 3.7+)
            plug_lang = next(iter(langs))
            lang_dict = langs.get(plug_lang)
            print(f"[PLUGIN {plugin_name}] Langue '{_plug_lang}' absente → fallback sur '{plug_lang}'")

        # Si toujours rien → vide
        if lang_dict is None:
            plug_lang = "not_lang"  # Ceci sera affiché dans le LOG !
            lang_dict = {}

        raiponce = lang_dict.get(key)
    else:
        plugin_name = ""
    
    if raiponce is None:
        raiponce = _translations.get(key, None)
        if raiponce is None:
            add_translation_error(_plug_lang, key, "Key is missing or corrupted.", plugin_id, plugin_name)
            #print(f"DEBUG_: langue: {_current_lang} key: {key}")
            raiponce = str(key)
    return raiponce

def Tr(key, plugin_id=None):
    """Retourne la traduction avec la première lettre en majuscule"""
    return tr(key, plugin_id=None).capitalize()

def TR(key, plugin_id=None):
    """Retourne la traduction en majuscule"""
    return tr(key, plugin_id=None).upper()

def add_translation_error(language, error_key, error_message, plugin_id=None, plugin_name=""):
    """Ajoute une erreur directement dans le log sous 'missing_languages' pour les langues manquantes ou corrompues."""
    global LOG_LANGUAGE, MAX_ERROR_LOG
    if plugin_id is not None:
        plug_name = str(plugin_name if plugin_name != "" else plugin_id) + "_"
    else:
        plug_name = ""
    lang_plus = plug_name + language
    
    if _current_lang == "fallback":
        # Ne pas écrire dans le log si la langue actuelle est "fallback" (c'est déjà fait)
        return
    #elif plugin_id is not None and language == "fallback":
    #    pass #Tudo: ajouter un truc dans la section "plugin".lang = language; genre langue absente du plugin
       
    if lang_plus not in LOG_LANGUAGE:    # Si la langue n'existe pas, ajouter l'erreur dans 'missing_languages'
        txt_error = f"Language '{lang_plus}' is missing or corrupted. Key: {error_key}"
        if len(LOG_LANGUAGE["missing_languages"]) < MAX_ERROR_LOG:
            LOG_LANGUAGE["missing_languages"][lang_plus] = txt_error
        else:
            LOG_LANGUAGE["missing_languages"].pop(next(iter(LOG_LANGUAGE["missing_languages"])))
            LOG_LANGUAGE["missing_languages"][lang_plus] = txt_error
        set_language("fallback")
    else:   # Ajouter l'erreur dans la langue
        txt_error = f"key: {error_key} : error_message: {error_message}"
        if len(LOG_LANGUAGE[lang_plus]) < MAX_ERROR_LOG:
            LOG_LANGUAGE[lang_plus][error_key] = txt_error
        else:
            LOG_LANGUAGE[lang_plus].pop(next(iter(LOG_LANGUAGE[lang_plus])))  # Supprimer la plus ancienne erreur
            LOG_LANGUAGE[lang_plus][error_key] = txt_error
            print(txt_error)
            # Ajouter un message dans 'missing_languages' pour signaler que la limite est atteinte
            txt_error = f">> The number of translation errors in {lang_plus} exceeds the log capacity."
            LOG_LANGUAGE["missing_languages"][lang_plus] = txt_error

    print(f"Translat error: {txt_error}")
    # Afficher un pop-up avec l'erreur
    global popup_timer, error_message_buffer
    error_message_buffer.append(txt_error)    # Accumuler l'erreur au lieu de la montrer immédiatement
    if popup_timer is None:    # Si un timer est déjà en cours, on ne fait rien
        # Démarre un timer pour afficher le pop-up après 2 secondes
        popup_timer = Clock.schedule_once(display_errors_accumulated, 1)

    # Sauvegarder les modifications dans le fichier log
    save_json_log(LOG_LANGUAGE_FILE, LOG_LANGUAGE)

def display_errors_accumulated(dt):
    """Affiche les erreurs accumulées dans un seul pop-up après un délai"""
    global error_message_buffer, popup_timer
    
    # Si des erreurs sont accumulées, affiche-les
    if error_message_buffer:
        txt_error = "\n".join(error_message_buffer)
        show_popup_error(txt_error)
        error_message_buffer = []  # Réinitialiser le buffer après l'affichage
        popup_timer = None

def show_popup_error(txt_error):
    """Affiche un pop-up d'erreur avec le message passé en paramètre"""
    popup_content = Label(text="Translat error:")
    popup_content = Label(text=txt_error)
    close_button = Button(text="Close", size_hint=(None, None), size=(100, 50))
    
    def close_popup(instance):
        popup.dismiss()  # Ferme le pop-up

    close_button.bind(on_press=close_popup)
    popup = Popup(title="Translation Error", content=popup_content, size_hint=(None, None), size=(800, 800))
    popup.open()


def register_plugin(plugin_id, plugin_name, lang={}):
    """
    Crée l'entrée de base pour un plugin s’il n’existe pas encore.
        (Ajoute toutes les langues incluses dans "lang":{})
    """
    lang = deepcopy(lang) 
    PLUGIN_TRANSLATIONS.setdefault(plugin_id, {
        "name": plugin_name,
        "lang": lang
    })

def add_lang_plugin_translation(plugin_id, plugin_name, lang_code, translations):
    """
    Ajoute les traductions d'une langue à un plugin déjà enregistré.
    Si le plugin n’est pas encore enregistré, il est créé automatiquement.
    """
    entry = PLUGIN_TRANSLATIONS.setdefault(plugin_id, {
        "name": plugin_name,
        "lang": {}
    })

    # Assure que le nom est bien mis à jour au cas où
    if entry.get("name", "") != plugin_name:
        entry["name"] = plugin_name

    entry["lang"][lang_code] = translations
