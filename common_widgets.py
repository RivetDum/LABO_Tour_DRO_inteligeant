# common_widgets.py

import os
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.widget import Widget
from copy import copy
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.togglebutton import ToggleButtonBehavior
from kivy.properties import BooleanProperty, StringProperty
#from kivy.uix.spinner import Spinner, SpinnerOption, SpinnerDropdown
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Rectangle, RoundedRectangle

from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

# Constante pour le Status de cellule (Label ou TextInput) Ci-dessous.
STATUS_NEUTRE  = 0
STATUS_INACTIF = 1
STATUS_ERREUR  = 2
STATUS_VALIDE  = 3
STATUS_TRANSLICIDE = 4

# Constantes de statut d'onglets de bouton
BTN_NEUTRE   = 0   # Bouton standard d'usine (Gris/Vert sombre)
BTN_ACTIF    = 1   # Onglet actuellement sélectionné / enfoncé (Vert flashy)
BTN_INACTIF  = 2   # Fonction non disponible ou bridée (Gris/Vert très sombre)
BTN_ALARME   = 3   # Alerte machine ou attention requise (Orange/Rouge saumon)
SW_GRIS_ON   = 4    # pout toogle_boton enfoncé Gris
SW_GRIS_OFF  = 5    # pout toogle_boton relâché Gris plus claire

Builder.load_file(os.path.join(os.path.dirname(__file__), "common_widgets.kv"))


class MyLabel(Label):
    """Label personnalisé avec alignement automatique et support du markup."""
    def __init__(self, markup=True, font_size_factor=1, **kwargs):
        kwargs.setdefault('halign', 'left')
        kwargs.setdefault('valign', 'middle')
        kwargs.setdefault('markup', markup)
        super().__init__(**kwargs)
        self.font_size_factor=font_size_factor

        self.original_font_size = kwargs.get("font_size", 18)  # fallback si non défini
        self.font_size = self.original_font_size * self.font_size_factor

        self.bind(size=self._update_text_size)

    def _update_text_size(self, *args):
        self.text_size = self.size

