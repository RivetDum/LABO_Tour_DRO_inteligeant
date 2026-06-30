# theme.py


# Thème de l'UI, qui contient les couleurs, polices, etc.
ui_theme_python = {
    # Aspect général du fond, couleur de fond de la fenêtre
    "background_color": "#1e1e1e",  # Fond de l'application
    "text_color": "#f5f5f5",         # Texte général de l'application
    "highlight_color": "#ff4081",    # Couleur de survol ou de mise en évidence

    # Couleurs liées aux fenêtres ou autres composants globaux
    "window_background": "#2e2e2e",  # Fond de la fenêtre (au niveau de l'application)
    "button_color": "#333333",       # Couleur de fond des boutons
    "label_color": "#ffffff",        # Couleur du texte des labels

    # Couleur des titres et des bordures
    "title_color": "#ff4081",        # Couleur des titres (par exemple, des fenêtres)
    "border_color": "#f0f0f0",       # Couleur de bordure des fenêtres

    # Paramètres généraux relatifs aux polices
    "font_size": 16,                 # Taille de police globale
    "font_family": "Arial",          # Police globale
    "font_bold": False,              # Option pour le texte en gras

    # Définir la transparence ou la couleur des arrière-plans des menus
    "menu_background_color": "#333333",  # Fond des menus et barres d'outils
    "menu_text_color": "#ffffff",        # Texte des menus et barres d'outils
    "menu_highlight_color": "#ff4081",   # Couleur de survol des éléments de menu

    # Comportements généraux
    "theme_name": "dark_theme",       # Nom du thème actif
    "default_button_style": "normal", # Style par défaut des boutons (normal, round, etc.)
}

