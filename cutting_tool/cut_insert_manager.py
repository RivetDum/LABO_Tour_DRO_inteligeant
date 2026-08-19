# cutting_tool/ cut_insert_manager.py

import os
import json
import copy

class CutInsertPntDraw:
    """
    Gestion complète et autonome d'un point géométrique de plaquette.
    Reçoit son manager parent pour pouvoir naviguer et appliquer l'offset_mount.
    """
    def __init__(self, parent, point_raw: list):
        self.parent = parent  # 🔗 Pointeur direct vers CutInsertManager (Navigation Parent-Enfant)
        
        # A. Les composants bruts issus de la base de données (microns)
        # point_raw est sous le format plat du JSON : [hor, vert, rayon_bec]
        self.brut_pos = [point_raw[0], point_raw[1]]
        self.radius_base = point_raw[2]
        
        # B. La coordonnée nette FAO calculée (0,0 insert + offset_mount de l'insert)
        # On va chercher l'offset directement chez le parent grâce au maillon !
        self.net_pos = [
            self.brut_pos[0] + self.parent.offset_mount[0],
            self.brut_pos[1] + self.parent.offset_mount[1]
        ]
        
        # Indicateur d'état pour le rafraîchissement graphique Kivy
        self.modified_data = True

    # --- (Les futures fonctions de conversion basées sur config.py viendront ici) ---

class CutInsertManager:
    """
    GÈRE UNE PLAQUETTE UNIQUE (ex: CCMT09).
    Contient l'identité de l'insert et sa liste d'objets points distincts.
    """
    def __init__(self, parent_lib, insert_ident: str, raw_dict: dict):
        self.ident = str(insert_ident)
        self.raw = raw_dict
        self.parent = parent_lib  # 🔗 Pointeur vers la bibliothèque globale CutInsertLib
        
        self.name = raw_dict.get("name", "Sans nom")
        self.desc = raw_dict.get("desc", "")
        self.offset_mount = raw_dict.get("offset_mount", [0.0, 0.0])
        
        # 🚀 LA LOGIQUE EN LISTE D'OBJETS RÉELS :
        self.drawing: list[CutInsertPntDraw] = []
        
        # Peuplage automatique de la géométrie en instanciant la classe distincte
        for pt in raw_dict.get("points", []):
            if len(pt) == 3:
                # On passe 'self' (l'instance de CutInsertManager) comme parent du point
                self.drawing.append(CutInsertPntDraw(parent=self, point_raw=pt))

    def extraire_profil_pour_kivy(self) -> list:
        """Renvoie le profil converti au format imbriqué [[hor, vert], r] pour le canvas."""
        return [[[p.brut_pos[0], p.brut_pos[1]], p.radius_base] for p in self.drawing]

    def exporter_en_dictionnaire(self) -> dict:
        """Re-compresse les objets points en listes plates pour la sauvegarde JSON."""
        points_plats = [[p.brut_pos[0], p.brut_pos[1], p.radius_base] for p in self.drawing]
        return {
            "name": self.name,
            "desc": self.desc,
            "points": points_plats,
            "offset_mount": self.offset_mount
        }