class LabeledCell(Label):
    def __init__(
        self,
        text="",
        halign='right',
        valign='middle',
        size_hint_x=None,
        width=180,
        bg_color=(0.3, 0.3, 1, 0.7),
        text_color=(1, 1, 1, 1),
        bold=False,
        font_size=None,
        on_click=None,
        **kwargs
    ):
        self.on_click = on_click
        super().__init__(**kwargs)

        self.text = text
        self.halign = halign
        self.valign = valign
        self.bold = bold
        self.color = text_color
        self.padding = (10, 0)

        # Taille x ou largeur
        if size_hint_x is not None:
            self.size_hint_x = size_hint_x
        else:
            self.size_hint_x = None
            self.width = width

        # Text wrapping et raccourci si débordement
        self.text_size = (self.width, None)
        self.shorten = True
        self.shorten_from = 'right'

        if font_size is not None:
            self.font_size = font_size

        # Fond custom
        #with self.canvas.before:
        #    Color(*bg_color)
        #    self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        with self.canvas.before:
            self.bg_color_instruction = Color(*bg_color)  # ✅ stocke la Color
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)            

        self.bind(size=self._update_rect, pos=self._update_rect)
        self.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

    def _update_rect(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Ne déclenche que si ce n’est PAS un ButtonBehavior (sinon ça double)
            if callable(self.on_click) and not isinstance(self, ButtonBehavior):
                self.on_click(self)
                return True
        return super().on_touch_down(touch)

class LabeledToggleCell(LabeledCell):
    """
    Widget affichant plusieurs états cycliques (off + états actifs).
    Idéal pour des options à état unique ou multiple (ex: relatif / absolu).

    Callback :
        on_state_change(key, new_state, was_off)

        - key (str) : identifiant du widget
        - new_state (int) : nouvel état actif (>= 1)
        - was_off (bool) : True si état précédent = 0 (inactif)
    """
    def __init__(self, key, text, callback=None, **kwargs):
        self.key = key
        self.state = 0  # Toujours démarrer à OFF
        self.on_state_change = callback

        # État par défaut (OFF)
        self.off_state = {
            "bg": (0.25, 0.25, 0.25, 0.7),
            "fg": (0.7, 0.7, 0.7, 1),
            "text": text
        }

        # Dictionnaires d'états
        self.bg_colors = {0: self.off_state["bg"]}
        self.fg_colors = {0: self.off_state["fg"]}
        self.text_states = {0: self.off_state["text"]}
        self.states = [copy(self.off_state)]  # Index 0 : off

        # Appel au parent
        super().__init__(
            text=text,
            halign='center',
            valign='middle',
            bg_color=self.off_state["bg"],
            text_color=self.off_state["fg"],
            on_click=self.toggle_up_state,
            **kwargs
        )

    def refresh_style(self):
        """Met à jour le style en fonction de l'état courant."""
        bg = self.bg_colors.get(self.state, self.off_state["bg"])
        fg = self.fg_colors.get(self.state, self.off_state["fg"])
        txt = self.text_states.get(self.state, self.off_state["text"])

        if hasattr(self, "bg_color_instruction"):
            self.bg_color_instruction.rgba = bg  # ✅ rgba, pas rgb/a séparés
        self.color = fg
        self.text = txt

    def add_state(self, bg_color=None, fg_color=None, text=None):
        """Ajoute un nouvel état actif (1, 2, ...)."""
        next_state = len(self.states)
        self.states.append(copy(self.off_state))

        self.bg_colors[next_state] = bg_color or self.off_state["bg"]
        self.fg_colors[next_state] = fg_color or self.off_state["fg"]
        self.text_states[next_state] = text or self.off_state["text"]

        return next_state

    def modify_state(self, state, bg_color=None, fg_color=None, text=None):
        """Modifie un état existant (0 compris)."""
        if not (0 <= state < len(self.states)):
            return

        if bg_color is not None:
            self.bg_colors[state] = bg_color
        if fg_color is not None:
            self.fg_colors[state] = fg_color
        if text is not None:
            self.text_states[state] = text

        if self.state == state:
            self.refresh_style()

    def toggle_up_state(self, *_):
        """Change d'état en boucle (1 → 2 → ... → 1)."""
        was_off = (self.state == 0)
        num_states = len(self.states) - 1

        if num_states == 0:
            return  # Aucun état actif défini

        self.state += 1
        if self.state > num_states:
            self.state = 1  # Boucle dans les états actifs

        self.refresh_style()

        if callable(self.on_state_change):
            self.on_state_change(self.key, self.state, was_off)

    def set_state(self, state, trigger_callback=False):
        if not (0 <= state < len(self.states)):
            print(f">> ERREUR << : status ({state}) envoyer à LabelToggleCell() absant ou invalide")
            return
        was_off = (self.state == 0)
        self.state = state
        self.refresh_style()
        if trigger_callback and callable(self.on_state_change):
            self.on_state_change(self.key, self.state, was_off)

    def turn_off(self, trigger_callback=False):
        was_off = (self.state == 0)
        self.state = 0
        self.refresh_style()
        if trigger_callback and callable(self.on_state_change):
            self.on_state_change(self.key, self.state, was_off)

    def get_state(self):
        """Retourne l’état courant."""
        return self.state

class ClickableLabel(ButtonBehavior, LabeledCell):
    __events__ = ('on_click',)  # ✅ déclare un événement Kivy utilisable dans KV

    def __init__(self, **kwargs):
        self.bg_color = kwargs.pop('bg_color', (0, 0, 1, 0))
        self.hover_color = kwargs.pop('hover_color', (0, 0, 0, 0.2))
        super().__init__(**kwargs)
        Window.bind(mouse_pos=self._on_mouse_pos)
        self._hover = False

    def on_kv_post(self, base_widget):
        self.bg_color_instruction.rgba = self.bg_color        

    def _on_mouse_pos(self, window, pos):
        inside = self.collide_point(*pos)
        if inside and not self._hover:
            self._hover = True
            self.on_enter()
        elif not inside and self._hover:
            self._hover = False
            self.on_leave()

    def on_enter(self):
        self.bg_color_instruction.rgba = self.hover_color

    def on_leave(self):
        self.bg_color_instruction.rgba = self.bg_color

    def on_press(self):
        # Appelé quand l’utilisateur clique
        #self.dispatch('on_click')  # ✅ déclenche l’événement pour KV
        pass

    def on_click(self, *args):
        #"""Événement personnalisé (peut être redéfini dans KV)."""
        #pass
        print("ClickableLabel.on_click() triggered!")

class HoverLabel(Label):
    """
    Label comme LabeledCell (avec les ... si le texte est trop long)
    + avec en plus couleur différensier au survol de la souris
    - sans la fonction réagisant au click
    """
    def __init__(
        self,
        text="",
        halign='right',
        valign='middle',
        size_hint_x=None,
        width=180,
        bg_color=(0.3, 0.3, 1, 0.7),
        hover_color = None,
        text_color=(1, 1, 1, 1),
        bold=False,
        font_size=None,
        **kwargs
    ):
        super().__init__(**kwargs)
		
        Window.bind(mouse_pos=self._on_mouse_pos)

        self.text = text
        self.halign = halign
        self.valign = valign
        self.bold = bold
        self.color = text_color
        self.padding = (10, 0)
        self.bg_color = bg_color
        self.hover_color = hover_color if hover_color else bg_color
        self._hover = False

        # Taille x ou largeur
        if size_hint_x is not None:
            self.size_hint_x = size_hint_x
        else:
            self.size_hint_x = None
            self.width = width

        # Text wrapping et raccourci si débordement
        self.text_size = (self.width, None)
        self.shorten = True
        self.shorten_from = 'right'

        if font_size is not None:
            self.font_size = font_size

        with self.canvas.before:
            self.bg_color_instruction = Color(*bg_color)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)            

        self.bind(size=self._update_rect, pos=self._update_rect)
        self.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

    def on_kv_post(self, base_widget):
        self.bg_color_instruction.rgba = self.bg_color        

    def _on_mouse_pos(self, window, pos):
        inside = self.collide_point(*pos)
        if inside and not self._hover:
            self._hover = True
            self.on_enter()
        elif not inside and self._hover:
            self._hover = False
            self.on_leave()

    def on_enter(self):
        self.bg_color_instruction.rgba = self.hover_color

    def on_leave(self):
        self.bg_color_instruction.rgba = self.bg_color


    def _update_rect(self, *args):
        self.bg_rect.size = self.size
        self.bg_rect.pos = self.pos

