from .base_shape import BaseShape
from common_widgets import (
    STATUS_ERREUR, STATUS_NEUTRE, STATUS_VALIDE,
    LabeledToggleCell, GroupHeader, InputCell)
from common_draw import (intersection_of_lines, normalize_vector, normalize_angle, is_clockwise, 
        bissectrice_normalised, create_entities_from_raw, compute_angle_rad, dot_scalaire_vector)
from ui_configurator.theme_manager import draw_line as th_drl
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.metrics import dp
from functools import partial
import config as conf
import math
from copy import copy

class ChamferShape(BaseShape):
    shape_type = ['standard', 'chanfrein']

    # Valeurs par défaut si aucune configuration n'est fournie
    val_default = {
        "largeur_c": [2000, False],   # µm ,  valeur cartésienne (depuis l'axe vétrical ou horizontal)?
        "largeur_a": [2000, False]    # µm ,  valeur cartésienne (depuis l'axe vétrical ou horizontal)?
    }

    options_config = {
        "grp_sérartor00":"Dimensions",
        "largeur_a": {"label_1": "Longueur BA", "label_2": "Hauteur BA", "unit": "unit_distance", "default": 4000, "autofill1": "len_a", "autofill2": "len_a_cart"},
        "largeur_c": {"label_1": "Longueur BC", "label_2": "Hauteur BC", "unit": "unit_distance", "default": 4000, "autofill1": "len_c", "autofill2": "len_c_cart"},
        "hauteur_b": {"label_1": "Distance du point B", "label_2": None, "unit": "unit_distance", "default": 1000, "autofill1": "haut_b"},
        "grp_sérartor01":"Angles",        
        "angle_a":   {"label_1": "Angle avec segment A", "label_2": "Angle avec axe A", "unit": "unit_angle", "default": 30000, "autofill1": "ang_a", "autofill2": "ang_a_cart"},
        "angle_c":   {"label_1": "Angle avec segment C", "label_2": "Angle avec axe C", "unit": "unit_angle", "default": 30000, "autofill1": "ang_c", "autofill2": "ang_c_cart"},
        "symetry": {"label_1": "Symétrique ABC", "label_2": None, "unit": "unit_angle", "default": True},
    }

    def __init__(self, point_a, entry_b, point_c, mirror_z=False):

        self.param_list = []    # contient self-params sous forme de liste
        self.input_widgets = {} # conteint les inputs de shape_config_box (quand il existent !)
        self.toggle_widgets = {} # conteint les boutons d'options de shape_config_box (quand il existent !)

        super().__init__(point_a, entry_b, point_c, mirror_z, params_options_nbr=2)

        self.pntA = point_a
        self.pntB = entry_b
        self.pntC = point_c

        self._updating_inputs = False # Flag qui bloque les màj en boucle des Inputs de shape_config_box

        self.geom_values = None   # Pour stocké les valeurs de définition des cellules du sous-form de configuration
        self.input_cells ={
            "len_a":[None, "dist"], "len_a_cart":[None, "dist"], "len_c":[None, "dist"], "len_c_cart":[None, "dist"],
            "ang_a":[None, "ang"], "ang_a_cart":[None, "ang"], "ang_c":[None, "ang"], "ang_c_cart":[None, "ang"],
            "haut_b":[None, "dist"]}
        for key, cfg in self.options_config.items():    #Màj avec les valeurs par défaut
            if isinstance(cfg, dict):  # ← On traite seulement les vraies configs
                unit_id = cfg.get("unit", "unit_distance")
                for i in (1, 2):
                    autofill = cfg.get(f"autofill{i}")
                    if autofill and autofill not in self.input_cells:
                        self.input_cells[autofill] = [None, unit_id]

        # On initialise la param_list avec les 2 premiers paramètres valides du dict
        for k in self.params:
            if len(self.param_list) < 2:
                self.param_list.append({"name": k, "val": self.params[k][0], "cartesien":self.params[k][1]})

        self.compute_geometry()

    def update_param_list(self, key, value, unit_id="dist", state_toggle=0, was_off=False):
        if key not in self.options_config:
            return

        # Sauvegarde de l’état précédent (pour debug/rollback éventuel)
        last_param_list = copy(self.param_list)

        # Désactivation du paramètre (toggle OFF)
        if state_toggle == 0:
            self.param_list = [
                item for item in self.param_list
                if item["name"] != key
            ]

        else:
            is_angle = self.options_config[key]["unit"] == "unit_angle"
            cart = (state_toggle == 2)

            if was_off:
                # Si c’est un angle, retirer les autres angles
                if is_angle:
                    self.param_list = [
                        item for item in self.param_list
                        if self.options_config[item["name"]]["unit"] != "unit_angle"
                    ]

                # Limiter à 2 params max
                if len(self.param_list) >= 2:
                    self.param_list.pop(0)

                # Ajout du nouveau paramètre
                self.param_list.append({
                    "name": key,
                    "val": value,
                    "cartesien": cart
                })

            else:
                # Le paramètre est déjà dans la liste → mise à jour du mode (ex: passage cartésien ↔ normal)
                index = next((i for i, p in enumerate(self.param_list) if p["name"] == key), None)
                if index is not None:
                    self.param_list[index]["cartesien"] = cart
                    self.param_list[index]["val"] = value  # au cas où la valeur a changé

        # Mise à jour du dictionnaire principal
        self.params = {
            item["name"]: [item["val"], item["cartesien"]]
            for item in self.param_list
        }
        # Mise à jour de l'enregistrement: PointManager.PointEntry.raw
        self.entry.raw["shape_params"] = self.params
        print(f"DEBUG_Open_chanf_update_param_list: entry.raw.shape_params{self.entry.raw["shape_params"]}")

        # === Suivi des changements entre ancien et nouveau param_list ===
        last_keys = {item["name"]: item for item in last_param_list}
        new_keys  = {item["name"]: item for item in self.param_list}

        #added_keys   = [k for k in new_keys if k not in last_keys]
        removed_keys = [k for k in last_keys if k not in new_keys]
        #modified_keys = [k for k in new_keysif k in last_keys and new_keys[k] != last_keys[k]]
        print(f"Removed_keys: {removed_keys}")
        print(f"Param_list: {self.param_list}")

        # === Synchronisation visuelle des LabelToggleCell ===
        for key in removed_keys:
            cell = self.toggle_widgets.get(key)
            if cell:
                cell.turn_off(trigger_callback=False)  # On force l’état visuel à OFF sans rappeler on_toggle
    def update_param_value(self, key, value, unit_id):
        """Met à jour uniquement la valeur d'un paramètre déjà actif, sans modifier son état."""
        for item in self.param_list:
            if item["name"] == key:
                item["val"] = value
                cartesien=item["cartesien"]
                break
        else:
            # Optionnel : ajouter le paramètre si absent
            print(f"[WARN] Paramètre '{key}' non actif, impossible de mettre à jour sa valeur.")
            return

        # Mise à jour du dictionnaire principal
        self.params = {
            item["name"]: [item["val"], item["cartesien"]]
            for item in self.param_list
        }
        # Mise à jour de l'enregistrement: PointManager.PointEntry.raw
        self.entry.raw["shape_params"] = self.params

        # Ici màj de  self.input_cells avec unit_id transmise
        option_line = self.options_config[key]
        key_input = option_line.get("autofill1") if not cartesien else option_line.get("autofill2")
        if key_input in self.input_cells:
            self.input_cells[key_input] = [value, unit_id]

        self.compute_geometry()

    def compute_geometry(self):
        """À compléter avec la géométrie du chanfrein basée sur self.param_list"""
        try:
            new_pos = self.resolve_reference_values()
        except ValueError as e:
            #self.log_error(f"Erreur de géométrie : {e}")
            return

        self.geom_values = new_pos

        # Contrôle de la bonne définition des points:
        if new_pos["pnt_aa"] is None or new_pos["pnt_cc"] is None:
            #raise ValueError(f"Erreur lors de la définission des points du chanfrein")
            #self.log_error("Erreur lors de la définition des points du chanfrein")
            return
        
        point_aa= [self.point_b[0] + new_pos["pnt_aa"][0], self.point_b[1] + new_pos["pnt_aa"][1]]
        point_cc= [self.point_b[0] + new_pos["pnt_cc"][0], self.point_b[1] + new_pos["pnt_cc"][1]]
       
        # Définition des valeurs pour le formulaire config
        self.config_shape_cell_value(new_pos)

        # Donné brut
        self.draw_part= [{"type": "l", "start": point_aa,    "end": point_cc,  "color": th_drl["profil"], 
            "id_pnt":None}]  # id_pnt sera màj après depuis prof_seg_pnt_recompute()
        entities = [
            {"type": "l", "start": self.pntA,   "end": self.point_b,  "color": th_drl["liaison"]},
            {"type": "d", "start": point_aa,    "end": point_cc,  "color": th_drl["detail"]},
            {"type": "l", "start": self.point_b,    "end": self.pntC, "color": th_drl["liaison"]},
        ]
        # donnés formatés pour dessin
        self.entities_shape = create_entities_from_raw(entities, error_color=th_drl["erreur_detail"])
        
        # Mettre à jour le dessin du détail
        self.update_draw_shape(self.entities_shape)

    def resolve_reference_values(self):
        """
        Résout self.param_list en deux longueurs fixes : largeur_a (BA) et largeur_c (BC),
        en utilisant tous types de paramètres définis (longueur segment, projection cartésienne, angle, etc.)
        """
                
        if len(self.param_list) != 2:
            raise ValueError("Deux paramètres sont nécessaires pour résoudre la géométrie.")

        # intitaliser des accès rapides
        param_0, param_1 = self.param_list
        name_0 = param_0["name"]
        name_1 = param_1["name"]
       
        # Vecteur normalisés:
        n_ba = normalize_vector(self.point_a, self.point_b)  # Direction B -> A
        n_bc = normalize_vector(self.point_c, self.point_b)  # Direction B -> A
        n_ac = None     # Direction du chanfrein depuis vecteur B-A -> vers -> B-C
        n_ca = None     # Direction du chanfrein depuis vecteur B-C -> vers -> B-A
        if abs(n_ba[1]) >= abs(n_ba[0]):    # directions des axes cartésien les plus proches
            n_ba_cart = [0, (-1 if n_ba[1] < 0 else 1)]
        else:
            n_ba_cart = [(-1 if n_ba[0] < 0 else 1), 0]
        if abs(n_bc[1]) >= abs(n_bc[0]):
            n_bc_cart = [0, (-1 if n_bc[1] < 0 else 1)]
        else:
            n_bc_cart = [(-1 if n_bc[0] < 0 else 1), 0]

        # initialisation des longeurs de vecteur direction A et direction C
        len_ba = None
        len_bc = None
        p_aa = []  #initialisation des point à retourner
        p_cc = []

        # Direction du chanfrein vue depuis le segment B-A (rotation vers B-C)
        clockwise = is_clockwise(dir_in=n_ba, dir_out=n_bc)

        # Définir le vecteur mormalisé de la direction en fonction d'un angle
        def direction_from_relative_angle(base_vector, angle_rad, clockwise=True):
            """
            Tourne un vecteur de base d’un angle donné, dans le sens horaire ou antihoraire.

            Args:
                base_vector (tuple): Vecteur à faire pivoter (x, y), normalisé
                angle_rad (float): Angle du vecteur B vers extérieur (A ou C). Angle positif mesuré entre le vecteur et le chanfrein (ex: angle intérieur du chanfrein)
                clockwise (bool): True pour tourner dans le sens horaire (CW), False pour antihoraire (CCW)

            Returns:
                tuple: Vecteur unitaire dans la direction tournée
            """
            # Rotation dans le bon sens
            angle = -abs(angle_rad) if clockwise else abs(angle_rad)

            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            print(f" angle: {math.degrees(angle)}° | {angle}rad  | cos:{cos_a} , sin:{sin_a}")
            angle_B =  angle * -1
            cos_b = math.cos(angle_B)
            sin_b = math.sin(angle_B)
            print(f" angle_Inverce: {math.degrees(angle_B)}° | {angle_B}rad  | cos:{cos_b} , sin:{sin_b}")
            #x, y = -base_vector[0], -base_vector[1]
            x, y = base_vector

            return (
                x * cos_a - y * sin_a,
                x * sin_a + y * cos_a
            )

        # Définir une longueur en fonction de ça valeur cartésienne           
        def val_to_cart(value_cart, indice= None):
            '''Transforme une distance cartésienne en distance colinéaire '''
            if indice == "a":
                rapport = abs(n_ba[0] * n_ba_cart[0] + n_ba[1] * n_ba_cart[1])
            elif indice == "c":
                rapport = abs(n_bc[0] * n_bc_cart[0] + n_bc[1] * n_bc_cart[1])
            else:
                raise ValueError("Indice invalide (attendu 'a' ou 'c')")
                #return value_cart
            
            return value_cart / rapport if rapport != 0 else 0

        result = {
            "len_a": [None, None], # [le long de B-A , sur l'axe cartésien]
            "len_c": [None, None],
            "hauteur":None,
            "pnt_aa": None,
            "pnt_cc": None,
            "dir_ba": [n_ba, n_ba_cart],
            "dir_bc": [n_bc, n_bc_cart],
            "dir_chamfer": [None, None],    # [n_ac , n_ca]
            "angle_in": [None, None],
            "angle_out": [None, None],
            "clockwise": clockwise,
        }

        # === Étape 1 : Résolution des angles ===
        if "angle_a" in (name_0, name_1):
            angle_base = param_0["val"] if name_0 == "angle_a" else param_1["val"]
            angle_in = float(conf.format_unit(angle_base, "rad"))
            print(f" --- angle_in {angle_in}  | angle_base {angle_base}")
            angle = normalize_angle(angle_in)
            cart = param_0["cartesien"] if name_0 == "angle_a" else param_1["cartesien"]
            base_vector = n_ba_cart if cart else n_ba
            # Définir la direction du chanfrein de a vers c et de c vers a
            # (ici c'est invercé, vue que les vecteurs c'est b -> A, est que l'angle est donné dans l'autre sens (A-aa-cc , pas B-aa-cc))
            n_ca = direction_from_relative_angle(base_vector=base_vector, angle_rad=angle, clockwise=clockwise)
            n_ac = [-n_ca[0], -n_ca[1]]

            result["angle_in"]= [None, angle_base] if cart else [angle_base, None]
            result["dir_chamfer"]= [n_ac,n_ca]

        elif "angle_c" in (name_0, name_1):
            angle_base = param_0["val"] if name_0 == "angle_c" else param_1["val"]
            angle_out = float(conf.format_unit(angle_base, "rad"))
            angle = normalize_angle(angle_out)
            cart = param_0["cartesien"] if name_0 == "angle_c" else param_1["cartesien"]
            base_vector = n_bc_cart if cart else n_bc
            n_ac = direction_from_relative_angle(base_vector=base_vector, angle_rad=angle, clockwise=not clockwise)
            n_ca = [-n_ac[0], -n_ac[1]]

            result["angle_out"]= [None, angle_base] if cart else [angle_base, None]
            result["dir_chamfer"]= [n_ac,n_ca]

        elif "symetry" in (name_0, name_1):
            bisect = bissectrice_normalised(n_ba, n_bc, point_start=(0,0), normalised_dir=True) #point_start=self.point_b
            if isinstance(bisect, str):
                raise ValueError(f"Erreur bissectrice : {bisect}")
            # Définir la direction du chanfrein de a vers c et de c vers a (normal à la bissectrice)
            n_ac = (bisect[1], -bisect[0]) if not clockwise else  (-bisect[1], bisect[0])  # Rotation de 90°
            n_ca = (-n_ac[0], -n_ac[1])        
            print(f" dir B->A:{n_ba} , dir B->C:{n_bc} | dir bisect:{bisect} | dir a-c:{n_ac} , dir c-a:{n_ca}")
            result["dir_chamfer"]= [n_ac,n_ca]

        
        # === Étape 2 : On résoud avec la/les dimensions fournies ===
        # On boucle sur les deux paramètres pour trouver une distance traitable
        for param in self.param_list:
            name = param["name"]
            dir_chamfer = None

            if name =="largeur_a":
                if param["cartesien"]:
                    len_cart = param["val"]
                    len_ba = val_to_cart(len_cart, indice="a")
                    
                    result["len_a"][1]= len_cart
                else:
                    len_ba = param["val"] #if not param["cartesien"] else val_to_cart(param["val"], indice="a")
                result["len_a"][0]= len_ba
                
                if n_ac:    # Définir la direction du chanfrein
                    dir_chamfer = n_ac
                elif "hauteur_b" in (name_0, name_1):    # Trouver la direction du chanfrein en fonction de ça hauteur
                    dist_to_b = param_0["val"] if name_0 == "hauteur_b" else param_1["val"]
                    dir_chamfer = self.dir_to_dist_point(dir_in=n_ba, dir_out=n_bc, len_in=len_ba, dist_b=dist_to_b)
                    result["hauteur"]= dist_to_b
                    result["dir_chamfer"]= [dir_chamfer, [-dir_chamfer[0],-dir_chamfer[1]]]
                
                # Si une direction est fournie on peut résoudre le point sur le segment B-C
                if dir_chamfer:
                    valout = self.calculer_len_out(len_ba, n_ba, n_bc, dir_chamfer)                    
                    if valout is not None:
                        result["len_c"][0]= valout["len_out"]
                        result["pnt_aa"]=  valout["pnt_in"]
                        result["pnt_cc"]=  valout["pnt_out"]
                        return result              
                else:
                    p_aa = [n_ba[0] * len_ba, n_ba[1] * len_ba]
                    result["pnt_aa"]=  p_aa

            elif name =="largeur_c":
                if param["cartesien"]:
                    len_cart = param["val"]
                    len_bc = val_to_cart(len_cart, indice="c")
                    
                    result["len_c"][1]= len_cart
                else:
                    len_bc = param["val"]
                result["len_c"][0]= len_bc

                if n_ca:
                    dir_chamfer = n_ca
                elif "hauteur_b" in (name_0, name_1):
                    dist_to_b = param_0["val"] if name_0 == "hauteur_b" else param_1["val"]
                    dir_chamfer = self.dir_to_dist_point(dir_in=n_bc, dir_out=n_ba, len_in=len_bc, dist_b=dist_to_b)
                    result["hauteur"]= dist_to_b
                    result["dir_chamfer"]= [[-dir_chamfer[0],-dir_chamfer[1]], dir_chamfer]
                
                if dir_chamfer:
                    valout = self.calculer_len_out(len_bc, n_bc, n_ba, dir_chamfer)
                    if valout is not None:
                        result["len_a"][0]= valout["len_out"]
                        result["pnt_cc"]=  valout["pnt_in"]
                        result["pnt_aa"]=  valout["pnt_out"]
                        return result
                else:
                    p_cc = [n_bc[0] * len_bc, n_bc[1] * len_bc]
                    result["pnt_cc"]=  p_cc

            elif name =="hauteur_b":            
                if n_ac:    # Si une direction est fournie, on peux définir un point temporaire à l'intersect du chanfrein et de ça normal passant par B
                    dist_to_b = param["val"]
                    result["hauteur"]= dist_to_b 
                    # Normale à dir_ac : 90° dans le bon sens horaire
                    normal_to_chamfer = (n_ac[1], -n_ac[0]) if clockwise else (-n_ac[1], n_ac[0])
                    # Résoudre len_ba et len_bc depuis la direction normal ci-dessus
                    valout_a = self.calculer_len_out(len_in=dist_to_b, dir_in=normal_to_chamfer, dir_out=n_ba, dir_chamfer=n_ca)
                    valout_c = self.calculer_len_out(len_in=dist_to_b, dir_in=normal_to_chamfer, dir_out=n_bc, dir_chamfer=n_ac)

                    len_ba = result["len_a"][0] = valout_a["len_out"]
                    p_aa   = result["pnt_aa"]   = valout_a["pnt_out"]
                    len_bc = result["len_c"][0] = valout_c["len_out"]
                    p_cc   = result["pnt_cc"]   = valout_c["pnt_out"]
                    #break   # tous est définis, on peut sortir du "for..."
                    return result
                else: 
                    # définir depuis len_ba ou len_bc si pas d'angle défini
                    pass
            else: 
                # définir depuis l'autre argument si parm est un angle
                pass

        # Contrôler si tous est bien définis:
        #if not len_ba or p_aa is None:
        #    raise ValueError(f"Erreur lors de la définission du point sur le segment A-B")
        #if not len_bc or p_cc is None:
        #    raise ValueError(f"Erreur lors de la définission du point sur le segment B-C")
        
        #test rempo:
        
        return result


    def get_shape_label_name_test(self):
        dim_arg = None
        compl_arg= None
        compl_sym = False

        denom_txt = [
            ["largeur_a", "[l]", "[L]"],
            ["largeur_c", "[p]", "[P]"],
            ["hauteur_b", "[h]", "[long]"],
            ["angle_a", "", "[cart]"],
            ["angle_c", "", "[cart]"],
            ["symetry", "", ""]
        ]

            # On recherche la première dimension
        for k in self.params:
            if k == "largeur_a" or k == "largeur_c":
                if dim_arg == "":
                    dim_arg = k
                else:
                    compl_arg = k
            elif k == "hauteur_b":
                    compl_arg = k
        
        if dim_arg == "":
            dim_arg = compl_arg
            compl_arg = ""

        if compl_arg == "":
            for k in self.params:
                if k != dim_arg:
                    compl_arg = k
                    if k == "symetry":
                        compl_sym = True
                    break

        dim_cart = dim_arg[1]
        denom_dim = dim_arg in enumerate(denom_txt)
        val_dim = dim_arg[0]
        dim_txt = (denom_dim[1] if dim_cart else denom_dim[2]) + " " + val_dim/1000
        if not compl_sym:
            compl_cart = compl_arg[1]
            denom_compl = compl_arg in enumerate(denom_txt)
            val_compl = compl_arg[0]
            compl_txt = (denom_compl[1] if compl_cart else denom_compl[2]) + " " + val_compl/1000
        else:
            compl_txt = "sym"

        return f"Chanfrein ({dim_txt} * {compl_txt})"

    def shape_config_box(self):
        print(f"DEBUG_Open_chanf_Shape_config_box: entry.raw.shape_params{self.entry.raw["shape_params"]}")
        layout = self.create_standard_config_box(orientation='vertical', pilot_hint=(1, 0), spacing=dp(5))
        self.input_widgets.clear()  # On s'assure de repartir de zéro # ré-initialiser à vide

        for idx, opt_key in enumerate(self.options_config):
            config_line = self.options_config[opt_key]

            if isinstance(config_line, dict):  # ← On traite seulement les vraies configs
                layout.add_widget(self._build_param_line(idx, opt_key, config_line))
            else:
                layout.add_widget(GroupHeader(config_line, thickness=1))  # Le nom du groupe est la valeur
                line = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20), spacing=dp(10))
                line.add_widget(Widget(size_hint_x=0.5))
                line.add_widget(Label(text="Relatif", color=(1, 1, 1, 0.65), size_hint_x=0.25))
                line.add_widget(Label(text="Absolu", color=(1, 1, 1, 0.65), size_hint_x=0.25))
                layout.add_widget(line)

        return layout

    def _build_param_line(self, index, key, config):
        unit_type = config["unit"]
        label_text = config["label_1"]
        autofill1 = config.get("autofill1")
        autofill2 = config.get("autofill2")

        val1 = self.input_cells.get(autofill1) if autofill1 else None
        val2 = self.input_cells.get(autofill2) if autofill2 else None


        def on_text_change(instance, value):
            if self._updating_inputs:   # Eviter les màj en boucles
                return
            
            if key not in [item["name"] for item in self.param_list]:
                instance.set_status(STATUS_NEUTRE)
                return
            parsed = conf.parse_user_input(value, default_unit_type_or_id=unit_type)
            if isinstance(parsed, str):
                instance.set_status(STATUS_ERREUR)
                return
            val_float, unit_id, _ = parsed
            factor = conf.get_unit_config(unit_id).get("factor", 1.0)
            val_um = int(round(val_float * factor))
            instance.set_status(STATUS_VALIDE)
            self.update_param_value(key, val_um, unit_id)

        def on_toggle(key_toggle, state_toggle, was_off):
            """
            Callback du bouton LabeledToggleCell.
            - key_toggle : le nom du paramètre (ex: "largeur_a")
            - state_toggle : état sélectionné (0=off, 1=normal, 2=cartésien)
            - was_off : bool indiquant si le bouton était désactivé avant
            """

            # Récupère la config du paramètre
            config = self.options_config.get(key_toggle, {})
            key_fill_1 = config.get("autofill1")
            key_fill_2 = config.get("autofill2")

            # Initialisation des variables pour NEW_update_param_list
            key_fill = None
            val_base = 0
            unit_id = "dist"  # Valeur par défaut raisonnable

            # --- Gérer les états ---
            if state_toggle == 1:
                # activer autofill1, désactiver autofill2
                key_fill = key_fill_1
            elif state_toggle == 2:
                # activer autofill2, désactiver autofill1
                key_fill = key_fill_2
            else:  # state_toggle == 0 → désactivation                
                # désactiver inputs ici si tu veux  
                '''Laisser couler jusqu'à self.update_param_list qui fera le travail'''
                pass
                    # On nettoie param_list directement
                    #self.param_list = [p for p in self.param_list if p["name"] != key_toggle]
                    #self.params = {
                    #    item["name"]: [item["val"], item["cartesien"]]
                    #    for item in self.param_list
                    #}
                    #self.compute_geometry()
                    #return  # Ne pas continuer plus loin

            # Si on a un champ de saisie associé (autofill1 ou 2)
            if key_fill and key_fill in self.input_widgets:
                val_brut = self.input_widgets[key_fill].text
                parsed = conf.parse_user_input(val_brut, default_unit_type_or_id=self.input_cells[key_fill][1])

                if not isinstance(parsed, str):  # Pas d'erreur de parsing
                    val_float, unit_id, _ = parsed
                    factor = conf.get_unit_config(unit_id).get("factor", 1.0)
                    val_base = int(round(val_float * factor))

            # Dans tous les cas, même sans champ input (ex: "symetry")
            self.update_param_list(key_toggle, val_base, unit_id, state_toggle, was_off)

        # Layout ligne
        line = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), spacing=dp(10))
        
        # Button de sélection d'option (avec LabelToggleCell):
        toggle_cell = LabeledToggleCell(key,  text=label_text, callback=on_toggle, size_hint_x=0.5)
        toggle_cell.add_state(text=label_text, bg_color=(0,0.5,0.5,0.8), fg_color=(1,1,1,1))  #add_state(self, bg_color=None, fg_color=None, text=None):
            # Récupère le paramètre s’il est actif
        param = next((p for p in self.param_list if p["name"] == key), None)
        toggle_state = 1 if param else 0
        if autofill2:
            toggle_cell.add_state(text=config.get("label_2", label_text), bg_color=(0,0.1,0.6,0.8), fg_color=(1,1,1,1))
            if param and param["cartesien"]:
                toggle_state = 2
        toggle_cell.set_state(toggle_state)

        self.toggle_widgets[key] = toggle_cell
        line.add_widget(toggle_cell)

        # Input 1 ou widget vide
        if autofill1:
            val1_text, unit_str = conf.format_unit(val1[0], unit_type, True) if val1[0] is not None else ("", conf.get_unit_type(unit_type))
            input1 = InputCell(text=f"{val1_text} {unit_str}", size_hint_x=0.25)
            input1.bind(text=on_text_change)
            self.input_widgets[autofill1] = input1
        else:
            input1 = Widget(size_hint_x=0.25)

        # Input 2 ou widget vide
        if autofill2:
            val2_text, _ = conf.format_unit(val2[0], unit_type, True) if val2[0] is not None else ("", conf.get_unit_type(unit_type))
            input2 = InputCell(text=f"{val2_text} {unit_str}", size_hint_x=0.25)
            input2.bind(text=on_text_change)
            self.input_widgets[autofill2] = input2
        else:
            input2 = Widget(size_hint_x=0.25)

        # Construction de la ligne
        line.add_widget(input1)
        line.add_widget(input2)

        return line

    def update_all_inputs_display(self):
        if not self.input_widgets:
            return
        self._updating_inputs = True
        try:
            for key, (val, unit_type) in self.input_cells.items():
                if val is None:
                    #continue
                    val_text = "Err: "
                    unit_str=""
                else:
                    val_text, unit_str = conf.format_unit(val, unit_type, True)

                widget = self.input_widgets.get(key)
                if widget:
                    widget.text = f"{val_text} {unit_str}"
        finally:
            self._updating_inputs = False

    def config_shape_cell_value(self, new_pos):
        """
        Met à jour self.input_cells avec les valeurs calculées (en unités de base) extraites de new_pos.
        Conserve les unités déjà présentes dans input_cells (ne les modifie pas).
        """

        if not new_pos:
            return

        # Alias pour plus de lisibilité
        dir_ba, dir_ba_cart = new_pos.get("dir_ba", (None, None))
        dir_bc, dir_bc_cart = new_pos.get("dir_bc", (None, None))
        dir_ac, dir_ca = new_pos.get("dir_chamfer", (None, None))

        if not dir_ac or not dir_ca:
            pta = new_pos["pnt_aa"]
            ptc = new_pos["pnt_cc"]
            dir_ac = normalize_vector(ptc, pta)
            dir_ca = normalize_vector(pta, ptc)


        for key, (src_key, idx) in {
            "len_a":       ("len_a", 0),
            "len_a_cart":  ("len_a", 1),
            "len_c":       ("len_c", 0),
            "len_c_cart":  ("len_c", 1),
            "ang_a_cart":  ("angle_in", 1),
            "ang_c_cart":  ("angle_out", 1),
            "ang_a":       ("angle_in", 0),
            "ang_c":       ("angle_out", 0),
            "haut_b":      ("hauteur", None),
        }.items():
            if key not in self.input_cells:
                continue  # sécurité

            # Initialisation
            val = None

            # Cas standard : valeur présente dans new_pos
            if idx is None:
                val = new_pos.get(src_key)
            else:
                src = new_pos.get(src_key)
                if isinstance(src, (list, tuple)) and len(src) > idx:
                    val = src[idx]

            # Si la valeur est manquante, tenter de la calculer
            if val is None:

                # -- Angles A
                if key in ("ang_a_cart") and dir_ca:
                    # on calcul d'aord ça l'angle relatif pour avoir la direction de l'angle
                    if dir_ba:
                        angle_in = compute_angle_rad(dir_ca, dir_ba) 
                    if angle_in:
                        if new_pos["angle_in"][0] == None: # Si pas défini dans new_pos, on évite de la recalculer
                            new_pos["angle_in"][0] = abs(int(round(math.degrees(angle_in) * 1000)))

                    # puis on calcul l'angle cartésien est on lui applique le même facteur de correction qu'au relatif
                        val_t = compute_angle_rad(dir_ca, dir_ba_cart)
                        val = int(round(math.degrees(val_t) * 1000))
                        if angle_in < 0:
                            val = -val
                    print(f">>>>DEBUG_ Angle_a_cart = {val}")
                            
                elif key == "ang_a" and dir_ca and dir_ba:
                    val_t = abs(compute_angle_rad(dir_ca, dir_ba))
                    val = int(round(math.degrees(val_t) * 1000))

                # -- Angles C
                if key in ("ang_c_cart") and dir_ac:
                    # on calcul d'aord ça l'angle relatif pour avoir la direction de l'angle
                    if dir_bc:
                        angle_in = compute_angle_rad(dir_ac, dir_bc) 
                    if angle_in:
                        if new_pos["angle_out"][0] == None: # Si pas défini dans new_pos, on évite de la recalculer
                            new_pos["angle_out"][0] = abs(int(round(math.degrees(angle_in) * 1000)))
                            
                    # puis on calcul l'angle cartésien est on lui applique le même facteur de correction qu'au relatif
                        val_t = compute_angle_rad(dir_ac, dir_bc_cart)
                        val = int(round(math.degrees(val_t) * 1000))
                        if angle_in < 0:
                            val = -val
                            
                elif key == "ang_c" and dir_ac and dir_bc:
                    val_t = abs(compute_angle_rad(dir_ac, dir_bc))
                    val = int(round(math.degrees(val_t) * 1000))

                # -- len_a_cart et len_c_cart (projection cartésienne)
                elif key == "len_a_cart" and new_pos.get("len_a", [None])[0] is not None and dir_ba_cart:
                    base = new_pos["len_a"][0]
                    proj = abs(dot_scalaire_vector(dir_ba, dir_ba_cart))
                    val = int(round(base * proj))

                elif key == "len_c_cart" and new_pos.get("len_c", [None])[0] is not None and dir_bc_cart:
                    base = new_pos["len_c"][0]
                    proj = abs(dot_scalaire_vector(dir_bc, dir_bc_cart))
                    val = int(round(base * proj))

                # -- hauteur (distance entre point B et segment AC)
                elif key == "haut_b" and dir_ac and dir_ba and new_pos.get("len_a", [None])[0] is not None:
                    len_a = new_pos["len_a"][0]
                    normal_to_chamfer = (-dir_ac[1], dir_ac[0])  # ou (dir_ac[1], -dir_ac[0]) peu importe
                    proj = dot_scalaire_vector(dir_ba, normal_to_chamfer)
                    val = int(round(abs(len_a * proj)))

            # Appliquer la mise à jour si une valeur a été obtenue
            if val is not None:
                old = self.input_cells.get(key, [None, "dist"])
                self.input_cells[key] = [val, old[1]]  # conserve l'unité

            # Mise à jour graphique
            self.update_all_inputs_display()

    # Fonctions spécifique au calcul du chanfrein
    def dir_to_dist_point(self, dir_in, dir_out, len_in, dist_b, clockwise=None):
        """
        Calcule un vecteur direction unitaire `n_ac` pour une droite aa → cc
        telle que :
            - le point aa est à distance `len_in` du point central (supposé à l'origine)
            - la droite aa → cc est à une distance `dist_b` du point central
            - la droite aa → cc est perpendiculaire à la direction fictive du triangle rectangle
            - le sens (horaire ou anti-horaire) détermine de quel côté est la courbure

        Paramètres :
        - dir_in : vecteur unitaire d'entrée (ex : B → A)
        - dir_out : vecteur unitaire de sortie (ex : B → C)
        - len_in : distance du point central jusqu'à `aa`
        - dist_b : distance perpendiculaire entre le point central et la droite aa → cc
        - clockwise : bool | None, sens de rotation (CW), optionnel

        Retourne :
        - n_ac : vecteur direction unitaire de la droite aa → cc
        """
        if clockwise is None:       # Déterminer le sens (CW/CCW) si non fourni
            clockwise = is_clockwise(dir_in, dir_out)

        center = [0.0, 0.0]  # point central (anciennement B)
       
        base_point = [  # Point sur dir_in à distance dist_b (base du triangle)
            center[0] + dist_b * dir_in[0],
            center[1] + dist_b * dir_in[1]
        ]

        header_len = math.sqrt(len_in**2 - dist_b**2)   # Longueur de l'hypoténuse miroir

        perp = [-dir_in[1], dir_in[0]]    # Perpendiculaire à dir_in (rotation +90°)

        # Deux positions possibles pour le sommet du triangle rectangle
        header1 = [base_point[0] + header_len * perp[0],
                base_point[1] + header_len * perp[1]]   # sens horaire
        header2 = [base_point[0] - header_len * perp[0],
                base_point[1] - header_len * perp[1]]   # sens anti-horaire

        dir1 = [header1[0] - center[0], header1[1] - center[1]]     # Vecteurs depuis le centre (0, 0)
        dir2 = [header2[0] - center[0], header2[1] - center[1]]

        # Perpendiculaires aux directions (rotation ±90°)
        n_ac1 = normalize_vector([-dir1[1], dir1[0]])       # +90°
        n_ac2 = normalize_vector([ dir2[1], -dir2[0]])      # -90°

        aa = [center[0] + len_in * dir_in[0],
            center[1] + len_in * dir_in[1]]

        def dot(a, b): return a[0]*b[0] + a[1]*b[1]

        to_header1 = [header1[0] - aa[0], header1[1] - aa[1]]
        to_header2 = [header2[0] - aa[0], header2[1] - aa[1]]

        # Vérifie que les vecteurs pointent vers les headerX
        if dot(n_ac1, to_header1) < 0:
            n_ac1 = [-n_ac1[0], -n_ac1[1]]
        if dot(n_ac2, to_header2) < 0:
            n_ac2 = [-n_ac2[0], -n_ac2[1]]

        return n_ac1 if clockwise else n_ac2

    def calculer_len_out(self, len_in, dir_in, dir_out, dir_chamfer):
        """
        Calcule les informations de sortie à partir :
        - d'une longueur d'entrée `len_in`
        - d'une direction d'entrée `dir_in`
        - d'une direction de sortie `dir_out`
        - d'une direction de chanfrein 'dir_chamfer' du point_in vers le point_out

        Les directions sont des vecteurs unitaires (normalisés).

        Retourne un dict avec :
        - "len_in" : la distance entre le point d'origine et le point d'entrée (aa)
        - "len_out" : la distance entre le point d'origine et le point de sortie (cc)
        - "pnt_in"  : le point d'entrée (aa)
        - "pnt_out" : le point de sortie (cc)
        """
        # Point d'origine
        origin = [0.0, 0.0]

        # Calcul du point d'entrée (aa)
        aa = [origin[0] + len_in * dir_in[0], origin[1] + len_in * dir_in[1]]

        # Point de sortie (intersection entre la droite aa→cc et la sortie)
        cc = intersection_of_lines(pnt_in=aa, dir_ac=dir_chamfer, pnt_base=origin, dir_out=dir_out)
        if cc is None:
            return None

        # Calcul de la distance entre l'origine et le point cc
        dx = cc[0] - origin[0]
        dy = cc[1] - origin[1]
        len_out = (dx**2 + dy**2)**0.5
        print(f"lenout:{len_out} | dir chanfrein:{dir_chamfer} | len_in:{len_in} | pos_aa:{aa} , pos_cc:{cc}")
        return {
            "len_in": len_in,
            "len_out": len_out,
            "pnt_in": aa,
            "pnt_out": [origin[0]+dx, origin[1]+dy]
        }

