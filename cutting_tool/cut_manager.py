# cutting_tool/ - cut_manager.py         # Contrôleur + Modèle : Gère la liste, les calculs
import os
import json
import copy
from kivy._event import EventDispatcher  # AJOUTER L'IMPORTATION DE BASE KIVY
from kivy.properties import BooleanProperty

from cutting_tool.cut_insert_manager import CutInsertLib as InsLib


# 🚀 LA MATRICE DE RÉFÉRENCE DE L'ATELIER (Visible dès l'ouverture du fichier)
DEF_CUTTER_JSON = {
    # "id" et une copie de l'identifiant de l'outil dans la librairie CutterLib(). Ps l'identifiant pas l'index de la liste !
    "ident": "255",           # Ident (redéfini automatiquement par la fonction en ordre croissant sans trous)
    "ident_insert": "0",      # Ident de l'insert (plaquette)
    "tool_mount": None,       # Idexe du porte-outil (si None, pas monté dans le porte-outil) Ps: Ici l'index pas l'identifiant
    
    "name": "new_cutter",       # Nom affiché du burin
    "homming": [                # Diverses validations de homing
        True,                       # Porte-outil changé
        False,                      # Plaquette changée
        False                       # Rayon changé
    ],
    "mount_angle": 0,           # Angle de pivotement du burin (angle de fixation)

    "offset_hor":[0, 0, 0],     # Offset du burin:
    "offset_vert":[0, 0, 0],    # [probe (palpeur), usure_machine (MCU), corr_fine (pièce)]

    "body": {
        "clearance": [3000, 5000],  # Décallage insert <-> corp du burin
        "lead_angle": -5000,        # Angle d'orientation de l'arête de coupe de l'insert
        "lead_reverse": False,      # Inverser l'arête de coupe de l'autre côté du bec (miroir vertical)
        "cadran": 4,                # Référence à la direction de coupe
        "points": [                 # Dessin de contour du corps de burin [[pos: x, pos: y], rayon_congé]
            [[0, 0], 0],            # Garder en tête que ce point + "clearance" donne le point de rotation et de placement de (l'insert + son offset_mount)
            [[16000, 0], 0],
            [[16000, 100000], 0],
            [[0, 100000], 0]
        ]
    }
}


class CutPntDraw:
    """
    Gestion complète et autonome d'un point géométrique du manche du burin.
    Reçoit son manager parent pour appliquer la clearance et les rotations.
    """
    def __init__(self, parent, point_raw: list):
        self.parent = parent  # 🔗 Pointeur direct vers CutterManager
        
        # Les composants bruts issus du JSON [[hor, vert], rayon_conge]
        self.brut_pos = point_raw[0]
        self.radius_base = point_raw[1]
        
        # Indicateur d'état pour le rafraîchissement graphique Kivy
        self.modified_data = True