class InputCell(TextInput):
    # Déclaration de vos constantes de statut en haut de fichier (rappel)
    # STATUS_NEUTRE = 0, STATUS_INACTIF = 1, etc.
    # STATUS_TRANSLICIDE = 4  # Votre nouvelle constante

    STATUS_COLORS = {
        STATUS_NEUTRE:      (1, 1, 1, 0.85),        # blanc doux
        STATUS_INACTIF:     (0.75, 0.75, 0.75, 1),  # gris clair
        STATUS_ERREUR:      (1, 0.5, 0.5, 1),       # rouge clair
        STATUS_VALIDE:      (0.6, 1, 0.6, 1),       # vert clair
        STATUS_TRANSLICIDE: (0, 0, 0, 0),           # 🎯 Transparent pur comme un Label
    }

    def __init__(self, text, status=STATUS_NEUTRE, size_hint_x = None, width=180, halign = 'right', **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.status = status
        self.def_back_color = self.STATUS_COLORS[STATUS_NEUTRE]
        
        if size_hint_x is not None:
            self.size_hint_x = size_hint_x
        else:
            self.size_hint_x = None
            if width is not None:
                self.width = width
                
        self.padding = (10, 1)
        self.multiline = False
        self.write_tab = False
        self.halign = halign
        self.valign = 'middle'
        self.text_size = (self.width, None)
        self.foreground_color = (0, 0, 0, 1)

        # 🎯 DÉCLENCHEMENT INITIAL : La méthode set_status va configurer l'arrière-plan dès le départ
        self.set_status(status)
        self.bind(focus=self.on_focus)
        self.bind(height=self._update_padding)

    def _update_padding(self, *args):
        font_height = self.line_height  # Hauteur d'une ligne de texte
        vertical_padding = max((self.height - font_height) / 2, 0)
        self.padding = [10, vertical_padding]

    def set_status(self, status=None):
        """Met à jour le statut et applique dynamiquement les masques de textures."""
        self.status = STATUS_NEUTRE if status is None else status
        
        # 🎯 LE DÉCLENCHEUR D'EFFACEMENT (Votre intuition géniale !)
        if self.status == STATUS_TRANSLICIDE:
            # Si on demande du translucide, on vide les textures pour libérer le canal Alpha à 0
            self.background_normal = ""
            self.background_active = ""
            self.background_disabled_normal = ""
        else:
            # Sinon, on laisse Kivy utiliser ses images d'usine pour garder le joli relief des cases de saisie
            # Si vous aviez des images spécifiques (ex: "atlas://data/images/defaulttheme/textinput"), remettez-les ici.
            # En laissant Kivy gérer, il ré-applique les valeurs par défaut du framework si on change de statut.
            pass

        # Récupération et application de la couleur associée dans votre dictionnaire
        color = self.def_back_color if status is None else self.STATUS_COLORS.get(self.status, (1, 1, 1, 1))
        self.background_color = color

    def get_status(self):
        return self.status

    def on_focus(self, instance, value):
        if value:
            Clock.schedule_once(lambda dt: instance.select_all(), 0.2)

class InputCellLabel(InputCell):
    def __init__(self, label_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuration du texte et du label
        self.label_text = label_text
        self.label = MyLabel(text=label_text, font_size=18, color=(0.7, 0.7, 0.7, 1), italics=True, font_size_factor=0.75)
        
        # Ajouter le label dans le canvas de l'InputCell
        self.add_widget(self.label)

        # Positionnement et ajustements du label par rapport à l'InputCell
        self.label.pos = self.pos
        self.label.size = self.size
        
        # Lier le label aux dimensions de l'InputCell
        self.bind(size=self.update_label_position)
        self.bind(pos=self.update_label_position)
        
        self.background_normal = ''  # Pas de fond normal
        self.background_active = ''  # Pas de fond actif

    def update_label_position(self, *args):
        """Met à jour la position et la taille du label lorsque l'InputCell change"""
        self.label.pos = self.pos
        self.label.size = self.size

    def on_touch_down(self, touch):
        """Gestion de l'interaction, on empêche la sélection du label"""
        if self.collide_point(*touch.pos):
            # Ignore toute interaction sur le label
            return super().on_touch_down(touch)
        return False

class MenuButton(ToggleButtonBehavior, Label):
    STATUS_COLORS = {
        BTN_NEUTRE:   (0.2, 0.35, 0.2, 1),    # Vert d'ambiance d'origine
        BTN_ACTIF:    (0.3, 0.6, 0.3, 1),     # Vert plus flashy (sélectionné / enfoncé)
        BTN_INACTIF:  (0.12, 0.15, 0.12, 1),  # Gris éteint et bloqué
        BTN_ALARME:   (1, 0.5, 0.3, 1),       # Orange/Rouge d'alerte
        SW_GRIS_OFF:   (0.32, 0.28, 0.35, 1),    # "#9EA69E"
        SW_GRIS_ON:  (0.62, 0.65, 0.62, 1)     # "#6B736B"
    }

    # 🎯 TRICHE UNIFIÉE : On ajoute is_toggle=False par défaut
    def __init__(self, text="", status=BTN_NEUTRE, is_toggle=False, **kwargs):
        super().__init__(**kwargs)
        
        self.text = text
        self.bold = True
        self.halign = "center"
        self.valign = "middle"
        self.is_toggle = is_toggle  # Sauvegarde de ta manette de contrôle
        # Création du fond RoundedRectangle opaque
        with self.canvas.before:
            self.canvas_bg_color = Color(0, 0, 0, 1)
            self.canvas_bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4)])
        
        # Attaches géométriques et de texte
        self.bind(pos=self._update_canvas_geometry, size=self._update_canvas_geometry)
        self.bind(size=lambda inst, size: setattr(inst, 'text_size', size))
        
        # Écoute de l'état Kivy pour changer la couleur automatiquement
        self.bind(state=self._on_state_changed)
        
        self.set_status(status)

    def _update_canvas_geometry(self, *args):
        self.canvas_bg_rect.pos = self.pos
        self.canvas_bg_rect.size = self.size

    def _on_state_changed(self, instance, state):
        """Bascule la couleur du fond dès que Kivy change l'état du Toggle."""
        self.set_status(self.status)

    def set_status(self, status='normal'):
        """Applique la couleur selon le statut ou l'enfoncement."""
        self.status = status
        self.disabled = True if self.status == BTN_INACTIF else False

        # Si le bouton est enfoncé (down), il prend la couleur active
        if not self.is_toggle:
            if self.state == 'down':
                color = self.STATUS_COLORS[BTN_ACTIF]  # Devient vert flashy
            else:
                color = self.STATUS_COLORS.get(self.status, self.STATUS_COLORS[BTN_NEUTRE])
        else:
            if self.state == 'down':
                color = self.STATUS_COLORS[SW_GRIS_ON]  # Devient vert flashy
            else:
                toogle_status = 5 if self.status == 0 and self.state == 'normal' else self.status
                color = self.STATUS_COLORS.get(toogle_status, self.STATUS_COLORS[SW_GRIS_OFF])
            
        self.canvas_bg_color.rgba = color

    # =====================================================================
    # 🎯 LE SECRET DE LA TRICHE : LE RETOUR AUTOMATIQUE A L'ÉTAT INITIAL
    # =====================================================================
    def on_release(self):
        """Déclenché quand l'opérateur relâche le clic."""
        # Si ce bouton n'est PAS un vrai interrupteur permanent (is_toggle est False)
        if not self.is_toggle:
            # On force le bouton à se relâcher immédiatement tout seul !
            self.state = "normal"
        return super().on_release()


