# part/  draw_pnt_manager.py

import json
import os
from kivy.app import App
import math
import copy
from collections import namedtuple
from dataclasses import dataclass
#from kivy.properties import BooleanProperty, StringProperty, DictProperty
from utils import save_json_with_format
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from configurator.config import get_unit_config, get_unit_property, format_unit, get_unit_id, get_all_units_for_type, get_unit_type, AXIS_CONFIG, parse_user_input, USER_PREFERENCES, save_json, USER_LAST_SELECT
from ui_configurator.theme_manager import draw_line as th_drl   # th_drl => Thème draw line
import common_draw as cdraw
import part.shapes.shape_registry as sr
from part.shapes.shape_manager import ShapeManager

DATA_FILE_PART = os.path.join(os.path.dirname(__file__), 'draw_point.json')
'''
OBSOLETTE_DATA_FILE_TOOL = os.path.join(os.path.dirname(__file__), 'cutter_data.json')
'''

class JsonPointStorage:
    """Gère uniquement les noms des pièces et l'index sélectionné (designator)."""
    def __init__(self):
        self._ensure_file_exists()  # Si .json inexistant, initialisation de {self.path} avec 5 pièces vides ou un outil.
        self.draw_id_actif = 0   # Index du dessin actuellement actif.
        self.draw_json_loaded = 0     # Copie complète du block pièce/outil (données JSON) lors du dernier chargement.
        pass

    def debug_state(self):
        print("Part actif:", self.part_id_actif)
        print("Part enregistré:", self.saved_actif)
        print("Nom des pièces:", self.part_name)

class JsonPartStorage(JsonPointStorage):
    def __init__(self):
        self.path = DATA_FILE_PART
        super().__init__()
        self._ensure_file_exists()  # Si .json inexistant, initialisation de {self.path} avec 5 pièces vides.
        self.part_name = []      # Liste pour les noms des pièces
        self.part_id_actif = 0   # Index de la pièce actuellement sélectionnée.
        self.part_json_loaded = 0     # Copie complète de la pièce (données JSON) lors du dernier chargement.
        self.load_designator()

    def make_default_part(self, index=0):
        """Crée un dictionnaire représentant une pièce par défaut."""
        return {
            "name": f"{Tr('part')} {chr(65 + index)}",  # Pièce A, B, C...
            "points": [ {"pos": [0, 0], "shape": None, "shape_label":None, "shape_params": {}} ]
        }
    
    def _ensure_file_exists(self):
        """ Contrôle si le fichier .json existe"""
        if not os.path.exists(self.path):
            data = {
                "parts": [self.make_default_part(i) for i in range(5)],
                #"selected_part_index": 0
            }
            self.save_data(data)
            print(f"Initialisation de {self.path} avec 5 pièces vides.")
    
    def reset_part(self, part_id=None):
        """Réinitialise une pièce à son état par défaut (nom et points)."""
        part_id = self.part_id_actif if part_id is None else part_id
        data = self.load_data()
        if 0 <= part_id < len(data["parts"]):
            data["parts"][part_id] = self.make_default_part(part_id)
            self.save_data(data)
            self.load_designator()  # recharge les noms
        else:
            print(f"ID de pièce invalide pour reset : {part_id}")

    def load_data(self):
        '''
        ATTENTION: avec l'utilisation de cette fonction,
        -> self.part_json_loaded n'est pas mise à jour,
            -> donc si vous l'utilisez pour définir PointEntries, ne pas oublier de màj [.part_json_loaded]
        '''
        with open(self.path, 'r', encoding='utf-8') as f:
            fichier = json.load(f)
        return fichier

    def save_data(self, data):
        save_json_with_format(self.path, data, compact_keys=[("points", False)], indent=4)
        parts = data.get("parts", [])
        if 0 <= self.part_id_actif < len(parts):
            self.part_json_loaded = copy.deepcopy(parts[self.part_id_actif])
        else:
            self.part_json_loaded = None  # ou {} selon tes préférences

    def load_designator(self):
        ''' chargement des nom de pièces et les datas de la pièce active depuis le json'''
        data = self.load_data() # data n'a pas d'effet de bord qui sorte de la fonction

        #self.part_id_actif = data.get("selected_part_index", 0) # Pas d'effet de bord ici (juste un integer)
        self.part_id_actif = USER_LAST_SELECT.get("selected_part_idx", 0)

        json_name = [p.get("name", f"Part {i}") for i, p in enumerate(data.get("parts", []))]
        self.part_name = copy.deepcopy(json_name)   # Copie indépendante

        parts = data.get("parts", [])
        if 0 <= self.part_id_actif < len(parts):
            self.part_json_loaded = copy.deepcopy(parts[self.part_id_actif])   # Copie indépendante
        else:
            self.part_json_loaded = None  # ou {} selon tes préférences

    def save_designator(self):
        data = self.load_data()
        #data["selected_part_index"] = self.part_id_actif
        USER_LAST_SELECT["selected_part_idx"] = self.part_id_actif
        save_json() # Sauvegarde de user_settings.json
        for i, name in enumerate(self.part_name):
            if i < len(data["parts"]):
                data["parts"][i]["name"] = name
        self.save_data(data)

    def set_selected_index(self, index):
        if 0 <= index < len(self.part_name):
            self.part_id_actif = index
            self.save_designator()
        else:
            print(f"[Erreur] Index invalide : {index}")

    def get_selected_part(self, part_index=None):
        '''
        ATTENTION: avec l'utilisation de cette fonction, (préférer la fonction "load_selected_part()")
        -> self.part_json_loaded n'est pas mise à jour,
            -> donc si vous l'utilisez pour définir PointEntries, ne pas oublier de màj [.part_json_loaded]
        '''
        data = self.load_data()
        part_id = self.part_id_actif if part_index is None else part_index
        parts = data.get("parts", [])
        if 0 <= part_id < len(parts):
            return parts[part_id]
        else:
            print(f"Index de pièce invalide : {part_id}")
            return None

    def load_selected_part(self, part_id=None):
        '''
        ATTENTION: avec l'utilisation de cette fonction,
        -> self.part_json_loaded EST mise à jour, si part_index est None ou == self.storage.part_id_actif
        (Double usage: Charger une pièce en mode édition/utilisation; ou avec part_id différent: charger une pièce pour la copier dans la pièce active)
        '''
        part_id = self.part_id_actif if part_id is None else part_id
        data = self.get_selected_part(part_id)  # A ce stade data correspond à : {"name": "Pièce A","points": [{...},{...}]}
        if self.part_id_actif == part_id and data is not None:
            if isinstance(data, dict) and "points" in data:
                self.part_json_loaded = copy.deepcopy(data) # Copie de l'original
            else:
                self.part_json_loaded = None
                #print(f"DEBUG_load_selected_part: données invalides ou incomplètes: {data}")
        else:
            # TODO: Je penses que ce else est une ERREUR : à vérifier ! Si c'est vraiment pour le double emplois documenté ci-dessus
            self.part_json_loaded = None  # ou {} selon tes préférences
            #print("DEBUG_load_selected_part: Null ou id diff")
        return data # L'original franchement lue dans le json

    def set_selected_part(self, part_id=None, points=None):
        ''' Enregistre les points transmis dans la pièce[part_id] du json
         Ps: ?? sans autres màj (par ex dans self.part_json_loaded) ??'''
        # Si part_id est None, on utilise la pièce active
        part_id = self.storage.part_id_actif if part_id is None else part_id
        
        data = self.load_data() # L'original franchement lue dans le json: Toutes les pièces
        
        if 0 <= part_id < len(data.get("parts", [])):
            # Mettre à jour les points de la pièce spécifiée (uniquement les points, pas le reste !)
            data["parts"][part_id]["points"] = points
            self.save_data(data)
        else:
            print(f"ID de pièce invalide : {part_id}")


UnitSpec = namedtuple("UnitSpec", ["type", "unit_id"])    # Pour PointData et ColumnDefaultSpec
class ColumnDefaultSpec:
    '''valeur par défaut des colonnes pour les PointData (unités, ...)'''
    def __init__(self):
        self.unit_map = {
            "vert": UnitSpec("dist", None),
            "hor": UnitSpec("dist", None),
            "vert2": UnitSpec("dist", None),
            "hor2": UnitSpec("dist", None),
            "l": UnitSpec("dist", None),
            "alpha": UnitSpec("ang", None)
        }
        #self.load_units()

    def get_unit(self, key):
        """Retourne (type, unit_id) pour une clé donnée."""
        spec = self.unit_map.get(key)
        if spec is None:
            #print(f"DEBUG_ColumnDefSpec_get: key: {key}, absent de la liste unit_map[]")
            return None
        #print(f"DEBUG_ColumnDefSpec_get: key: {key}, type: {spec.unit_id}, unit: {get_unit_id(spec.type)}")
        if spec.unit_id is not None:
            return spec
        # fallback dynamique
        return UnitSpec(spec.type, get_unit_id(spec.type))
    
    def set_unit(self, key, unit_ident=None):
        """
            Changer l'identifiant d'une colonne (ex: colonne[key]: unit_id = unit_ident).
            Si l'identifiant est invalide ou absent, (None), la valeur par défaut du type est utilisée.
        """
        if key not in self.unit_map:
            raise KeyError(f"Clé d’unité inconnue : {key}")

        unit_id = get_unit_id(unit_ident)  # valide l'ident ou None pour préférence utilisateur

        self.unit_map[key] = UnitSpec(self.unit_map[key].type, unit_id)

