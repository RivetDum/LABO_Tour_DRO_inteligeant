# part/shapes/round_corner.py

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
import math
#import copy deepcopy devient: copy.deepcopy
from copy import deepcopy
from kivy.metrics import dp

from .base_shape import BaseShape
from common_widgets import LabeledCell, InputCell, MyLabel, Separator, STATUS_VALIDE,STATUS_ERREUR,STATUS_NEUTRE,STATUS_INACTIF
#from common_draw import *
import common_draw as cd
import config as conf
#from ui_configurator.theme_ui import UiTheme
from ui_configurator.theme_manager import draw_line as th_drl

class RoundedCornerShape(BaseShape):
    shape_type = ['round', 'corner']
    val_default = { "rayon_conge": 2000}  # en microns

    def __init__(self, point_a, entry_b, point_c, mirror_z=False):
        super().__init__(point_a, entry_b, point_c, mirror_z)
        self.params = self.entry.raw["shape_params"]
        self.compute_geometry()

    def update_params(self, params=None):
        self.update_params_Base(params)
        self.compute_geometry()
        self.update_shape_label_name(self.get_shape_label_name())

    def compute_geometry(self):
        self.entities = []

        r = self.params.get("rayon_conge", self.val_default["rayon_conge"])

        A = self.point_a
        B = self.point_b
        C = self.point_c
        
        conge = cd.create_fillet(point_before=A, point_intersect=B, point_after=C, radius=r, dict_formated_auto=True)
        prof_conge = deepcopy(conge) 
        prof_conge["color"] = th_drl["profil"]
        prof_conge["id_pnt"] = None  # id_pnt sera màj après depuis prof_seg_pnt_recompute()
        self.draw_part = [prof_conge]

        conge["color"] = th_drl["detail"]
        ''' Pour info:
        Args:
            raw_list (list): Liste de dict des définitions brutes (type, points, etc.).
                ex ligne : {"type":"l", "start":[0,0], "end":[0,0], "color":(0.5,0.5,0.5,1), "id_pnt":None} 
                ex arc : {"type":"a", "start":[0,0], "end":[0,0], "center":[0,0], "radius":0, "dir":True}
                ex cercle: {"type":"c", "center":[0,0], "radius":0, "color":#rrggbb, "id_pnt":10}
                args:
                    type   (str):   une lettre désignant le type de segment
                    start  ([float,float]): position X Y du point de départ (début du trait)
                    end    ([float,float]): position X Y du point d'arrivé  (fin du trait)
                    center ([float,float]): position X Y du centre pour segment arrondi
                    radius  (float): dimention du rayon
                    dir    (bool):  direction de dessin :vrai sens horaire ; faux sens anti-horaire
                    color: "Optionnel" couleur format (R,G,B,A) ou "#exa"
                id_pnt: "Optionnel" identifiant du point d'incertion
        '''
        entities = []
        entities.append({"type":"l", "start":A, "end":B, "color":th_drl["liaison"]}) # "#838d83"
        entities.append(conge)
        #center_conge=conge["center"]
        #entities.append({"type":"c", "center":center_conge, "radius":r, "color":(0,0,1,1)})        
        entities.append({"type":"l", "start":B, "end":C, "color":th_drl["liaison"]})



        # TODO: à voir ci déplacable dans la partie dessin pour aléger en cas de non dessin
        self.entities = cd.create_entities_from_raw(entities, error_color=th_drl["erreur_detail"])

        # met à jour la boxe de dessin
        self.update_draw_shape(self.entities)

    def get_shape_label_name(self):
        return f"Congé (R={self.params.get('rayon_conge', self.val_default['rayon_conge'])/1000})"

    def shape_config_box(self):
        
        layout = self.create_standard_config_box(orientation='horizontal', pilot_hint=(1, None), fixed_size=(None, None))

        # Ajouter ici les widgets spécifiques
        label = Label(text="Rayon :", size_hint=(0.5, None), height=dp(30))
        text_val = conf.format_unit(self.params.get("rayon_conge", 1000),"unit_distance",True)
        input_r = InputCell(text=f"{text_val[0]} {text_val[1]}", size_hint=(0.5, None), height=dp(30), halign="center")
        
        def on_text_change(instance, value):
            parsed = conf.parse_user_input(value, default_unit_type_or_id='unit_distance')

            if isinstance(parsed, str):  # Erreur de parsing
                instance.set_status(STATUS_ERREUR)
                return

            val_float, unit_id, _ = parsed
            instance.set_status(STATUS_NEUTRE)

            # Mise à jour de la valeur en µm
            factor = conf.get_unit_config(unit_id).get("factor", 1.0)
            self.update_params({"rayon_conge": int(round(val_float * factor))})     
        
        input_r.bind(text=on_text_change)
        layout.add_widget(label)
        layout.add_widget(input_r)
        return layout