class BtnSwitchImageLed(ButtonBehavior, BoxLayout):
    """
    🎛️ HYBRID MENU BUTTON WITH LIGHT-FRAME (Version 7.2) :
    Bouton-conteneur d'adresse. Reçoit des images/textes depuis le .kv.
    Gère la triche de retour automatique à l'état normal.
    """
    target_screen = StringProperty("")  # Clé de la DictProperty (ex: 'screen_CUTTER')
    is_toggle = BooleanProperty(False)  # True = Interrupteur fixe | False = Impulsion / Triche
    is_switch = BooleanProperty(False)  # Détecte s'il s'agit du bouton tactile
    # 🟢 SÉCURISÉ : On déclare le suffixe comme une vraie propriété Kivy avec une valeur de base solide !
    suffixe_act = StringProperty("_ia")

    def __init__(self, **kwargs):
        # Configuration industrielle par défaut du conteneur vertical
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('padding', '6dp')
        kwargs.setdefault('spacing', '4dp')
        kwargs.setdefault('size_hint_y', None)
        kwargs.setdefault('height', '65dp')
        super().__init__(**kwargs)

    def _init_button_logic(self, instance, value):
        """ Calcule si c'est un interrupteur et se branche sur l'écoute de l'App """
        self.is_switch = "sw_" in self.target_screen
        
        app = App.get_running_app()
        if app:
            # Dès que l'écran actif change dans le main, on recalcule notre reflet !
            app.bind(screen_actif=self._update_suffix)
            self._update_suffix()

    def _update_suffix(self, *args):
        """ Moulinette Python synchrone qui garantit le "_a" ou le "_ia" en RAM """
        app = App.get_running_app()
        if app and app.screen_actif == self.target_screen:
            self.suffixe_act = "_a"
        else:
            self.suffixe_act = "_ia" # Valeur de repli automatique, jamais None !


    def on_release(self):
        """ 🎯 LE SECRET DE LA TRICHE SÉCURISÉ """
        # Si ce n'est pas un interrupteur permanent (comme sw_TACTILE)
        if not self.is_toggle:
            # On force le bouton à se relâcher immédiatement tout seul
            self.state = "normal"
        return super().on_release()