ui_kivy_theme = {
    "Window": {
        "clearcolor": [1, 1, 1, 1],  # Couleur de fond (blanc)
        "top": 50,  # Déplacer la fenêtre par rapport au haut de l'écran (en pixels)
        "borderless": False,  # Gérer si la fenêtre est sans bordure (plein écran)
    },
    "Font": {
        "default_font": "Arial",  # Police par défaut à utiliser dans toute l'app
        "default_size": 16,       # Taille de police par défaut pour tout
    },
    "Button": {
        "lib" : "from kivy.uix.button import Button",
        "args" : {            
            "background_color": "#1e1e1e",  # Couleur de fond du bouton
            "background_normal": "path/to/image.png",  # Image de fond
            "background_down": "path/to/image.png",  # Image lorsque le bouton est pressé
            "color": "#ffffff",  # Couleur du texte
            "font_size": 14,  # Taille de la police
            "font_name": "Arial",  # Nom de la police
            "border": [4, 4, 4, 4]  # Bordure du bouton (left, top, right, bottom)
        }
    },
    "Label": {
        "lib" : "from kivy.uix.label import Label",
        "args" : {            
            "color": "#f5f5f5",  # Couleur du texte
            "font_size": 16,  # Taille de la police
            "font_name": "Arial",  # Nom de la police
            "text_size": [None, None],  # Taille du texte
            "halign": "center",  # Alignement horizontal
            "valign": "middle"  # Alignement vertical
        }
    },
    "TextInput": {
        "lib" : "from kivy.uix.textinput import TextInput",
        "args" : {            
            "background_color": "#333333",  # Couleur de fond
            "foreground_color": "#ffffff",  # Couleur du texte
            "cursor_color": "#ff4081",  # Couleur du curseur
            "cursor_width": 2,  # Largeur du curseur
            "font_size": 14,  # Taille de la police
            "font_name": "Arial",  # Nom de la police
            "hint_text": "Entrez du texte",  # Texte d'exemple
            "hint_text_color": "#cccccc",  # Couleur du texte d'exemple
            "border": [2, 2, 2, 2]  # Bordure du champ
        }
    },
    "Slider": {
        "lib" : "from kivy.uix.slider import Slider",
        "args" : {
            "background_color": "#222222",  # Couleur de fond du slider
            "color": "#ff4081",  # Couleur de la barre
            "cursor_color": "#ffffff",  # Couleur du curseur
            "cursor_size": [10, 20],  # Taille du curseur
            "min": 0,  # Valeur minimale
            "max": 100,  # Valeur maximale
            "value": 50,  # Valeur actuelle
            "step": 1  # Pas de variation
        }
    },
    "Switch": {
        "lib" : "from kivy.uix.switch import Switch",
        "args" : {
            "active": True,  # Etat du switch (activé ou non)
            "background_color": "#333333",  # Couleur de fond du switch
            "active_color": "#ff4081",  # Couleur quand activé
            "inactive_color": "#888888",  # Couleur quand inactif
            "thumb_color": "#ffffff",  # Couleur du bouton
            "thumb_disabled_color": "#cccccc"  # Couleur du bouton désactivé
        }
    },
    "CheckBox": {
        "lib" : "from kivy.uix.checkbox import CheckBox",
        "args" : {
            "active": False,  # Etat de la case (cochée ou non)
            "color": "#ff4081",  # Couleur de la case
            "background_normal": "path/to/image.png",  # Image de fond décochée
            "background_active": "path/to/image.png",  # Image de fond cochée
            "border": [2, 2, 2, 2]  # Bordure de la case
        }
    },
    "Popup": {
        "lib" : "from kivy.uix.popup import Popup",
        "args" : {
            "background_color": "#222222",  # Couleur de fond
            "border": [10, 10, 10, 10],  # Bordure de la popup
            "title": "Popup Title",  # Titre de la popup
            "title_color": "#ffffff",  # Couleur du titre
            "content": None,  # Contenu de la popup
            "size_hint": [None, None]  # Taille de la popup
        }
    },
    "Image": {
        "lib" : "from kivy.uix.image import Image",
        "args" : {
            "source": "path/to/image.png",  # Source de l'image
            "allow_stretch": True,  # Permet d'étirer l'image
            "keep_aspect": True,  # Préserve le ratio de l'image
            "size_hint": [None, None]  # Taille de l'image par rapport à son parent
        }
    },
    "ProgressBar": {
        "lib" : "from kivy.uix.progressbar import ProgressBar",
        "args" : {
            "background_color": "#444444",  # Couleur de fond de la barre
            "color": "#ff4081",  # Couleur de la barre de progression
            "value": 50,  # Valeur actuelle
            "max": 100,  # Valeur maximale
            "step": 1,  # Pas de variation
            "height": 20  # Hauteur de la barre
        }
    },
    "GridLayout": {
        "lib" : "from kivy.uix.gridlayout import GridLayout",
        "args" : {
            "cols": 3,  # Nombre de colonnes
            "rows": 2,  # Nombre de lignes
            "padding": [10, 10, 10, 10],  # Espace autour de la grille
            "spacing": [5, 5],  # Espacement entre les éléments
            "size_hint": [1, 1]  # Taille relative de la grille
        }
    },
    "BoxLayout": {
        "lib" : "from kivy.uix.boxlayout import BoxLayout",
        "args" : {
            "orientation": "vertical",  # Orientation de la boîte
            "spacing": 10,  # Espacement entre les éléments
            "padding": [10, 10, 10, 10],  # Espace autour de la boîte
            "size_hint": [1, 1]  # Taille relative de la boîte
        }
    },
    "ScrollView": {
        "lib" : "from kivy.uix.scrollview import ScrollView",
        "args" : {
            "scroll_type": ["bars", "content"],  # Type de défilement
            "bar_width": 10,  # Largeur de la barre de défilement
            "scroll_distance": 25,  # Distance de défilement
            "do_scroll_x": True,  # Activer le défilement horizontal
            "do_scroll_y": True  # Activer le défilement vertical
        }
    },
    "Spinner": {
        "lib" : "from kivy.uix.spinner import Spinner",
        "args" : {
            "text": "Sélectionnez un élément",  # Texte du spinner
            "values": ["Option 1", "Option 2", "Option 3"],  # Liste des options
            "background_color": "#1e1e1e",  # Couleur de fond
            "text_color": "#ffffff",  # Couleur du texte
            "font_size": 14,  # Taille de la police
        }
    },
    "TabView": {
        "lib" : "from kivy.uix.tabbedpanel import TabbedPanel",
        "args" : {
            "tab_width": 100,  # Largeur des onglets
            "tab_height": 50,  # Hauteur des onglets
            "background_color": "#333333",  # Couleur de fond des onglets
            "tab_position": "top"  # Position des onglets
        }
    },
    "Canvas": {
        "lib" : "from kivy.graphics import Canvas",
        "args" : {
            "color": "#ff4081",  # Couleur de dessin
            "line_width": 2,  # Largeur des lignes
            "line_color": "#ffffff",  # Couleur des lignes
        }
    }
}

