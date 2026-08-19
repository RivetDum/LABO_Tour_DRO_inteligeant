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
import configurator.config as conf
#from ui_configurator.theme_ui import UiTheme
from ui_configurator.theme_manager import draw_line as th_drl

class RoundedCornerShape(BaseShape):
    shape_type = ['angle', 'corner']    # Identification du type et sub-type
    shape_text = ['Angle', 'Congé']     # Type et sub-type afficher dans les spinners de sélection
    val_default = { "rayon_conge": 2000}  # en microns

    def __init__(self, point_a, entry_b, point_c):
        super().__init__(point_a, entry_b, point_c)
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
        self.draw_part = [prof_conge]

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
        entities = [{"type":"l", "start":A, "end":B}]
        entities.append(conge)  
        entities.append({"type":"l", "start":B, "end":C})

        self.draw_part = [conge]
        self.shape_start = conge.get("start", B)
        self.shape_end = conge.get("end", B)


        # TODO: à voir ci déplacable dans la partie dessin pour aléger en cas de non dessin
        self.entities = cd.re_paint_entities(raw_list=cd.create_entities_from_raw(entities),draw_type="detail", liaison_line=1)

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
    shape_type = ['angle', 'arc rayon']
    shape_text = ['Angle', 'Arc rayon']
    val_default = { "rayon_conge": 2000}  # en microns

    def __init__(self, point_a, entry_b, point_c):
        # 🚀 Nettoyage de mirror_z qui n'a plus rien à faire dans la géométrie brute
        super().__init__(point_a, entry_b, point_c)
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
        
        # 🚀 HARMONISATION TECHNIQUE : On force dict_formated_auto=True 
        # pour obtenir un dictionnaire standardisé de type court "a"
        conge = cd.create_fillet(point_before=A, point_intersect=B, point_after=C, radius=r, dict_formated_auto=True)
        
        # Extraction des points de transition exacts pour les liaisons du PointManager
        self.shape_start = conge.get("start", B)
        self.shape_end = conge.get("end", B)
        center_conge = conge.get("center", B)

        # 🚀 1. ALIMENTATION DU CACHE GÉOMÉTRIQUE BRUT POUR LA PIÈCE (SANS COULEURS)
        self.draw_part = [conge]
        
        # 💡 SOUVENIR DU DÉBUT DE NOTRE CONVERSATION : 
        # Si cette forme représente l'offset de coupe et que vous voulez y injecter 
        # votre nouveau type de forme pleine "rond" (le disque plein violet offset_fill) :
        #
        # self.self.draw_part.append({"type": "r", "center": center_conge, "radius": r})

        # =====================================================================
        # 🖥️ PARTIE DESSIN LOCAL (Vignette de la Pop-up IHM)
        # =====================================================================
        entities_vignette = []
        # Traits de construction théoriques (Gris)
        entities_vignette.append({"type": "l", "start": A, "end": B}) 
        entities_vignette.append({"type": "l", "start": B, "end": C}) 
        
        # L'arc du congé
        entities_vignette.append(conge)
        
        # Optionnel : Le contour du cercle complet d'outillage en filaire pour l'IHM
        entities_vignette.append({"type": "c", "center": center_conge, "radius": r})

        # Envoi au pistolet à peinture local de l'IHM (style "detail" vert)
        self.entities = cd.re_paint_entities(
            raw_list=cd.create_entities_from_raw(entities_vignette), 
            draw_type="detail", liaison_line=1
        )

        # Met à jour la boîte d'affichage de la Pop-up
        self.update_draw_shape(self.entities)

    def get_shape_label_name(self):
        return f"_Arc_ (R={self.params.get('rayon_conge', self.val_default['rayon_conge'])/1000})"


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


