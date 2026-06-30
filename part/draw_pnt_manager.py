# part/  draw_pnt_manager.py

import json
import os
import math
import copy
from collections import namedtuple
from dataclasses import dataclass
from utils import save_json_with_format
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from config import get_unit_config, get_unit_property, format_unit, get_unit_id, get_all_units_for_type, get_unit_type, AXIS_CONFIG, parse_user_input
from ui_configurator.theme_manager import draw_line as th_drl   # th_drl => Thème draw line
import common_draw as cdraw
import part.shapes.shape_registry as sr

DATA_FILE_PART = os.path.join(os.path.dirname(__file__), 'draw_point.json')
DATA_FILE_TOOL = os.path.join(os.path.dirname(__file__), 'cutter_data.json')


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
                "selected_part_index": 0
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

        self.part_id_actif = data.get("selected_part_index", 0) # Pas d'effet de bord ici (juste un integer)

        json_name = [p.get("name", f"Part {i}") for i, p in enumerate(data.get("parts", []))]
        self.part_name = copy.deepcopy(json_name)   # Copie indépendante

        parts = data.get("parts", [])
        if 0 <= self.part_id_actif < len(parts):
            self.part_json_loaded = copy.deepcopy(parts[self.part_id_actif])   # Copie indépendante
        else:
            self.part_json_loaded = None  # ou {} selon tes préférences

    def save_designator(self):
        data = self.load_data()
        data["selected_part_index"] = self.part_id_actif
        #self.saved_actif = self.part_id_actif
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
        '''
        part_id = self.part_id_actif if part_id is None else part_id
        data = self.get_selected_part(part_id)
        if self.part_id_actif == part_id and data is not None:
            if isinstance(data, dict) and "points" in data:
                self.part_json_loaded = copy.deepcopy(data)
            else:
                self.part_json_loaded = None
                #print(f"DEBUG_load_selected_part: données invalides ou incomplètes: {data}")
        else:
            self.part_json_loaded = None  # ou {} selon tes préférences
            #print("DEBUG_load_selected_part: Null ou id diff")
        return data

    def set_selected_part(self, part_id=None, points=None):
        # Si part_id est None, on utilise la pièce active
        part_id = self.storage.part_id_actif if part_id is None else part_id
        
        data = self.load_data()
        
        if 0 <= part_id < len(data.get("parts", [])):
            # Mettre à jour les points de la pièce spécifiée
            data["parts"][part_id]["points"] = points
            self.save_data(data)
        else:
            print(f"ID de pièce invalide : {part_id}")

class JsonCuttingToolStorage(JsonPointStorage):
    MAX_ID_CUTT_TOOL = 100
    def __init__(self):
        self.path = DATA_FILE_TOOL
        super().__init__()
        self.cutt_id_actif = 0
        self.cutt_json_loaded = {}
        self.cutt_name = []

        self.last_new_id_cutt_tool = -1 # Identifiant du dernier burin ajouté 

        self.load_designator()

    def _ensure_file_exists(self):
        if not os.path.exists(self.path):
            data = {
                "cutt_profile": {},
                "cutt_tool": {},
                "selected_tool_index": 0
            }
            self.save_data(data)
            print(f"Initialisation de {self.path} avec une structure vide.")

    def make_default_cutting_tool(self, tool_id=0, cadran=4):
        cutter_val = self.draw_cadran_default(cadran)
        return {
            "id_cutt": tool_id, # Identifiant unique
            "p_change": False,  # Si l'outil est concidéré comme calibré (positions prettent à l'emplois)
            "tool_mount": None,    # Identifiant du porte outil
            "form": 11,         # Identifiant de la plaquette actuelement montée sur l'outil
            "cadran": cadran,        # Direction du tranchant (par demi-cadran)
            "dir_pos": cutter_val["dir_cutt_profile"],  # Direction de montage de la plaquette
            "draw": cutter_val["pnt_draw"],             # dessin de burin avec [0,0]= point 0,0 de la plaquette = point de coupe
            "probe_x": 0,       # Offset de palpage en X
            "probe_z": 0,       # Offset de palpage en Z
            "corr_x": [0, 0],   # Coorection de l'outil en X : [coorection standart (rémanante), coorection fine (temporaire)]
            "corr_z": [0, 0]    # Coorection de l'outil en Z : [coorection standart (rémanante), coorection fine (temporaire)]
        }
    
    def draw_cadran_default(self, cadran):
        cutter_val_def = {}
        
        if cadran == 1:   # burin pour usinage de la porté intérieur et face. (direction opérateur/broche)
            cutter_val_def["pnt_draw"]= [[0,0],[100,100],[100,16000],[1700,16000],[1700,100]]
            cutter_val_def["dir_cutt_profile"]= [10,10]
        elif cadran == 4:   # burin pour usinage de la porté et face. (direction axe/broche)
            cutter_val_def["pnt_draw"]= [[0,0],[-100,-100],[-16000,-100],[-16000,-1700],[-100,-1700]]
            cutter_val_def["dir_cutt_profile"]= [-10,10]
        elif cadran == 3.5:   # burin pour usinage de la porté . (direction axe de rotation)
            cutter_val_def["pnt_draw"]= [[0,0],[-800,-800],[-800,-16000],[800,-16000],[800,-800]]
            cutter_val_def["dir_cutt_profile"]= [-10,0]
            #cutter_val_def["icon"]= ...
        elif cadran == 1.5:   # burin pour usinage de la porté intérieur. (direction opérateur)
            cutter_val_def["pnt_draw"]= [[0,0],[-800,-800],[-800,-16000],[800,-16000],[800,-800]]
            cutter_val_def["dir_cutt_profile"]= [-10,0]
        elif cadran == 2:   # burin pour usinage de la porté intérieur et face invercé. (direction opérateur/contre pointe)
            cutter_val_def["pnt_draw"]= [[0,0],[100,-100],[100,16000],[1700,16000],[1700,-1000],[100,-1000]]
            cutter_val_def["dir_cutt_profile"]= [10,-10]
        elif cadran == 2.5:   # burin pour usinage de la face inverce. (direction contre-pointe)
            cutter_val_def["pnt_draw"]= [[0,0],[-800,-800],[-800,-16000],[800,-16000],[800,-800]]
            cutter_val_def["dir_cutt_profile"]= [0,-10]
        elif cadran == 3:   # burin pour usinage de la porté et face inverce. (direction axe/contre-pointe)
            cutter_val_def["pnt_draw"]= [[0,0],[-100,100],[-16000,100],[-16000,1700],[-100,1700]]
            cutter_val_def["dir_cutt_profile"]= [-10,10]
        elif cadran == 4.5:   # burin pour usinage de la face. (direction mandrin)
            cutter_val_def["pnt_draw"]= [[0,0],[-800,800],[-800,16000],[800,16000],[800,800]]
            cutter_val_def["dir_cutt_profile"]= [0,10]
        else:
            cutter_val_def["pnt_draw"] = [[0, 0]]
            cutter_val_def["dir_cutt_profile"] = [0, 0]
            print(f"[Avertissement] Cadran inconnu : {cadran}")

        return cutter_val_def

    def load_data(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_data(self, data):
        save_json_with_format(self.path, data, indent=4)
        cutt_tool = data.get("cutt_tool", {})
        if str(self.cutt_id_actif) in cutt_tool:
            self.cutt_json_loaded = copy.deepcopy(cutt_tool[str(self.cutt_id_actif)])
        else:
            self.cutt_json_loaded = {}

    def load_designator(self):
        data = self.load_data()
        cutt_tool = data.get("cutt_tool", {})
        self.cutt_id_actif = data.get("selected_tool_index", 0)
        self.cutt_name = []

        for k in sorted(cutt_tool.keys(), key=lambda x: int(x)):
            tool = cutt_tool[k]
            name = tool.get("nom", f"Cutting Tool {k}")
            self.cutt_name.append(name)

        if str(self.cutt_id_actif) in cutt_tool:
            self.cutt_json_loaded = copy.deepcopy(cutt_tool[str(self.cutt_id_actif)])
        else:
            self.cutt_json_loaded = {}

    def save_designator(self):
        data = self.load_data()
        data["selected_tool_index"] = self.cutt_id_actif

        cutt_tool = data.get("cutt_tool", {})
        for i, k in enumerate(sorted(cutt_tool.keys(), key=lambda x: int(x))):
            if i < len(self.cutt_name):
                cutt_tool[k]["nom"] = self.cutt_name[i]

        self.save_data(data)

    def set_selected_index(self, tool_id):
        data = self.load_data()
        if str(tool_id) in data.get("cutt_tool", {}):
            self.cutt_id_actif = int(tool_id)
            self.save_designator()
        else:
            print(f"[Erreur] ID d'outil invalide : {tool_id}")

    def get_selected_cutting_tool(self):
        data = self.load_data()
        return data.get("cutt_tool", {}).get(str(self.cutt_id_actif))

    def load_selected_cutting_tool(self):
        tool = self.get_selected_cutting_tool()
        if tool:
            self.cutt_json_loaded = copy.deepcopy(tool)
        else:
            self.cutt_json_loaded = {}
        return self.cutt_json_loaded

    def get_cutting_tool_profile(self, form_id=None):
        data = self.load_data()
        profiles = data.get("cutt_profile", {})
        tool = self.cutt_json_loaded or self.get_selected_cutting_tool()
        form = tool.get("form") if form_id is None else form_id
        return profiles.get(str(form), None)

    def reset_cutting_tool(self, tool_id=None):
        tool_id = self.cutt_id_actif if tool_id is None else tool_id
        data = self.load_data()
        data["cutt_tool"][str(tool_id)] = self.make_default_cutting_tool(tool_id)
        self.save_data(data)
        self.load_designator()


    def add_cutting_tool(self):
        data = self.load_data()
        cutt_tool = data.get("cutt_tool", {})

        start_id = self.last_new_id_cutt_tool + 1
        for i in range(self.MAX_ID_CUTT_TOOL):
            candidate_id = (start_id + i) % self.MAX_ID_CUTT_TOOL
            if str(candidate_id) not in cutt_tool:
                # ID disponible, on crée l’outil
                new_tool = self.make_default_cutting_tool(candidate_id)
                cutt_tool[str(candidate_id)] = new_tool

                data["cutt_tool"] = cutt_tool
                self.last_new_id_cutt_tool = candidate_id
                self.cutt_id_actif = candidate_id  # sélectionne le nouveau
                self.save_data(data)
                self.load_designator()
                print(f"[Info] Outil #{candidate_id} ajouté.")
                return

        print(f"[Erreur] Bibliothèque d'outils complète. Maximum atteint ({self.MAX_ID_CUTT_TOOL}).")

    def set_selected_cutting_tool(self, tool_data, tool_id=None):
        tool_id = self.cutt_id_actif if tool_id is None else tool_id
        data = self.load_data()
        data["cutt_tool"][str(tool_id)] = tool_data
        self.save_data(data)




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
    def __init__(self, column_spec, pos, prev_pos=None, shape=None, shape_params=None):
        """
        pos         : [hor, vert] en unité de base
        prev_pos    : [hor, vert] du point précédent (pour calculs vert2, hor2, l, alpha)
        column_spec : instance de ColumnDefaultSpec
        """
        self.shape_values = {}  # Dict[str, PointValue] → pour les paramètres liés à la forme

        self.column_spec = column_spec  # ColumnDefaultSpec() unités par défaut pour les colonnes du formulaire
        self.shape = shape or "- - -"
        self.shape_params = shape_params or {}


        # Créer les objets PointValue une fois
        self.hor = PointValue(0, axis_key="hor", unit_id=self.column_spec.get_unit("vert").unit_id)
        self.hor2 = PointValue(0, axis_key="hor2", unit_id=self.column_spec.get_unit("hor2").unit_id)
        self.vert = PointValue(0, axis_key="vert", unit_id=self.column_spec.get_unit("hor").unit_id)
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
        Met à jour le PointValue.value à partir d’une chaîne utilisateur, avec ou sans unité.
        (convertion: val_disp >> val_work)
            Exemples valides :
            - "12.5"        → interprété en self.unit_id
            - "12.5mm"      → détecte l'unité "mm"
            - "12.5 mm"     → idem
            - "12.5 in"     → convertit correctement en unité de base

        Retourne :
        - True  → si la valeur a été modifiée
        - False → si la valeur est restée identique
        - 'invalid_unit'   → si l’unité est inconnue ou incomplette
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
    def __init__(self):
        self.entries: list[PointEntry] = []
        self.profil_segments = []   # liste des segments composant le profil
        self.mcu_synchronise = False  # True si les segments dans le MCU sont identiques à ceux de "self.profil_segments" : False par défaut à l'allumage
        self.unit_spec = ColumnDefaultSpec()  # Unité par défaut à utiliser dans les colonnes du formulaire
        self.data_loaded = False  # Indicateur pour savoir si PointData doit être chargé
        self.data_mirror = False  # Indicateur pour savoir si PointData doit être en mode mirror
        self.storage = JsonPartStorage()
        self.current_name = None  # Nom temporaire pour la pièce active
        #Ajouter ceci à l'init : (chargement au démarrage de la dernière pièce utilisée)
        self.load()

    def load(self, part_index=None, load_data=None):
        part_id = self.storage.part_id_actif if part_index is None else part_index            
        part = self.storage.load_selected_part(part_id)

        self.next_id_point = 0  # Compteur pour id de point unique
        def new_id_pnt():
            self.next_id_point += 1
            return self.next_id_point - 1

        if isinstance(load_data, bool): 
            self.data_loaded = load_data    # Forcer ou ingnorer le chargement de PointData (Définir la variable)

        if not part:
            self.entries = []
            return

        self.entries = []
        for raw in part.get("points", []):
            id_pnt = new_id_pnt()
            entry = PointEntry(raw=raw, id_pnt=id_pnt)
            self.entries.append(entry)

        self.current_name = self.storage.part_name[part_id]

        # Définition du dessin de profil de la pièce
            # Je préfaire le séparer de l'autre for car pour la définition du shape, j'ai besoin du point suivant !
        self.profil_segments = []   # liste des segments composant le profil
        for idx in range(len(self.entries)):
            self.prof_seg_pnt_recompute(idx)

        # Si data doit être chargé, on met à jour les données
        if self.data_loaded: 
            self.update_entries_data()

    def add_entry(self, index: int, hor: float, vert: float, shape=None, shape_label=None, shape_params=None) -> PointEntry:
        """Ajoute un nouveau PointEntry à l'index donné (après index), avec conversion automatique."""
        new_raw = {
            "pos": [int(round(hor)), int(round(vert))],
            "shape": shape,
            "shape_label": shape_label,
            "shape_params": shape_params or {}
        }
        id_pnt = self.next_id_point
        self.next_id_point += 1 # actualisation de l'id pour le prochain point
        new_entry = PointEntry(raw=new_raw, id_pnt=id_pnt)

        self.entries.insert(index + 1, new_entry)
        # Si data doit être chargé, on met à jour les données
        if self.data_loaded: 
            self.update_entry_data(index + 1)
        # self.save()   # Enregistrer draw_point.json

        # màj de la liste des segments 'self.profil_segments'
        self.prof_seg_pnt_recompute(index + 1, changed_pos=True)


        return new_entry

    def update_entries_data(self, appli_mirorz= True):
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

                if appli_mirorz and self.data_mirror:
                    raw_hor *= -1

                pos = [raw_hor, raw_vert]

                # Si data existe déjà, on met à jour
                if entry.data:
                    entry.data.refresh_units()
                    entry.data.recompute(pos=pos, prev_pos=prev_pos)
                else:
                    # Sinon on la crée depuis zéro
                    entry.data = PointData(column_spec=self.unit_spec, pos=pos, prev_pos=prev_pos)

                prev_pos = pos  # pour le suivant
                entry.modified_data = False

            except Exception as e:
                print(f"Erreur pour l'entry {i} : {e}")
                entry.data = None

        # màj du profil général:
        for idx, _ in enumerate(self.entries):
            self.prof_seg_pnt_recompute(idx, changed_pos=False)

    def update_entry_data(self, index, appli_mirorz= True):
        """Met à jour un point et le suivant (car dépendances avec prev_pos)."""
        if not (0 <= index < len(self.entries)):
            print(f"Index {index} hors limites pour update_entry_data")
            return

        try:
            prev_pos = orig_prev_pos = self.entries[index - 1].raw.get("pos") if index > 0 else None
            entry = self.entries[index]
            pos = orig_pos = entry.raw.get("pos")

            # appliquer le mode mirrior Z
            if orig_pos:
                raw_hor, raw_vert = orig_pos
                if appli_mirorz and self.data_mirror:
                    raw_hor *= -1
                pos = [raw_hor, raw_vert]
            if orig_prev_pos:
                raw_hor, raw_vert = orig_prev_pos
                if appli_mirorz and self.data_mirror:
                    raw_hor *= -1
                prev_pos = [raw_hor, raw_vert]

            if entry.data:
                entry.data.recompute(pos=pos, prev_pos=prev_pos)
            else:
                entry.data = PointData(column_spec=self.unit_spec, pos=pos, prev_pos=prev_pos)
            entry.modified_data = False

            # màj du profil général:
            self.prof_seg_pnt_recompute(index, changed_pos=True)

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
        part_id = self.storage.part_id_actif if part_index is None else part_index

        if commit_name:
            self.commit_part_names()

        if self.entries is not None:
            points = [entry.raw for entry in self.entries if entry.raw]
            self.storage.set_selected_part(part_id, points)
        else:
            print("[Erreur] La liste 'entries' est vide ou non initialisée.") 

    def reset_part_in_memory(self):
        '''Effacer et réinitialiser la liste de points (PointEntries)'''

        data = self.storage.make_default_part(self.storage.part_id_actif)
        self.set_part_names(data.get("name","inconnue"))

        #self.next_id_point = 0  # Compteur réinitialisé pour id de point unique
        self.entries = [
            PointEntry(raw=raw, id_pnt=i)
            for i, raw in enumerate(data.get("points", []))
        ]
        self.next_id_point = len(self.entries)
        
        # On met à jour les données
        #self.commit_part_names()
        self.update_entries_data()

    def has_unsaved_changes(self):
        """Compare self.entries.raw avec le json original (self.storage.part_json_loaded["points"])"""
        current_points = [e.raw for e in self.entries]
        
        if not self.storage.part_json_loaded:
            return bool(current_points)  # True si des points existent mais aucun point chargé
        loaded_points = self.storage.part_json_loaded.get("points", [])
        # Comparaison stricte
        changed_points = current_points != loaded_points
        changed_name = False if self.current_name is None else (self.current_name != self.storage.part_name[self.storage.part_id_actif])
        return changed_points or changed_name
    
    def copy_part_from_index(self, source_index):
        """Charge les points de source_index dans l'éditeur actif, et renomme sans sauvegarder."""
        if source_index == self.storage.part_id_actif:
            print("[Info] La source et la destination sont identiques, copie ignorée.")
            return

        # Charger les points de la pièce source dans le manager (sans modifier part_id_actif)
        self.load(part_index=source_index, load_data=True)

        # Renommer la pièce active (seulement le nom, pas les données)
        source_name = self.get_part_name(source_index)
        self.set_part_names(f"{source_name}_copy")
        self.commit_part_names()

        print(f"[Copie] Points de '{source_name}' chargés dans la pièce active renommée en '{self.get_part_name()}', nbr points: {len(self.entries)}.")

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
            unit_type (str): Type d'unité ou identifiant d’unité.
            with_labels (bool): Si True, retourne une liste de tuples (id, label).

        Returns:
            list[str] ou list[tuple[str, str]]
        """
        return get_all_units_for_type(unit_type, with_labels=with_labels)

    def set_mirror(self, enabled: bool):
        self.data_mirror = enabled
        if self.data_loaded:
            self.update_entries_data()

    # Gestion de profil_segments:
    def prof_seg_index_start_end(self, id_pnt: int) -> tuple:
        '''Renvois l'index de début et de fin d'un identifiant, dans self.profil_segments'''
        start_index = None
        end_index = None
        for i, seg in enumerate(self.profil_segments):
            if seg["id_pnt"] == id_pnt:
                if start_index == None:
                    start_index = i
                end_index = i
            elif end_index != None:
                break
        return (start_index, end_index)

    def prof_seg_pnt_recompute(self, idx_new: int, changed_pos=False):
        """
        Recalcule les segments du profil autour d'un point donné dans `self.entries`.

        Cette fonction supprime les segments existants autour du point désigné 
        (entre le point précédent et le point suivant, inclusivement) puis les 
        remplace par de nouveaux segments générés dynamiquement en fonction des 
        types de formes associées au point (via l'attribut `shape` de `entry.raw`).

        Ce recalcul inclut :
        - La liaison droite entre le point précédent et le point courant.
        - Les segments générés par une forme définie (si applicable).
        - La liaison entre le point courant et le suivant.
        - La reprise des segments du point suivant, jusqu'à trouver le prochain segment utile.

        Args:
            idx_new (int): Index du point (dans `self.entries`) pour lequel les 
                segments du profil doivent être recalculés.

        Notes:
            - Si le point est le premier ou le dernier de la liste, l'algorithme 
              s'adapte pour recalculer uniquement les segments valides.
            - Les segments remplacés sont supprimés de `self.profil_segments`, 
              puis remplacés à l'endroit exact de la coupe.
            - L'attribut `id_pnt` est automatiquement ajouté aux segments générés.
        """

        
        # Informe que le dessin actuel n'est plus sychronisé avec le dessin du MCU qui pilote la machine
        self.mcu_synchronise = False # Le dessin a changé, la machine n'est plus à jour !

        len_pnts = len(self.entries)    # Nombre de points de références
        if len_pnts <= 1:
            return  # Rien à faire si on n’a qu’un seul point

        # Initialisation des variables
        new_seg = []            # Liste des segments brut à re-définir
        last_pnt_ref = None   # position de référence du segment précédant
        seg_idx_start_cut = 0   # Index du premier segment redéfini dans self.profil_segments
        seg_idx_end_cut = len(self.profil_segments)  # Index du dernier segment redéfini dans self.profil_segments

        idx_current = idx_new - 1   # Index dans la liste entries en cours de traitement
        id_current = self.entries[idx_current].id_pnt   # Identifiant unique du point en cours de traitement (id de liaison entre .entries et .profil_segments)
        #entry_current = self.entries[idx_new]
        loop_shape = 1      # Nombre de shape à re-définir (un lors de l'initialisation ou édition d'un shape, 3 lors du déplacement d'un point "entries")

        color = th_drl["profil"]                # Couleur à appliquer aux segments
        color_error = th_drl["erreur_profil"]   # Couleur à appliquer aux segments en cas d'erruer

        def load_seg_shape(idx_entry):
            """
                Extraction des segments de la forme de terminaison (shape) du point `entry`, 
                ainsi que ses points de début et de fin de raccordement.

                Retourne un tuple (segments, shape_start_point, shape_end_point)
                ou None si aucune forme n'est définie ou valide.
            """

            this_entry = self.entries[idx_entry]
            shape_type = this_entry.raw.get("shape")
            if not isinstance(shape_type, (list, tuple)) or len(shape_type) != 2:
                return None     # Type/subtype invalide ou non défini

            grp1, grp2 = shape_type
            this_id = this_entry.id_pnt
            shape_cls = sr.get_shape_class(grp1, grp2)

            if shape_cls:
                shape_start_point = None
                shape_end_point = this_entry.raw["pos"]
                pos_a = self.entries[idx_entry-1].raw["pos"]
                pos_c = self.entries[idx_entry+1].raw["pos"]
                tmp_shape = shape_cls(pos_a, this_entry, pos_c, self.data_mirror)
                raw_segs = getattr(tmp_shape, "draw_part", [])
                if isinstance(raw_segs, list):
                    for _seg in raw_segs:
                        _seg["id_pnt"] = this_id    # c'est un list, ajouter l'ident du "point entry" au segments
                        if "start" in _seg and "end" in _seg: # Chercher la première ligne correspondant à une ligne ou un arc
                            if shape_start_point is None:
                                shape_start_point = _seg["start"]   # Réccupérer la point de raccordement
                            shape_end_point = _seg["end"]           # Réccupérer la point de raccordement

                    if shape_start_point is None:
                        shape_start_point = this_entry.raw["pos"]
                    return (raw_segs, shape_start_point, shape_end_point)
            return None     # Cette terminaison et invalide ou null

        
        # 1. récupérer les datas du dernier segment de l'entry précédant prev → new (prev → shape_recompute)
        if idx_new > 0:
            if changed_pos and idx_new > 1: # Si recalcule du shape précédant (et qu'il peut exister)
                idx_current = idx_new - 2
                id_current = self.entries[idx_new-1].id_pnt   # Identifiant unique du point en cours de traitement (id de liaison entre .entries et .profil_segments)
                loop_shape = 3
            elif changed_pos and idx_new <= 1:
                loop_shape = 2

            id_current = self.entries[idx_current].id_pnt
            prev_start_idx, prev_end_idx = self.prof_seg_index_start_end(id_current) # Recherche les index dans la liste de segments correspondant à identifiant
            # TODO: Ci-dessous peut-être inutile ! A contrôler ??
            if prev_start_idx is None and loop_shape == 3:
                loop_shape = 2
                idx_current = idx_new - 1
                id_current = self.entries[idx_new-1].id_pnt
                prev_start_idx, prev_end_idx = self.prof_seg_index_start_end(id_current)

            if prev_start_idx is not None:  # Si l'ident en cour existe dans la liste de segments
                # Rechercher le premier segment dans le point précédant qui n'est pas un segment indépendant (par ex. pas un cercle)
                for idx_prev in range(prev_end_idx, prev_start_idx -1, -1):
                    seg_idx_start_cut = idx_prev    # indexe du premier segment à remplacer
                    new_seg.insert(0, cdraw.extract_raw_from_entity(self.profil_segments[idx_prev]))
                    if "end" in new_seg[0]:
                        break
            last_pnt_ref = self.entries[idx_current].raw["pos"]

        elif len(self.profil_segments) > 0: # 🟡 Cas particulier : on modifie la position du point 0
            # Ici on doit màj la ligne de liaison et le shape du point suivant
            idx_current = 0
            last_pnt_ref = self.entries[idx_current].raw["pos"]
            self.entries[idx_current].update_shape_startend(last_pnt_ref, last_pnt_ref)
            loop_shape = 1  # On vas juste re-définir le shape suivant (sur le point_1) si il existe
            
        else:       # 🔴 Cas de création du tout premier point seul — aucun segment possible
            return

        

        # 2. Segment droit entre prev → shape + segments du/des shapes
        if last_pnt_ref is not None:

            # Ici un for 1 à 3 boucles selon changed_pos. Pour màj de la ligne de liaison et du shape
            for _ in range(loop_shape):
                idx_current += 1            # Index dans la liste entries en cours de traitement 
                if idx_current < len_pnts:
                    id_current = self.entries[idx_current].id_pnt
                    pt_new = self.entries[idx_current].raw["pos"]   # position du point en cours de traitement pour destination de la ligne de liaison

                    # - La ligne de liaison entre points de référence
                    new_seg.append({"type": "l", "start": last_pnt_ref, "end": pt_new,
                        "color": color, "id_pnt": id_current})
                
                    # - Segments du shape s’il y en a
                    shape_result = load_seg_shape(idx_current)
                    if shape_result:    # Si un shape existe sur ce point de référence
                        new_seg.extend(shape_result[0])
                        self.entries[idx_current].update_shape_startend(shape_result[1],shape_result[2])
                    else:               # Si aucun shape n'existe sur ce point de référence
                        self.entries[idx_current].update_shape_startend(pt_new, pt_new)
                    last_pnt_ref = pt_new
                else:
                    idx_current -= 1     # Si on a dépassé le dernier index dans la liste entries
                    break
                    
        # 3. Segment new → next >> Ici redessiner le segment de liaison suivant et copier le segment suivant de cet entry si il existe
        last_pnt_ref = self.entries[idx_current].raw["pos"]
        idx_current += 1
        if idx_current < len_pnts:
            id_current = self.entries[idx_current].id_pnt
            next_start_idx, next_end_idx = self.prof_seg_index_start_end(id_current)
            if next_start_idx is None:
                # Aucun segment encore assigné au point suivant → on coupe à la fin de la liste actuelle
                next_start_idx = next_end_idx = seg_idx_end_cut -1
            pt_next = self.entries[idx_current].raw["pos"]
            # on s'occupe du segment de liaison avec le point de réf suivant
            new_seg.append({"type": "l", "start": last_pnt_ref, "end": pt_next,
                "color": color, "id_pnt": id_current})
            seg_idx_end_cut = next_start_idx + 1  # Mise à jour de la fin de la coupe
            
            # On passe le segment de liaison puis on boucle pour trouver le "start" suivant
            for idx_next in range(next_start_idx +1, next_end_idx +1, +1):
                # Rechercher le premier segment dans le point suivant qui n'est pas un segment indépendant (par ex. pas un cercle)
                seg_idx_end_cut = idx_next +1    # indexe du premier segment à ne pas remplacer
                new_seg.append(cdraw.extract_raw_from_entity(self.profil_segments[idx_next]))
                if "start" in new_seg[-1]:
                    break

        # 4. Création, recalcul et insertion/remplacement
        # --- Mise au format common_draw (format Kivy + bbox) ---
        add_seg = cdraw.create_entities_from_raw(new_seg, error_color = color_error)    # TODO: A intégrer dans la liste: , id_pnt=id_new
        # --- Suppression des segments qui ont été recalculés ---
        if seg_idx_end_cut > seg_idx_start_cut:
            del self.profil_segments[seg_idx_start_cut:seg_idx_end_cut]
        # --- Ajout des nouveaux segments recalculés ---
        self.profil_segments[seg_idx_start_cut:seg_idx_start_cut] = add_seg



    
#-------------------------------------------------
    # Dépannage temporaire qui devrais être supprimé
    def get_selected_part(self, part_index=None):
        return self.storage.get_selected_part(part_index)
    