class PointData:
    def __init__(self, column_spec, pos, prev_pos=None, shape=None, shape_params=None, shape_lbl="- - -"):
        """
        pos         : [hor, vert] en unité de base
        prev_pos    : [hor, vert] du point précédent (pour calculs vert2, hor2, l, alpha)
        column_spec : instance de ColumnDefaultSpec
        """
        self.shape_values = {}  # Dict[str, PointValue] → pour les paramètres liés à la forme

        self.column_spec = column_spec  # ColumnDefaultSpec() unités par défaut pour les colonnes du formulaire
        self.shape = shape or "- - -"
        self.shape_params = shape_params or {}
        self.shape_label = shape_lbl


        # Créer les objets PointValue une fois
        self.hor = PointValue(0, axis_key="hor", unit_id=self.column_spec.get_unit("hor").unit_id)
        self.hor2 = PointValue(0, axis_key="hor2", unit_id=self.column_spec.get_unit("hor2").unit_id)
        self.vert = PointValue(0, axis_key="vert", unit_id=self.column_spec.get_unit("vert").unit_id)
        self.vert2 = PointValue(0, axis_key="vert2", unit_id=self.column_spec.get_unit("vert2").unit_id)
        self.l = PointValue(0, axis_key="l", unit_id=self.column_spec.get_unit("l").unit_id)
        self.alpha = PointValue(0, axis_key="alpha", unit_id=self.column_spec.get_unit("alpha").unit_id)
        self.unit_fixed_flags = { #("key", uint_forced) : -uint_forced si False utiliser l'unité par défaut; si True bloquer l'utilisation de PointValue.unit_id
            'hor': False,
            'hor2': False,
            'vert': False,
            'vert2': False,
            'l': False,
            'alpha': False
        }

        self.recompute(pos=pos, prev_pos=prev_pos)

    def recompute(self, pos=None, prev_pos=None):
        if pos:
            hor_base, vert_base = pos
        else:
            hor_base = self.hor.val_base()
            vert_base = self.vert.val_base()

        if prev_pos:
            prev_hor, prev_vert = prev_pos
        else:
            prev_hor = None
            prev_vert = None

        # MàJ des valeurs converties depuis base
        self.hor.value = self.base_to_work('hor', hor_base)
        self.vert.value = self.base_to_work('vert', vert_base)

        dx = hor_base - prev_hor if prev_hor is not None else 0
        dy = vert_base - prev_vert if prev_vert is not None else 0
        length = (dx ** 2 + dy ** 2) ** 0.5
        if dx < 0:
            length = -length
            
        angle_rad = math.atan2(dy, dx) if prev_pos else 0

        self.hor2.value = self.base_to_work('hor2', dx)
        self.vert2.value = self.base_to_work('vert', dy)
        self.l.value = self.base_to_work('l', length)
        self.alpha.set_converted_from(angle_rad, source_unit_id="rad")
        
        #print(f"DEBUG_PointData_recompute: hor:{self.hor.value} vert:{self.vert.value}")

    def base_to_work(self, key: str, base_val: float) -> float:
        """Conversion d’une valeur base vers l’unité de travail du PointValue correspondant à `key`."""
        point = getattr(self, key, None)
        if isinstance(point, PointValue):
            unit_id = point.get_id_unit()
        else:
            # fallback : unité par défaut de la colonne
            spec = self.column_spec.get_unit(key)
            if not spec:
                # Par défaut µm (i.e. 1:1)
                return float(base_val)
            unit_id = spec.unit_id

        factor = get_unit_config(unit_id).get("factor", 1.0)
        return base_val / factor

    def refresh_units(self):
        for key in self.unit_fixed_flags:
            if not self.unit_fixed_flags[key]:
                pv = getattr(self, key)
                pv.unit_id = self.column_spec.get_unit(key).unit_id
        #self.recompute()

    def set_unit_for_key(self, key: str, new_unit_id: str):
        """Modifie l'unité d'une cellule (ex: 'x', 'z', 'alpha').

        Si new_unit_id est None, la valeur par défaut (selon le type) est rétablie.
        """
        unit_id = get_unit_id(new_unit_id)  # valide l'ident ou None pour préférence utilisateur
        if key in self.unit_fixed_flags:
            pv = getattr(self, key)
            self.unit_fixed_flags[key] = unit_id is not None
            pv.unit_id = unit_id or self.column_spec.get_unit(key).unit_id
        #self.recompute()       

    def update_shape(self, shape=None, shape_params=None):
        self.shape = shape or "- - -"
        self.shape_params = shape_params or {}

    def add_shape_value(self, key: str, value: float, unit_id= None, user_unit_group="unit_distance"):
        id_unit = unit_id if unit_id is not None else get_unit_id(get_unit_type(user_unit_group)) 
        self.shape_values[key] = PointValue(value=value, unit_id=id_unit)

    def get_shape_pointvalue(self, key: str) -> 'PointValue':
        return self.shape_values.get(key)
    
    def get_shape_value_formatted(self, key: str, with_unit=True):
        pv = self.shape_values.get(key)
        if pv:
            return pv.val_formatted(with_unit=with_unit)
        return "-"

    def get_shape_value_base(self, key: str):
        pv = self.shape_values.get(key)
        if pv:
            return pv.val_base()
        return None

    def set_shape_value_base(self, key: str, val_base: int):
        if isinstance(self.shape_values) and val_base:
            self.shape_values[key].value = self.base_to_work(key,val_base)

    def clear_shape_values(self):
        self.shape_values.clear()

    def __repr__(self):
        return f"<PointDataNew x={self.x.val_formatted()} z={self.z.val_formatted()} ...>"

@dataclass
class PointValue:
    def __init__(self, value: float = 0.0, unit_id: str = None, axis_key: str = None):
        self.value = value                    # valeur interne (en unité "effective")
        self.unit_id = unit_id                # unité locale (prioritaire si définie)
        self.axis_key = axis_key              # ex: 'x', 'z', 'alpha'...

    def get_id_unit(self) -> str:
        """
        Retourne l'identifiant de l'unité utilisée pour ce PointValue.

        L'unité est définie en amont par la classe parente PointData, en fonction :
        - de la clé de l'axe (axis_key)
        - et des spécifications de colonne (ColumnDefaultSpec)

        Ce getter ne fait que retourner `self.unit_id`, qui est supposée être déjà initialisée
        correctement. Aucune logique de fallback n'est effectuée ici.
        """
        return self.unit_id or None

    def get_unit_type(self) -> str:
        """
        Retourne le type logique de l'unité utilisée (ex: 'distance', 'angle', 'speed').

        Utilise la priorité suivante :
        - unité locale (self.unit_id)
        - unité de la colonne (self.unit_used.unit_id)
        - fallback 'mm' → 'distance'
        """
        unit_id = self.get_id_unit()
        type_unit = get_unit_property(unit_id, "type") or None
        return type_unit

    def val_base(self, axis_factor=False) -> int:
        """
        Retourne la valeur convertie en unité de base (int), en tenant compte du facteur écran.
        Accepte que `self.value` soit :
            - un float/int déjà "propre" → conversion directe
            - une chaîne (ex: "12.0mm") → nettoyage via parse_user_input
        """
        unit_id = self.get_id_unit()
        val = self.value

        if isinstance(val, str):
            parsed = parse_user_input(val, unit_id)
            if isinstance(parsed, str):
                raise ValueError(f"Erreur de saisie : {parsed}")
            val_float, parsed_unit_id, _ = parsed
            factor = get_unit_config(parsed_unit_id).get("factor", 1.0)
            val = val_float * factor
        elif isinstance(val, (int, float)):
            factor = get_unit_config(unit_id).get("factor", 1.0)
            val = float(val) * factor
        else:
            raise TypeError(f"Type non supporté pour self.value: {type(val)}")

        if axis_factor and self.axis_key and self.axis_key in AXIS_CONFIG:
            screen_factor = AXIS_CONFIG[self.axis_key].get("factor", 1.0)
            val /= screen_factor

        return int(round(val))

    def val_formatted(self, with_unit: bool = False, decimals: int = None) -> str:
        """Retourne une chaîne formatée pour affichage.
            (format retourné: val_disp -> avec facteur_screen et éventuellement labèle
        """
        unit_id = self.get_id_unit()
        cfg = get_unit_config(unit_id)
        nb_decimals = decimals if decimals is not None else cfg.get("decimals", 2)
        label = cfg.get("label", unit_id)

        screen_factor = 1.0
        if self.axis_key and self.axis_key in AXIS_CONFIG:
            screen_factor = AXIS_CONFIG[self.axis_key].get("factor", 1.0)

        display_val = self.value * screen_factor
        formatted = f"{display_val:.{nb_decimals}f}"
        return f"{formatted} {label}" if with_unit else formatted

    def convert_to(self, target_unit_id: str) -> float:
        """Renvoie la valeur convertie vers une autre unité sans la modifier.
            (format retourné: val_work -> sans facteur_screen
        """
        source_unit = self.get_id_unit()
        f1 = get_unit_config(source_unit).get("factor", 1.0)
        f2 = get_unit_config(target_unit_id).get("factor", 1.0)
        
        return self.value * f1 / f2

    def set_converted_from(self, source_value: float, source_unit_id: str):
        """
        Met à jour `self.value` à partir d’une valeur donnée dans une autre unité.
            (format de source_value: val_work -> sans facteur_screen)
        """
        target_unit_id = self.get_id_unit()
        f_source = get_unit_config(source_unit_id).get("factor", 1.0)
        f_target = get_unit_config(target_unit_id).get("factor", 1.0)
        self.value = source_value / f_target * f_source
        
    def set_from_input(self, input_str: str):
        """
        Met à jour le PointValue.value à partir d'une chaîne utilisateur, avec ou sans unité.
        (convertion: val_disp >> val_work)
            Exemples valides :
            - "12.5"        → interprété en self.unit_id
            - "12.5mm"      → détecte l'unité "mm"
            - "12.5 mm"     → idem
            - "12.5 in"     → convertit correctement en unité de base

        Retourne :
        - True  → si la valeur a été modifiée
        - False → si la valeur est restée identique
        - 'invalid_unit'   → si l'unité est inconnue ou incomplette
        - 'invalid_format' → si le texte est intraitable
        """
        # Nettoyage de la valeur contrôle et extraction de l'unité écrite
        parsed = parse_user_input(input_str, self.get_id_unit())

        if isinstance(parsed, str):  # Erreur
            #print(f"DEBUD_set_from_input: texte Non valide:{parsed}")
            return parsed

        val_float, unit_detected, _ = parsed

        # Conversion en val_work (float en unité machine)
        factor_input = get_unit_config(unit_detected).get("factor", 1.0)
        factor_target = get_unit_config(self.get_id_unit()).get("factor", 1.0)
        new_value = val_float * factor_input / factor_target

        # Dé-normalisation si facteur visuel (diamètre = rayon × 2)
        if self.axis_key and self.axis_key in AXIS_CONFIG:
            screen_factor = AXIS_CONFIG[self.axis_key].get("factor", 1.0)
            new_value /= screen_factor

        if abs(self.value - new_value) > 1e-8:
            self.value = new_value
            return True
        else:
            return False