class CutterManager(EventDispatcher):
    """
    GÈRE UN BURIN UNIQUE.
    Contient ses offsets tridimensionnels, ses clearances, sa liste de points distincts
    et l'objet plaquette (insert) associé.
    """

    modified_not_save = BooleanProperty(False)  # l'outilen RAM différent de l'outil JSON

    def __init__(self, parent_lib, tool_ident: int, raw_dict: dict, insert_manager_obj=None):
        #self.modified_not_save = False  # l'outilen RAM différent de l'outil JSON
        self.modified_geometry = True   # Dessin de l'outil modifiable
        self.ident = tool_ident
        self.raw = raw_dict
        self.parent = parent_lib             # 🔗 Pointeur vers la bibliothèque CutterLib
        
        self.name = raw_dict.get("name", f"Burin_N°{tool_ident}")
        self.homming = raw_dict.get("homming", [True, False, False])
        self.tool_mount = raw_dict.get("tool_mount", None)
        self.mount_angle = raw_dict.get("mount_angle", 0)
        
        # Les 3 couches d'offsets [Palpeur, Usure machine, Correction fine]
        self.offset_hor = raw_dict.get("offset_hor", [0, 0, 0])
        self.offset_vert = raw_dict.get("offset_vert", [0, 0, 0])
        
        # Données de géométrie du corps
        body = raw_dict.get("body", {})
        #if body == {}:
        #    print("DEBUG: Body null")
        #else:
            #print(f"DEBUG: Body OK <<<<<<<<<<<<<<<<<<<< {body}")
        self.clearance = body.get("clearance", [0, 0])
        self.lead_angle = body.get("lead_angle", -5000)
        self.lead_reverse = body.get("lead_reverse", False)
        self.cadran = body.get("cadran", 5.0)
        #print(f"DEBUG >>>>>>>>>>>>>>>>>>> cadran: {self.cadran}")
        
        # 🎯 LE CORPS SOUDÉ AUX COORDONNÉES EN LISTE D'OBJETS DISTINCTS
        self.drawing: list[CutPntDraw] = []
        for pt in body.get("points", []):
            self.drawing.append(CutPntDraw(parent=self, point_raw=pt))
            
        # 🛡️ L'EMBARQUEMENT : L'objet Plaquette est vissé sur ce burin
        self.insert = insert_manager_obj
        

    def get_draw_pnt_brut(self) -> list:
        """
        📐 EXTRACTEUR CAO :
        Parcourt la liste d'objets points distincts self.drawing du manche
        et extrait une liste de coordonnées plates [[Z, X], r] pour le canvas Kivy.
        """
        # Chaque p est un objet CutPntDraw qui contient .brut_pos et .radius_base
        return [p.brut_pos for p in self.drawing]

    def get_icone_cadran(self) -> str:
        """
        🎯 SÉLECTEUR THERMIQUE D'ICÔNES :
        Lit la valeur numérique ou texte de self.cadran, la convertit en int strict
        et renvoie le chemin du PNG transparent associé.
        """
        table_icones = {
            1: "bitmaps/burin_C1.png",
            2: "bitmaps/burin_C2.png",
            3: "bitmaps/burin_C3.png",
            4: "bitmaps/burin_C4.png",
            0: "bitmaps/burin_C4.png",       # Équivalence cadran 0 -> 4           
            # Les demi-valeurs (neutres ou orientations spécifiques)
            0.5: "bitmaps/burin_C05.png",
            4.5: "bitmaps/burin_C05.png",     # Équivalence cadran 4.5 -> 0.5
            1.5: "bitmaps/burin_C15.png",
            2.5: "bitmaps/burin_C25.png",
            3.5: "bitmaps/burin_C35.png"
        }

        # 🟢 SECURISE LE FORMAT : On convertit de force en entier ou float pour le dictionnaire
        try:
            # On transforme le texte "1" en nombre 1
            valeur_numerique = float(self.cadran) 
            # Si c'est un nombre entier (ex: 1.0 ou 1), on le passe en type INT strict (1)
            if valeur_numerique.is_integer():
                cle_recherche = int(valeur_numerique)
            else:
                cle_recherche = valeur_numerique

            #print(f"DEBUG_ICONE_TOOL: cadran de l'icône : {cle_recherche}")

        except (ValueError, TypeError):
            # En cas de valeur corrompue textuelle, repli de sécurité
            cle_recherche = 4

        import os
        chemin_cible = table_icones.get(cle_recherche, "bitmaps/burin_select.png")
        
        #print(f"DEBUG_ICONE_TOOL: chemin_cible : {chemin_cible} / ident_tool: {self.ident}")

        if os.path.exists(chemin_cible):
            return chemin_cible
        elif 1+1 == 2:
            return chemin_cible

        #print(f"DEBUG_ICONE_TOOL: Valeur de remplacement !!!")

        return "bitmaps/burin_select.png"
    