class BottonImageLed(ButtonBehavior, BoxLayout):
    """ 🖥️ BOUTON D'ONGLET DE NAVIGATION PURE (V_7.2) """
    show_both = BooleanProperty(False)
    target_screen = StringProperty("")  # Ex: 'screen_CUTTER'
    suffixe_act = StringProperty("_ia")
    display_mode = StringProperty("TEXT_ONLY")
    # Référance utilisé Par le .kv (Réactif au changements)
    source_image = StringProperty("")
    status_led = StringProperty("ok")
    text_bouton = StringProperty("- -")

    def __init__(self, **kwargs):
        show_both_val = kwargs.pop('show_both', False)
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('padding', '6dp')
        kwargs.setdefault('spacing', '4dp')
        kwargs.setdefault('size_hint_x', 1.0)
        kwargs.setdefault('size_hint_y', 1.0)
        #kwargs.setdefault('height', '65dp')
        super().__init__(**kwargs)

        self.show_both = show_both_val
        Clock.schedule_once(self._recalculer_mode_affichage, 0.05)  # Refrech après initiation complette

        self.bind(target_screen=self._connect_to_app)

    def _connect_to_app(self, instance, value):
        app = App.get_running_app()
        if app and self.target_screen:
            app.bind(screen_actif=self._update_ui_state)
            # Écoute réactive de la DictProperty plate du main
            app.bind(**{self.target_screen: self._recalculer_mode_affichage})
            self._update_ui_state()
            self._recalculer_mode_affichage()

    def _update_ui_state(self, *args):
        app = App.get_running_app()
        self.suffixe_act = "_a" if (app and app.screen_actif == self.target_screen) else "_ia"

    def _recalculer_mode_affichage(self, *args):
        """ 🎯 L'AUTOMATE CENTRALISÉ : Répartit les données dans vos passerelles """
        app = App.get_running_app()
        if not app or not self.target_screen:
            self.display_mode = "TEXT_ONLY"
            self.source_image = ""
            self.status_led = "ok"
            self.text_bouton = "-"
            return
            
        screen_dict = getattr(app, self.target_screen, None)
        if not screen_dict:
            return

        # 🟢 TRANSFERT DIRECT DANS VOS PASSERELLES LOCALES (Texte brut, ultra-sûr)
        chemin_icon = screen_dict.get("icon")
        self.source_image = str(chemin_icon) if chemin_icon else ""
        self.status_led = str(screen_dict.get("status", "OK")).lower()
        self.text_bouton = str(screen_dict.get("text", "Er."))
        
        # Validation de l'existence de l'icône
        has_icon = self.source_image != ""

        # Aiguillage des états géométriques X, Y, Z
        if has_icon and self.show_both:
            self.display_mode = "BOTH"
        elif has_icon and not self.show_both:
            self.display_mode = "ICON_ONLY"
        else:
            self.display_mode = "TEXT_ONLY"

    def on_release(self):
        # Relâchement automatique natif sans triche mécanique
        self.state = "normal"
        return super().on_release()