class PointEntry:
    def __init__(self, raw: dict, id_pnt: int, data: PointData = None, extra: dict = None):
        self.raw = raw              # ==> Clône modifiable du .json
        self.data = data            # ==> Mise au format et valeurs dérivée pour l'affichage d'édition
        self.extra = extra or {}    # ==> Actuellement libre
        self.id_pnt = id_pnt        # Identifiant unique pour chaque point "de référance"
        self.shape_entry_start = raw["pos"]  # Point de départ de la forme
        self.shape_entry_end   = raw["pos"]  # Point de sortie du shape
        self.modified_data = True  # on marque dirty
        self.modified_extra = True  # on marque dirty

        # 🚀 AJOUT DE LA COUCHE GÉOMÉTRIQUE CAO
        self.raw_shape_segments = []  # Liste des dict bruts {"type": "m"/"r"/"a"..."id_pnt": self.id_pnt} généré par le shape
        self.bbox_um_editing = [copy.deepcopy(raw["pos"]),copy.deepcopy(raw["pos"])]    # bbox du shape
        self.modified_shape = True    # Flag dirty spécifique pour la géométrie !

    def shape_raw_generat(self, last_pnt_pos, next_pnt_pos, shape_manager):
        """
        🎯 L'USINE GÉOMÉTRIQUE INDIVIDUELLE (Version Pure JSON-Raw) :
        Placée dans PointEntry. Lit exclusivement le clone du JSON en microns,
        appelle le ShapeManager pour instancier la forme, aspire ses segments 
        CAO bruts et verrouille les coordonnées exactes d'entrée/sortie.
        """

        #print(f"DEBUG PointEntry_shape_raw-generat: raw_shape_segments AVANT: {self.raw_shape_segments}")


        # 1️⃣ Réinitialisation complète du cache géométrique de ce point
        self.raw_shape_segments = []
        
        # Par sécurité, si le point n'a pas de forme, l'entrée et la sortie
        # de la liaison sont confondues avec la coordonnée physique du point
        pos_x, pos_y = self.raw["pos"][0], self.raw["pos"][1]
        self.shape_entry_start = [pos_x, pos_y]
        self.shape_entry_end = [pos_x, pos_y]
        self.shape_bbox_um = [[pos_x, pos_y],[pos_x, pos_y]]

        # 2️⃣ Barrières de sécurité étanches basées uniquement sur le clone JSON
        shape_def = self.raw.get("shape")
        if not shape_def or not isinstance(shape_def, (list, tuple)):
            self.modified_shape = False
            return  # Point de liaison pur (sans forme), on s'arrête ici proprement.
        # Sécurité : on s'assure que shape_params est bien un dictionnaire dans le raw
        if not isinstance(self.raw.get("shape_params"), dict):
            self.raw["shape_params"] = {}           
        params = self.raw["shape_params"]

        # =====================================================================
        # 🚀 APPEL AU ROUTEUR GÉOMÉTRIQUE (L'USINE DE FORMES)
        # =====================================================================
        # On demande au ShapeManager d'instancier l'objet lourd (ex: ThreadReliefISOShape)
        # en lui passant les coordonnées absolues des points voisins (A et C)
        shape_obj = shape_manager.create_shape(
            pos_a=last_pnt_pos, 
            entry_b=self,         # On passe l'instance de PointEntry elle-même !
            pos_c=next_pnt_pos, 
            shape_typ=shape_def, 
            shape_params=params
        )

        # =====================================================================
        # 🎯 CAPTURE ET ENCAPSULATION DE LA GÉOMÉTRIE (CONTRAT BASESHAPE)
        # =====================================================================
        # Si la forme a calculé sa géométrie avec succès (votre status 95 réglementaire)
        if hasattr(shape_obj, "satus") and shape_obj.satus == 95:
            
            # 🚀 Extraction du cache standardisé (qui renvoie le tableau self.draw_part de la forme)
            #self.raw_shape_segments = shape_obj.draw_part
            self.raw_shape_segments = shape_obj.get_shape_seg_brut()
                
            # On estampille immédiatement chaque micro-segment interne de la forme
            # avec l'ID unique de ce PointEntry pour le futur ciblage d'IHM ou d'erreurs
            for seg in self.raw_shape_segments:
                seg["id_pnt"] = self.id_pnt

            # 🚀 Extraction dynamique ultra-fiable du début et de la fin de la forme
            # (Basé sur vos lignes : self.draw_part[0]["start"] et self.draw_part[-1]["end"])
            self.shape_entry_start, self.shape_entry_end = shape_obj.get_start_end(recompute=False)
            self.shape_bbox_um = shape_obj.get_bbox_shape()

        dynamic_label = None
        if hasattr(shape_obj, "get_shape_label_name"):
            dynamic_label = shape_obj.get_shape_label_name()            
        # A. On met à jour le clone JSON (pour la future sauvegarde)
        self.raw["shape_label"] = dynamic_label       
        # B. Si l'IHM est active et que self.data existe déjà (mode édition en direct),
        # on lui injecte le nouveau texte pour que l'écran se mette à jour instantanément !
        if self.data:
            self.data.shape = dynamic_label if dynamic_label else "- - -"            
        # On baisse le drapeau, le cache de ce point est à jour en microns
        self.modified_shape = False

        #print(f"DEBUG PointEntry_shape_raw-generat: raw_shape_segments APRÈS: {self.raw_shape_segments}")

    #TODO: old à contrôler !
    def update_shape_startend(self, startpos, endpos):
        self.shape_entry_start = startpos
        self.shape_entry_end = endpos

    def as_display_row(self, with_unit: bool = False) -> list[str]:
        '''Retourne une ligne formatée pour l'affichage, avec ou sans unités.'''
        return [
            self.data.vert.val_formatted(with_unit=with_unit),
            self.data.hor.val_formatted(with_unit=with_unit),
            self.data.vert2.val_formatted(with_unit=with_unit),
            self.data.hor2.val_formatted(with_unit=with_unit),
            self.data.l.val_formatted(with_unit=with_unit),
            self.data.alpha.val_formatted(with_unit=with_unit),
        ]