class CutInsertLib:
    """
    🎒 LE CATALOGUE CENTRALISÉ :
    Contient le fichier physique et pilote les ajouts/suppressions de plaquettes.
    """
    def __init__(self, lib_filename="cut_insert_lib.json"):
        self.filepath = os.path.join(os.path.dirname(__file__), lib_filename)
        self.library = {"cutt_profile": {}}
        
        # 🚀 La liste de vos managers ordonnée pour l'IHM / ScrollView
        self.inserts: list[CutInsertManager] = []
        
        # 🎯 Votre table d'indexation croisée rapide id -> Instance
        self.get_idx_to_ident = {}
        
        self.load_library()

    def load_library(self):
        """ Charge le JSON, force la présence de l'IDX 0 et instancie la RAM """
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.library = json.load(f)
            except Exception as e:
                print(f"⚙️ DRO [InsertLib Error] : Échec lecture JSON ({e})")
                self.library = {"cutt_profile": {}}
        else:
            self.library = {"cutt_profile": {}}

        # SÉCURITÉ ABSOLUE : Injection/Verrouillage de l'IDx "0" de secours immuable
        self.library["cutt_profile"]["0"] = {
            "name": "❌ NO_INSERT",
            "desc": "Profil de secours non éditable - Aucun insert monté",
            "points": [[0.0, 0.0, 1000.0]],
            "offset_mount": [0.0, 0.0]
        }
        
        # Phase de reconstruction de vos objets réels parents-enfants
        self.inserts.clear()
        self.get_idx_to_ident.clear()
        
        for ins_ident, ins_data in self.library["cutt_profile"].items():
            new_manager = CutInsertManager(self, ins_ident, ins_data)
            self.inserts.append(new_manager)
            self.get_idx_to_ident[ins_ident] = new_manager

        # Tri de votre liste d'affichage par ID numérique
        self.inserts.sort(key=lambda im: int(im.ident) if im.ident.isdigit() else 9999)

    def save_library(self):
        """ Enregistre la bibliothèque sur le disque """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.library, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚙️ DRO [InsertLib Error] : Échec écriture JSON ({e})")

    def new_insert_to_lib(self) -> str:
        """ Votre algorithme de recherche de trou numérique avec mise à disposition immédiate """
        items_bruts = self.library.get("cutt_profile", {}).items()
        liste_triee = sorted([(int(k), v) for k, v in items_bruts if k.isdigit()], key=lambda x: x[0])

        next_ident = 1
        index_insertion = 0
        for i, (ident_existant, _) in enumerate(liste_triee):
            if ident_existant == next_ident:
                next_ident += 1
                index_insertion = i + 1 
            elif ident_existant > next_ident:
                index_insertion = i
                break

        str_ident = str(next_ident)
        
        # Enregistrement brut dans le dictionnaire de base de données
        self.library["cutt_profile"][str_ident] = {
            "name": f"Plaquette_N°{str_ident}",
            "desc": "Ajouter une description",
            "points": [[0.0, 0.0, 1000.0]],
            "offset_mount": [0.0, 0.0]
        }

        self.save_library() 
        self.load_library()  # Reconstruit proprement la liste et le dictionnaire get_idx_to_ident
        return str_ident

    def delete_insert_from_lib(self, insert_ident) -> str:
        """ Supprime un insert et force le repli sécurisé vers l'IDx '0' """
        str_ident = str(insert_ident)
        if str_ident == "0":
            print("⚙️ DRO [InsertLib Refusal] : Impossible de supprimer l'insert de secours système.")
            return "0"

        if str_ident in self.library.get("cutt_profile", {}):
            self.library["cutt_profile"].pop(str_ident)
            
        self.save_library()
        self.load_library()
        return "0"

    def synchroniser_active_insert_dans_db(self, insert_manager_instance):
        """
        🎯 L'ENTONNOIR DE SYNCHRONISATION :
        Prend un objet CutInsertManager, extrait son active_insert, re-compresse 
        les points en format plat et met à jour le fichier JSON général.
        """
        tampon = insert_manager_instance.active_insert
        ins_ident = str(tampon.get("id", ""))

        if not ins_ident or ins_ident == "0":
            return False

        # Conversion inverse : [[hor, vert], r] -> [hor, vert, r]
        points_storage = []
        for pt in tampon["points"]:
            points_storage.append([pt[0][0], pt[0][1], pt[1]])

        # Écriture dans le dictionnaire de la DB
        self.library["cutt_profile"][ins_ident] = {
            "name": tampon["name"],
            "desc": tampon["desc"],
            "points": points_storage,
            "offset_mount": tampon["offset_mount"]
        }
        
        self.save_library()
        self.load_library() # Étape cruciale : recharge tout le monde en objets RAM frais !
        return True

    def get_index_to_ident(self, target_ident: str) -> int:
        """
        🎯 PASSERELLE IHM :
        Parcourt la liste triée des inserts et renvoie l'index numérique (0, 1, 2...)
        correspondant à l'ID recherché. Utile pour le Spinner ou ScrollView.
        Retourne -1 si l'ID n'existe pas.
        """
        str_ident = str(target_ident)
        # Recherche rapide. En supposant que seulement 3 plaquettes max sont supprimés sans être remplacer:
        min_idx = max(int(target_ident) - 4 , 0)
        max_idx = min(int(target_ident), len(self.inserts))
        for index, insert_manager in enumerate(self.inserts[min_idx:max_idx]):
            if str(insert_manager.ident) == str_ident:
                return index
        # Recherche complette si la rapide échoue
        for index, insert_manager in enumerate(self.inserts):
            if str(insert_manager.ident) == str_ident:
                return index
        # Valeur de replie si la recherche échoue
        return -1

    def get_all_insert_list(self) -> list[dict]:
        """
        Renvoie l'intégralité du catalogue d'inserts sous forme d'une liste 
        de dictionnaires neutres.
        """
        reponse = []
        
        for idx, ins in enumerate(self.inserts):
            # Sécurité de lecture du rayon de bec sur le premier point de l'insert
            rayon_micron = 1000  # Valeur de repli (1.0 mm) si la plaquette n'a pas de points
            if ins.drawing:
                rayon_micron = ins.drawing[0].radius_base

            line = {
                "idx": idx,
                "ident": ins.ident,
                "name": ins.name,
                "design": ins.desc,
                "radius": rayon_micron  # Stocké en microns bruts
            }
            reponse.append(line)
            
        return reponse