class SwitchImageLed(ButtonBehavior, BoxLayout):
    """ 🎛️ INTERRUPTEUR TACTILE AVEC PALIER DE PROPRIÉTÉS ISOLÉES (V_7.2 Master) """
    show_both = BooleanProperty(False)
    target_screen = StringProperty("")  
    suffixe_act = StringProperty("_ia")
    prefixe = StringProperty("")    #("sw_") Si status "OK"
    display_mode = StringProperty("TEXT_ONLY")
    
    # 🟢 LES MÊMES PASSERELLES LOCALES POUR LE COMMUTATEUR
    source_image = StringProperty("")
    status_led = StringProperty("ok")
    text_bouton = StringProperty("--")

    def __init__(self, show_both:bool = False, **kwargs):
        show_both_val = kwargs.pop('show_both', False)
        kwargs.setdefault('orientation', 'vertical')
        kwargs.setdefault('padding', '6dp')
        kwargs.setdefault('spacing', '4dp')
        kwargs.setdefault('size_hint_x', 1.0)
        kwargs.setdefault('size_hint_y', 1.0)
        super().__init__(**kwargs)

        self.show_both = show_both_val
        Clock.schedule_once(self._sync_with_machine, 0.05)  # Refrech après initiation complette
        
        app = App.get_running_app()
        if app:
            app.bind(mode_tactile_actif=self._sync_with_machine)
            app.bind(sw_TACTILE=self._sync_with_machine)
            self._sync_with_machine()



    def _sync_with_machine(self, *args):
        app = App.get_running_app()
        if not app or not self.target_screen:
            self.prefixe = ""
            self.display_mode = "TEXT_ONLY"
            self.source_image = ""
            self.status_led = "ok"
            self.text_bouton = "-"
            return
            
        # Étage 1 : Activation
        if app.mode_tactile_actif:
            self.state = "down"
            self.suffixe_act = "_a"
        else:
            self.state = "normal"
            self.suffixe_act = "_ia"
            
        # Étage 2 : Données d'armoire
        statut_brut = app.sw_TACTILE.get("status", "OK")
        self.status_led = str(statut_brut).lower()
        self.text_bouton = str(app.sw_TACTILE.get("text", "Er."))
        
        chemin_icon = app.sw_TACTILE.get("icon")
        self.source_image = str(chemin_icon) if chemin_icon else ""
        
        # Étage 3 : Préfixe de santé
        self.prefixe = "" if statut_brut != "OK" else "sw_"
        
        # Étage 4 : Automate géométrique
        has_icon = self.source_image != ""
        if has_icon and self.show_both:
            self.display_mode = "BOTH"
        elif has_icon and not self.show_both:
            self.display_mode = "ICON_ONLY"
        else:
            self.display_mode = "TEXT_ONLY"