class PointManager:
    ''' ci-dessous doit dans la class PointDraw_editor() ou alors ajouter (...) à cette class pour le bind !
        >> Pour (...) voir CutterManager(EventDispatcher)
    '''
    #error_drawing = BooleanProperty(True)
    #not_saved_drawing = BooleanProperty(False)

    def __init__(self):
        self.entries: list[PointEntry] = []
        # 🚀 ON INSTANCIE LE ROUTEUR DE PLUGINS ET DE SHAPES ICI :
        self.shape_manager = ShapeManager()

        self.saved_profile_brut = [] # Segments brutes du profil sauvegardé (ligne + shape), sans miroirs
        self.saved_profile_seg_net = []   # [json] Segments sauvegardés composant le profil (segments_Canvas), sans miroirs
        self.curent_profile_seg_net = []  # [CAO] Segments en cours d'édition composant le profil (segments_Canvas), sans miroirs
        self.barriere_segments = 0   # nombres de segments barrières qui sont inclus à chaque extrémités du profil
        self.barriere_color = "#FFFFFF40"
        self.mcu_synchronise = False  # True si les segments dans le MCU sont identiques à ceux de "self.profil_segments" : False par défaut à l'allumage
        self.unit_spec = ColumnDefaultSpec()  # Unité par défaut à utiliser dans les colonnes du formulaire
        self.data_loaded = False  # Indicateur pour savoir si PointData doit être chargé
        self.data_mirror = False  # Indicateur pour savoir si PointData doit être en mode mirror
        self.storage = JsonPartStorage()
        self.current_name = None  # Nom temporaire pour la pièce active

        #self.bind(error_drawing= self.up_satus_page_cao)
        #self.bind(not_saved_drawing= self.up_satus_page_cao)
        self.load()

    def load(self, part_index=None, load_data=None):

        part_id = self.storage.part_id_actif if part_index is None else part_index            
        part = self.storage.load_selected_part(part_id)

        self.next_id_point = 0  
        def new_id_pnt():
            self.next_id_point += 1
            return self.next_id_point - 1

        if isinstance(load_data, bool): 
            self.data_loaded = load_data    

        if not part:
            self.entries = []
            return

        # 1️⃣ Instanciation à blanc de toutes vos PointEntry depuis le JSON
        self.entries = []
        for raw in part.get("points", []):
            id_pnt = new_id_pnt()   # retourne le new indent et incrémente la variable pour le prochain
            entry = PointEntry(raw=raw, id_pnt=id_pnt)
            self.entries.append(entry)  

        # 🎯 2️⃣ USINE DE FAO INITIALE (Grand Orchestre Géométrique des segments)   
        len_pnts = len(self.entries)
        if len_pnts > 1:    # On vérifie qu'on a au moins 2 points pour tracer une ligne, sinon pas de pièce.
            
            for idx in range(len_pnts):
                current_entry = self.entries[idx]

                # CAS A : Extrémités de la pièce (Premier ou Dernier Point)
                # Ils n'ont pas de voisins complets -> pas de forme physique possible.
                if idx == 0 or idx == len_pnts - 1:
                    current_entry.raw_shape_segments = []
                    current_entry.shape_entry_start = current_entry.raw["pos"]
                    current_entry.shape_entry_end = current_entry.raw["pos"]
                    current_entry.shape_bbox_um = [current_entry.raw["pos"],current_entry.raw["pos"]]
                    # TODO: Ci-dessous contrôler l'utilitée, certainnement obsolette
                    current_entry.modified_shape = False # On valide le cache à vide
                    continue

                # CAS B : Points intermédiaires (Calcul Trigonometrique)
                # 🚀 Gestion du temps de retard/d'avance pour capturer les voisins exacts
                pos_a = self.entries[idx - 1].raw["pos"] # Point précédent (Amont)
                pos_c = self.entries[idx + 1].raw["pos"] # Point suivant (Aval)
                # Le point calcule sa forme via les classes (Chanfrein, Gorge, ...)
                current_entry.shape_raw_generat(
                    last_pnt_pos=pos_a, 
                    next_pnt_pos=pos_c, 
                    shape_manager=self.shape_manager # Passe le ShapeManager de PointManager
                )
        else:   # Si moins de 2 points on laisse simplement les listes de segments vides (par défaut)
            pass

        # 🚀 3. FIGER LA SOURCE DE VÉRITÉ SAUVEGARDÉE ( origin_seg_brut )
        self.saved_profile_brut = self.build_flat_segments_list()    # On assemble la chaîne plate complète en microns (liaisons + formes) 

        # 4a L'usine génère une structure graphique neuve avec les Bbox
        entities_loaded = cdraw.create_entities_from_raw(raw_list=self.saved_profile_brut)  
        # 4b Le profil CAO actif prend toute la liste avec ses barrières
        self.curent_profile_seg_net = cdraw.re_paint_entities(
            raw_list=entities_loaded, draw_type="profil_cao",
            liaison_line=self.barriere_segments, liaison_color=self.barriere_color
        )
        # 4c Si on a des barrières, on ampute directement la liste entities_loaded
        # TODO: A voir avec la nouvelle idée de barrières:
            # Idée: Placer la barrière comme un point spécial ... qui n'est pas forcément au début et à la fin mais plaçable ???
        # TODO: A voir si on ne mets pas quand-même le barrières dans la sauvegarde ???
        if self.barriere_segments > 0 and len(entities_loaded) > (2 * self.barriere_segments):
            entities_saved_pure = entities_loaded[self.barriere_segments : -self.barriere_segments]
        else:
            entities_saved_pure = entities_loaded
        # 4d On peint la pièce d'origine pure en rose nominal
        self.saved_profile_seg_net = cdraw.re_paint_entities(
            raw_list=entities_saved_pure, draw_type="profil_save",
            liaison_line= None
        )
        
        self.current_name = self.storage.part_name[part_id]
        
        # (L'IHM s'éveillera ici tout à la fin si demandé)
        if self.data_loaded: 
            self.update_entries_data()

    def build_flat_segments_list(self) -> list:
        """
        🎯 LE GRAND CHAÎNAGE CONTINU :
        Parcourt toutes les PointEntry et assemble les segments de formes complexes
        avec les grandes lignes de liaison "l" basées sur les coordonnées JSON originelles.
        """
        liste_plate = []
        len_pnts = len(self.entries)
        last_pos = []
        
        for idx in range(len_pnts):
            current_entry = self.entries[idx]
                
            # 1: Injection automatique de la ligne de liaison dépendante
            if idx > 0:                
                # SÉCURITÉ INDUSTRIELLE : On donne les positions JSON originelles.
                # Votre compute_raw s'occupera d'ajuster dynamiquement les extrémités !
                liaison = {
                    "type": "l",
                    "start": last_pos,
                    "end": current_entry.raw["pos"],
                    "id_pnt": current_entry.id_pnt
                }
                liste_plate.append(liaison)
            last_pos = current_entry.raw["pos"]
            
            # 2 Aspiration du cache géométrique de la forme (draw_part)
            if hasattr(current_entry, "raw_shape_segments") and current_entry.raw_shape_segments:
                liste_plate.extend(current_entry.raw_shape_segments)
                
        return liste_plate

    def refresh_drawing(self, idx_entry=None, idx_pos_raw=None):
        """
        🎯 LE CHEF D'ORCHESTRE GÉOMÉTRIQUE CENTRAL (FAO + DESSIN) :
        1. Synchronise le .raw d'un point si ses coordonnées absolues ont changé.
        2. Recalcule localement la trigonométrie de la cellule des 3 points (N-1, N, N+1).
        3. Ré-assemble la chaîne plate globale en microns de toute la pièce.
        4. Repérit l'écran vert d'édition (curent_profile_seg_net) via le pistolet à peinture.
        """
        len_pnts = len(self.entries)
        if len_pnts <= 1:
            return

        # ÉTAPE 1 : ÉCRITURE DANS LE MODÈLE REEL (.raw)
        # Si un index et une nouvelle position absolue en microns sont fournis, on écrit dans la brique
        if idx_entry is not None:
            if idx_pos_raw is not None:
                if 0 <= idx_entry < len_pnts:
                    self.entries[idx_entry].raw["pos"] = [int(round(idx_pos_raw[0])), int(round(idx_pos_raw[1]))]
                    self.entries[idx_entry].modified_data = True

           # 🚀 ÉTAPE 2 : LE CADENCEUR FAO LOCAL
            index_min = max(1, idx_entry - 1)
            index_max = min(len_pnts - 2, idx_entry + 1)
            
            # 🎯 CORRECTION : Parenthèses et "+ 1" pour inclure index_max dans la boucle !
            for idx in range(index_min, index_max + 1):
                pos_a = self.entries[idx - 1].raw["pos"]
                pos_c = self.entries[idx + 1].raw["pos"]
                
                # Le point ré-exécute sa géométrie (Chanfrein, Congé, Gorge ISO) en direct

                #print("DEBUG PointManager: refresh_drawing: appel: shape_raw_generat()")

                
                self.entries[idx].shape_raw_generat(
                    last_pnt_pos=pos_a,
                    next_pnt_pos=pos_c,
                    shape_manager=self.shape_manager
                )

        # 🚀 ÉTAPE 3 : LE GRAND CHAÎNAGE GLOBAL (Ré-assemblage microns)
        # On vide les tiroirs de tous les points pour recréer la liste plate à jour
        raw_active_profile = self.build_flat_segments_list()
        #print("== raw_active_profile =====================")
        #print(raw_active_profile)
        #print("===========================================")
        # Passage dans l'usine pour injecter les Bounding Boxes (Bbox)
        entities_active = cdraw.create_entities_from_raw(raw_list=raw_active_profile)
        #  LE PISTOLET À PEINTURE CENTRAL (Rendu Kivy)
        self.curent_profile_seg_net = cdraw.re_paint_entities(
            raw_list=entities_active, 
            draw_type="profil_cao",
            liaison_line=self.barriere_segments, 
            liaison_color=self.barriere_color
        )
        
       # print("== curent_profile_seg_net =====================")
       # print(self.curent_profile_seg_net)
       # print("===========================================")

    def add_entry(self, index: int, hor: float, vert: float, shape=None, shape_label=None, shape_params=None) -> PointEntry:
        """Ajoute un nouveau PointEntry à la suite de l'index donné (index + 1)."""
        new_raw = {
            "pos": [int(round(hor)), int(round(vert))],
            "shape": shape,
            "shape_label": shape_label,
            "shape_params": shape_params or {}
        }
        id_pnt = self.next_id_point
        self.next_id_point += 1  # Actualisation de l'id pour le prochain point
        new_entry = PointEntry(raw=new_raw, id_pnt=id_pnt)

        # Insertion physique dans la liste de mémoire vive
        self.entries.insert(index + 1, new_entry)
        
        # 🚀 ALIGNEMENT 3 COUCHES :
        # Comme l'insertion d'un point décale toute la structure de la pièce, 
        # on relance update_entries_data. Elle va recalculer le voisinage, 
        # générer la forme du nouveau point et re-dessiner l'écran vert d'édition.
        if self.data_loaded: 
            self.update_entries_data()

        return new_entry

    def delete_entry(self, index: int) -> bool:
        """
        🚀 LA SUPPRESSION SÉCURISÉE :
        Supprime le PointEntry à l'index donné, recalcule les raccordements 
        des points devenus voisins et rafraîchit l'IHM.
        """
        if not (0 <= index < len(self.entries)):
            print(f"[Erreur] Index {index} hors limites pour la suppression.")
            return False

        # Sécurité d'atelier : on évite de vider complètement la pièce
        if len(self.entries) <= 2:
            print("[Sécurité] Impossible de supprimer : la pièce doit comporter au moins 2 points.")
            return False

        # 1️⃣ Suppression physique du point en mémoire vive
        removed_entry = self.entries.pop(index)
        print(f"[Suppression] Point ID {removed_entry.id_pnt} retiré de l'index {index}.")

        # 2️⃣ ALIGNEMENT 3 COUCHES :
        # Le point ayant disparu, les points qui l'entouraient se touchent désormais.
        # Leurs angles et leurs tangentes ont changé. On relance la mise à jour globale
        # pour recalculer leurs formes et mettre à jour les grilles de saisie textuelles.
        if self.data_loaded:
            self.update_entries_data()
            
        return True
    
    def update_entries_data(self):
        if not self.entries:
            print("Pas d'entries à mettre à jour")
            return

        prev_pos = None
        for i, entry in enumerate(self.entries):
            try:
                orig_pos = entry.raw.get("pos")
                if not orig_pos:
                    entry.data = None
                    continue

                raw_hor, raw_vert = orig_pos

                pos = [raw_hor, raw_vert]

                # Si data existe déjà, on met à jour
                if entry.data:
                    entry.data.refresh_units()
                    # 🚀 CORRIGÉ : On sépare bien le type technique (shape) du texte (shape_label)
                    entry.data.shape = entry.raw.get("shape") or "- - -"
                    entry.data.shape_label = entry.raw.get("shape_label") or "- - -"
                    entry.data.recompute(pos=pos, prev_pos=prev_pos)
                else:
                    # Sinon on le crée depuis zéro avec toutes ses clés
                    entry.data = PointData(
                        column_spec=self.unit_spec, 
                        pos=pos, 
                        prev_pos=prev_pos,
                        shape=entry.raw.get("shape"),
                        shape_params=entry.raw.get("shape_params"),
                        shape_lbl=entry.raw.get("shape_label") # 🚀 AJOUTÉ ICI
                    )

                prev_pos = pos  # Pour le suivant
                entry.modified_data = False

            except Exception as e:
                print(f"Erreur pour l'entry {i} : {e}")
                entry.data = None

        # 🚀 RECONSTRUCTION DE TOUT LE PROFIL GÉNÉRAL
        # L'ancienne boucle prof_seg_pnt_recompute est supprimée !
        # On demande au manager de repeindre proprement le calque actif (la pièce verte)
        #self.refresh_display_profiles()
        self.refresh_drawing(None, None)

    def update_entry_data(self, index):
        """Met à jour un point et le suivant (car dépendances avec prev_pos)."""
        if not (0 <= index < len(self.entries)):
            print(f"Index {index} hors limites pour update_entry_data")
            return

        len_pnts = len(self.entries)

        try:
            prev_pos = orig_prev_pos = self.entries[index - 1].raw.get("pos") if index > 0 else None
            entry = self.entries[index]
            pos = orig_pos = entry.raw.get("pos")

            # Appliquer le mode mirror Z pour les calculs de formulaires
            if orig_pos:
                raw_hor, raw_vert = orig_pos
                pos = [raw_hor, raw_vert]
            if orig_prev_pos:
                raw_hor, raw_vert = orig_prev_pos
                prev_pos = [raw_hor, raw_vert]

            if entry.data:
                entry.data.shape = entry.raw.get("shape") or "- - -"
                entry.data.shape_label = entry.raw.get("shape_label") or "- - -"
                entry.data.recompute(pos=pos, prev_pos=prev_pos)
            else:
                entry.data = PointData(
                    column_spec=self.unit_spec, 
                    pos=pos, 
                    prev_pos=prev_pos,
                    shape=entry.raw.get("shape"),
                    shape_params=entry.raw.get("shape_params"),
                    shape_lbl=entry.raw.get("shape_label")
                )
            entry.modified_data = False

            # =====================================================================
            # 🚀 LE CADENCEUR FAO EN DIRECT (MOUVEMENT SOURIS)
            # =====================================================================
            # Si le Point N a bougé, ses coordonnées modifiées changent l'assise trigonométrique 
            # de sa propre forme, mais AUSSI celle du point d'avant (N-1) et du point d'après (N+1) !
            # On force le recalcul géométrique de cette cellule de 3 points :
            for idx in [index - 1, index, index + 1]:
                if 0 <= idx < len_pnts:
                    # On intercepte les extrémités (0 et fin) pour ne pas calculer hors tableau
                    if idx == 0 or idx == len_pnts - 1:
                        continue
                        
                    # Extraction des positions réelles des voisins actuels
                    pos_a = self.entries[idx - 1].raw["pos"]
                    pos_c = self.entries[idx + 1].raw["pos"]
                    
                    # Le point ré-exécute ses calculs de Chanfrein ou de Gorge ISO en direct

                    print("DEBUG PointManager_update_entry_data: appel: shape_raw_generat()")

                    self.entries[idx].shape_raw_generat(
                        last_pnt_pos=pos_a,
                        next_pnt_pos=pos_c,
                        shape_manager=self.shape_manager
                    )

            # 🚀 ÉTAPE FINALE : Re-dessiner l'écran
            # Toutes les formes impactées ont mis à jour leur cache raw_shape_segments.
            # On demande au manager de ré-assembler la liste plate et de rafraîchir l'IHM !
            self.refresh_display_profiles()

        except Exception as e:
            print(f"Erreur update_entry_data pour l'entry {index} : {e}")
            entry.data = None

    def update_raw_from_data_UTILE(self):   # je penses inutilisable
        """Synchronise self.raw depuis self.data avec conversion des unités."""
        if not self.data:
            print("[Warning] Impossible de mettre à jour raw : data est vide.")
            return

        self.raw["pos"] = [
            self.data.hor.val_base(),
            self.data.vert.val_base()
        ]
        self.raw["shape"] = self.data.shape
        self.raw["shape_params"] = self.data.shape_params.copy()

        self.modified_data = False

    def save(self, part_index=None, commit_name=True):
        """🚀 ENREGISTREMENT ET FIGEAGE DU CALQUE ROSE"""
        import copy
        part_id = self.storage.part_id_actif if part_index is None else part_index

        if commit_name:
            self.commit_part_names()

        if self.entries:
            # 1. Extraction et sauvegarde des clones JSON modifiés
            points = [entry.raw for entry in self.entries if entry.raw]
            self.storage.set_selected_part(part_id, points)
            
            # 🚀 2. SYNCHRONISATION DU FOND GRAPHIQUE ROSE
            # Puisque la pièce est officiellement sauvegardée, le calque actif (en microns)
            # devient la nouvelle référence fixe de fond. 
            self.saved_profile_brut = self.build_flat_segments_list()
            
            # On génère la structure graphique d'IHM associée
            import common_draw as cdraw
            entities_loaded = cdraw.create_entities_from_raw(raw_list=self.saved_profile_brut)
            
            # Application du slicing chirurgical pour masquer les barrières sur le calque de fond rose
            if self.barriere_segments > 0 and len(entities_loaded) > (2 * self.barriere_segments):
                entities_saved_pure = entities_loaded[self.barriere_segments : -self.barriere_segments]
            else:
                entities_saved_pure = entities_loaded

            # On repeint notre témoin d'arrière-plan en rose nominal
            self.saved_profile_seg_net = cdraw.re_paint_entities(
                raw_list=entities_saved_pure, 
                draw_type="profil_save",
                liaison_line=0
            )
            print(f"[Succès] Pièce {part_id} enregistrée. Calque rose synchronisé.")
        else:
            print("[Erreur] La liste 'entries' est vide ou non initialisée.") 

    def reset_part_in_memory(self):
        """🚀 RÉINITIALISATION COMPLÈTE ET FAO INITIALE"""
        import copy
        import common_draw as cdraw

        # Génération des données de la pièce par défaut
        data = self.storage.make_default_part(self.storage.part_id_actif)
        self.set_part_names(data.get("name", "inconnue"))

        # Re-construction des PointEntry
        self.entries = [
            PointEntry(raw=raw, id_pnt=i)
            for i, raw in enumerate(data.get("points", []))
        ]
        self.next_id_point = len(self.entries)
        
        # 🚀 RECONSTRUCTION DE L'USINE FAO INITIALE POUR LES EXTRÉMITÉS ET FORMES
        len_pnts = len(self.entries)
        if len_pnts > 1:   
            for idx in range(len_pnts):
                current_entry = self.entries[idx]

                if idx == 0 or idx == len_pnts - 1:
                    current_entry.raw_shape_segments = []
                    current_entry.shape_entry_start = current_entry.raw["pos"]
                    current_entry.shape_entry_end = current_entry.raw["pos"]
                    current_entry.shape_bbox_um = [current_entry.raw["pos"],current_entry.raw["pos"]]
                    current_entry.modified_shape = False
                    continue

                pos_a = self.entries[idx - 1].raw["pos"]
                pos_c = self.entries[idx + 1].raw["pos"]

                current_entry.shape_raw_generat(
                    last_pnt_pos=pos_a, 
                    next_pnt_pos=pos_c, 
                    shape_manager=self.shape_manager
                )

        # On fige la nouvelle source de référence vide dans le calque rose d'origine
        self.saved_profile_brut = self.build_flat_segments_list()
        entities_loaded = cdraw.create_entities_from_raw(raw_list=self.saved_profile_brut)
        self.saved_profile_seg_net = cdraw.re_paint_entities(raw_list=entities_loaded, draw_type="profil_save", liaison_line=0)

        # Met à jour les formulaires et force le rafraîchissement global de l'écran actif (vert)
        self.update_entries_data()

    def has_unsaved_changes(self):
        """🚀 COMPARAISON GÉOMÉTRIQUE SÉCURISÉE"""
        # On extrait uniquement les clés de géométrie pure (pos, shape, shape_params)
        # pour éviter que l'absence ou la présence de 'shape_label' ne crée un faux positif !
        current_geometry = [
            {
                "pos": e.raw.get("pos"),
                "shape": e.raw.get("shape"),
                "shape_params": e.raw.get("shape_params", {})
            }
            for e in self.entries
        ]
        
        if not self.storage.part_json_loaded:
            return bool(self.entries)  
            
        loaded_points = self.storage.part_json_loaded.get("points", [])
        
        loaded_geometry = [
            {
                "pos": p.get("pos"),
                "shape": p.get("shape"),
                "shape_params": p.get("shape_params", {})
            }
            for p in loaded_points
        ]
        
        # Comparaison des structures épurées
        changed_points = current_geometry != loaded_geometry
        
        changed_name = False if self.current_name is None else (
            self.current_name != self.storage.part_name[self.storage.part_id_actif]
        )
        
        return changed_points or changed_name

    def up_satus_page_cao(self):
        if self.error_drawing:
            status_cao = "ERROR"
        elif self.not_saved_drawing:
            status_cao = "warning"
        else:
            status_cao = "OK"

        # >> self.page_status_alert = status_cao >> passer par app pour atteindre la page !
        app = App.get_running_app()
        if app:
            app.screen_CAO["status"] = status_cao
        '''
            app.screen_CUTTER["status"] = final_status
            app.property('screen_CUTTER').dispatch(app)  # Propagateur d'allumage nominal Kivy'''

    def copy_part_from_index(self, source_index):
        """
        🚀 LOGIQUE FAO EN ATELIER :
        Charge une pièce source dans un emplacement actif vide pour servir de base de travail.
        Le calque rose affiche la source, le calque vert est prêt pour les modifications.
        """
        if source_index == self.storage.part_id_actif:
            print("[Info] La source et la destination sont identiques, copie ignorée.")
            return

        # 1. Charger la géométrie de la pièce source (Remplit le fond rose ET la pièce verte)
        self.load(part_index=source_index, load_data=True)

        # 2. Renommer la pièce active en mémoire vive
        source_name = self.get_part_name(source_index)
        self.set_part_names(f"{source_name}_copy")
        self.commit_part_names()

        # 🚀 3. SÉCURITÉ DE SAUVEGARDES AUTOMATIQUE (Votre excellente idée) :
        # On valide immédiatement l'existence de cette copie sur le disque dur 
        # à l'emplacement de l'ID actif actuel !
        self.save(part_index=self.storage.part_id_actif, commit_name=False)

        print(f"[Copie] Points de '{source_name}' copiés et enregistrés dans l'emplacement actif sous le nom '{self.get_part_name()}'.")

    def get_part_all_names(self):
        all_names = copy.deepcopy(self.storage.part_name)
        if self.current_name is not None:
            all_names[self.storage.part_id_actif] = self.current_name
        return all_names
    
    def get_part_name(self, index=None):
        part_id = self.storage.part_id_actif if index is None else index

        if part_id == self.storage.part_id_actif and self.current_name is not None:
            return self.current_name
        return copy.copy(self.storage.part_name[part_id])
    
    def set_part_names(self, new_name): #, index = None):
        #part_id = self.storage.part_id_actif if index is None else index
        #self.storage.part_name[part_id]= new_name
        self.current_name = new_name
    
    def commit_part_names(self):
        last_index = self.storage.part_id_actif
        #self.storage.part_id_actif = self.storage.saved_actif
        self.storage.part_name = self.get_part_all_names()
        self.storage.save_designator()
        self.storage.part_id_actif = last_index
    
    def get_units_for_type(self, unit_type, with_labels=False):
        """
        Retourne la liste des unités disponibles pour un type donné.

        Args:
            unit_type (str): Type d'unité ou identifiant d'unité.
            with_labels (bool): Si True, retourne une liste de tuples (id, label).

        Returns:
            list[str] ou list[tuple[str, str]]
        """
        return get_all_units_for_type(unit_type, with_labels=with_labels)

    def A_SUPPRIMER_set_mirror(self, enabled: bool):
        self.data_mirror = enabled
        if self.data_loaded:
            self.update_entries_data()

    
