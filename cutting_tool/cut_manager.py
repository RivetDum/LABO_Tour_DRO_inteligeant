# cutting_tool/ - cut_manager.py         # Contrôleur + Modèle : Gère la liste, les calculs
import os
from kivy.app import App
import json
import copy
from kivy._event import EventDispatcher  # AJOUTER L'IMPORTATION DE BASE KIVY
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty

from utils import save_json_with_format
from configurator.config import MACHINE_CONFIG
from cutting_tool.cut_insert_manager import CutInsertLib as InsLib


# 🚀 LA MATRICE DE RÉFÉRENCE DE L'ATELIER (Visible dès l'ouverture du fichier)
DEF_CUTTER_JSON = {
    # "id" et une copie de l'identifiant de l'outil dans la librairie CutterLib(). Ps l'identifiant pas l'index de la liste !
    "ident": "255",           # Ident (redéfini automatiquement par la fonction en ordre croissant sans trous)
    "ident_insert": "0",      # Ident de l'insert (plaquette)
    "ident_mount": None,       # Ident du porte-outil (si None, pas monté dans le porte-outil) Ps: Ici l'index pas l'identifiant

    "name": "new_cutter",       # Nom affiché du burin
    "cadran_icone": 5,      # Demi-cadran correspondant à l'image du burin (par défaut 5 = non-définit)

    "tourelle_def":{        # Position par défaut de montage (indexage) du porte-outil sur la tourelle
        "idx_mount": [0,False], # Index de la liste, sauvegardé/validé
        "idx_dro": [0,0,False], # C'est visuelement, ou l'opérateur veux son point 0, par rapport au bec de coupe (son rayon):
            #1er: 1 à gauche, 0 au centre, 2 à droite
            #2èm: 1 en haut, 0 au centre, 2 en bas(extérieur)
            #3èm: Le bool, toujours pour valider l'état. ou un truc vers l'image ?la validation et déjà dans crant_indexage !
        "angle_machine": 0,     # Angle de fixation de la tourelle par-rapport à l'axe pièce utilisé pour les offsets ci-dessous
        "ofst_probbe": [0,0,False],     # Offset de palpage de l'outil
        "ofst_machine": [0,0,False],    # Offset correction machine
        "ofst_corr": [0,0,False]        # Offset de réglage fin (correction de mesure par l'opérateur)
    },
    "tourelle_def":{        # Position volante (éditable) d'indexage du porte-outil sur la tourelle
        "idx_mount": [0,False],     # Idem à "tourelle_def"
        "idx_dro": [0,0,False],
        "angle_machine": 0,
        "ofst_probbe": [0,0,False],
        "ofst_machine": [0,0,False],
        "ofst_corr": [0,0,False]
    },

    "body": {
        "clearance": [3000, 5000],  # Décallage insert <-> corp du burin
        "lead_angle": -5000,        # Angle d'orientation de l'arête de coupe de l'insert
        "lead_reverse": False,      # Inverser l'arête de coupe de l'autre côté du bec (miroir vertical)
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
        self.modified_data = True   # TODO: Contrôler l'utilisation ?


class OLD_CutterManager(EventDispatcher):
    """
    GÈRE UN BURIN UNIQUE AVEC ARCHITECTURE MULTI-POSITIONS TOURELLE ET DRO.
    Contient ses offsets tridimensionnels, ses clearances, sa liste de points distincts,
    l'objet plaquette (insert) associé et gère la sécurité des états de calibration.
    """
    # Propriété Kivy pour notifier l'IHM si l'outil en RAM diffère du JSON
    modified_not_save = BooleanProperty(False)

    def __init__(self, parent_lib, tool_ident: str, raw_dict: dict, insert_manager_obj=None):
        super().__init__()  # 🚨 CRUCIAL : Initialise proprement l'EventDispatcher de Kivy !
        
        self.modified_geometry = True   # Dessin de l'outil modifiable
        self.ident = str(tool_ident)    # On force l'identifiant à rester un STR pur
        self.raw = raw_dict
        self.parent = parent_lib        # 🔗 Pointeur vers la bibliothèque CutterLib
        
        self.name = raw_dict.get("name", f"Burin_N°{tool_ident}")
        self.tool_mount = raw_dict.get("ident_mount", None) # None = aucun porte-outil associé
        
        # 🎯 LES COUCHES DE CONFIGURATION MULTI-POSITIONS [[Valeur_Défaut, Valid], [Valeur_Volante, Valid]]
        self.crant_idexage = raw_dict.get("idx_mount", [[0, False, 0], [0, False, 0]])
        self.cadran_dro = raw_dict.get("idx_dro", [[0, 0, False], [0, 0, False]])
        
        # 🛡️ LES 3 COUCHES D'OFFSETS SÉCURISÉES MULTI-POSITIONS
        self.offset_probe = raw_dict.get("ofst_probbe", [[0, 0, False], [0, 0, False]])  # Par défaut False (non certifié)
        self.offset_machine = raw_dict.get("ofst_machine", [[0, 0, False], [0, 0, False]])
        self.offset_correction = raw_dict.get("ofst_corr", [[0, 0, False], [0, 0, False]])
        
        # Données de géométrie du corps
        body = raw_dict.get("body", {})
        
        # Sécurité : On extrait uniquement les valeurs numériques de clearance (index 0 et 1), on ignore l'info texte
        raw_clearance = body.get("clearance", [0, 0])
        self.clearance = [raw_clearance[0], raw_clearance[1]]
        
        self.lead_angle = body.get("lead_angle", 0)
        self.lead_reverse = body.get("lead_reverse", False)
        self.cadran_icone = raw_dict.get("cadran_icone", 5)  # L'icône de forme physique de l'outil
                        
        # 🎯 LE CORPS SOUDÉ AUX COORDONNÉES EN LISTE D'OBJETS DISTINCTS
        self.drawing: list[CutPntDraw] = []
        for pt in body.get("points", []):
            self.drawing.append(CutPntDraw(parent=self, point_raw=pt))
            
        # 🛡️ L'EMBARQUEMENT : L'objet Plaquette est vissé sur ce burin
        self.insert = insert_manager_obj
        print(f"DEBUG tool ident: {self.ident} OK")

        # 🚀 ÉTAT DU CRAN ACTIF EN RAM (0 = Position par défaut, 1 = Position volante)
        # Déterminé automatiquement au démarrage selon le booléen validé dans le JSON
        self.idx_cran_actif = self.obtenir_index_cran_valide_origine()

        # ⚡ CACHES VISUELS RAM (Évite les accès dictionnaires lourds à 60Hz dans l'IHM)
        self.cached_tool_icon = ""         # Chemin du PNG de forme de l'outil (C1, C2...)
        self.cached_offset_dro_icon = ""   # Chemin du PNG de la tangente DRO (0_centre, gauche...)
        
        # Premier calcul des caches au chargement de l'objet
        self.rafraichir_les_caches_visuels()

    def obtenir_index_cran_valide_origine(self) -> int:
        """ Parcourt le JSON à l'initialisation pour trouver quel cran est actif (True) """
        try:
            if self.crant_idexage[1][1] is True:
                return 1
        except IndexError:
            pass
        return 0

    def select_tourelle(self, dict_used: dict):
        #self. ... = dict_used[...]

        pass

    def changer_cran_multifix(self, index_recu: int):
        """
        🎯 SÉCURITÉ MÉTIER : Change l'indexation physique de la tourelle Multifix.
        Si l'index est connu (Défaut ou Volant existant), on l'active.
        Si l'index est NOUVEAU, on écrase la position volante, on invalide tous les homings (False) 
        et on force l'opérateur à recalibrer.
        """
        idx_multifix = int(index_recu)
        
        # 1. Est-ce que ça correspond à la position par défaut (Index 0) ?
        if self.crant_idexage[0][0] == idx_multifix:
            self.idx_cran_actif = 0
            self.rafraichir_les_caches_visuels()
            return

        # 2. Est-ce que ça correspond à la position volante déjà stockée (Index 1) ?
        if self.crant_idexage[1][0] == idx_multifix:
            self.idx_cran_actif = 1
            self.rafraichir_les_caches_visuels()
            return

        # 3. 🚨 SÉCURITÉ : Index inconnu ! On écrase la position volante et on INVALIDE TOUT
        self.crant_idexage[1] = [idx_multifix, False]
        self.cadran_dro[1] = [0, 0, False]
        self.offset_probe[1] = [0, 0, False]
        self.offset_machine[1] = [0, 0, False]
        self.offset_correction[1] = [0, 0, False]
        
        # On bascule l'outil sur ce cran volant non calibré
        self.idx_cran_actif = 1
        self.modified_not_save = True
        
        # Mise à jour des icônes (qui passera l'affichage en mode Alerte/Non calibré)
        self.rafraichir_les_caches_visuels()
        print(f"⚠️ Outil {self.ident} déplacé sur un cran Multifix inconnu ({idx_multifix}). Calibration requise !")

    def rafraichir_les_caches_visuels(self):
        """ Calcule et fige les chemins d'images en RAM pour cet outil précis """
        # 1. Icône de forme de l'outil (C1, C2, C3...)
        self.cached_tool_icon = self.get_icone_cadran()
        
        # 2. Sécurité : Vérification si le cran en cours d'utilisation est validé
        cran_est_valide = self.crant_idexage[self.idx_cran_actif][1]
        dro_est_valide = self.cadran_dro[self.idx_cran_actif][2]
        
        if not cran_est_valide or not dro_est_valide:
            # Si le cran ou le choix DRO n'est pas validé, icône d'alerte spécifique
            self.cached_offset_dro_icon = "bitmaps/tool_attention_uncalibrated.png"
            return

        # 3. Icône dynamique de la tangente DRO [Z, X] pour le badge bordeaux
        active_cadran = self.cadran_dro[self.idx_cran_actif]
        z_mode = active_cadran[0]  # 0=centre, 1=gauche, 2=droite
        x_mode = active_cadran[1]  # 0=centre, 1=haut, 2=bas
        
        chemin_icone_dro = f"bitmaps/tool_{z_mode}_{x_mode}.png"
        if os.path.exists(chemin_icone_dro):
            self.cached_offset_dro_icon = chemin_icone_dro
        else:
            self.cached_offset_dro_icon = "bitmaps/tool_0_centre.png"

    def obtenir_angle_tourelle_reel(self, machine_config: dict) -> float:
        """
        Lit l'index de cran physique actif et extrait l'angle mécanique réel (0°, 18°, 36°...)
        défini dans la configuration de la machine.
        """
        index_physique = self.crant_idexage[self.idx_cran_actif][0]
        liste_angles_machine = machine_config.get("index_multi_fix", [])
        
        try:
            return float(liste_angles_machine[index_physique])
        except IndexError:
            return 0.0

    def get_draw_pnt_brut(self) -> list:
        """
        📐 EXTRACTEUR CAO : Parcourt la liste d'objets points distincts
        et extrait une liste de coordonnées plates [[Z, X], r] pour le canvas Kivy.
        """
        return [p.brut_pos for p in self.drawing]

    def get_icone_cadran(self) -> str:
        """
        🎯 SÉLECTEUR D'ICÔNES DE FORME (BURIN CORPS) :
        Lit la valeur numérique de self.cadran_icone et renvoie le PNG transparent associé.
        """
        table_icones = {
            1: "bitmaps/burin_C1.png",
            2: "bitmaps/burin_C2.png",
            3: "bitmaps/burin_C3.png",
            4: "bitmaps/burin_C4.png",
            0: "bitmaps/burin_C4.png",
            0.5: "bitmaps/burin_C05.png",
            4.5: "bitmaps/burin_C05.png",
            1.5: "bitmaps/burin_C15.png",
            2.5: "bitmaps/burin_C25.png",
            3.5: "bitmaps/burin_C35.png"
        }

        try:
            valeur_numerique = float(self.cadran_icone) 
            if valeur_numerique.is_integer():
                cle_recherche = int(valeur_numerique)
            else:
                cle_recherche = valeur_numerique
        except (ValueError, TypeError):
            cle_recherche = 4

        chemin_cible = table_icones.get(cle_recherche, "bitmaps/burin_select.png")
        if os.path.exists(chemin_cible):
            return chemin_cible
        return "bitmaps/burin_select.png"


class OLD_CutterLib:
    """
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
                "ident_mount": "Etalon",
                "name": "COMPARATEUR_MAITRE",
                "cadran_icone": 5,
                "idx_mount": [[0, False, 0],[0, False, 0]],
                "cadran_dro": [[0, 0, False],[0, 0, False]],  "angle_machine": 0,
                "ofst_probbe": [[0, 0, False],[0, 0, False]],
                "ofst_machine": [[0, 0, False],[0, 0, False]],
                "ofst_corr": [[0, 0, False], [0, 0, False]],
                "body": {
                    "clearance":[0,0],
                    "lead_angle": 0,
                    "lead_reverse": False,
                    "points": [
                        [[0, 0], 1000],
                        [[1000, 0], 1000],
                        [[1000, 1000], 1000],
                        [[0, 1000], 1000]
                    ]
                }
            }
            self.save_library()

        self.cutters.clear()    # Phase de reconstruction de vos objets réels parents-enfants
        
        for t_id, t_data in self.library["cutt_tool"].items():
            id_ins = str(t_data.get("ident_insert", "0"))    # Résolution de l'insert lié via votre dictionnaire croisé rapide de l'insert_lib
            test_index_insert= self.insert_lib.get_idx_to_ident.get(id_ins)
            obj_insert_manager = self.insert_lib.get_idx_to_ident.get(
                id_ins, 
                self.insert_lib.get_idx_to_ident.get("0") # Repli de sécurité
            )
            
            str_ident = str(t_id)    #  On force l'identifiant à rester un STR pur d'un bout à l'autre !
            
            # Création du CutterManager individuel en lui passant son identifiant texte
            new_cutter_manager = CutterManager(self, str_ident, t_data, obj_insert_manager)
            self.cutters.append(new_cutter_manager)

        # 🟢 LE TRI NUMÉRIQUE AVEC L'ASTUCE DU TRANSTYPAGE :
        # On garde 'cm.ident' sous forme de texte en RAM, mais on dit à la lambda de le convertir temporairement en int uniquement pour faire le tri !
        # Cela évite que l'outil "10" ne se retrouve trié avant l'outil "2" par ordre alphabétique.
        self.cutters.sort(key=lambda cm: int(cm.ident))

        # Définition de l'outil actif par défaut (ex: le premier de la liste triée)
        if self.cutters:
            self.active_cutter = self.cutters[0]

    def save_library(self):
        """ Enregistre la bibliothèque cutt_tool sur le disque avec formatage humain """
        # Définition précise du comportement de chaque clé selon ton script
        cles_de_compactage = [
            ("idx_mount", True),      # True -> Tout sur une seule ligne
            ("idx_dro", True),        # True -> Tout sur une seule ligne
            ("ofst_probbe", True),      # True -> Tout sur une seule ligne (attention à l'orthographe du JSON)
            ("ofst_machine", True),     # True -> Tout sur une seule ligne
            ("ofst_corr", True),  # True -> Tout sur une seule ligne
            ("clearance", True),          # True -> Tout sur une seule ligne [0, 0]
            ("points", False)             # False -> Découpé par point, un point par ligne !
        ]
        
        try:
            # Appel de ta fonction personnalisée
            save_json_with_format(
                filepath=self.filepath,
                data=self.library,
                compact_keys=cles_de_compactage,
                #compact_keys=[("points", False)],
                indent=4
            )
            self.lib_not_save = False  # On remet le flag à False puisque c'est sur le disque
            print("⚙️ DRO [CutterLib] : Fichier JSON sauvegardé avec formatage personnalisé.")
            
        except Exception as e:
            print(f"⚙️ DRO [CutterLib Error] : Échec écriture JSON formaté ({e})")

    def add_cutter(self) -> str:
        """ 🎯 CREATION DE BURIN : Recherche de trou numérique libre et duplication étanche """
        import copy
        
        existing_idents = [int(cm.ident) for cm in self.cutters]    # On extrait les identifiants sous forme d'entiers uniquement pour calculer le prochain numéro

        next_num = 1
        while next_num in existing_idents or next_num == 199:
            next_num += 1
            
        str_ident = str(next_num)
        
        # Duplication et configuration du dictionnaire brut dans la DB de la lib
        from cutting_tool.cut_manager import DEF_CUTTER_JSON 
        nouveau_burin_raw = copy.deepcopy(DEF_CUTTER_JSON)
        
        nouveau_burin_raw["ident"] = str_ident
        nouveau_burin_raw["name"] = f"Burin_N°{str_ident}"

        self.library["cutt_tool"][str_ident] = nouveau_burin_raw

        # Re-tri et re-génération automatique de la DB vers le dictionnaire ordonné numériquement
        self.library["cutt_tool"] = dict(sorted(self.library["cutt_tool"].items(), key=lambda item: int(item[0])))

        self.save_library()
        self.load_library() # Étape capitale : re-peuple la liste d'objets réels à jour en RAM !
        return str_ident

    def get_index_to_ident(self, target_ident: str) -> int:
        """
        Parcourt la liste triée des burins et renvoie l'index numérique réel (0, 1, 2...) correspondant à l'identifiant textuel recherché.
        Retourne -1 si l'identifiant n'existe pas.
        """
        str_ident = str(target_ident)

        try:        # Sécurité pour la recherche par tranche rapide
            valeur_num = int(str_ident)
        except ValueError:
            valeur_num = 0

        if valeur_num < len(self.cutters):
            min_idx = max(valeur_num - 4, 0)
            max_idx = min(valeur_num + 2, len(self.cutters))
            # Recherche Rapide des index autour de l'ident
            for tranche_idx, cutter_manager in enumerate(self.cutters[min_idx:max_idx]):
                if cutter_manager.ident == str_ident:
                    return min_idx + tranche_idx
                
        # COMPLETTE DE SECOURS (Filet de sécurité absolu, gère l'outil 199 parfaitement)
        for index, cutter_manager in enumerate(self.cutters):
            if cutter_manager.ident == str_ident:
                return index
            
        return -1

    #def select_idx_tourelle(self, choix="def"):
        #if choix == "vol":
            #dict_send = copy.deepcopy(self. ...[tourelle_def])
            #dict_send["actif"] = "vol"  # On ajoute la référance pour que l'outil sachent ou enregistrer les futures changements
        #else:
            #dict_send = copy.deepcopy(self. ...[tourelle_def])
            #dict_send["actif"] = "def"

        #self.active_cutter.select_tourelle(dict_used= dict_send)



########################################################################
##### NEW ################## NEW ############################# NEW #####
########################################################################


# =====================================================================
# 👑 1. LE GESTIONNAIRE SUPRÊME : CUTTERLIB
# =====================================================================
class CutterLib(EventDispatcher):
    """
    CONTRÔLEUR CENTRAL : Gère la liste des outils en RAM, le chargement/sauvegarde
    du JSON et stocke l'unique Snapshot éphémère de secours de la session.
    """
    # Pointeur dynamique réactif lu par toutes les pages de l'IHM (DRO, CAO...)
    active_cutter = ObjectProperty(None, allownone=True)
    # Drapeau global pour savoir si le fichier disque est désynchronisé
    lib_not_save = BooleanProperty(False)

    def __init__(self, insert_lib_instance, lib_filename="cut_lib.json", **kwargs):
        super().__init__(**kwargs)
        self.filepath = os.path.join(os.path.dirname(__file__), lib_filename)
        self.insert_lib = insert_lib_instance # Lien direct vers la lib des plaquettes
        
        self.cutters: list[CutterManager] = [] # La grande famille des outils en RAM
        self.active_cutter  = None             # Lien vers le CutterManager() actif
        self.act_cut_idx_tourelle = -1    # L'index réel de la position MlutiFix
        self.active_cutter_idx_mount = "vol"
        self.act_cut_valide_mount = False
        self.active_cutter_backup_dict = None  # 🎯 LE CASIER UNIQUE ÉPHÉMÈRE DE SECOURS
        self.lib_not_save = False

        self.list_holder = []   # Liste des blocs porte-outil existants (juste leur identifiant)

        self.load_library()

    def load_library(self):
        """ Lit le fichier JSON et donne naissance aux objets CutterManager """
        if not os.path.exists(self.filepath):
            # Si le fichier n'existe pas, on initialise une structure vide sécurisée
            print(f"⚠️ [CutterLib] Fichier introuvable. Création d'une base vide.")
            initial_data = {"cutt_holders": [], "cutt_tool": {}}
        else:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                initial_data = json.load(f)

        dict_outils = initial_data.get("cutt_tool", {})
        list_tool_holders = initial_data.get("cutt_holders", {})
        self.list_holder = list_tool_holders
        self.cutters.clear()

        # Instanciation de chaque outil
        for t_id, data_outil in dict_outils.items():
            # On va chercher l'objet Plaquette associé s'il existe
            id_insert = data_outil.get("ident_insert", "0")
            insert_obj = self.insert_lib.get_insert(id_insert) if hasattr(self.insert_lib, 'get_insert') else None
            
            # Naissance de l'outil (Init épuré)
            nouvel_outil = CutterManager(parent_lib=self, tool_ident=t_id, insert_manager_obj=insert_obj)
            # Armement des variables via la fonction dédiée
            nouvel_outil.build_from_json(data_outil)
            self.cutters.append(nouvel_outil)

        # Sécurité : Si la liste est vide, on force la présence de l'outil Maître 199
        if not any(o.ident == "199" for o in self.cutters):
            self.creer_outil_maitre_199()

        # Au démarrage, on charge l'outil par défaut (ex: le premier de la liste ou le 199)
        #self.charger_outil_sur_le_tour("199")
        self.lib_not_save = False

    def creer_outil_maitre_199(self):
        """ Génère l'outil étalon obligatoire de l'application """
        maitre_dict = {
            "ident": "199", "ident_insert": "0", "ident_mount": "Etalon",
            "name": "COMPARATEUR_MAITRE", "cadran_icone": 5,
            "tourelle_def": {
                "idx_mount": [0, True], "idx_dro": [0, 0, True], "angle_machine": 0,
                "ofst_probbe": [0, 0, True], "ofst_machine": [0, 0, True], "ofst_corr": [0, 0, True]
            },
            "tourelle_vol": {
                "idx_mount": [0, False, 0], "idx_dro": [0, 0, False], "angle_machine": 0,
                "ofst_probbe": [0, 0, False], "ofst_machine": [0, 0, False], "ofst_corr": [0, 0, False]
            },
            "body": {"clearance":[0,0], "lead_angle": 0, "lead_reverse": False, "points": []}
        }
        maitre = CutterManager(parent_lib=self, tool_ident="199")
        maitre.build_from_json(maitre_dict)
        self.cutters.append(maitre)

    def set_cutter_active(self, identifiant_outil: str, mount_idx= 0, grp_offset= None, validate=None):
        """ Commute le pointeur central réactif vers le nouvel outil choisi """

        app = App.get_running_app()

        idx = self.get_index_to_ident(identifiant_outil)
        if idx == -1: 
            return

        self.active_cutter = self.cutters[idx]

        self.act_cut_idx_tourelle = mount_idx
        #self.act_cut_angle_mont = angle_mont

        '''
        if grp_offset is None:
            #tot_angle = app.offset_page_instance.tourelle_angle[0] + MACHINE_CONFIG["index_multi_fix"][mount_idx]
            tot_angle = self.act_cut_angle_mont
            ofst_def_angle = self.active_cutter.config_defaut["angle_machine"]
            if tot_angle == ofst_def_angle:
                #self.act_cut_grp_ofst = "def"
                pass
            else:
                #self.act_cut_grp_ofst = "vol"
                pass
        elif grp_offset == "vol":
            #self.act_cut_grp_ofst = "vol"
            pass
        else:
            #self.act_cut_grp_ofst = "def"
            pass'''

        self.active_cutter.set_grp_offset(grp_offset, validate)
        
        # 📸 PRISE DE LA PHOTO DE SECOURS DE DEBUT DE SESSION
        self.active_cutter_backup_dict = copy.deepcopy(self.active_cutter.generer_snapshot())
        print(f"🔄 [CutterLib] Pointeur branché sur l'outil N°{self.active_cutter.ident}. Snapshot verrouillée.")

    def annuler_les_modifications_outil_actif(self):
        """ Bouton Annuler : Force l'outil à recharger sa photo de secours """
        if not self.active_cutter or not self.active_cutter_backup_dict: 
            return
            
        # Re-construction à partir du dictionnaire de secours
        self.active_cutter.build_from_json(self.active_cutter_backup_dict["data_json"])
        self.active_cutter.idx_cran_actif = self.active_cutter_backup_dict["meta_idx_cran_actif"]
        self.active_cutter.modified_not_save = False
        print(f"⏪ [CutterLib] Annulation validée. Outil N°{self.active_cutter.ident} restauré.")

    def save_library(self):
        """ Reconstruit l'intégralité du JSON depuis la RAM vivante et écrit sur le disque """
        dictionnaire_disque = {"cutt_tool": {}}
        
        for outil in self.cutters:
            dictionnaire_disque["cutt_tool"][outil.ident] = outil.exporter_en_dictionnaire()
            outil.modified_not_save = False # L'outil redevient propre
            
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(dictionnaire_disque, f, indent=4, ensure_ascii=False)
            
        self.lib_not_save = False
        print("💾 [CutterLib] Base de données écrite et synchronisée sur le disque.")

    def get_index_to_ident(self, identifiant: str) -> int:
        """ Utilitaire pour trouver la position d'un outil dans la liste """
        for index, o in enumerate(self.cutters):
            if str(o.ident) == str(identifiant): 
                return index
        return -1


# =====================================================================
# 📦 2. L'OBJET MÉTIER INDIVIDUEL : CUTTERMANAGER
# =====================================================================
class CutterManager(EventDispatcher):
    """
    MODÈLE DE L'OUTIL : Représente un burin unique en RAM. Contient ses deux
    dictionnaires tourelle_def/tourelle_vol et sait évaluer son état par rapport au backup.
    """
    # Propriété Kivy pour notifier l'IHM en temps réel des changements
    #dict_modifs = DictProperty({}) # Dictionnaire des modifications
    modified_not_save = BooleanProperty(False)

    def __init__(self, parent_lib, tool_ident: str, insert_manager_obj=None, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent_lib
        self.ident = str(tool_ident)
        self.insert = insert_manager_obj
        self.modified_not_save = False # Initialisation propre au repos
        self.dict_modifs = {}

        # Déclaration à vide des tiroirs
        self.name = ""
        self.tool_mount = ""
        self.cadran_icone = 5
        self.idx_0_dro = [0,0,"bitmaps/tool_offset_0_0.png"]
        self.config_defaut = {}
        self.config_volante = {}
        self.grp_offset = self.config_defaut    # Lien directe vers le groupe sélectionné (défaud vs. volant)
        
        self.clearance = [0, 0]
        self.lead_angle = 0
        self.lead_reverse = False
        self.draw_pnt = []
        
        # État de la session (0 = Position Défaut active, 1 = Position Volante active)
        self.idx_cran_actif = 0

        self.initialiser_registre_auto_description()

    def build_from_json(self, data_json: dict):
        """ Dépaquète et arme la RAM avec les vraies cotes du dictionnaire """
        self.name = data_json.get("name", f"Burin_N°{self.ident}")
        self.tool_mount = data_json.get("ident_mount", "")
        self.cadran_icone = data_json.get("cadran_icone", 5)
        self.idx_0_dro = data_json.get("idx_dro", [0,0,"bitmaps/tool_offset_0_0.png"])
        
        # Chargement de tes deux sous-dictionnaires explicites !
        self.config_defaut = data_json.get("tourelle_def", {})
        self.config_volante = data_json.get("tourelle_vol", {})
        
        body = data_json.get("body", {})
        self.clearance = body.get("clearance", [0, 0])
        self.lead_angle = body.get("lead_angle", 0)
        self.lead_reverse = body.get("lead_reverse", False)
        
        # Points CAO du manche (Tu adapteras avec ta classe de points)
        self.draw_pnt = []
        for pt in body.get("points", []):
            self.draw_pnt.append(CutPntDraw(self,pt))
        
        # Choix automatique du cran d'origine selon la validation du JSON
        if self.config_volante.get("idx_mount", [0, False, 0])[1] is True:
            self.idx_cran_actif = 1
        else:
            self.idx_cran_actif = 0

    def initialiser_registre_auto_description(self):
        """
        🗺️ LA CARTE D'IDENTITÉ UNIVERSELLE DE L'OUTIL (V_7.7)
        Centralise l'intégralité des pointeurs RAM, chemins JSON, 
        étiquettes de clés .kv et traductions de l'atelier.
        Format : [ Clé_KV_Flat, Liste_Etages_JSON, Libellé_Opérateur, Nom_Attribut_RAM ]
        """
        self.registre_metier = [
            ["ident", ["ident"], "Identifiant Unique", "ident"],
            ["name", ["name"], "Nom du Burin", "name"],
            ["ident_mount", ["ident_mount"], "Support Porte-Outil (Holder)", "tool_mount"],
            ["ident_insert", ["ident_insert"], "Code Plaquette Amovible", "insert_id_str"], # (ou une lambda si besoin)
            ["cadran_icone", ["cadran_icone"], "Orientation Silhouette Graphique", "cadran_icone"],
            
            ["tourelle_def", ["tourelle_def"], "Pack Géométrique (Position par Défaut)", "config_defaut"],
            ["tourelle_vol", ["tourelle_vol"], "Pack Géométrique (Position Volante)", "config_volante"],
            
            ["body.clearance", ["body", "clearance"], "Angles de Dépouille (Clearance)", "clearance"],
            ["body.lead_angle", ["body", "lead_angle"], "Angle d’Attaque (Lead Angle)", "lead_angle"],
            ["body.lead_reverse", ["body", "lead_reverse"], "Inversion du sens de coupe", "lead_reverse"],
        ]


    def generer_snapshot(self) -> dict:
        """ Renvoie le paquet complet [Session IHM + Cotes Disque] pour le coffre-fort """
        return {
            "meta_idx_cran_actif": int(self.idx_cran_actif),
            "data_json": self.exporter_en_dictionnaire()
        }

    def exporter_en_dictionnaire(self) -> dict:
        """ Compile les variables vivantes pour fabriquer la ligne JSON propre """
        return {
            "ident": str(self.ident),
            "ident_insert": str(self.insert.ident if self.insert else "0"),
            "ident_mount": str(self.tool_mount),
            "name": str(self.name),
            "cadran_icone": int(self.cadran_icone),
            "tourelle_def": self.config_defaut,
            "tourelle_vol": self.config_volante,
            "body": {
                "clearance": self.clearance,
                "lead_angle": self.lead_angle,
                "lead_reverse": self.lead_reverse,
                "points": self.get_draw_pnt_to_json()
            }
        }

    def OLD_get_modif_data(self):
        last = self.parent.active_cutter_backup_dict["data_json"]

        if last["ident"]!= str(self.ident): self.tracker_modif(str(self.ident), ["ident"])
        if last["ident_insert"]!= str(self.insert.ident if self.insert else "0"):
            self.tracker_modif(str(self.insert.ident if self.insert else "0"), ["ident_insert"])
        if last["ident_mount"]!= str(self.tool_mount): self.tracker_modif(str(self.tool_mount), ["ident_mount"])
        if last["name"] != str(self.name): self.tracker_modif(str(self.name), ["name"])
        if last["cadran_icone"] != int(self.cadran_icone): self.tracker_modif(int(self.cadran_icone), ["cadran_icone"])
        if last["tourelle_def"] != self.config_defaut: self.tracker_modif(self.config_defaut, ["tourelle_def"])
        if last["tourelle_vol"] != self.config_volante: self.tracker_modif(self.config_volante, ["tourelle_vol"])
        #"body": {
        if last["body"]["clearance"] != self.clearance: self.tracker_modif(self.clearance, ["body", "clearance"])
        if last["body"]["lead_angle"] != self.lead_angle: self.tracker_modif(self.lead_angle, ["body", "lead_angle"]) 
        if last["body"]["lead_reverse"] != self.lead_reverse: self.tracker_modif(self.lead_reverse, ["body", "lead_reverse"])
        if last["body"]["points"] != self.get_draw_pnt_to_json(): self.tracker_modif(self.get_draw_pnt_to_json(), ["body", "points"])
    def get_modif_data(self):
        """ 
        🔍 L'INSPECTEUR UNIVERSEL EN BOUCLE AUTOMATIQUE
        Parcourt le registre d'auto-description, compare la RAM avec le JSON,
        et lève le tracker chirurgical de manière totalement dynamique !
        """
        if not self.parent or not self.parent.active_cutter_backup_dict:
            return
            
        last = self.parent.active_cutter_backup_dict["data_json"]

        # 🚀 LA BOUCLE MAGIQUE :
        for cle_kv, liste_etages, libelle, nom_attribut in self.registre_metier:
            
            # 1. On va cueillir dynamiquement la valeur vivante dans la RAM de l'outil
            val_actuelle = getattr(self, nom_attribut)
            
            # 2. On va chercher dynamiquement la valeur correspondante dans la photo JSON
            val_last_back = last
            for etage in liste_etages:
                val_last_back = val_last_back[etage]
                
            # 3. Comparaison instantanée ! Si déviation, on appelle ton tracker infaillible !
            if val_actuelle != val_last_back:
                self.tracker_modif(val_actuelle, liste_etages)
                
        # 🎯 CAS SPÉCIFIQUE DES POINTS CAO (qui demande ton getter de conversion)
        if last["body"]["points"] != self.get_drawing_to_json():
            self.tracker_modif(self.get_drawing_to_json(), ["body", "points"])

    def tracker_modif(self, val_actuelle, nom_argument: list):
        """
        🎯 LE TRACKER SOUVERAIN (Ton idée à toute épreuve !)
        Gère le registre des modifications champ par champ.
        """

        # On construit le chemin vers la photo d'ouverture
        path_last = self.parent.active_cutter_backup_dict["data_json"]
        for etage in nom_argument[:-1]:        # La descente des étages
            path_last = path_last[etage] # Ici path_last devient path_last["body"]                        
        cle_finale = nom_argument[-1] # Ici cle_finale devient "clearance" 

        val_last_back = copy.deepcopy(path_last[cle_finale])

        # POUR LE CARNET DE MODIFICATIONS
        name_arg = ".".join(nom_argument)    # On transforme la liste ["body", "clearance"] en un seul mot de texte : "body.clearance"

        if val_actuelle != val_last_back:
            if name_arg not in self.dict_modifs:
            # CAS 1 : L'argument a dévié de sa valeur d'origine
                # S'il n'est pas encore dans notre registre, c'est que val_last_back est égale au json
                self.dict_modifs[name_arg] = val_last_back
                #print(f"📝 [Tracker] Clé '{nom_argument}' modifiée. Valeur originale sauvegardée.")

            else:
                if self.dict_modifs[name_arg] == val_actuelle:
                # CAS 2 : L'opérateur a remis la valeur d'origine
                    # On le retire du registre puisqu'il est revenu à l'état du JSON !
                    del self.dict_modifs[name_arg]

                    # On ré-aligne la photo avec la valeur original pour le prochain contrôle
                    path_last[cle_finale] = copy.deepcopy(val_actuelle)

                    print(f"🧹 [Tracker] Clé '{nom_argument}' revenue à l'origine, retirée du registre.")
                else:
                # CAS 3 : Il a de-nouveau modifié la valeur sans remettre la valeur d'origine
                    pass    # On fait rien la valeur dans le dict reste celle de son premier ajout (celle du json)

        # 📊 VERDICT : Si le dictionnaire contient des clés, l'outil est modifié !
        self.modified_not_save = (len(self.dict_modifs) > 0)

    def reload_argument(self, nom_argument: list):
        """
        Recharger un argument à ça valeur json:
            arg: son emplacement dans le json 

            return la valeur (+ màj de la photo)
        """

        # On construit le chemin vers la photo d'ouverture
        path_last = self.parent.active_cutter_backup_dict["data_json"]
        for etage in nom_argument[:-1]:        # La descente des étages
            path_last = path_last[etage] # Ici path_last devient path_last["body"]                        
        cle_finale = nom_argument[-1] # Ici cle_finale devient "clearance" 

        # POUR LE CARNET DE MODIFICATIONS
        name_arg = ".".join(nom_argument)    # On transforme la liste ["body", "clearance"] en un seul mot de texte : "body.clearance"

        if name_arg in self.dict_modifs:
            original_val = self.dict_modifs[name_arg]
            path_last[cle_finale] = copy.deepcopy(original_val)
            del self.dict_modifs[name_arg]
            # Si le dictionnaire contient pas de clé, l'outil n'est pas modifié !
            self.modified_not_save = (len(self.dict_modifs) > 0)

        return copy.deepcopy(path_last[cle_finale])

    def set_grp_offset(self, ofst_grp= None, valide=None):
        ''' Màj du groupe d'offsets selon choix d'indexage de la tourelle (défaud vs. volant),
            sans recharge compette de l'outil
        '''
        if ofst_grp is None: ofst_grp = self.parent.active_cutter_idx_mount
        if valide is None: valide = self.parent.act_cut_valide_mount

        if ofst_grp == "vol":
            self.parent.active_cutter_idx_mount = "vol"
            self.parent.act_cut_valide_mount = valide
            self.grp_offset = self.config_volante
        else:
            self.parent.active_cutter_idx_mount = "def"
            self.parent.act_cut_valide_mount = valide
            self.grp_offset = self.config_defaut

    def get_icone_cadran(self) -> str:
        """
        🎯 SÉLECTEUR D'ICÔNES DE FORME (BURIN CORPS) :
        Lit la valeur numérique de self.cadran_icone et renvoie le PNG transparent associé.
        """
        table_icones = {
            1: "bitmaps/burin_C1.png",
            2: "bitmaps/burin_C2.png",
            3: "bitmaps/burin_C3.png",
            4: "bitmaps/burin_C4.png",
            0: "bitmaps/burin_C4.png",
            0.5: "bitmaps/burin_C05.png",
            4.5: "bitmaps/burin_C05.png",
            1.5: "bitmaps/burin_C15.png",
            2.5: "bitmaps/burin_C25.png",
            3.5: "bitmaps/burin_C35.png"
        }

        try:
            valeur_numerique = float(self.cadran_icone) 
            if valeur_numerique.is_integer():
                cle_recherche = int(valeur_numerique)
            else:
                cle_recherche = valeur_numerique
        except (ValueError, TypeError):
            cle_recherche = 4

        chemin_cible = table_icones.get(cle_recherche, "bitmaps/burin_select.png")
        if os.path.exists(chemin_cible):
            return chemin_cible
        return "bitmaps/burin_select.png"

    def get_draw_pnt_to_json(self) -> list:
        """ Renvoie la liste brute des coordonnées [X, Z] pour le JSON ou la comparaison """
        exporter_point= []
        for pt in self.draw_pnt:
            exporter_point.append([pt.brut_pos, pt.radius_base])
        return exporter_point