# Paramètres spécifiques à l'application (app)
app_theme = {
    "theme_name": "dark_theme",    # Nom du thème
    "ligne_de_liaison": "#838d83",  # Exemple de clé interne spécifique à l'application
    "highlight_button": "#ff4081",  # Exemple d'une autre clé interne spécifique à l'application
    
    "draw_line": {
        "liaison_line": "#838d83",
        "detail_line": "#11de1b",
        "erreur_detail_line": "#ff4081",
        "profil_line": "#96fbbe",
        "erreur_profil_line": "#ff4081",
        "profil_big_bbox": "#81ff5e",
        "profil_bbox": "#a0ff86",
        "detail_bbox": "#a0ff86"
        }
}




#test de fonctionnement dans le main()
# from kivy.uix.button import Button
# color = [1,0,0,06]
# widget_class = globals()[Button]
# setattr(widget_class, background_color, color)
  
from kivy.core.window import Window
from kivy.app import App
import importlib.util
import json
import os

class ThemeManager:
    def __init__(self):
        # Attribut pour stocker le thème actuel
        self.app_theme = {}

    def apply_app_theme(self, app_theme_dict):
        """
        Applique le thème spécifique à l'application en créant ou en mettant à jour l'attribut `self.app_theme`.
        """
        # Si l'attribut self.app_theme n'existe pas encore, on le crée
        if not hasattr(self, 'app_theme'):
            self.app_theme = {}

        # Parcours du dictionnaire app_theme_dict pour appliquer les valeurs
        for param, value in app_theme_dict.items():
            # Applique directement la valeur dans l'attribut app_theme
            self.app_theme[param] = value

    def apply_theme_kivy(self, theme_dict):
        """
        Applique les valeurs du thème à tous les widgets du dictionnaire
        qui contiennent des arguments à appliquer.
        """
        for widget_name, widget_info in theme_dict.items():
            
            # Vérifier si le widget a des arguments à appliquer
            if "args" not in widget_info:
                continue             
                
            if widget_name == "Window":
                # Appliquer les paramètres de la fenêtre
                if "clearcolor" in widget_info:
                    Window.clearcolor = widget_info["clearcolor"]
                if "top" in widget_info:
                    Window.top = widget_info["top"]
                if "borderless" in widget_info:
                    Window.borderless = widget_info["borderless"]
                continue
            
            if widget_name == "Font":
                apply_kivy_font_settings(theme_dict)
                continue

            widget_lib = widget_info.get("lib")
            widget_args = widget_info["args"]

            # Charger dynamiquement le module du widget
            if widget_lib and isinstance(widget_lib, str):
                try:
                    exec(widget_lib)  # Exécuter la chaîne pour importer dynamiquement le module
                except Exception as e:
                    print(f"Erreur lors de l'importation de {widget_lib} : {e}")
                    continue  # Passer à l'élément suivant si une erreur se produit
            else:
                print(f"widget_lib n'est pas une chaîne valide : {widget_lib}")
                continue  # Passer à l'élément suivant si ce n'est pas une chaîne valide

            # Accéder à la classe du widget
            widget_class = globals().get(widget_name)

            if widget_class:
                # Appliquer les valeurs du thème directement à la classe du widget
                for prop, value in widget_args.items():
                    if hasattr(widget_class, prop):
                        setattr(widget_class, prop, value)
                    else:
                        print(f"Avertissement : La propriété '{prop}' n'existe pas dans la classe {widget_name}.")
            else:
                print(f"Avertissement : La classe '{widget_name}' n'a pas été trouvée.")

    def apply_kivy_font_settings(theme_dict):
        """
        Applique les paramètres de police globale.
        """
        from kivy.uix.label import Label

        if "Font" in theme_dict:
            font_settings = theme_dict["Font"]
            # Applique les paramètres de police à Kivy
            if "default_font" in font_settings:
                from kivy.core.text import LabelBase
                LabelBase.register(name='CustomFont', fn_regular=font_settings["default_font"])
            if "default_size" in font_settings:
                Label.font_size = font_settings["default_size"]

    # Pas vraiment utile, pourrait être ignorée
    def apply_theme_python(self, theme_dict):
        """
        Applique les valeurs du thème Python aux paramètres généraux de l'UI.
        """
        for param, value in theme_dict.items():
            # Si la valeur est une couleur hexadécimale ou un format compatible
            if isinstance(value, str) and value.startswith("#"):
                # Appliquer les couleurs (par exemple, à une variable globale de couleur)
                globals()[param] = value
            elif isinstance(value, bool):
                # Appliquer les options booléennes (ex. : "font_bold")
                globals()[param] = value
            elif isinstance(value, int):
                # Appliquer les paramètres numériques (ex. : "font_size")
                globals()[param] = value
            elif isinstance(value, str):
                # Appliquer les chaînes de texte (ex. : "font_family", "theme_name")
                globals()[param] = value
            else:
                print(f"Avertissement : Le type de valeur pour '{param}' n'est pas pris en charge.")
                
    def load_theme(self, theme_path: str):
        """
        Charge un thème à partir d'un fichier Python et l'applique à l'application.
        Enregistre également le nom du thème dans un fichier JSON de configuration.
        """
        try:
            # Vérifier si le fichier Python existe
            if not os.path.exists(theme_path):
                raise FileNotFoundError(f"Le fichier de thème '{theme_path}' n'existe pas.")

            # Charger dynamiquement le module Python du thème
            spec = importlib.util.spec_from_file_location("app_theme_module", theme_path)
            theme_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(theme_module)

            # Accéder au thème dans le module
            app_new_theme = theme_module.app_theme if hasattr(theme_module, "app_theme") else {}

            # Vérifier que le thème contient les clés nécessaires
            if not app_new_theme:
                raise ValueError(f"Le fichier de thème '{theme_path}' ne contient pas un dictionnaire 'app_theme' valide.")

            # Vérification si le nom du thème a changé
            if self.get_json_theme_name() != app_new_theme.get("theme_name"):
                self.set_json_theme_changed(app_new_theme["theme_name"], theme_path)

            # Appliquer les paramètres du thème spécifique à l'application
            self.apply_app_theme(app_new_theme)

            # Appliquer les thèmes Kivy (ui_kivy_theme)
            self.apply_theme_kivy(ui_kivy_theme)

            # Appliquer les paramètres Python (ui_theme_python)
            self.apply_theme_python(ui_theme_python)

        except Exception as e:
            print(f"Erreur lors du chargement du thème : {e}")



    def get_json_theme_name(self):
        """
        Méthode pour obtenir le nom du thème à partir du fichier JSON (exemple).
        """
        # Charger le fichier JSON de configuration pour obtenir le thème
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            return config.get("theme_name", "default_theme")
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier de configuration : {e}")
            return "default_theme"

    def set_json_theme_changed(self, theme_name, theme_path):
        """
        Méthode pour enregistrer le changement de thème dans un fichier JSON.
        """
        try:
            config = {
                "theme_name": theme_name,
                "theme_path": theme_path
            }
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du fichier de configuration : {e}")




    """
    Charge un thème à partir d'un fichier Python et l'applique à l'application.
    Enregistre également le nom du thème dans un fichier JSON de configuration.
    """
    try:
        # Vérifier si le fichier Python existe
        if not os.path.exists(theme_path):
            raise FileNotFoundError(f"Le fichier de thème '{theme_path}' n'existe pas.")

        # Charger dynamiquement le module Python du thème
        spec = importlib.util.spec_from_file_location("app_theme_module", theme_path)
        theme_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(theme_module)

        # Accéder au thème dans le module
        app_new_theme = theme_module.app_theme if hasattr(theme_module, "app_theme") else {}

        # Vérifier que le thème contient les clés nécessaires
        if not app_new_theme:
            raise ValueError(f"Le fichier de thème '{theme_path}' ne contient pas un dictionnaire 'app_theme' valide.")

        # Vérification si le nom du thème a changé
        if self.get_json_theme_name() != app_new_theme.get("theme_name"):
            set_json_theme_changed(app_new_theme["theme_name"], theme_path)

        # Appliquer les paramètres du thème spécifique à l'application
        apply_app_theme(self, app_new_theme)

        # Appliquer les thèmes Kivy (ui_kivy_theme)
        apply_theme_kivy(ui_kivy_theme)

        # Appliquer les paramètres Python (ui_theme_python)
        apply_theme_python(ui_theme_python)

    except Exception as e:
        print(f"Erreur lors du chargement du thème : {e}")
    
#end