#-------------------------------------------------
    # Dépannage temporaire qui devrais être supprimé
    def get_selected_part(self, part_index=None):
        return self.storage.get_selected_part(part_index)


"""
class NEW_PointManager:
    '''Copy de PointManager avec les modifications que je désirerais y apporter:
        Surtous sur la gestion JSON <> RAM avec possibilitée de comparaison accrue !
        ...
        TODO: En regardant, je dois avoir tous ce qu'il faut, ... ou presque:
        - J'ai JsonPartStorage() - part_json_loaded qui est la copie .json de la pièce
        - dans chaque Entry() la fonction has_unsaved_changes() qui peux comparer le point RAM <> 'JSON'
        Donc: ce que je devrais faire c'est à chaque sortie du mode édition d'un point utiliser 
        cette fonction et je penses tenir à jour dans PartManager() un list[] contenant l'idx des pnts modifiés ?
        avec cette nouvelle liste, je n'ai plus qu'à voir si elle est vide ou non pour savoir les modif actives ?
        ET faire de même pour ce qui et pas [points] de la pièce (nom, ....) ?
        Ensuite dans mon formulaire d'édition, je peux même envisager signaler les points modifiés avec ma liste (si il sont à l'intérieur ou non!)
    '''
    def __init__(self):
        self.entries: list[PointEntry] = [] # -> Toutes la gestion d'un point, point par point
        # 🚀 ON INSTANCIE LE ROUTEUR DE PLUGINS ET DE SHAPES ICI :
        # ... A faire ... pour l'instant sans plugins
        self.shape_manager = ShapeManager() # -> Gestionnaire de terminaison CAO

        self.saved_profile_brut = [] # Segments brutes du profil sauvegardé (ligne + shape), sans miroirs
            # NOTE: Ici c'est tous les segments brutes du profil, y compris les segments des terminaisons (shape) !
        self.saved_profile_seg_net = []   # [json] Segments sauvegardés composant le profil (segments_Canvas), sans miroirs
        self.curent_profile_seg_net = []  # [CAO] Segments en cours d'édition composant le profil (segments_Canvas), sans miroirs
            # NOTE: 2 lignes si-dessus: c'est tous les segments net du profil, Prêts à envoyer dans le Canvas!
        self.barriere_segments = 0   # nombres de segments barrières qui sont inclus à chaque extrémités du profil
        self.barriere_color = "#FFFFFF40"
        self.mcu_synchronise = False  # True si les segments dans le MCU sont identiques à ceux de "self.profil_segments" : False par défaut à l'allumage
        ''' TODO: Il faut supprimer toutes liaison à ColumnDefaultSpec et 
        remplacer par lecture directe dans config.py - AXIS_CONFIG ou un clône éditable'''
        self.unit_spec = ColumnDefaultSpec()  # Unité par défaut à utiliser dans les colonnes du formulaire

        self.data_loaded = False  # Indicateur pour savoir si PointData doit être chargé
        ''' TODO: Toute la partie mirroirs et à revoir avec la nouvelle stratégie et voir si l'on intègre une fonction retournement de pièce pour le dessin ET l'usinage ?'''
        self.data_mirror = False  # Indicateur pour savoir si PointData doit être en mode mirror

        # NOTE: C'est ici que tous ce joue ... avec son part_json_loaded
        self.storage = JsonPartStorage()

        self.current_name = None  # Nom temporaire pour la pièce active
        self.load()

    def load(self, part_index=None, load_data=None):

        part_id = self.storage.part_id_actif if part_index is None else part_index            
        part = self.storage.load_selected_part(part_id)

        self.next_id_point = 0  
        def new_id_pnt():
            self.next_id_point += 1
            return self.next_id_point - 1

        if isinstance(load_data, bool): 
            self.data_loaded = load_data    

        if not part:
            self.entries = []
            return

        # 1️⃣ Instanciation à blanc de toutes vos PointEntry depuis le JSON
        self.entries = []
        for raw in part.get("points", []):
            id_pnt = new_id_pnt()
            entry = PointEntry(raw=raw, id_pnt=id_pnt)
            self.entries.append(entry)  

        # 🎯 2️⃣ USINE DE FAO INITIALE (Grand Orchestre Géométrique)
        # On vérifie qu'on a au moins 2 points pour tracer une ligne, sinon pas de pièce.
        len_pnts = len(self.entries)
        if len_pnts > 1:   
            
            for idx in range(len_pnts):
                current_entry = self.entries[idx]

                # CAS A : Extrémités de la pièce (Premier ou Dernier Point)
                # Ils n'ont pas de voisins complets -> pas de forme physique possible.
                if idx == 0 or idx == len_pnts - 1:
                    current_entry.raw_shape_segments = []
                    current_entry.shape_entry_start = current_entry.raw["pos"]
                    current_entry.shape_entry_end = current_entry.raw["pos"]
                    current_entry.modified_shape = False # On valide le cache à vide
                    continue

                # CAS B : Points intermédiaires (Calcul Trigonometrique)
                # 🚀 Gestion du temps de retard/d'avance pour capturer les voisins exacts
                pos_a = self.entries[idx - 1].raw["pos"] # Point précédent (Amont)
                pos_c = self.entries[idx + 1].raw["pos"] # Point suivant (Aval)

                # Le point calcule sa forme via vos classes (Chanfrein, Congé, Gorge)
                current_entry.shape_raw_generat(
                    last_pnt_pos=pos_a, 
                    next_pnt_pos=pos_c, 
                    shape_manager=self.shape_manager # Passe le ShapeManager de PointManager
                )

        # 🚀 3. FIGER LA SOURCE DE VÉRITÉ SAUVEGARDÉE ( origin_seg_brut )
        # On assemble la chaîne plate complète en microns (liaisons + formes)
        self.saved_profile_brut = self.build_flat_segments_list()  

        # 4a L'usine génère une structure graphique neuve avec les Bbox
        entities_loaded = cdraw.create_entities_from_raw(raw_list=self.saved_profile_brut)  
        # 4b Le profil CAO actif prend toute la liste avec ses barrières
        self.curent_profile_seg_net = cdraw.re_paint_entities(
            raw_list=entities_loaded, draw_type="profil_cao",
            liaison_line=self.barriere_segments, liaison_color=self.barriere_color
        )
        # 4c Si on a des barrières, on ampute directement la liste entities_loaded
        # TODO: A voir avec la nouvelle idée de barrières:
            # Idée: Placer la barrière comme un point spécial ... qui n'est pas forcément au début et à la fin mais plaçable ???
        # TODO: A voir si on ne mets pas quand-même le barrières dans la sauvegarde ???
        if self.barriere_segments > 0 and len(entities_loaded) > (2 * self.barriere_segments):
            entities_saved_pure = entities_loaded[self.barriere_segments : -self.barriere_segments]
        else:
            entities_saved_pure = entities_loaded
        # 4d On peint la pièce d'origine pure en rose nominal
        self.saved_profile_seg_net = cdraw.re_paint_entities(
            raw_list=entities_saved_pure, draw_type="profil_save",
            liaison_line= None
        )
        
        self.current_name = self.storage.part_name[part_id]
        
        # (L'IHM s'éveillera ici tout à la fin si demandé)
        if self.data_loaded: 
            self.update_entries_data()

    def build_flat_segments_list(self) -> list:
        '''
        🎯 LE GRAND CHAÎNAGE CONTINU :
        Parcourt toutes les PointEntry et assemble les segments de formes complexes
        avec les grandes lignes de liaison "l" basées sur les coordonnées JSON originelles.
        '''
        liste_plate = []
        len_pnts = len(self.entries)
        last_pos = []
        
        for idx in range(len_pnts):
            current_entry = self.entries[idx]
                
            # 1: Injection automatique de la ligne de liaison dépendante
            if idx > 0:                
                # SÉCURITÉ INDUSTRIELLE : On donne les positions JSON originelles.
                # Votre compute_raw s'occupera d'ajuster dynamiquement les extrémités !
                liaison = {
                    "type": "l",
                    "start": last_pos,
                    "end": current_entry.raw["pos"],
                    "id_pnt": current_entry.id_pnt
                }
                liste_plate.append(liaison)
            last_pos = current_entry.raw["pos"]
            
            # 2 Aspiration du cache géométrique de la forme (draw_part)
            if hasattr(current_entry, "raw_shape_segments") and current_entry.raw_shape_segments:
                liste_plate.extend(current_entry.raw_shape_segments)
                
        return liste_plate

    def refresh_drawing(self, idx_entry=None, idx_pos_raw=None):
        '''
        🎯 LE CHEF D'ORCHESTRE GÉOMÉTRIQUE CENTRAL (FAO + DESSIN) :
        1. Synchronise le .raw d'un point si ses coordonnées absolues ont changé.
        2. Recalcule localement la trigonométrie de la cellule des 3 points (N-1, N, N+1).
        3. Ré-assemble la chaîne plate globale en microns de toute la pièce.
        4. Repérit l'écran vert d'édition (curent_profile_seg_net) via le pistolet à peinture.
        '''
        len_pnts = len(self.entries)
        if len_pnts <= 1:
            return

        # ÉTAPE 1 : ÉCRITURE DANS LE MODÈLE REEL (.raw)
        # Si un index et une nouvelle position absolue en microns sont fournis, on écrit dans la brique
        if idx_entry is not None:
            if idx_pos_raw is not None:
                if 0 <= idx_entry < len_pnts:
                    self.entries[idx_entry].raw["pos"] = [int(round(idx_pos_raw[0])), int(round(idx_pos_raw[1]))]
                    self.entries[idx_entry].modified_data = True

           # 🚀 ÉTAPE 2 : LE CADENCEUR FAO LOCAL
            index_min = max(1, idx_entry - 1)
            index_max = min(len_pnts - 2, idx_entry + 1)
            
            # 🎯 CORRECTION : Parenthèses et "+ 1" pour inclure index_max dans la boucle !
            for idx in range(index_min, index_max + 1):
                pos_a = self.entries[idx - 1].raw["pos"]
                pos_c = self.entries[idx + 1].raw["pos"]
                
                # Le point ré-exécute sa géométrie (Chanfrein, Congé, Gorge ISO) en direct
                self.entries[idx].shape_raw_generat(
                    last_pnt_pos=pos_a,
                    next_pnt_pos=pos_c,
                    shape_manager=self.shape_manager
                )

        # 🚀 ÉTAPE 3 : LE GRAND CHAÎNAGE GLOBAL (Ré-assemblage microns)
        # On vide les tiroirs de tous les points pour recréer la liste plate à jour
        raw_active_profile = self.build_flat_segments_list()
        # Passage dans l'usine pour injecter les Bounding Boxes (Bbox)
        entities_active = cdraw.create_entities_from_raw(raw_list=raw_active_profile)
        #  LE PISTOLET À PEINTURE CENTRAL (Rendu Kivy)
        self.curent_profile_seg_net = cdraw.re_paint_entities(
            raw_list=entities_active, 
            draw_type="profil_cao",
            liaison_line=self.barriere_segments, 
            liaison_color=self.barriere_color
        )

    def add_entry(self, index: int, hor: float, vert: float, shape=None, shape_label=None, shape_params=None) -> PointEntry:
        '''Ajoute un nouveau PointEntry à la suite de l'index donné (index + 1).'''
        new_raw = {
            "pos": [int(round(hor)), int(round(vert))],
            "shape": shape,
            "shape_label": shape_label,
            "shape_params": shape_params or {}
        }
        id_pnt = self.next_id_point
        self.next_id_point += 1  # Actualisation de l'id pour le prochain point
        new_entry = PointEntry(raw=new_raw, id_pnt=id_pnt)

        # Insertion physique dans la liste de mémoire vive
        self.entries.insert(index + 1, new_entry)
        
        # 🚀 ALIGNEMENT 3 COUCHES :
        # Comme l'insertion d'un point décale toute la structure de la pièce, 
        # on relance update_entries_data. Elle va recalculer le voisinage, 
        # générer la forme du nouveau point et re-dessiner l'écran vert d'édition.
        if self.data_loaded: 
            self.update_entries_data()

        return new_entry

    def delete_entry(self, index: int) -> bool:
        '''
        🚀 LA SUPPRESSION SÉCURISÉE :
        Supprime le PointEntry à l'index donné, recalcule les raccordements 
        des points devenus voisins et rafraîchit l'IHM.
        '''
        if not (0 <= index < len(self.entries)):
            print(f"[Erreur] Index {index} hors limites pour la suppression.")
            return False

        # Sécurité d'atelier : on évite de vider complètement la pièce
        if len(self.entries) <= 2:
            print("[Sécurité] Impossible de supprimer : la pièce doit comporter au moins 2 points.")
            return False

        # 1️⃣ Suppression physique du point en mémoire vive
        removed_entry = self.entries.pop(index)
        print(f"[Suppression] Point ID {removed_entry.id_pnt} retiré de l'index {index}.")

        # 2️⃣ ALIGNEMENT 3 COUCHES :
        # Le point ayant disparu, les points qui l'entouraient se touchent désormais.
        # Leurs angles et leurs tangentes ont changé. On relance la mise à jour globale
        # pour recalculer leurs formes et mettre à jour les grilles de saisie textuelles.
        if self.data_loaded:
            self.update_entries_data()
            
        return True
    
    def update_entries_data(self):
        if not self.entries:
            print("Pas d'entries à mettre à jour")
            return

        prev_pos = None
        for i, entry in enumerate(self.entries):
            try:
                orig_pos = entry.raw.get("pos")
                if not orig_pos:
                    entry.data = None
                    continue

                raw_hor, raw_vert = orig_pos

                pos = [raw_hor, raw_vert]

                # Si data existe déjà, on met à jour
                if entry.data:
                    entry.data.refresh_units()
                    # 🚀 CORRIGÉ : On sépare bien le type technique (shape) du texte (shape_label)
                    entry.data.shape = entry.raw.get("shape") or "- - -"
                    entry.data.shape_label = entry.raw.get("shape_label") or "- - -"
                    entry.data.recompute(pos=pos, prev_pos=prev_pos)
                else:
                    # Sinon on le crée depuis zéro avec toutes ses clés
                    entry.data = PointData(
                        column_spec=self.unit_spec, 
                        pos=pos, 
                        prev_pos=prev_pos,
                        shape=entry.raw.get("shape"),
                        shape_params=entry.raw.get("shape_params"),
                        shape_lbl=entry.raw.get("shape_label") # 🚀 AJOUTÉ ICI
                    )

                prev_pos = pos  # Pour le suivant
                entry.modified_data = False

            except Exception as e:
                print(f"Erreur pour l'entry {i} : {e}")
                entry.data = None

        # 🚀 RECONSTRUCTION DE TOUT LE PROFIL GÉNÉRAL
        # L'ancienne boucle prof_seg_pnt_recompute est supprimée !
        # On demande au manager de repeindre proprement le calque actif (la pièce verte)
        #self.refresh_display_profiles()
        self.refresh_drawing(None, None)

    def update_entry_data(self, index):
        '''Met à jour un point et le suivant (car dépendances avec prev_pos).'''
        if not (0 <= index < len(self.entries)):
            print(f"Index {index} hors limites pour update_entry_data")
            return

        len_pnts = len(self.entries)

        try:
            prev_pos = orig_prev_pos = self.entries[index - 1].raw.get("pos") if index > 0 else None
            entry = self.entries[index]
            pos = orig_pos = entry.raw.get("pos")

            # Appliquer le mode mirror Z pour les calculs de formulaires
            if orig_pos:
                raw_hor, raw_vert = orig_pos
                pos = [raw_hor, raw_vert]
            if orig_prev_pos:
                raw_hor, raw_vert = orig_prev_pos
                prev_pos = [raw_hor, raw_vert]

            if entry.data:
                entry.data.shape = entry.raw.get("shape") or "- - -"
                entry.data.shape_label = entry.raw.get("shape_label") or "- - -"
                entry.data.recompute(pos=pos, prev_pos=prev_pos)
            else:
                entry.data = PointData(
                    column_spec=self.unit_spec, 
                    pos=pos, 
                    prev_pos=prev_pos,
                    shape=entry.raw.get("shape"),
                    shape_params=entry.raw.get("shape_params"),
                    shape_lbl=entry.raw.get("shape_label")
                )
            entry.modified_data = False

            # =====================================================================
            # 🚀 LE CADENCEUR FAO EN DIRECT (MOUVEMENT SOURIS)
            # =====================================================================
            # Si le Point N a bougé, ses coordonnées modifiées changent l'assise trigonométrique 
            # de sa propre forme, mais AUSSI celle du point d'avant (N-1) et du point d'après (N+1) !
            # On force le recalcul géométrique de cette cellule de 3 points :
            for idx in [index - 1, index, index + 1]:
                if 0 <= idx < len_pnts:
                    # On intercepte les extrémités (0 et fin) pour ne pas calculer hors tableau
                    if idx == 0 or idx == len_pnts - 1:
                        continue
                        
                    # Extraction des positions réelles des voisins actuels
                    pos_a = self.entries[idx - 1].raw["pos"]
                    pos_c = self.entries[idx + 1].raw["pos"]
                    
                    # Le point ré-exécute ses calculs de Chanfrein ou de Gorge ISO en direct
                    self.entries[idx].shape_raw_generat(
                        last_pnt_pos=pos_a,
                        next_pnt_pos=pos_c,
                        shape_manager=self.shape_manager
                    )

            # 🚀 ÉTAPE FINALE : Re-dessiner l'écran
            # Toutes les formes impactées ont mis à jour leur cache raw_shape_segments.
            # On demande au manager de ré-assembler la liste plate et de rafraîchir l'IHM !
            self.refresh_display_profiles()

        except Exception as e:
            print(f"Erreur update_entry_data pour l'entry {index} : {e}")
            entry.data = None

    def update_raw_from_data_UTILE(self):   # je penses inutilisable
        '''Synchronise self.raw depuis self.data avec conversion des unités.'''
        if not self.data:
            print("[Warning] Impossible de mettre à jour raw : data est vide.")
            return

        self.raw["pos"] = [
            self.data.hor.val_base(),
            self.data.vert.val_base()
        ]
        self.raw["shape"] = self.data.shape
        self.raw["shape_params"] = self.data.shape_params.copy()

        self.modified_data = False

    def save(self, part_index=None, commit_name=True):
        '''🚀 ENREGISTREMENT ET FIGEAGE DU CALQUE ROSE'''
        import copy
        part_id = self.storage.part_id_actif if part_index is None else part_index

        if commit_name:
            self.commit_part_names()

        if self.entries:
            # 1. Extraction et sauvegarde des clones JSON modifiés
            points = [entry.raw for entry in self.entries if entry.raw]
            self.storage.set_selected_part(part_id, points)
            
            # 🚀 2. SYNCHRONISATION DU FOND GRAPHIQUE ROSE
            # Puisque la pièce est officiellement sauvegardée, le calque actif (en microns)
            # devient la nouvelle référence fixe de fond. 
            self.saved_profile_brut = self.build_flat_segments_list()
            
            # On génère la structure graphique d'IHM associée
            import common_draw as cdraw
            entities_loaded = cdraw.create_entities_from_raw(raw_list=self.saved_profile_brut)
            
            # Application du slicing chirurgical pour masquer les barrières sur le calque de fond rose
            if self.barriere_segments > 0 and len(entities_loaded) > (2 * self.barriere_segments):
                entities_saved_pure = entities_loaded[self.barriere_segments : -self.barriere_segments]
            else:
                entities_saved_pure = entities_loaded

            # On repeint notre témoin d'arrière-plan en rose nominal
            self.saved_profile_seg_net = cdraw.re_paint_entities(
                raw_list=entities_saved_pure, 
                draw_type="profil_save",
                liaison_line=0
            )
            print(f"[Succès] Pièce {part_id} enregistrée. Calque rose synchronisé.")
        else:
            print("[Erreur] La liste 'entries' est vide ou non initialisée.") 

    def reset_part_in_memory(self):
        '''🚀 RÉINITIALISATION COMPLÈTE ET FAO INITIALE'''
        import copy
        import common_draw as cdraw

        # Génération des données de la pièce par défaut
        data = self.storage.make_default_part(self.storage.part_id_actif)
        self.set_part_names(data.get("name", "inconnue"))

        # Re-construction des PointEntry
        self.entries = [
            PointEntry(raw=raw, id_pnt=i)
            for i, raw in enumerate(data.get("points", []))
        ]
        self.next_id_point = len(self.entries)
        
        # 🚀 RECONSTRUCTION DE L'USINE FAO INITIALE POUR LES EXTRÉMITÉS ET FORMES
        len_pnts = len(self.entries)
        if len_pnts > 1:   
            for idx in range(len_pnts):
                current_entry = self.entries[idx]

                if idx == 0 or idx == len_pnts - 1:
                    current_entry.raw_shape_segments = []
                    current_entry.shape_entry_start = current_entry.raw["pos"]
                    current_entry.shape_entry_end = current_entry.raw["pos"]
                    current_entry.modified_shape = False
                    continue

                pos_a = self.entries[idx - 1].raw["pos"]
                pos_c = self.entries[idx + 1].raw["pos"]

                current_entry.shape_raw_generat(
                    last_pnt_pos=pos_a, 
                    next_pnt_pos=pos_c, 
                    shape_manager=self.shape_manager
                )

        # On fige la nouvelle source de référence vide dans le calque rose d'origine
        self.saved_profile_brut = self.build_flat_segments_list()
        entities_loaded = cdraw.create_entities_from_raw(raw_list=self.saved_profile_brut)
        self.saved_profile_seg_net = cdraw.re_paint_entities(raw_list=entities_loaded, draw_type="profil_save", liaison_line=0)

        # Met à jour les formulaires et force le rafraîchissement global de l'écran actif (vert)
        self.update_entries_data()

    def has_unsaved_changes(self):
        '''🚀 COMPARAISON GÉOMÉTRIQUE SÉCURISÉE'''
        # On extrait uniquement les clés de géométrie pure (pos, shape, shape_params)
        # pour éviter que l'absence ou la présence de 'shape_label' ne crée un faux positif !
        current_geometry = [
            {
                "pos": e.raw.get("pos"),
                "shape": e.raw.get("shape"),
                "shape_params": e.raw.get("shape_params", {})
            }
            for e in self.entries
        ]
        
        if not self.storage.part_json_loaded:
            return bool(self.entries)  
            
        loaded_points = self.storage.part_json_loaded.get("points", [])
        
        loaded_geometry = [
            {
                "pos": p.get("pos"),
                "shape": p.get("shape"),
                "shape_params": p.get("shape_params", {})
            }
            for p in loaded_points
        ]
        
        # Comparaison des structures épurées
        changed_points = current_geometry != loaded_geometry
        
        changed_name = False if self.current_name is None else (
            self.current_name != self.storage.part_name[self.storage.part_id_actif]
        )
        
        return changed_points or changed_name
    
    def copy_part_from_index(self, source_index):
        '''
        🚀 LOGIQUE FAO EN ATELIER :
        Charge une pièce source dans un emplacement actif vide pour servir de base de travail.
        Le calque rose affiche la source, le calque vert est prêt pour les modifications.
        '''
        if source_index == self.storage.part_id_actif:
            print("[Info] La source et la destination sont identiques, copie ignorée.")
            return

        # 1. Charger la géométrie de la pièce source (Remplit le fond rose ET la pièce verte)
        self.load(part_index=source_index, load_data=True)

        # 2. Renommer la pièce active en mémoire vive
        source_name = self.get_part_name(source_index)
        self.set_part_names(f"{source_name}_copy")
        self.commit_part_names()

        # 🚀 3. SÉCURITÉ DE SAUVEGARDES AUTOMATIQUE (Votre excellente idée) :
        # On valide immédiatement l'existence de cette copie sur le disque dur 
        # à l'emplacement de l'ID actif actuel !
        self.save(part_index=self.storage.part_id_actif, commit_name=False)

        print(f"[Copie] Points de '{source_name}' copiés et enregistrés dans l'emplacement actif sous le nom '{self.get_part_name()}'.")

    def get_part_all_names(self):
        all_names = copy.deepcopy(self.storage.part_name)
        if self.current_name is not None:
            all_names[self.storage.part_id_actif] = self.current_name
        return all_names
    
    def get_part_name(self, index=None):
        part_id = self.storage.part_id_actif if index is None else index

        if part_id == self.storage.part_id_actif and self.current_name is not None:
            return self.current_name
        return copy.copy(self.storage.part_name[part_id])
    
    def set_part_names(self, new_name): #, index = None):
        #part_id = self.storage.part_id_actif if index is None else index
        #self.storage.part_name[part_id]= new_name
        self.current_name = new_name
    
    def commit_part_names(self):
        last_index = self.storage.part_id_actif
        #self.storage.part_id_actif = self.storage.saved_actif
        self.storage.part_name = self.get_part_all_names()
        self.storage.save_designator()
        self.storage.part_id_actif = last_index
    
    def get_units_for_type(self, unit_type, with_labels=False):
        '''
        Retourne la liste des unités disponibles pour un type donné.

        Args:
            unit_type (str): Type d'unité ou identifiant d’unité.
            with_labels (bool): Si True, retourne une liste de tuples (id, label).

        Returns:
            list[str] ou list[tuple[str, str]]
        '''
        return get_all_units_for_type(unit_type, with_labels=with_labels)

    def A_SUPPRIMER_set_mirror(self, enabled: bool):
        self.data_mirror = enabled
        if self.data_loaded:
            self.update_entries_data()

    
#-------------------------------------------------
    # Dépannage temporaire qui devrais être supprimé
    def get_selected_part(self, part_index=None):
        return self.storage.get_selected_part(part_index)
"""    