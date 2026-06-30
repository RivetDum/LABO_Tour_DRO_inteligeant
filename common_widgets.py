# common_widgets.py

from kivy.uix.widget import Widget
from copy import copy
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty
#from kivy.uix.spinner import Spinner, SpinnerOption, SpinnerDropdown
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window

# Constante pour le Status de cellule (Label ou TextInput) Ci-dessous.
STATUS_NEUTRE  = 0
STATUS_INACTIF = 1
STATUS_ERREUR  = 2
STATUS_VALIDE  = 3

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
        """Met à jour le style en fonction de l’état courant."""
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
        """Change d’état en boucle (1 → 2 → ... → 1)."""
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
        self.bg_color = kwargs.pop('bg_color', (0, 0, 1, 1))
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
    STATUS_COLORS = {
        STATUS_NEUTRE:  (1, 1, 1, 0.85),        # blanc doux
        STATUS_INACTIF: (0.75, 0.75, 0.75, 1),  # gris clair
        STATUS_ERREUR:  (1, 0.5, 0.5, 1),       # rouge clair
        STATUS_VALIDE:  (0.6, 1, 0.6, 1),       # vert clair
    }

    def __init__(self, text, status=STATUS_NEUTRE, size_hint_x = None, width=180, halign = 'right', **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.status = status
        self.def_back_color = self.STATUS_COLORS[STATUS_NEUTRE]
        if size_hint_x is not None:    # Gère intelligemment size_hint_x et width
            self.size_hint_x = size_hint_x
        else:
            self.size_hint_x = None
            if width is not None:
                self.width = width  # Pas de width = None ici !
        self.padding = (10, 1)
        #self.padding_y = [5, 5]
        self.multiline = False
        self.write_tab = False
        self.halign = halign
        self.valign = 'middle'
        self.text_size = (self.width, None)
        self.foreground_color = (0, 0, 0, 1)

        self.set_status(status)
        self.bind(focus=self.on_focus)
        self.bind(height=self._update_padding)

    def _update_padding(self, *args):
        font_height = self.line_height  # Hauteur d'une ligne de texte
        vertical_padding = max((self.height - font_height) / 2, 0)
        self.padding = [10, vertical_padding]

    def set_status(self, status=None):
        self.status = STATUS_NEUTRE if status is None else status
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