class RoundTanShape(BaseShape):
    """ Cette class et pour dessiner
    UN ARC TANGEANT à un des segments (entré A-B ; sortie B-C)
    Paramètres pour dessiner:
        - déjà les trois points ABC
        - Le segment qui doit être tangeant
        - le rayon de l'arc
        - et une dimention pour définir le placement du point de tangeance
        Ps: éventuellement avec rayon négatif le rayon qui sort de la matière ?
        
    La calculation en grosses lignes:
        1- positionner le point de tangeance à la distance fournie sur le segment sélectionné
        2- calculer le point de centre du rayon: rayon * [Y, X] du vecteur.normalisé[X,Y] du segment de placment + point de tangeance
        3- trouver la distance tangeante du centre au segment à raccorder et mémoriser ce point sur le segment de raccordement
        4- par Pytagore, on connait: hypoténus = rayon; adjacent = dist du point 3 ==> opposé = (hypo^2 - adj^2)^0.5
        5- on ajoute la distance 4 (opp) vectorisé au point mémorié au point 3
        Ps le point mémosié au point 3 devrais je penses correspondre au rayon vectorisé du point "B" (en utilisant les vecteur du segment de raccordement ?)
    Si la dimention fournie correspond à la distance B <-> point de raccordement sur segment non tangeant ?
        1- une fois vectorisée, elle correspond à la hauteur d'arc
        ....
    Autre approche un peux plus visuel pour moi:
    Si je pivote tous pour que disons le segment non tangeant soit vertical,
    et le vecteur normalisé, appelons-le veBC représante un vecteur partant du point B en direction du point de tangeance:
        1- le point de centre sera sur le vecteur parallèle à veBC à une distance vertical de r/ veBC[y]?
        2- les distance de B:
            a- si dist sur veBC connu: dist horizontal = dist * veBC[x]
            b- si vertical connu, la dist restante jusqu'à la parappèle et de r/veBC[y] - dist = reste
                donc hor-centre = (r^2 - reste^2)^0.5? 
    """
    shape_type = ['angle', 'arc_tan']
    shape_text = ['Angle', 'Arc tangeant']
    val_default = { "rayon_conge": 4000,
            "seg_tangeant":"A-B",
            "long_B-tan": 1000}  # en microns

    def __init__(self, point_a, entry_b, point_c):
        super().__init__(point_a, entry_b, point_c)
        self.params = self.entry.raw["shape_params"]


        #self.compute_geometry() ==> BaseShape s'en charge déjà à la fin de son init !

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
        
        # 🚀 HARMONISATION TECHNIQUE : On force dict_formated_auto=True 
        # pour obtenir un dictionnaire standardisé de type court "a"
        conge = cd.create_fillet(point_before=A, point_intersect=B, point_after=C, radius=r, dict_formated_auto=True)
        
        # Extraction des points de transition exacts pour les liaisons du PointManager
        self.shape_start = conge.get("start", B)
        self.shape_end = conge.get("end", B)
        center_conge = conge.get("center", B)

        # 🚀 1. ALIMENTATION DU CACHE GÉOMÉTRIQUE BRUT POUR LA PIÈCE (SANS COULEURS)
        self.draw_part = [conge]
        
        # 💡 SOUVENIR DU DÉBUT DE NOTRE CONVERSATION : 
        # Si cette forme représente l'offset de coupe et que vous voulez y injecter 
        # votre nouveau type de forme pleine "rond" (le disque plein violet offset_fill) :
        #
        # self.self.draw_part.append({"type": "r", "center": center_conge, "radius": r})

        # =====================================================================
        # 🖥️ PARTIE DESSIN LOCAL (Vignette de la Pop-up IHM)
        # =====================================================================
        entities_vignette = []
        # Traits de construction théoriques (Gris)
        entities_vignette.append({"type": "l", "start": A, "end": B}) 
        entities_vignette.append({"type": "l", "start": B, "end": C}) 
        
        # L'arc du congé
        entities_vignette.append(conge)
        
        # Optionnel : Le contour du cercle complet d'outillage en filaire pour l'IHM
        entities_vignette.append({"type": "c", "center": center_conge, "radius": r})

        # Envoi au pistolet à peinture local de l'IHM (style "detail" vert)
        self.entities = cd.re_paint_entities(
            raw_list=cd.create_entities_from_raw(entities_vignette), 
            draw_type="detail", liaison_line=1
        )

        # Met à jour la boîte d'affichage de la Pop-up
        self.update_draw_shape(self.entities)

    def get_shape_label_name(self):
        return f"_Arc_ (R={self.params.get('rayon_conge', self.val_default['rayon_conge'])/1000})"


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
        
