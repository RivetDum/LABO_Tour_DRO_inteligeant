# part/shapes/base_shape.py

import copy
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp

from common_widgets import LabeledCell
import common_draw as cd


class BaseShape:
    shape_type = None   #['generic_shape', 'base']
    val_default = {}
    add_connect_line = False

    def __init__(self, point_a, entry_b, point_c, mirror_z=False, registry=None, params_options_nbr=None):
        """
        Classe de base pour les formes géométriques. Peut être héritée.

        :param point_a: Point A (x, z)
        :param entry_b: Dictionnaire contenant les données du point d'entrée 
                        (doit contenir une clé 'raw' avec 'pos', 'shape_params', etc.)
        :param point_c: Point C (x, z)
        :param mirror_z: Booléen pour activer la symétrie selon l'axe Z
        :param registry: (Optionnel) Registre ou contexte externe — utilisé autrefois pour des spinners (peut être supprimé)
        :param params_options_nbr: (Optionnel) Nombre de paramètres à utiliser parmi ceux présents dans le JSON. 
                                Permet de limiter le nombre de paramètres actifs (ex: dans ChamferShape).
                                Si None, tous les paramètres par défaut sont utilisés.

        TODO: Supprimer `registry` s'il n'est plus utilisé (historique: formulaire obsolète).
        """

        self.point_a = point_a
        self.point_b = entry_b.raw["pos"]
        self.point_c = point_c

        self.shape_start = copy.deepcopy(self.point_b)  # Position de départ du 1er segment
        self.shape_end = copy.deepcopy(self.point_b)    # Position d'arrivée du dernier segment
        self.draw_part = []
        self.profil_piece = None

        self.entry = entry_b
        self.mirror_z = mirror_z
        self.registry = registry
        self.status = 0  # État à la création (utile pour les formulaires dynamiques, etc.)

        #self.box_draw_shape = BoxLayout()   # Boxe contenant le graphique de la forme en cours
        self.box_draw_shape = ClickableBox(size_hint=(1,1))
        with self.box_draw_shape.canvas.before:
            self.box_draw_shape_color = Color(0.8, 0.9, 0.8, 0)
            self.box_draw_shape_border = Line(rectangle=(0, 0, 100, 100), width=1)
        self.box_draw_shape.bind(pos=self.update_box_border_pos, size=self.update_box_border_size)
        self.box_draw_shape.bind(on_press=self.on_box_click)

        # Fusion des paramètres utilisateur avec les valeurs par défaut de la forme
        default_params = getattr(self, "val_default", {})
        merged = default_params.copy()

        # Paramètres passés dans le fichier ou générés
        self.params = entry_b.raw.get("shape_params", {})

        if not self.params:
            # Aucune config fournie : on met les valeurs par défaut
            self.params = self.val_default.copy()
        elif isinstance(params_options_nbr, (int, float)):
            # Autorise un total de N paramètres, pas plus - pas moins
            current_param_count = len(self.params)
            remaining_slots = int(params_options_nbr) - current_param_count

            if remaining_slots > 0:
                for key in default_params:
                    if key not in self.params:
                        self.params[key] = default_params[key]
                        remaining_slots -= 1
                        if remaining_slots <= 0:
                            break
        else:
            merged.update(entry_b.raw.get("shape_params", {}) or {})
            self.params = merged    



        self.entry.raw["shape_params"] = self.params    # Mise à jour du point d’entrée avec les paramètres fusionnés
       
        # Màj du label de désignation
        if hasattr(self, 'get_shape_label_name'):
            entry_shape_label = self.get_shape_label_name()
        else:
            entry_shape_label = None
        self.entry.raw["shape_label"] = entry_shape_label

        # Appel automatique à la géométrie si définie
        if hasattr(self, 'compute_geometry'):
            self.compute_geometry()

    def update_params_Base(self, params=None):
        """Fusionne les paramètres utilisateurs avec les valeurs par défaut et enregistre dans entry.raw[shape_params]"""
        raw = self.entry.raw
        merged = raw.get("shape_params", {}).copy()
        merged.update(params or {})
        self.params = merged   
        raw["shape_params"] = merged    # Mise à jour du point d’entrée avec les paramètres fusionnés

    def update_shape_label_name(self, new_name= ""):
        """Changement du nom dans entry.raw[shape_label]"""
        raw = self.entry.raw
        raw["shape_label"] = new_name    # Mise à jour nom pour label

    def recompute(self):
        """
        Permet de relancer le calcul
        -Si la class de la forme n'a pas de fonction recompute, lance la fonction compute_geometry
        """
        if hasattr(self, 'compute_geometry'):
            self.compute_geometry()

    def compute_geometry(self):
        """Permet d'afficher une forme par défaut si aucune géométrie n'est définie dans la sous-classe."""
        # Si la fonction n'existe pas dans la class de la forme, initialise box2_draw_shape avec un défaut selon self.status
        self.update_draw_shape(self.status)

    def get_start_end(self, recompute=False):
        if recompute:
            if hasattr(self, 'recompute'):
                self.recompute()
        return self.shape_start, self.shape_end

    def update_draw_shape(self, entities=[], status=None):
        """
        Met à jour le BoxLayout_dessin avec les entités de la forme.
        Cette méthode peut être appelée par les classes filles après chaque calcul de géométrie.
        """
        # Efface les anciens widgets de la BoxLayout
        self.box_draw_shape.clear_widgets()

        # Si le status n'est pas fourni, utiliser la valeur de self.status
        if status is None:
            status = self.status

        if not entities:
            #self.profil_fall = None # S'assurer de détruire l'ancien objet profil_fall
            #fall_entities = []

            #fall_entities.append(["l", self.point_a, self.point_b,(0.3, 0.3, 0.3, 0.6)]) #couleur gris très pâle
            fall_entities=[{"type":"l", "start":self.point_a, "end":self.point_b, "color":(0.3, 0.3, 0.3, 0.6)}] #couleur gris très pâle
            # calcul du diamètre du cercle =~ 1/20 du cadre
            h_max=(max(abs(self.point_a[1]-self.point_b[1]), abs(self.point_a[1]-self.point_c[1]),abs(self.point_b[1]-self.point_c[1])))
            l_max=(max(abs(self.point_a[0]-self.point_b[0]), abs(self.point_a[0]-self.point_c[0]),abs(self.point_b[0]-self.point_c[0])))
            diam= round(max(h_max,l_max)/20)
            #fall_entities.append(["c", self.point_b, diam, (0.6, 0.6, 0.6, 0.6)]) #couleur gris pâle
            fall_entities.append({"type":"c", "center":self.point_b, "radius":diam, "color":(0.6, 0.6, 0.6, 0.6)}) #couleur gris pâle
            #fall_entities.append(["l", self.point_b, self.point_c,(0.3, 0.3, 0.3, 0.6)]) #couleur gris très pâle
            fall_entities.append({"type":"l", "start":self.point_b, "end":self.point_c, "color":(0.3, 0.3, 0.3, 0.6)}) #couleur gris très pâle        
            fall_draw = cd.create_entities_from_raw(fall_entities, error_color=(1,0,0))
            self.draw_part= []  # initialiser aussi pour le profil de la pièce à aucun segment

            # Ajouter un ProfilPiece avec les entités mises à jour
            if hasattr(self, "profil_fall") and isinstance(self.profil_fall, cd.ProfilPiece):
                self.profil_fall.update_entities(fall_draw)
            else:   # Si aucun ProfilPièce n'existe, en créer un nouveau
                self.profil_fall = cd.ProfilPiece(
                    entities=fall_draw,
                    box_size=self.box_draw_shape.size,
                    conect_line=False
                )

            self.profil_piece = None

            # Afficher un message d'erreur ou d'information selon le statut
            if status == 0:
                msg="Aucune forme sélectionnée"
            elif status == 1:
                msg="Forme Invalide"
            elif status == 2:
                msg="Sous-type manquant ou invalide."
            else:
                msg="Graphique indisponible\npour cette forme"

            fall_label = Label(
                text=msg,
                size_hint=(None, None),   # Taille fixe
                size=(self.box_draw_shape.width * 0.9, self.box_draw_shape.height * 0.4),
                pos_hint={"center_x": 0.0, "center_y": 0.5},
                halign="center", valign="middle",
            )
            fall_label.bind(size=lambda instance, value: setattr(instance, "text_size", value))

            overlay = FloatLayout(size_hint=(1,1))
            overlay.add_widget(fall_label)

            self.box_draw_shape.add_widget(self.profil_fall)
            self.box_draw_shape.add_widget(overlay)

        else:
            # Ajouter un ProfilPiece avec les entités mises à jour
            if isinstance(self.profil_piece, cd.ProfilPiece):
                self.profil_piece.update_entities(entities)
            else:   # Si aucun ProfilPièce n'existe, en créer un nouveau
                self.profil_piece = cd.ProfilPiece(
                    entities=entities,
                    box_size=self.box_draw_shape.size
                )

            self.profil_fall = None
            self.box_draw_shape.add_widget(self.profil_piece)

    def update_box_border_pos(self, instance, value):
        ''' en cas de péplacement du boxe: Ne pas recalculer l'échelle dans le dessin, juste redessiner'''
        self.update_box_border()
        if isinstance(self.profil_piece, cd.ProfilPiece):
            self.profil_piece.on_pos_changed()
        elif hasattr(self, "profil_fall") and isinstance(self.profil_fall, cd.ProfilPiece):
            self.profil_fall.on_pos_changed()
        #f hasattr(self.box_draw_shape, "on_pos_changed"):
        #    self.box_draw_shape.on_pos_changed()
    def update_box_border_size(self, instance, value):
        ''' en cas de changement des dimenssions du boxe: Recalculer l'échelle du dessin avant de redessiner'''
        size_border = self.update_box_border()
        if isinstance(self.profil_piece, cd.ProfilPiece):
            self.profil_piece.on_size_changed(size_border)
        elif hasattr(self, "profil_fall") and isinstance(self.profil_fall, cd.ProfilPiece):
            self.profil_fall.on_size_changed(size_border)    
    
    def update_box_border(self, *args):
        self.box_draw_shape_border.rectangle = (
            self.box_draw_shape.x-5,
            self.box_draw_shape.y-5,
            self.box_draw_shape.width-10,
            self.box_draw_shape.height-10
        )
        return (self.box_draw_shape.width, self.box_draw_shape.height)

    def on_box_click(self, instance):

        if isinstance(self.profil_piece, cd.ProfilPiece):
            add_connect_line = self.profil_piece.conect_line
            self.profil_piece.conect_line = not add_connect_line
        elif hasattr(self, "profil_fall") and isinstance(self.profil_piece, cd.ProfilPiece):
            # ICI: Je pourrais tester avec une màj de box size, pour voir ? 
            # - > mais je penses que update_box_border_size et update_box_border_pos serait plus approprié ?
            add_connect_line = self.profil_fall.conect_line
            self.profil_fall.conect_line = not add_connect_line
        self.update_box_border_size(self.box_draw_shape, None)

        if list(self.box_draw_shape_color.rgba) != [0, 0.5, 0.4, 0]:
            self.box_draw_shape_color.rgba = [0, 0.5, 0.4, 0]
        else:
            self.box_draw_shape_color.rgba = [0.8, 0.8, 0.9, 0]

    def shape_config_box_OLD(self):
        return Label(text="Pas de configuration disponible")
    def shape_config_box(self):
        layout = self.create_standard_config_box(
            orientation='vertical',
            pilot_hint=(1, None),
            fixed_size=(None, None)
        )

        # Message selon le status
        msg = "Aucune forme sélectionnée"
        if self.status == 1:
            msg = "Forme Invalide"
        elif self.status == 2:
            msg = "Sous-type manquant ou invalide"
        elif self.status >= 90:
            msg = "Forme inconnue"

        label = Label(
            text=msg,
            size_hint=(1, None),
            height=dp(40),
            halign="center",
            valign="middle"
        )
        label.bind(size=lambda inst, val: setattr(inst, "text_size", val))

        layout.add_widget(label)
        return layout

    def create_standard_config_box(self, orientation='vertical', pilot_hint=(1, None), fixed_size=(None, dp(400)), spacing=dp(10)):
        """
        Crée un BoxLayout standard configurable.

        Args:
            orientation (str): 'horizontal' ou 'vertical'
            size_hint (tuple): (width_hint, height_hint)
            fixed_size (tuple): (fixed_width_px, fixed_height_px)
            spacing (int): Espace entre les widgets

        Returns:
            BoxLayout: configuré avec update_size_from_parent
        """
        layout = BoxLayout(orientation=orientation, size_hint=(None, None), spacing=spacing, padding=(dp(10), dp(10), dp(10), dp(10)))
        # Ajout du fond ici
        with layout.canvas.before:
            Color(0.7, 0.7, 0.7, 0.2)  # couleur de fond
            layout._bg_rect = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(
            pos=lambda *_: setattr(layout._bg_rect, 'pos', layout.pos),
            size=lambda *_: setattr(layout._bg_rect, 'size', layout.size)
        )        
        
        if pilot_hint[0] != 1:
            layout.bind(minimum_width=layout.setter('width'))

        if pilot_hint[1] != 1:
            layout.bind(minimum_height=layout.setter('height'))

        # Variables internes pour suivre la taille flottante (typiquement taille du parent)
        float_size = [dp(400), dp(400)]

        def update_size_from_parent(new_size):
            """À appeler depuis le parent quand sa taille change.
            new_size = (width, height) disponible dans le parent.
            """
            float_size[:] = new_size
            # Si size_hint pour la largeur est None, on applique une largeur fixe ou flottante
            if pilot_hint[0] == 1:
                layout.width = fixed_size[0] or float_size[0]
            # Même pour la hauteur
            if pilot_hint[1] == 1:
                layout.height = fixed_size[1] if fixed_size[1] is not None else float_size[1]

        layout.update_size_from_parent = update_size_from_parent

        # Init avec une taille par défaut
        update_size_from_parent(float_size)

        return layout

    def get_debug_info(self):
        return {
            "type": self.shape_type,
            "shape_params": self.params,
            "start": self.shape_start,
            "end": self.shape_end,
            "entities": self.entities
        }

    '''def open_subform_OBSOLETTE(self):
        """
        Ouvre le formulaire en fonction du statut de la forme.
        """
        form = BoxLayout(orientation='vertical')
        form.clear_widgets()
        

        def on_spinner_type_change(spinner, value):
            self.update_type(type_shape= value, subtype_shape= None)
            if hasattr(self.subtype_spinner):
                self.subtype_spinner.unbind(on_text=on_spinner_subtype_change) # déactiver
                self.subtype_spinner(value= self.registry.get_all_shape_subtype(self.type_shape))
                self.subtype_spinner.text = "Sélectionnez un sous-type"
                self.subtype_spinner.bind(on_text=on_spinner_subtype_change) # réactiver
        def on_spinner_subtype_change(spinner, value):
            self.update_type(type_shape= self.type_shape, subtype_shape= value)
            #definir la 'class': update_data ?

        self.type_spinner = Spinner(values=self.registry.get_all_shape_type())
        self.type_spinner.text = "Sélectionnez un type" if self.shape_type[0] is None else self.shape_type[0]
        self.type_spinner.bind(on_text=on_spinner_type_change)
        self.type_spinner.size_hint_x = 0.5  # Prendre 50% de l'espace horizontal

        self.subtype_spinner = Spinner(values= [] if self.shape_type[0] is None else self.registry.get_all_shape_subtype(self.shape_type[0]))
        self.subtype_spinner.text = " "  if self.shape_type[1] is None else self.shape_type[1]
        self.subtype_spinner.bind(on_text=on_spinner_subtype_change)
        self.subtype_spinner.size_hint_x = 0.5  # Prendre 50% de l'espace horizontal

        if self.status == 0:
            # Formulaire pour l'état de "point sans forme"
            form.add_widget(Label(text=""))
            form.add_widget(Label(text="Actuellement point sans terminaison."))
            form.add_widget(Label(text=""))
            form.add_widget(Label(text="Pour ajouter une forme, sélectionnez un type."))
            # Ajouter un Spinner pour les types de formes
            form.add_widget(self.type_spinner)
            self.type_spinner.focus = True

        elif self.status == 1:
            # Formulaire pour l'état où le type sélectionné n'est pas valide
            form.add_widget(Label(text=""))
            form.add_widget(Label(text="Le type actuel n'est pas valide"))
            form.add_widget(Label(text=""))
            form.add_widget(Label(text="Sélectionnez un type pour cette forme."))
            # Spinner pour type
            form.add_widget(self.type_spinner)
            self.type_spinner.focus = True

        elif self.status == 2:
            # Formulaire pour l'état où la définition du sous-type est absente ou invalide
            form.add_widget(Label(text="Type ok."))
            form.add_widget(self.type_spinner)
            form.add_widget(Label(text=""))
            label = Label(text="Sous-type manquant ou invalide. Veuillez sélectionner un sous-type valide.")
            form.add_widget(label)
            form.add_widget(self.subtype_spinner)
            self.subtype_spinner.focus = True

        elif self.status >= 90:
            # Formulaire pour l'état où la forme est totalement définie
            type_box = BoxLayout(orientation='horizontal')
            type_box.add_widget(self.type_spinner)
            type_box.add_widget(self.subtype_spinner)
            self.subtype_spinner.focus = True
            form.add_widget(type_box)
            label = Label(text="Forme complète, vous pouvez ajuster ses paramètres.")
            form.add_widget(label)
            # Ajouter ici les champs spécifiques à la forme
            self.add_parameters_fields(form)

        return form'''


class ClickableBox(ButtonBehavior, BoxLayout):
#class ClickableBox(ButtonBehavior, FloatLayout):
    pass

