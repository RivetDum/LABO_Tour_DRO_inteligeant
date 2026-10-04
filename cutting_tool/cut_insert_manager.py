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


class OLD_CutInsertLib:
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

        # Tri de votre liste d'affichage par Ident numérique
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

    def get_insert(self, indent_insert:str):

        idx_insert = self.get_index_to_ident(indent_insert)
        if idx_insert >=0:
            return self.inserts[idx_insert]

        return None

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
class CutInsertLib:
    """
    🎒 LE CATALOGUE CENTRALISÉ (Version Épurée - 100% Linéaire) :
    Contient les instances d'inserts et pilote le registre des normes d'atelier.
    """
    def __init__(self, lib_filename="cut_insert_lib.json"):
        self.filepath = os.path.join(os.path.dirname(__file__), lib_filename)
        
        # La liste ordonnée pour l'IHM, le tri et la recherche
        self.inserts: list[CutInsertManager] = []
        
        # Le registre des normes
        self.normes = {
            "ISO_TURNING": {"class_ptr": "IsoInserteCreator"},
            "NOT_NORMED": {"class_ptr": None}
        }
        
        self.load_library()

    def load_library(self):
        """ Charge le JSON, instancie la RAM et structure les normes """
        # dictionnaire temporaire local de chargement
        raw_data = {"cutt_profile": {}, "cutt_normes": {}}
        
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
            except Exception as e:
                print(f"⚙️ DRO [InsertLib Error] : Échec lecture JSON ({e})")

        # Fusion des normes du fichier
        if "cutt_normes" in raw_data:
            self.normes.update(raw_data["cutt_normes"])

        # Sécurité : Profil 0 de secours
        raw_data.setdefault("cutt_profile", {})["0"] = {
            "name": "❌ NO_INSERT",
            "desc": "Profil de secours non éditable - Aucun insert monté",
            "normed": {"systeme": "NOT_NORMED", "code": None, "not_customed_geometry": False, "pdf_associe": None},
            "points": [[0.0, 0.0, 1000.0]],
            "offset_mount": [0.0, 0.0]
        }
        
        # Phase de reconstruction linéaire
        self.inserts.clear()
        for ins_ident, ins_data in raw_data["cutt_profile"].items():
            self.inserts.append(CutInsertManager(self, ins_ident, ins_data))

        # Tri unique par Ident numérique
        self.inserts.sort(key=lambda im: int(im.ident) if im.ident.isdigit() else 9999)

        # 🔌 Mutation des chaînes en Classes vivantes (globals)
        for nom_norme, bloc_norme in self.normes.items():
            nom_classe_string = bloc_norme.get("class_ptr")
            if nom_classe_string and nom_classe_string in globals():
                bloc_norme["class_ptr"] = globals()[nom_classe_string]
            else:
                bloc_norme["class_ptr"] = None

        # Scan automatique des plaquettes de l'armoire (IFANGER, DIN...)
        for manager in self.inserts:
            systeme = str(manager.normed.get("systeme", "NOT_NORMED")).strip().upper()
            if systeme not in self.normes:
                print(f"📌 [InsertLib] Découverte automatique de la norme d'atelier : {systeme}")
                self.normes[systeme] = {"class_ptr": None}

    def get_index_to_ident(self, target_ident: str) -> int:
        """ 🎯 LA BOUCLE DE RECHERCHE UNIQUE (Légère et suffisante) """
        for idx, item in enumerate(self.inserts):
            if item.ident == str(target_ident):
                return idx
        return -1

    def save_library(self):
        """
        💾 GRAVURE SUR DISQUE (Version Épurée - Zéro doublon)
        Reconstruit le dictionnaire propre à partir des objets réels de la RAM
        et l'écrit proprement en UTF-8 dans ton fichier JSON.
        """
        print(f"💾 [InsertLib] Sauvegarde du catalogue d'inserts dans {self.filepath}...")
        
        # 1. On prépare la structure d'export vierge
        export_data = {
            "cutt_profile": {},
            "cutt_normes": {}
        }
        
        # 2. On exporte le dictionnaire de configuration des normes (en ré-inversant les pointeurs)
        for nom_norme, bloc_norme in self.normes.items():
            # On ne peut pas écrire une classe vivante Python dans un fichier texte JSON !
            # Donc si class_ptr est une variable/classe, on extrait son nom en string, sinon null.
            classe_vivante = bloc_norme.get("class_ptr")
            nom_string = classe_vivante.__name__ if classe_vivante else None
            
            # Si c'est une norme découverte automatiquement (sans chemin), on évite de polluer le JSON
            if nom_string is None and nom_norme != "NOT_NORMED":
                continue
                
            export_data["cutt_normes"][nom_norme] = {
                "class_ptr": nom_string
            }

        # 3. On extrait les données réelles de chaque insert en RAM
        for manager in self.inserts:
            # Sécurité : On n'enregistre jamais l'ID "0" de secours (il est ré-injecté au chargement !)
            if manager.ident == "0":
                continue
            
            # Chaque manager d'insert renvoie son dictionnaire de microns tout propre
            export_data["cutt_profile"][manager.ident] = manager.exporter_en_dictionnaire()

        # 4. Écriture physique sécurisée avec indentation pour la relecture humaine dans VS Code
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            print("🟢 [InsertLib] Catalogue d'inserts gravé avec succès !")
        except Exception as e:
            print(f"❌ [InsertLib Error] : Échec de l'écriture physique ({e})")

    def new_insert_to_lib(self) -> str:
        """ 
        🔍 ALGORITHME DU TROU NUMÉRIQUE (Version Épurée & Linéaire) :
        Parcourt les managers réels en RAM, trouve le premier ID libre (en ignorant le 0 de secours),
        instancie le nouvel insert, trie la RAM et sauvegarde sur disque.
        """
        # 1. On extrait et trie numériquement les identifiants réels des managers en RAM
        # On ne prend que les ID numériques et on ignore l'ID "0" pour notre calcul de trou
        id_existants = sorted([int(im.ident) for im in self.inserts if im.ident.isdigit() and im.ident != "0"])

        # 2. Recherche du premier trou dans la séquence (1, 2, 3...)
        next_ident = 1
        for ident_existant in id_existants:
            if ident_existant == next_ident:
                next_ident += 1
            elif ident_existant > next_ident:
                # On a trouvé un trou dans la liste ! (ex: on a 1, 2, puis directement 4)
                break
            # Le cas 'ident_existant < next_ident' que tu voulais forcer pour le 0
            # est mathématiquement déjà géré et ignoré grâce au tri initial préalable !

        str_ident = str(next_ident)
        
        # 3. Préparation du dictionnaire de naissance de la plaquette
        nouvelles_donnees = {
            "name": f"Plaquette_N°{str_ident}",
            "desc": "Ajouter une description",
            "normed": {
                "systeme": "NOT_NORMED", 
                "code": None,
                "not_customed_geometry": False,
                "pdf_associe": None # En Python on écrit None, il se transformera en null dans le fichier .json !
            },
            # On passe à 400 microns (0.4mm) standard d'atelier plutôt que 1mm (1000.0)
            # car c'est le rayon de bec le plus courant pour commencer à dessiner
            "points": [[0.0, 0.0, 400.0]], 
            "offset_mount": [0.0, 0.0]
        }

        # 4. Injection directe dans la RAM via ta fonction dédiée
        # (Elle crée le CutInsertManager, l'ajoute à self.inserts et retrie la liste)
        self.creer_nouvel_insert(str_ident, nouvelles_donnees)

        # 5. Gravure immédiate sur le disque dur
        self.save_library() 
        
        return str_ident

    def delete_insert_from_lib(self, target_ident: str) -> bool:
        """
        🗑️ MISE AU REBUT :
        Retire l'insert de la RAM. Sécurité absolue sur l'ID "0".
        """
        ident_propre = str(target_ident).strip()
        
        # Interdiction absolue de jeter l'insert de sécurité !
        if ident_propre == "0":
            print("🚨 [InsertLib] Action interdite : Impossible de supprimer l'insert de secours ID 0 !")
            return False

        idx = self.get_index_to_ident(ident_propre)
        if idx == -1:
            print(f"⚠️ [InsertLib] Impossible de supprimer l'insert ID {ident_propre} (Introuvable)")
            return False

        # Retrait de la liste linéaire
        self.inserts.pop(idx)
        print(f"🗑️ [InsertLib] Insert N°{ident_propre} supprimé de la RAM.")
        return True



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

        # Tri de votre liste d'affichage par Ident numérique
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
                ''' Ici je rajouterais pour l'ident 0 que l'on force:
            elif ident_existant < next_ident:
                continue
                '''
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



    def get_insert(self, indent_insert:str):

        idx_insert = self.get_index_to_ident(indent_insert)
        if idx_insert >=0:
            return self.inserts[idx_insert]

        return None

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