class CustomSpinnerOption(SpinnerOption):
    def on_parent(self, instance, parent):
        # Quand l'option est attachée à l'affichage
        if self.text == self.spinner.text:
            # Sélectionnée : bouton pressé
            self.background_down = 'atlas://data/images/defaulttheme/button_pressed'
            self.color = (1, 1, 1, 1)  # Texte blanc
        else:
            # Non sélectionnée : bouton normal
            self.background_down = 'atlas://data/images/defaulttheme/button'
            self.color = (1, 1, 1, 1)  # Ou autre couleur si besoin

#class CustomSpinnerDropdown(SpinnerDropdown):
class CustomSpinnerDropdown(DropDown):
    def _create_option(self, text):
        return CustomSpinnerOption(text=text, spinner=self.spinner)

    def open(self, spinner):
        super().open(spinner)
        self.y += spinner.height  # Remonte la dropdown

class CustomSpinner(Spinner):
    def _dropdown_cls(self):
        return CustomSpinnerDropdown

class Separator(Widget):
    """Ligne de séparation horizontale avec marges verticales."""
    def __init__(self, margin=10, color=(0.7, 0.7, 0.7, 1), thickness=1, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.margin = dp(margin)
        self.thickness = dp(thickness)
        self.height = self.margin * 2 + self.thickness

        with self.canvas.before:
            Color(*color)
            self.rect = Rectangle(pos=self.pos, size=(self.width, self.thickness))

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = (self.x, self.y + self.margin)
        self.rect.size = (self.width, self.thickness)

class GroupHeader(BoxLayout):
    """Titre de section avec une ligne de séparation à droite."""
    def __init__(self, title, color=(0.7, 0.7, 0.7, 1), thickness=2, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(30)
        self.spacing = dp(5)        

        self.label = Label(
            text=f"[b]{title}[/b]" if thickness > 2 else f"{title}",
            markup=True,
            halign="left",
            valign="middle",
            size_hint_x=None,
            color=color,
        )
        self.label.bind(texture_size=self._resize_label)
        self.add_widget(self.label)

        self.separator = Separator(margin=14, color=color, thickness=thickness)
        self.add_widget(self.separator)

    def _resize_label(self, instance, value):
        instance.width = value[0] + dp(10)  # petit padding