class CutterLib:
    """
    🎯 LA TOURELLE DE L'ATELIER :
    Gère le fichier 'cut_lib.json', peuple la liste de CutterManager
    et garde en permanence une référence sur l'outil actif sur le tour.
    """
    def __init__(self, insert_lib_instance, lib_filename="cut_lib.json"):
        self.filepath = os.path.join(os.path.dirname(__file__), lib_filename)
        self.library = {"cutt_tool": {}}            # Copy local de cut_lib.json (copy en RAM)
        self.cutters: list[CutterManager] = []      # La liste de tous les outils de coupe
        self.active_cutter: CutterManager = None    # L'outil en cours d'utilisation sur la machine
        self.insert_lib = insert_lib_instance    # Instanciation automatique du catalogue d'inserts miroir
        self.lib_not_save = True if len(self.cutters)>0 else False  # Flag à vrai si un seul cutter et en cours de modification non enregistrée
        
        self.load_library()

    def load_library(self):
        """ Charge le JSON, force la présence du Comparateur Maître 199 et instancie la RAM """
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.library = json.load(f)
            except Exception as e:
                print(f"⚙️ DRO [CutterLib Error] : Échec lecture JSON ({e})")
                self.library = {"cutt_tool": {}}
        else:
            self.library = {"cutt_tool": {}}

        # 🚨 FILET DE SÉCURITÉ IMMUABLE : L'outil 199 (Comparateur Maître)
        if "199" not in self.library["cutt_tool"]:
            self.library["cutt_tool"]["199"] = {
                "ident": "199",
                "ident_insert": "0",
                "tool_mount": 0,
                "name": "🎯 COMPARATEUR_MAITRE",
                "homming": [False, False, False],
                "mount_angle": 0,
                "offset_hor":[0,0,0],
                "offset_vert":[0,0,0],
                "body": {
                    "clearance":[0,0],
                    "lead_angle": 0,
                    "lead_reverse": False,
                    "cadran": 4,
                    "points": []
                }
            }
            self.save_library()

        # Phase de reconstruction de vos objets réels parents-enfants
        self.cutters.clear()
        
        for t_id, t_data in self.library["cutt_tool"].items():
            # Résolution de l'insert lié via votre dictionnaire croisé rapide de l'insert_lib
            id_ins = str(t_data.get("ident_insert", "0"))
            test_index_insert= self.insert_lib.get_idx_to_ident.get(id_ins)
            obj_insert_manager = self.insert_lib.get_idx_to_ident.get(
                id_ins, 
                self.insert_lib.get_idx_to_ident.get("0") # Repli de sécurité
            )
            
            # 🟢 SÉCURISÉ : On force l'identifiant à rester un STR pur d'un bout à l'autre !
            str_ident = str(t_id)
            
            # Création du CutterManager individuel en lui passant son identifiant texte
            new_cutter_manager = CutterManager(self, str_ident, t_data, obj_insert_manager)
            self.cutters.append(new_cutter_manager)

        # 🟢 LE TRI NUMÉRIQUE AVEC L'ASTUCE DU TRANSTYPAGE :
        # On garde 'cm.ident' sous forme de texte en RAM, mais on dit à la lambda 
        # de le convertir temporairement en int uniquement pour faire le tri !
        # Cela évite que l'outil "10" ne se retrouve trié avant l'outil "2" par ordre alphabétique.
        self.cutters.sort(key=lambda cm: int(cm.ident))

        # Définition de l'outil actif par défaut (ex: le premier de la liste triée)
        if self.cutters:
            self.active_cutter = self.cutters[0]

    def save_library(self):
        """ Enregistre la bibliothèque sur le disque dur """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.library, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚙️ DRO [CutterLib Error] : Échec écriture JSON ({e})")

    def add_cutter(self) -> str:
        """ 🎯 CREATION DE BURIN : Recherche de trou numérique libre et duplication étanche """
        import copy
        
        # 🟢 RECTIFIÉ : On extrait les identifiants sous forme d'entiers uniquement pour calculer le prochain numéro
        existing_idents = [int(cm.ident) for cm in self.cutters]

        next_num = 1
        while next_num in existing_idents or next_num == 199:
            next_num += 1
            
        str_ident = str(next_num)
        
        # Duplication et configuration du dictionnaire brut dans la DB de la lib
        from cutting_tool.cut_manager import DEF_CUTTER_JSON 
        nouveau_burin_raw = copy.deepcopy(DEF_CUTTER_JSON)
        
        # 🟢 RECTIFIÉ : Alignement sur le mot 'ident' partout !
        nouveau_burin_raw["ident"] = str_ident
        nouveau_burin_raw["name"] = f"Burin_N°{str_ident}"

        self.library["cutt_tool"][str_ident] = nouveau_burin_raw

        # Re-tri et re-génération automatique de la DB vers le dictionnaire ordonné numériquement
        self.library["cutt_tool"] = dict(
            sorted(self.library["cutt_tool"].items(), key=lambda item: int(item[0]))
        )

        self.save_library()
        self.load_library() # Étape capitale : re-peuple la liste d'objets réels à jour en RAM !
        return str_ident

    def get_index_to_ident(self, target_ident: str) -> int:
        """
        🎯 PASSERELLE IHM :
        Parcourt la liste triée des burins et renvoie l'index numérique réel (0, 1, 2...)
        correspondant à l'identifiant textuel recherché.
        Retourne -1 si l'identifiant n'existe pas.
        """
        str_ident = str(target_ident)

        # 🟢 RECTIFIÉ : Sécurité pour la recherche par tranche rapide
        try:
            valeur_num = int(str_ident)
        except ValueError:
            valeur_num = 0

        # On effectue le test de tranche uniquement si la valeur numérique est cohérente 
        # avec la taille actuelle de notre liste (évite le piège de l'outil 199)
        if valeur_num < len(self.cutters):
            min_idx = max(valeur_num - 4, 0)
            max_idx = min(valeur_num + 2, len(self.cutters))
            
            # 🚨 ATTENTION : 'enumerate' sur une tranche repart de l'index 0. 
            # Il faut impérativement additionner 'min_idx' pour retrouver l'index RÉEL dans self.cutters !
            for tranche_idx, cutter_manager in enumerate(self.cutters[min_idx:max_idx]):
                if cutter_manager.ident == str_ident:
                    return min_idx + tranche_idx

        # 🟢 RECHERCNE COMPLETTE DE SECOURS (Filet de sécurité absolu, gère l'outil 199 parfaitement)
        for index, cutter_manager in enumerate(self.cutters):
            if cutter_manager.ident == str_ident:
                return index

        return -1