class RoundedShape(BaseShape):
    shape_type = ['round', 'Arc_rayon']
    val_default = { "rayon_conge": 2000}  # en microns

    def __init__(self, point_a, entry_b, point_c, mirror_z=False):
        super().__init__(point_a, entry_b, point_c, mirror_z)
        self.params = self.entry.raw["shape_params"]
        self.compute_geometry()

    def update_params(self, params=None):
        self.update_params_Base(params)
        self.compute_geometry()
        self.update_shape_label_name(self.get_shape_label_name())

    def compute_geometry(self):
        self.entities = []

        r = self.params.get("rayon_conge", self.val_default["rayon_conge"])

        A = self.point_a
        B = self.point_b
        C = self.point_c
        
        conge = cd.create_fillet(point_before=A, point_intersect=B, point_after=C, radius=r, list_formated_auto=True)
        #conge.append((0.5,0.9,0.5,1))
        conge.append(th_drl["detail"])
        center_conge=conge[3]

        entities = []
        #entities.append(["l", A, B,(0.9, 0.5, 0.3, 1)]) #couleur vert pâle
        entities.append(["l", A, B,th_drl["liaison"]]) 
        entities.append(conge)
        #entities.append(["c", B,r,(0,1,0,1)])
        #entities.append(["c", center_conge,r,(0,0,1,1)])
        #entities.append(["l", B, C,(0.3, 0.5, 0.3, 1)]) #couleur vert pâle
        entities.append(["l", B, C,th_drl["liaison"]]) 
        
        self.entities = cd.create_entities_from_raw(entities)

        # met à jour la boxe de dessin
        self.update_draw_shape(self.entities)

    def get_shape_label_name(self):
        return f"Congé (R={self.params.get('rayon_conge', self.val_default['rayon_conge'])/1000})"

    def shape_config_box(self):
        
        layout = self.create_standard_config_box(orientation='horizontal', pilot_hint=(1, None), fixed_size=(None, None))

        # Ajouter ici les widgets spécifiques
        label = Label(text="Rayon :", size_hint=(0.5, None), height=dp(30))
        text_val = conf.format_unit(self.params.get("rayon_conge", 1000),"unit_distance",True)
        input_r = InputCell(text=f"{text_val[0]} {text_val[1]}", size_hint=(0.5, None), height=dp(30), halign="center")
        
        def on_text_change(instance, value):
            parsed = conf.parse_user_input(value, default_unit_type_or_id='unit_distance')

            if isinstance(parsed, str):  # Erreur de parsing
                instance.set_status(STATUS_ERREUR)
                return

            val_float, unit_id, _ = parsed
            instance.set_status(STATUS_NEUTRE)

            # Mise à jour de la valeur en µm
            factor = conf.get_unit_config(unit_id).get("factor", 1.0)
            self.update_params({"rayon_conge": int(round(val_float * factor))})     
        
        input_r.bind(text=on_text_change)
        layout.add_widget(label)
        layout.add_widget(input_r)
        return layout


