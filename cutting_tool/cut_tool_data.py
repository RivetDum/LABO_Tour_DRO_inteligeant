# cutting_tool/ - cut_tool_data.py        # Modules fonctionnels liés au burin et au porte-outil
import os
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty, ObjectProperty, DictProperty
from kivy.metrics import dp
import copy
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
#import math
#from kivy.uix.widget import Widget
#from kivy.uix.popup import Popup
#from kivy.uix.gridlayout import GridLayout
#from kivy.uix.scrollview import ScrollView
#from kivy.uix.togglebutton import ToggleButton
#from kivy.uix.label import Label

Builder.load_file(os.path.join(os.path.dirname(__file__), "cut_tool_data.kv"))
#import common_draw as cdraw
from screen_base.common_screen import BaseScreenLayout  # Importation stricte de votre châssis universel
from cutting_tool.cutting_widgets import common_cut_tool as cut_tool
from cutting_tool import cut_insert_manager as ins_manager  #cutting_tool/cut_insert_manager.py
from configurator.config import MACHINE_CONFIG


class LignePointGrille(BoxLayout):
    index = NumericProperty(0)
    coord_x = NumericProperty(0.0)
    coord_y = NumericProperty(0.0)
    radius = NumericProperty(0.0)

    # Variable pour interdire l'écriture depuis le KV
    is_editable = BooleanProperty(True) 

    def notifier_modification(self, texte, champ):
        """
        Convertit la saisie du TextInput et la transmet à l'éditeur parent.
        Déclenché par 'on_text_validate' (Touche Entrée) et 'on_focus' (Perte de focus).
        """
        if not self.is_editable:
            return # Sécurité Python doublée
            
        try:
            valeur = float(texte) if texte else 0.0
        except ValueError:
            return # Ignore si l'utilisateur saisit un caractère invalide par mégarde
        
        # Remontée robuste dans l'arbre Kivy pour trouver l'InsertEditor parent
        p = self.parent
        while p and not isinstance(p, InsertEditor):
            p = p.parent
            
        if p and hasattr(p, 'modifier_point'):
            p.modifier_point(self.index, valeur, champ)

# Pour la pop-up insert édition
class InsertEditor(BoxLayout):
    active_id = StringProperty("0") # Ident de la plaquette actuellement sélectionnées
    insert_name = StringProperty("MON_BURIN_00")
    insert_type = StringProperty("Forme Libre")
    construction_points = ListProperty([[[0.0, 0.0], 400.0]])
    offset_mount = ListProperty([0.0, 0.0])
    canvas_points = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # On lie l'écouteur d'événement à la propriété de données
        #self.bind(construction_points=self.generate_and_render)
        # Premier appel manuel à l'initialisation de l'IHM
        #self.generate_and_render()
        self.insert_manager = ins_manager()
        
        self.bind(construction_points=self.recalculer_et_dessiner)
        self.load_insert_from_db("0")

    def load_insert_from_db(self, insert_id):
        """ 
        🎯 CHARGEMENT INTELLIGENT :
        Distingue un ID inexistant (repli sécurité) d'un ID corrompu (chargé pour réparation).
        """
        id_cible = str(insert_id)
        
        # 1. Vérification stricte : est-ce que cet ID existe dans la bibliothèque ?
        if id_cible not in self.insert_manager.library.get("cutt_profile", {}):
            print(f"⚠️ DRO [IHM] : ID {id_cible} inexistant dans le JSON. Repli sur l'insert de secours.")
            self.active_id = "0"
        else:
            self.active_id = id_cible

        # 2. Chargement dans le tampon RAM du manager (forcé sur "0" si l'ID initial était introuvable)
        self.insert_manager.set_active_insert_from_db(self.active_id)
        
        # 3. Synchronisation et affichage (va lire la RAM, même si les données sont bancales)
        self.rafraichir_ihm_depuis_ram()

    def rafraichir_ihm_depuis_ram(self):
        """ 2. SYNCHRONISATION RAM INTERNE MANAGER -> INTERFACE KIVY """
        # On interroge UNIQUEMENT le brouillon en RAM du manager
        data = self.insert_manager.get_insert_from_ram()
        
        self.insert_name = data["name"]
        
        # 🚨 L'injection dans cette ListProperty va automatiquement 
        # déclencher l'événement Kivy qui appelle 'recalculer_et_dessiner'
        self.construction_points = data["points"]

    def modifier_point(self, index, valeur, champ):
        """ Applique proprement 
            la modification d'un TextInput dans la structure [[hor, vert], r]
            Et recalcule le dessin
        """
        if self.active_id == "0" or index >= len(self.construction_points):
            return
            
        # On force la conversion en liste Python standard avant le deepcopy
        nouvelle_liste = copy.deepcopy(list(self.construction_points))

        # Application stricte sur la structure [[hor, vert], rayon]
        if champ == 'x':   nouvelle_liste[index][0][0] = valeur # horizontal
        elif champ == 'y': nouvelle_liste[index][0][1] = valeur # vertical
        elif champ == 'r': nouvelle_liste[index][1] = valeur    # rayon

        # Synchronisation RAM du manager + déclenchement Kivy
        self.insert_manager.active_insert["points"] = nouvelle_liste
        self.construction_points = nouvelle_liste

    def add_construction_point(self):
        """ Ajoute un point décalé de +5mm (5000 µm) par rapport au dernier point saisi """
        nouvelle_liste = []
        for pt in self.construction_points:
            nouvelle_liste.append([[pt[0][0], pt[0][1]], pt[1]])

        if nouvelle_liste:
            dernier_pt = nouvelle_liste[-1]
            # Création du nouveau point à +5000 microns sur les deux axes de construction
            nouveau_pt = [[dernier_pt[0][0] + 5000.0, dernier_pt[0][1] + 5000.0], 0.0]
        else:
            nouveau_pt = [[0.0, 0.0], 400.0]

        nouvelle_liste.append(nouveau_pt)
        self.construction_points = nouvelle_liste

    def del_construction_point(self):
        """ Supprime le dernier point de la liste (sauf P0, sécurité minimale de 1 point requis) """
        if len(self.construction_points) > 1:
            nouvelle_liste = []
            for pt in self.construction_points[:-1]: # On copie tout sauf le dernier
                nouvelle_liste.append([[pt[0][0], pt[0][1]], pt[1]])
            self.construction_points = nouvelle_liste

    def recalculer_et_dessiner(self, *args):
        """ 
        🎯 LE CHEF D'ORCHESTRE UNIQUE ET BLINDÉ :
        Fusionne l'ancien rendu avec la sécurité moderne anti-corruption.
        """
        n = len(self.construction_points)
        
        # Détermination du type de plaquette standard
        if self.active_id == "0": self.insert_type = "Sécurité Système"
        elif n <= 1:              self.insert_type = "Ronde (1P)"
        elif n == 2:              self.insert_type = "Oblong / Goutte (2P)"
        else:                     self.insert_type = f"Polygonale ({n}P)"

        # 1. Régénération de la grille de saisie (formulaire de gauche)
        if 'grid_points' in self.ids:
            self.ids.grid_points.clear_widgets()
            for idx, pt in enumerate(self.construction_points):
                ligne = LignePointGrille(
                    index=idx,
                    coord_x=pt[0][0],
                    coord_y=pt[0][1],
                    radius=pt[1],
                    is_editable=(self.active_id != "0")
                )
                self.ids.grid_points.add_widget(ligne)

        # 2. 📐 GESTION GÉOMÉTRIQUE ET TRACÉ CANVAS DANS LE FILET DE SÉCURITÉ
        try:
            if n == 0: 
                raise ValueError("Liste vide")
                
            data_forme = {"points": self.construction_points}
            point_fillet, arc_net, ref_centre_inverse = cut_tool.traiter_geometrie_generique(data_forme)
            
            # Sauvegarde de la mécanique calculée en microns purs [hor, vert]
            self.offset_mount = ref_centre_inverse
            
            # ----------------------------------------------------------------------
            # 3. PROJECTION ET RECENTRAGE GRAPHIQUE ÉCRAN (Récupéré de l'ancêtre !)
            # ----------------------------------------------------------------------
            pts_projetes = []
            facteur_zoom = 0.01  # Convertit les microns en pixels réels à l'écran
            
            # Calcul dynamique du centre du Widget de preview pour y épingler le centre du bec
            taille_canvas = self.ids.preview_canvas.size
            centre_x_canvas = self.ids.preview_canvas.pos[0] + (taille_canvas[0] / 2.0)
            centre_y_canvas = self.ids.preview_canvas.pos[1] + (taille_canvas[1] / 2.0)
            
            for pf in point_fillet:
                px = centre_x_canvas + (pf["pos"][0] * facteur_zoom)
                py = centre_y_canvas + (pf["pos"][1] * facteur_zoom)
                pts_projetes.extend([px, py])
                
            # Fermeture de la ligne filaire si c'est un polygone
            if n > 2 and point_fillet:
                px_first = centre_x_canvas + (point_fillet[0]["pos"][0] * facteur_zoom)
                py_first = centre_y_canvas + (point_fillet[0]["pos"][1] * facteur_zoom)
                pts_projetes.extend([px_first, py_first])
                
            # On donne la liste finale de pixels à la propriété Kivy Canvas (Line)
            self.canvas_points = pts_projetes
            
        except (TypeError, IndexError, ValueError) as e:
            # 🚨 LE NETTOYAGE EN CAS DE CORRUPTION GRAVE :
            print(f"💥 DRO [Geometry Error] : L'insert ID {self.active_id} est mal formé ({e}).")
            self.insert_type = "⚠️ CORROMPU (À réparer)"
            self.offset_mount = [0.0, 0.0]
            self.canvas_points = [] # Efface le dessin, la grille reste active pour correction

    def save_insert(self):
        """ Enregistrement final des données val_base (microns) dans cut_insert_lib.json """
        print(f"--- VALIDATION GÉOMÉTRIQUE INDUSTRIELLE ---")
        print(f"Insert : {self.insert_name} ({self.insert_type})")
        print(f"Structure sauvegardée : {self.construction_points}")
        print(f"Vecteur de compensation jauge [hor, vert] : {self.offset_mount}")

    def annuler_modifications(self):
        """ Déclenché par le bouton Annuler : on écrase le brouillon par le JSON d'origine """
        print("↩️ Annulation des modifications en cours.")
        self.load_insert_from_db(self.active_id)

# Pour la popup burin édition
class CutterEditor(BoxLayout):
    active_id = StringProperty("1")
    cutter_name = StringProperty("Nouveau Burin")
    tool_mount = NumericProperty(0, allownone=True)
    #mount_angle = NumericProperty(0) # en milli-degrés
    ident_insert = StringProperty("0")
    
    # Nos listes à 3 entrées [probe, wear, fine] en microns purs
    offset_hor = ListProperty([0, 0, 0])
    offset_vert = ListProperty([0, 0, 0])
    
    # Données géométriques du corps intégrées
    body_data = ListProperty([])
    
    # Etat général des alertes homing (Vrai si un des éléments perd sa réf)
    homming_status = BooleanProperty(False)
    
    # Liste pour alimenter le Spinner des plaquettes
    available_inserts = ListProperty([])
    canvas_points = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from cutting_tool.cut_manager import CutManager
        self.cutter_manager = CutManager()
        
        # Charger les plaquettes disponibles pour le Spinner
        #self.available_inserts = self.list_insert_for_spinner()
        
        # Liaison automatique sur les variables critiques pour redessiner
        self.bind(body_data=self.preparer_affichage_burin_complet)
        #self.bind(mount_angle=self.preparer_affichage_burin_complet)
        
        # Démarrage par défaut ==> Déjà fait proprement par le main()
        #self.charger_burin_depuis_ident("1")

    def charger_burin_depuis_ident(self, tool_id):
        """ Charge le profil complet du burin depuis la bibliothèque en RAM """
        # ❌ SÉCURITÉ : Avant de changer d'outil, on coupe l'écoute sur l'ancien burin
        # pour éviter que des fantômes en RAM ne continuent de crier en tâche de fond.
        if hasattr(self, 'cutter') and self.cutter:
            try:
                self.cutter.unbind(modified_not_save=self.synchronize_tool_ui_alerts)
            except Exception:
                pass

        self.active_id = str(tool_id)
        burin = self.cutter_manager.library["cutt_tool"].get(self.active_id)
        
        if burin:
            self.cutter_name = burin["name"]
            self.tool_mount = burin["tool_mount"]
            self.ident_insert = burin["ident_insert"]
            #self.mount_angle = burin["mount_angle"]
            self.offset_hor = burin["offset_hor"]
            self.offset_vert = burin["offset_vert"]
            #self.homming_status = any(burin["homming"])
            
            # Extraction de la structure géométrique du corps
            self.body_data = burin.get_draw_pnt_brut()
            self.preparer_affichage_burin_complet()

    def modifier_offset_couche(self, texte, axe, index_couche):
        """ Modifie proprement le composant micron demandé sans casser le dictionnaire """
        try:
            valeur_micron = int(texte) if texte else 0
        except ValueError:
            return
            
        if axe == 'hor':
            nouvelle_liste = list(self.offset_hor)
            nouvelle_liste[index_couche] = valeur_micron
            self.offset_hor = nouvelle_liste
        else:
            nouvelle_liste = list(self.offset_vert)
            nouvelle_liste[index_couche] = valeur_micron
            self.offset_vert = nouvelle_liste

    def changer_insert_associe(self, texte_spinner):
        """ Déclenché lors du changement de plaquette via le Spinner """
        if " - " in texte_spinner:
            id_ins = texte_spinner.split(" - ")[0]
            self.ident_insert = id_ins
            # On active l'alerte homing [plaquette changée = True]
            burin = self.cutter_manager.library["cutt_tool"][self.active_id]
            burin["homming"][1] = True
            #self.homming_status = True
            self.preparer_affichage_burin_complet()

    def preparer_affichage_burin_complet(self, *args):
        """ 📐 ASSEMBLAGE ET TRANSFORMATION CINÉMATIQUE CAO """
        # 1. Récupération de la plaquette liée depuis sa bibliothèque
        insert_data = self.cutter_manager.insert_manager.get_insert_for_kivy(self.ident_insert)
        if not insert_data:
            return

        insert_points = insert_data["points"]
        offset_plaquette = insert_data["offset_mount"] # vecteur [hor, vert] du bec

        # Récupération des cotes du burin courant
        burin = self.cutter_manager.library["cutt_tool"][self.active_id]
        clearance_hor = burin["body"]["clearance"][0]
        clearance_vert = burin["body"]["clearance"][1]
        
        # Somme des angles : angle_logement + angle_tourelle (convertis en degrés)
        angle_total_deg = (burin["body"]["lead_angle"] )#+ self.mount_angle) / 1000.0
        besoin_inverse = burin["body"]["lead_reverse"]

        # 2. Positionnement cinématique de la plaquette sur la clearance du corps
        # On fait pivoter la plaquette et on lui applique son vecteur clearance
        insert_oriente = cut_tool.transformer_geometrie_insert(
            insert_points, 
            angle_total_deg, 
            invert=besoin_inverse
        )

        # 3. Passage dans le moteur géométrique central pour les congés réels
        data_forme = {"points": insert_oriente}
        point_fillet, arc_net, _ = cut_tool.traiter_geometrie_generique(data_forme)

        # 4. Projection visuelle Kivy proportionnelle à l'écran (Zoom/Pan)
        pts_projetes = []
        facteur_zoom = 0.005 # Cotes de manches de 100mm -> pixels écran
        
        taille_canvas = self.ids.preview_canvas.size
        centre_x_canvas = self.ids.preview_canvas.pos[0] + (taille_canvas[0] / 2.0)
        centre_y_canvas = self.ids.preview_canvas.pos[1] + (taille_canvas[1] / 2.0)

        # Dessin de l'insert
        for pf in point_fillet:
            px = centre_x_canvas + (pf["pos"][0] * facteur_zoom)
            py = centre_y_canvas + (pf["pos"][1] * facteur_zoom)
            pts_projetes.extend([px, py])

        # 5. Dessin du manche (Ajout des points du corps)
        # Le point [0,0] du corps est notre référence. On le translate pour l'aligner
        for pt_body in self.body_data:
            bx = centre_x_canvas + ((pt_body[0][0] - clearance_hor) * facteur_zoom)
            by = centre_y_canvas + ((pt_body[0][1] - clearance_vert) * facteur_zoom)
            pts_projetes.extend([bx, by])

        self.canvas_points = pts_projetes

    def sauvegarder_burin(self):
        """ Enregistre de manière étanche les modifications dans la bibliothèque de la tourelle """
        if self.active_id == "199":
            return
            
        burin = self.cutter_manager.library["cutt_tool"][self.active_id]
        burin["name"] = self.cutter_name
        burin["tool_mount"] = self.tool_mount
        burin["ident_insert"] = self.ident_insert
        #burin["mount_angle"] = self.mount_angle
        burin["offset_hor"] = self.offset_hor
        burin["offset_vert"] = self.offset_vert
        
        self.cutter_manager.save_library()
        print(f"💾 Burin ID {self.active_id} synchronisé dans cut_lib.json.")

    def annuler_modifications(self):
        self.charger_burin_depuis_ident(self.active_id)


# Pour la page screen_TOOL

class CutLineSelect(BoxLayout):
    """
    🗜️ LIGNE DE SÉLECTION COMPACTE (Version 7.2) :
    Classe épurée liée au fichier .kv. Reçoit un objet CutterManager 
    et extrait ses propriétés de façon réactive.
    """
    # Propriétés lues en direct par votre fichier .kv
    tool_ident = StringProperty("0")
    nom_outil = StringProperty("")
    tool_mount = StringProperty(0, allownone=True)
    source_icone = StringProperty("")
    
    # Drapeaux (Flags) d'alertes métiers
    non_sauve = BooleanProperty(False)
    couleur_fond = ListProperty([0.1, 0.1, 0.1, 1])

    def __init__(self, objet_burin, page_manager, est_actif=False, **kwargs):
        super().__init__(**kwargs)
        self.burin = objet_burin
        self.manager = page_manager

        # 🚀 EXTRACTION CHIRURGICALE EN PROPERTIES KIVY
        self.tool_ident = str(objet_burin.ident)
        self.nom_outil = str(objet_burin.name)
        self.tool_mount = objet_burin.tool_mount
        self.source_icone = objet_burin.get_icone_cadran()
        
        # Gestion des alertes
        self.non_sauve = hasattr(objet_burin, 'modified_not_save') and objet_burin.modified_not_save

        # Extraction sécurisée des données de l'insert

        # 🎨 LES 3 TEINTES DE FOND DE LIGNE (Votre concept visuel d'atelier !)
        if est_actif:
            self.couleur_fond = [0.15, 0.25, 0.4, 1]      # 🔵 Bleu nuit (Outil actif dans la broche)
        elif objet_burin.tool_mount is not None:
            self.couleur_fond = [0.18, 0.18, 0.22, 1]     # 🪙 Gris moyen (Monté sur la tourelle physique)
        else:
            self.couleur_fond = [0.11, 0.11, 0.13, 0.6]     # 📦 Gris sombre (Au repos dans l'armoire)

    def on_touch_down(self, touch):
        """ Intercepte l'appui tactile sur l'intégralité du grand fond de ligne """
        if self.collide_point(*touch.pos):
            # Routage métier direct vers la fonction de commutation du manager de page
            self.manager.action_clic_selection_outil(self.burin.ident)
            return True
        return super().on_touch_down(touch)

class CutterPageHeader(BoxLayout):
    """
    🎯 LE BANDEAU D'EN-TÊTE DE LA PAGE OUTILS (Version 7.2) :
    Gère l'affichage du burin actif, l'icône du cadran et les boutons d'édition.
    """
    # 1️⃣ Déclaration de la propriété pour le Binding .kv
    manager_parent = ObjectProperty(None, allownone=True)
    ihm_initialisee = BooleanProperty(False)
    color_ico_tool = ListProperty([0.25, 0.25, 0.28, 0.4])
    source_image_user_ofst = StringProperty("bitmaps/tool_offset_0_0.png")

    # Signature explicite en POO pure avec injection à l'initiation
    def __init__(self, parent, icone=None, **kwargs):
        # Fondations Kivy obligatoires en première ligne
        super().__init__(**kwargs)
        
        # Injections directes des liens en RAM
        self.manager_parent = parent
        self.source_image_cadran = icone if icone else "bitmaps/burin_select.png"
        
        #print("RAM 🧬 : CutterPageHeader instancié avec injection directe du parent.")

    def refresh(self):
        """ 🎛️ LA MANIVELLE DE REPRISE DE SESSION (Version 7.2 - Reconnexion Auto) """
        if not self.manager_parent:
            return
        
        app = App.get_running_app()
        
        if not self.ihm_initialisee:
            self.ihm_initialisee = True
        self.property('ihm_initialisee').dispatch(self)

        actif_tool = self.manager_parent.cutter

        if actif_tool.modified_not_save:
            self.color_ico_tool = app.theme_colors["status_modified_a"]
        else:
            self.color_ico_tool = app.theme_colors["btn_bg_a"]

        box = self.ids.b_name
        box.children[0].text = actif_tool.name
        box.children[1].text = actif_tool.ident
        box = self.ids.b_tow_line
        if actif_tool.tool_mount:
            box.children[4].text = actif_tool.tool_mount # Name porte-outil
        else:
            box.children[4].text = "Aucun"
        if actif_tool.insert:
            ins_rayon_brut = actif_tool.insert.drawing[0].radius_base if actif_tool.insert.drawing else None
            ins_name = actif_tool.insert.name
        else:
            ins_rayon_brut = None
            ins_name = "- ... -"
        box.children[0].text = f"{( ins_rayon_brut / 1000.0):.3f}mm" if ins_rayon_brut else "-.-" #Rayon
        box.children[2].text = ins_name  # Name insert

    def OLD_clic_editer_burin(self):
        """ 🛠️ ACTION : Ouvre le mode édition géométrique du manche """
        print("IHM ⚙️ : Demande d'ouverture de l'éditeur de corps de burin.")
        # Ici viendra l'appel vers votre Popup ou votre bascule de formulaire de saisie

    def OLD_clic_editer_plaquette(self):
        """ 💎 ACTION : Ouvre le mode édition géométrique de la plaquette """
        print("IHM ⚙️ : Demande d'ouverture de l'éditeur de profil d'insert.")
        # Ici viendra l'appel vers l'éditeur spécifique d'insert

class CutterPageDashboard(BoxLayout):
    """
    LE FORMULAIRE MÉTIER DE LA PAGE CUTTER :
    Ce widget vide sert de structure d'accueil. Il possède ses identifiants 
    dans le fichier main_tool_screen.kv (container_liste_outils, preview_canvas, etc.)
    """
    manager_parent = ObjectProperty(None, allownone=True)
    source_image_cadran = StringProperty("bitmaps/burin_select.png")
    ihm_initialisee = BooleanProperty(False)
    
    color_ofst = DictProperty({
        "box_tourelle":[0.5, 0.5, 0.5, 0.8],    # Couleur du cadre Tourelle
        "b_bg_ang_tot":  [0.5, 0.5, 0.5, 0.4],
        "b_bg_ang_tour": [0.5, 0.5, 0.5, 0.4],
        "b_bg_ang_idx":  [0.5, 0.5, 0.5, 0.4],

        "b_bg_ref_ang": [0.5, 0.5, 0.5, 0.8],
        "b_bg_ofst_p":  [0.5, 0.5, 0.5, 0.8],
        "b_bg_ofst_m":  [0.5, 0.5, 0.5, 0.8],
        "b_bg_ofst_c":  [0.5, 0.5, 0.5, 0.8],
        "box_ofst_t":  [0.5, 0.5, 0.5, 0.8],    # Couleur du cadre offsets
        "b_bg_ofst_t": [0.2, 0.5, 0.2, 0.5]
    })

    def __init__(self, parent, icone=None, **kwargs):
        super().__init__(**kwargs)    # 1. On lance d'abord les fondations obligatoires de Kivy !
        
        # 2. Vos injections directes de variables en clair
        self.manager_parent = parent
        self.source_image_cadran = icone if icone else "bitmaps/burin_select.png"
        
        #print("RAM 🧬 : Injections initiales effectuées dans le __init__.")

    def refresh(self):
        """ 🎛️ LA MANIVELLE DE REPRISE DE SESSION (Version 7.2 - Reconnexion Auto) """
        if not self.manager_parent:
            return
        
        manager = self.manager_parent
        if not self.ihm_initialisee:
            self.ihm_initialisee = True
        self.property('ihm_initialisee').dispatch(self)

class CutterPageManager(BaseScreenLayout):
    """
    🎯 LE CAPITAINE DE L'ÉCRAN COUPEURS :
    Hérite directement de votre BaseScreenLayout.
    Gère la tourelle d'outils en tâche de fond (statique) sans consommer de 60Hz inutile.
    """
    active_tool_ident = StringProperty("199")       # Ident du burin sélectionné à l'écran
    #cutter_name = StringProperty("Nouveau Burin")
    mode_edition_actif = BooleanProperty(False)       # Débloque ou cadenasse les cases de droite
    tool_mount = StringProperty(0, allownone=True)
    ident_insert = StringProperty("0")
    
    # Listes à 3 couches [probe, wear, fine] en microns purs
    offset_hor = ListProperty([0, 0, 0])
    offset_vert = ListProperty([0, 0, 0])
    
    # Données géométriques du corps et alertes homing
    body_data = ListProperty([])
    homming_status = BooleanProperty(False)
    available_inserts = ListProperty([])
    canvas_points = ListProperty([])

    #NEW_Version  
    not_save_tool = BooleanProperty(True)

    def __init__(self, cutter_actif, machine_state=None, **kwargs):
        # on ajoute cette kwarg dans les args de BaseScreenLayout()
        kwargs.setdefault('associated_target_screen', 'screen_CUTTER')  # On lui donnele nom de la variable à surveiller dans le main() pour récupérer automatiquement l'icône et le status associer à cette page
        # Sauvegarde étanche de vos 3 gros blocs de données d'atelier
        #self.part = part   Pas d'utilité ici !     
        self.cutter = cutter_actif    # Lien vers CutterManager() de l'outil actif
        self.machine = machine_state  # Lien vers  MachineState() , la gestion depuis et vers les MCU de la machine
        
        super().__init__(**kwargs)

        # 🟢 TABLE UNIVERSELLE DES MÉTADONNÉES DE LA PAGE (Version 7.2)
        # Structure du dictionnaire : "Clé_KV": ("Nom lisible pour l'opérateur", "Unité technique ou None")
        self.label_abbr_dico = {
            # --- La Grille des Offsets (Numériques avec unités) ---
            "X0": ("X0 : Offset Palpeur", "mm"),
            "X2": ("X2 : Ajustement Fin", "mm"),
            "Z0": ("Z0 : Offset Palpeur", "mm"),
            "Z2": ("Z2 : Ajustement Fin", "mm"),
            # --- Les Paramètres Géométriques (Futurs blocs) ---
            "LEAD_ANG": ("Angle d'Attaque (Lead Angle)", "deg"),
            "MULTIFIX": ("Cran Tourelle Multifix", "deg"),
            # --- Les Variables Textuelles (Hors-grille sans unités) ---
            "TOOL_NAME": ("Nom du Burin", None),
            "INSERT_ID": ("Code Plaquette Amovible", None)
        }

        #NEW_VERSION
        self.cutter_name = "Nouveau Burin"

    def on_kv_post(self, base_widget):
        """
        DÉCLENCHEUR SÉCURISÉ : Le châssis de base .kv est prêt en mémoire.
        On injecte notre tableau de bord spécifique en pur Python sans risquer de bug .kv !
        """

        # 2️⃣ CRÉATION ET CLIPSAGE DU FORMULAIRE MÉTIER
        header = CutterPageHeader(self)
        self.injecter_entete_specifique(header)

        dashboard = CutterPageDashboard(self)
        #dashboard.manager_parent = self
        #print("RAM 🔗 : Liaison métrologique injectée -> dashboard.manager_parent = self")
        self.injecter_corps_specifique(dashboard)

        # 3️⃣ CARTOGRAPHIE DES IDENTIFIANTS
        # On sauvegarde le dashboard dans le dictionnaire self.ids pour un accès direct
        self.ids["bandeau_header"] = header # Cartographie directe pour le code
        self.ids["dashboard_box"] = dashboard

        self.ids["bandeau_header"].refresh()

        # Charger la liste des plaquettes disponibles pour le Spinner du .kv
        self.available_inserts = self.list_insert_for_spinner()

        # 4️⃣ CHARGEMENT DE L'OUTIL ACTIF
        # On démarre par défaut sur le premier outil de la bibliothèque
        #self.charger_burin_depuis_ident("1")
        #NEW --------------------
        # 4️⃣ 🟢 CHARGEMENT DYNAMIQUE SÉCURISÉ :
        # Au lieu d'écrire "1" en dur, on lit l'identifiant de l'objet self.cutter 
        # que le main.py nous a injecté à la naissance (votre outil préféré des SETTINGS) !
        #
        # Voir main() ligne 118 ==> C'est déjà fait proprement !
        #if hasattr(self, 'cutter') and self.cutter:
        #    self.active_tool_ident = str(self.cutter.ident)    # On force la variable active_tool_ident à être synchrone
        #    self.charger_burin_depuis_ident(self.active_tool_ident)    # On charge ses données, ses offsets et sa bonne icône (ex: l'outil 4 avec son cadran 2.5)
        #else:
        #    self.charger_burin_depuis_ident("199")    # Repli de sécurité si l'outil est absent à l'allumage (l'outil "199" étant automatiquement créé par CutterLib() si absant)

        #self.refresh_cut_list()    # charger_burin_depuis_ident s'en occupe déjà à 100% !


        print(f"DEBUG groupe d'offset: {self.cutter.grp_offset}")
        # MAJ DES LABELES OFFSETS
        self.ids["dashboard_box"].ids.b_ofst_p.children[2].text = " Palpeur "
        self.ids["dashboard_box"].ids.b_ofst_m.children[2].text = " Machine "
        self.ids["dashboard_box"].ids.b_ofst_c.children[2].text = " Correcteur "
        self.ids["dashboard_box"].ids.b_ofst_t.children[2].text = " TOTAL  "

        self.generer_magasin_outils_gauche()
        #self.up_tool_ofst_values()

    def up_tool_ofst_values(self):
        # 1️⃣ LE FILTRE DE SÉCURITÉ ULTRA-LÉGER (En pur Python, sans export JSON !)
        # On vérifie simplement si le groupe sélectionné (def ou vol) est chargé en RAM
        if not self.cutter or not self.cutter.grp_offset or not "ofst_probbe" in self.cutter.config_defaut:
            self.ids["dashboard_box"].ids.b_ofst_t.children[1].text = "LOADING"
            self.ids["dashboard_box"].ids.b_ofst_t.children[0].text = "ERROR"
            self.ids["dashboard_box"].color_ofst["b_bg_ofst_t"] =  [0.5, 0.2, 0.2, 0.8]
            return

        # Raccourci vers le groupe actif (Défaut ou Volant)
        pack = self.cutter.grp_offset

        app = App.get_running_app()
        # 2️⃣ SÉCURISATION DU DÉMARRAGE DU TRIPLET ANGLE (hasattr)
        if hasattr(app, 'offset_page_instance') and app.offset_page_instance and hasattr(app.offset_page_instance, 'tourelle_angle'):
            [ptour, ptour_v] = app.offset_page_instance.tourelle_angle
            [paxey, paxey_v] = app.offset_page_instance.axe_y_angle
        else:
            ptour, ptour_v = 0, False
            paxey, paxey_v = 0, False

        mach_angle = ptour #+ paxey
        mach_valide = True if ptour_v or paxey_v else False
            
        # 3️⃣ EXTRACTION DE L'ANGLE MACHINE DE RÉFÉRENCE DEPUI LE GRUPE ACTIF
        # Dans le JSON, l'angle machine de calibration fait partie de ta configuration :
        pofst = pack.get("angle_machine", 0) * 1000
        # Angle de l'offset enregistré
        ofst_idx = app.lib_cutter.act_cut_idx_tourelle
        if ofst_idx < 0 or ofst_idx >= len(MACHINE_CONFIG["index_multi_fix"]):
            #sauvetage en cas de changement de tourelle
            #TODO: idéalement déréférancer tous les outils !
            ofst_idx = -2
            app.lib_cutter.act_cut_valide_mount = False
        if ofst_idx >= 0:
            ofst_val = MACHINE_CONFIG["index_multi_fix"][ofst_idx]* 1000
        else:
            ofst_val = "Err"
        #_, ofst_valid = pack.get("idx_mount", [0, False])
        ofst_valid = app.lib_cutter.act_cut_valide_mount
        ofst_type = app.lib_cutter.active_cutter_idx_mount
        #ofst_val = pack.get("angle_machine", 0)
        #ofst_val = MACHINE_CONFIG["index_multi_fix"][ofst_idx] #* 1000
        
        # Injection des cotes angulaires (forçage des TextInputs/Labels enfants)
        self.ids["dashboard_box"].ids.lbl_tour_idx_idx.text = f"Index n° {ofst_idx+1}"
        self.ids["dashboard_box"].ids.lbl_tour_idx_angle.text = f"Angle index:  {(ofst_val / 1000.0):.2f}° " if ofst_val != "Err" else "Err."
        self.ids["dashboard_box"].color_ofst["b_bg_ang_idx"] = [0.2, 0.7, 0.2, 0] if ofst_valid else [0.7, 0.2, 0.2, 0.4]
        self.ids["dashboard_box"].ids.lbl_tour_brid.text = f"Angle bridage:  {(mach_angle / 1000.0):.2f}° "
        self.ids["dashboard_box"].color_ofst["b_bg_ang_tour"] = [0.2, 0.7, 0.2, 0] if mach_valide else [0.7, 0.2, 0.2, 0.4]
        self.ids["dashboard_box"].ids.lbl_tour_tot.text = f"Total porte-outil:  {((ofst_val + mach_angle) / 1000.0):.2f}°" if ofst_val != "Err" else "Err."
        self.ids["dashboard_box"].color_ofst["b_bg_ang_tot"] = [0.2, 0.7, 0.2, 0.3] if ofst_valid and mach_valide else [0.7, 0.2, 0.2, 0.4]
        self.ids["dashboard_box"].color_ofst["box_tourelle"] = [0.3,0.5,0.5,0.8] if ofst_valid and mach_valide else app.theme_colors["status_error_ia"]
        self.ids["dashboard_box"].ids.lbl_titre_ofst.text = "Offsets DEFAUTS" if ofst_type == "def" else "Offsets VOLANTS"
        #lbl_ofst_a_ref
        self.ids["dashboard_box"].ids.lbl_ofst_a_ref.text = f"réf: {(pofst / 1000.0):.2f}°"
        pt_v = (pofst == ofst_val + mach_angle) if ofst_val != "Err" else False
        self.ids["dashboard_box"].color_ofst["b_bg_ref_ang"] = [0.2, 0.7, 0.2, 0.3] if pt_v else [0.7, 0.2, 0.2, 0.4]
        
        # 4️⃣ EXTRACTION DES MICRONS DES 3 COUCHES D'OFFSETS VIA GRP_OFFSET
        [pt_z, pt_x , p_v] = pack.get("ofst_probbe", [0, 0, False])
        pt_v = pt_v and p_v # Sécurisation logique par cascade d'atlier
        self.ids["dashboard_box"].ids.b_ofst_p.children[1].text = f"{(pt_x / 1000.0):.3f}mm"
        self.ids["dashboard_box"].ids.b_ofst_p.children[0].text = f"{(pt_z / 1000.0):.3f}mm"
        self.ids["dashboard_box"].color_ofst["b_bg_ofst_p"] = [0.2, 0.7, 0.2, 0.0] if p_v else [0.7, 0.2, 0.2, 0.4]
        
        [p_z, p_x , p_v] = pack.get("ofst_machine", [0, 0, False])
        pt_z += p_z
        pt_x += p_x
        pt_v = pt_v and p_v # Sécurisation logique par cascade d'atlier
        self.ids["dashboard_box"].ids.b_ofst_m.children[1].text = f"{(p_x / 1000.0):.3f}mm"
        self.ids["dashboard_box"].ids.b_ofst_m.children[0].text = f"{(p_z / 1000.0):.3f}mm"
        self.ids["dashboard_box"].color_ofst["b_bg_ofst_m"] = [0.2, 0.7, 0.2, 0.0] if p_v else [0.7, 0.2, 0.2, 0.4]
        
        [p_z, p_x , p_v] = pack.get("ofst_corr", [0, 0, False])
        pt_z += p_z
        pt_x += p_x
        pt_v = pt_v and p_v
        self.ids["dashboard_box"].ids.b_ofst_c.children[1].text = f"{(p_x / 1000.0):.3f}mm"
        self.ids["dashboard_box"].ids.b_ofst_c.children[0].text = f"{(p_z / 1000.0):.3f}mm"
        self.ids["dashboard_box"].color_ofst["b_bg_ofst_c"] = [0.2, 0.7, 0.2, 0.0] if p_v else [0.7, 0.2, 0.2, 0.4]

        # 5️⃣ RE-DRESSAGE DU BLOC TOTAL SOMME
        self.homming_status = pt_v        
        self.ids["dashboard_box"].ids.b_ofst_t.children[1].text = f"{(pt_x / 1000.0):.3f}mm"
        self.ids["dashboard_box"].ids.b_ofst_t.children[0].text = f"{(pt_z / 1000.0):.3f}mm"
        self.ids["dashboard_box"].color_ofst["box_ofst_t"] = [0.3,0.5,0.5,0.8] if pt_v else app.theme_colors["status_error_ia"]
        self.ids["dashboard_box"].color_ofst["b_bg_ofst_t"] = [0.2, 0.7, 0.2, 0.3] if pt_v else [0.7, 0.2, 0.2, 0.4]

        ################################
        self.not_save_tool = self.cutter.modified_not_save
        self.ids["bandeau_header"].refresh()    # HEADER UP-DATE

    #def charger_burin_depuis_ident(self, tool_ident: str, idx_multifix=0, grp_ofst=None):
    def charger_burin_depuis_ident(self, tool_ident: str, crant_mont=0, grp_ofst=None, valide=None):
        """ 
        Arg:
            tool_ident: Indentifiant de l'outil (pas confondre avec son index !)
            crant_mont: L'index de positionnement sur la tourelle (MultiFix par ex.)
            grp_ofst:   Le groupe d'offset de l'outil utilisé (def ou vol)
            valide:     Si le crant utilisé et validé dans son groupe
            - Ps: crant_mont et valide son pour User_setting, pas pour modifier l'outil proprement dit !
            - Ps: grp_ofst est déjà màj avant, il devrait être inutile ici ? (à contrôler l'appel depuis le main() au démarrage !)
        """
        if not self.cutter or not self.cutter.parent:  
            return

        # 1. Ordre de bascule et d'aiguillage automatique à la Lib
            #Elle reçoit toutes les variables pour User_Setting de l'outil en cours d'utilisation
        self.cutter.parent.set_cutter_active(tool_ident, crant_mont, grp_ofst, valide)
        
        # 2. Réalignement du pointeur local d'IHM de la page
        self.cutter = self.cutter.parent.active_cutter
        self.active_tool_ident = str(self.cutter.ident)

        # 3.0 Màj de l'cône général du bouton TOOLs dans tous les baseScreen
        app = App.get_running_app()
        if app:
            app.screen_CUTTER["icon"] = str(self.cutter.get_icone_cadran())
            #app.property('screen_CUTTER').dispatch(app)  # Réveille la StringProperty de la base
            val = self.cutter.grp_offset["idx_dro"]
            app.dro_visual_offset_cut = self.ico_idx_dro(arg_x=val[0],arg_z=val[1], list_for_main=True)

        # 3.1  RE-GÉNÉRATION TACTILE DU MAGASIN D'OUTILS
        self.refresh_cut_list()

        # 4. On lance l'automate des 4 étages et le forçage des mm
        self.synchronize_tool_ui_alerts()
        self.ids["dashboard_box"].refresh()

    def generer_magasin_outils_gauche(self):
        """
        🛒 LE REMPLISSEUR DU SCROLLVIEW :
        Vide le magasin vertical de gauche et recrée les boutons.
        """
        if not self.cutter or not self.cutter.parent:
            return
            
        # On va chercher la zone de stockage à gauche dans ton habillage
        dashboard = self.ids["dashboard_box"]
        if not hasattr(dashboard.ids, 'box_select_tool'):
            return
        box_gauche = dashboard.ids.box_select_tool
    
        box_gauche.clear_widgets()    # Nettoyage complet    
        for outil in self.cutter.parent.cutters:    # Boucle sur la famille d'outils en RAM        
            btn = Button(    # Création du bouton tactile généreux
                text=f"  N°{outil.ident} - {outil.name}",
                size_hint_y=None,
                height="50dp",
                halign="left",
                valign="middle",
                # Surlignage bleu si sélectionné, sinon gris sombre d'atelier
                background_color=[0.2, 0.6, 0.9, 1] if str(outil.ident) == self.active_tool_ident else [0.15, 0.15, 0.18, 1]
            )
            # Alignement du texte Kivy
            btn.bind(size=lambda instance, size: setattr(instance, 'text_size', size))
            # Le clic tactile renvoie vers ton chargeur épuré
        
            #cran_actuel = self.cutter.parent.act_cut_idx_tourelle    # On conserve l'index de tourelle actuel de la session globale lors du clic
            #btn.bind(on_release=lambda instance, t_id=outil.ident: self.charger_burin_depuis_ident(t_id))   #, idx_multifix=cran_actuel))
            
            box_gauche.add_widget(btn)

    def synchronize_tool_ui_alerts(self, instance=None, value=None):
        """
        🚦 LE DISJONCTEUR DE SÉCURITÉ À 4 ÉTAGES (Version V_7.2 Premium)
        Déclenché automatiquement par le bind Kivy de l'objet de données.
        Priorités : ERROR (Rouge) > MODIFIED (Orange) > WARNING (Jaune) > OK (Vert).
        """
        #NEW:
        self.up_tool_ofst_values()

        if not self.cutter:
            return

        # Étape A : Inspection de l'armoire pour vérifier les autres outils
        lib_not_save = False
        if self.cutter.parent and hasattr(self.cutter.parent, 'cutters'):
            for tool_item in self.cutter.parent.cutters:
                if tool_item != self.cutter and getattr(tool_item, 'modified_not_save', False):
                    lib_not_save = True
            self.cutter.parent.lib_not_save = lib_not_save

        # Étape B : Lecture des drapeaux directement depuis les objets de données
        #self.homming_status = False #any(self.cutter.homming)
        active_tool_is_modified = self.cutter.modified_not_save
        library_has_modifications = getattr(self.cutter.parent, 'lib_not_save', False)

        # Étape C : Traitement de la matrice de priorité pour l'IHM
        if not self.homming_status:
            final_status = "ERROR"       # 🔴 Étage 1 : Outil actif non calibré (Danger de collision)
        elif active_tool_is_modified:
            final_status = "MODIFIED"    # 🟠 Étage 2 : Outil actif modifié en RAM non enregistré
        elif library_has_modifications:
            final_status = "WARNING"     # 🟡 Étage 3 : Un autre outil de la bibliothèque attend sa sauvegarde
        else:
            final_status = "OK"          # 🟢 Étage 4 : Tout est jaugé, propre et gravé sur le disque

        # Étape D : Stockage dans la variable héritée de la base (Fini l'ancien set_status !)
        self.page_status_alert = final_status

        # Étape E : Envoi direct au dictionnaire de l'application pour l'onglet de gauche
        app = App.get_running_app()
        if app:
            app.screen_CUTTER["status"] = final_status
            app.property('screen_CUTTER').dispatch(app)  # Propagateur d'allumage nominal Kivy

    def OLD_action_clic_selection_outil(self, tool_ident):
        """ 🎛️ COMMUTATION CINÉMATIQUE TACTILE AVEC SAUVEGARDE CONFIG """
        str_ident = str(tool_ident)
        print(f"⚙️ DRO [IHM] : Sélection tactile du burin Ident : {str_ident}")
        
        app = App.get_running_app()
        index_nouveau = app.lib_cutter.get_index_to_ident(str_ident)
        
        if index_nouveau != -1:

            ''' Je penses que ici il faut ajouter la popup de sélection d'index tourelle (MultiFix) ?
            On a ce qu'il faut pour rechercher les angles def et volant enregistré pour cette outil
            def_ref = app.lib_cutter.cutters[index_nouveau].config_defaut
            vol_ref = app.lib_cutter.cutters[index_nouveau].config_volante
            last_ref = app.lib_cutter.cutters[index_nouveau].grp_offset       # Optionnal
            Ps: Chacun contient: {"idx_mount": [0,true], "idx_dro": [1,1,true], "angle_machine": 0,
                "ofst_probbe": [12000,15000,true], "ofst_machine": [0,0,true], "ofst_corr": [0,0,true]}
                Ce qui nous intéraisses dans un premier temps c'est l'angle corespondant à "idx_mount" + "angle_machine" !
                D'ailleur je me demande si je devrait pas remplacer ces deux variables directement par "angle_offset" ?
            On aura aussi besoin de : (qui est la liste des angles correspondant à chaque indexe de la tourelle)
            MACHINE_CONFIG = SETTINGS.get("machine_config", {}) ==> "index_multi_fix": [0,18,36,54,72,90,108,126,144,162,180,-162,-144,-126,-108,-90,-72,-54,-36,-18],
            Et finalement de l'angle de bridage actuel de la tourelle.

            Après on recherhce si on arrive à atteindre "angle_offset" avec l'angle de bridage + un index-multifix ?

            premières lignes PopUp :
                - "DEFAUT" ; Angle_offset = ... ; index = ... ou non-accéssible (si non-acc. : non sélectionnable)
                - "VOLANTE"; Angle_offset = ... ; index = ... ou non-accéssible (si non-acc. : non sélectionnable)
            Puis en dessous, sur 4 colonnes de 90° (j'imagine): tous les "angles / index" possiblent

            Si je clique sur "DEFAUT" ou "VOLANT" on part là dessus sans modif
            Si je clique sur un autre angle, on part sur "Volant" mais on passe les flags de validations à false ?

            Quand penses-tu ?

            Après reste juste à adapter [self.charger_burin_depuis_ident()] pour quelle gère "def vs vol" ?
            '''

            # A. On commute les pointeurs d'objets globaux
            app.cutter_actif = app.lib_cutter.cutters[index_nouveau]
            app.lib_cutter.active_cutter = app.cutter_actif
            
            # B. On charge l'outil graphiquement sur l'écran en cours
            self.charger_burin_depuis_ident(str_ident)
            
            # C. On redessine les surbrillances bleues de la liste de gauche
            self.refresh_cut_list()
            
            # 💾 D. SYNCHRONISATION CONFIGURATION : On enregistre le changement dans le JSON !
            from configurator.config import SETTINGS, save_json, SETTINGS_FILE
            try:
                SETTINGS["user_last_select"]["selected_tool"] = [str_ident, 0, "def"]
                save_json(SETTINGS_FILE, SETTINGS)
                print(f"💾 [ user_settings.json ] : Outil actif de démarrage mis à jour sur l'Ident '{str_ident}'")
            except Exception as e:
                print(f"⚠️ Erreur lors de la sauvegarde de la préférence outil : {e}")
    def action_clic_selection_outil(self, tool_ident):
        """ 🎛️ COMMUTATION CINÉMATIQUE TACTILE AVEC POPUP MULTIFIX """
        str_ident = str(tool_ident)
        print(f"⚙️ DRO [IHM] : Sélection tactile du burin Ident : {str_ident}")
        
        app = App.get_running_app()
        index_nouveau = app.lib_cutter.get_index_to_ident(str_ident)
        
        if index_nouveau != -1:
            # Récupération des configurations de l'outil sélectionné
            outil = app.lib_cutter.cutters[index_nouveau]
            def_ref = outil.config_defaut
            vol_ref = outil.config_volante
            #last_cutter = app.lib_cutter.active_cutter         # Pas utile ici, c'est juste pour le chemin !
            #last_cut_angle = app.lib_cutter.act_cut_angle_mont # Pas utile ici, c'est juste pour le chemin !
            
            # Récupération des paramètres machine
            from configurator.config import SETTINGS, MACHINE_CONFIG
            #machine_config = SETTINGS.get("machine_config", {})
            liste_multifix = MACHINE_CONFIG.get("index_multi_fix", [0, 18, 36, 54, 72, 90, 108, 126, 144, 162, 180, -162, -144, -126, -108, -90, -72, -54, -36, -18])
            
            # La position physique de la tourelle
            if hasattr(app, 'offset_page_instance') and app.offset_page_instance and hasattr(app.offset_page_instance, 'tourelle_angle'):
                [ptour, ptour_v] = app.offset_page_instance.tourelle_angle
                #[paxey, paxey_v] = app.offset_page_instance.axe_y_angle
            else:
                ptour, ptour_v = 0, False
                #paxey, paxey_v = 0, False
            angle_bridage_actuel = ptour / 1000 #+ paxey
            #mach_valide = True if ptour_v or paxey_v else False

            # Définition du callback local qui s'exécutera UNE FOIS que l'opérateur aura cliqué dans le popup
            def au_choix_configuration(mode, angle_offset, idx_mount, valide):
                # A. Choix de la structure cible (Défaut vs Volant)
                '''OLD Variante
                if mode == "def":
                    outil.grp_offset = outil.config_defaut
                else:
                    outil.grp_offset = outil.config_volante
                    # Si on force un nouvel index manuel, on applique les nouvelles valeurs mécaniques
                    if not valide:
                        outil.grp_offset["angle_machine"] = angle_offset
                        outil.grp_offset["idx_mount"] = [idx_mount, False]
                        # On invalide également les états de palpage et correction
                        outil.grp_offset["ofst_probbe"][2] = False
                        outil.grp_offset["ofst_machine"][2] = False
                '''
                #NEW Variante
                outil.set_grp_offset(mode)

                # B. Commutation des pointeurs globaux
                app.cutter_actif = outil
                app.lib_cutter.active_cutter = app.cutter_actif
                
                # C. On charge l'outil graphiquement (la fonction va lire dans outil.grp_offset réorienté)
                self.charger_burin_depuis_ident(str_ident, crant_mont=idx_mount, valide=valide)
                
                # D. On redessine les surbrillances bleues de la liste de gauche
                self.refresh_cut_list()
                
                # 💾 E. Sauvegarde dans le JSON utilisateur
                from configurator.config import save_json, SETTINGS_FILE
                try:
                    SETTINGS["user_last_select"]["selected_tool"] = [str_ident, idx_mount, mode]
                    save_json(SETTINGS_FILE, SETTINGS)
                    print(f"💾 [ settings ] : Outil chargé en mode '{mode}' à l'index tourelle {idx_mount}°")
                except Exception as e:
                    print(f"⚠️ Erreur lors de la sauvegarde : {e}")

            # Ouverture du Popup de choix mécanique
            popup = SelectionIndexPopup(
                config_def=def_ref, 
                config_vol=vol_ref, 
                angle_bridage=angle_bridage_actuel, 
                liste_multifix=liste_multifix, 
                callback_validation=au_choix_configuration
            )
            popup.open()

    def trier_bibliotheque_outils(self, par_nom: bool = True) -> dict:
        """
        📊 LE TRIEUR COMPACT UNIVERSEL (Version 7.2) :
        Sépare la bibliothèque en 3 paquets (Actif, Tourelle, Armoire).
        L'argument par_nom (True/False) choisit dynamiquement la clé de la lambda !
        """
        liste_brute = self.cutter.parent.cutters if (self.cutter and self.cutter.parent) else []

        outil_actif = self.cutter
        ident_actif = self.active_tool_ident 
        outils_tourelle = []
        outils_armoire = []
        # Ajouter le flag
        lib_not_save = False    # Flag pour identifier si un cutter de la lib. à des modifications non enregistrées

        # 🔄 Boucle unique de répartition optimisée en amont
        for burin in liste_brute:
            ident_burin = str(burin.ident)

            if burin and burin.modified_not_save:   # Màj du flag pour la bibliothèque
                lib_not_save = True

            if ident_burin == ident_actif:
                #continue # On isole l'outil actif de la broche
                pass
            
            if burin.tool_mount is not None:
                outils_tourelle.append(burin)
            else:
                outils_armoire.append(burin)

        self.cutter.parent.lib_not_save = lib_not_save    # Sauvegarder notre résultat dans la bibliothèque

        # 🟢 L'AIGUILLAGE DE LA LAMBDA MAGIQUE :
        if par_nom:
            # Mode A : Tri par ordre alphabétique du nom
            cle_tri = lambda b: str(b.name).upper()
        else:
            # Mode B : Tri par numéro d'identifiant croissant (converti en int pour l'ordre numérique)
            cle_tri = lambda b: int(b.ident)

        # Application du pinceau de tri choisi
        outils_tourelle.sort(key=cle_tri)
        outils_armoire.sort(key=cle_tri)

        return {
            "actif": outil_actif,
            "tourelle": outils_tourelle,
            "armoire": outils_armoire,
            "lib_not_save": lib_not_save        #Ajouter éventuellement au retour:
        }

    def refresh_cut_list(self):
        """
        🎨 LE PINCEAU DU MAGASIN VIRTUEL (Version 7.2) :
        Récupère le dictionnaire trié et instancie les widgets CutLineSelect.
        """

        # 🟢 LE VERROU CNC : On vérifie que Kivy a bien fini de lier l'ID dans le dictionnaire !
        if "dashboard_box" not in self.ids or "box_select_tool" not in self.ids.dashboard_box.ids:
            print("🚧 [IHM Outils] ID conteneur non disponible en RAM. Rendu différé.")
            return
        else:
            #print("🟢 [IHM Outils] ID conteneur disponible en RAM.")
            pass

        # 1. On cible la box verticale du .kv de manière sécurisée
        box_magasin = self.ids.dashboard_box.ids["box_select_tool"]
        box_magasin.clear_widgets()

        if not self.cutter:
            return

        # 2. 📊 Récupération du colis trié via notre fonction dédiée
        colis_outils = self.trier_bibliotheque_outils()
        
        outil_actif = colis_outils["actif"]
        outils_tourelle = colis_outils["tourelle"]
        outils_armoire = colis_outils["armoire"]
        _ = colis_outils["lib_not_save"]    # pas d'utilité dans cette fonction

        # 3. ➕ INJECTION DES LIGNES COMPACTES PAR SECTEURS 
        #if outil_actif:
            #self.ids.dashboard_box.ids["box_actif_tool"].clear_widgets()
            #self.ids.dashboard_box.ids["box_actif_tool"].add_widget(CutLineSelect(outil_actif, self, est_actif=True))

        for index_loop, burin in enumerate(outils_tourelle):
            self._add_separation_titre_si_besoin(box_magasin, "   MONTÉS SUR PORTES-OUTILS", index_loop)
            box_magasin.add_widget(CutLineSelect(burin, self, est_actif=(burin.ident == outil_actif.ident)))

        for index_loop, burin in enumerate(outils_armoire):
            self._add_separation_titre_si_besoin(box_magasin, "    DANS L'ARMOIRE", index_loop)
            box_magasin.add_widget(CutLineSelect(burin, self, est_actif=(burin.ident == outil_actif.ident)))

        # Bouton d'ajout universel en bas
        btn_nouveau = Button(
            text="➕ Ajouter un Nouveau Burin dans l'Armoire",
            bold=True,
            font_size="12sp",
            size_hint_y=None,
            height=dp(45),
            background_color=[0.12, 0.45, 0.38, 1], 
            background_normal="" 
        )
        box_magasin.add_widget(btn_nouveau)
    def _add_separation_titre_si_besoin(self, conteneur_box, titre: str, idx_element: int):
        """ 📐 LISERÉ TECHNIQUE DISCRET :
        Ajoute une étiquette de délimitation de zone grise ('📌 MONTÉS...', '📦 DANS L'ARMOIRE')
        uniquement au-dessus du tout premier outil de la famille (index 0).
        """
        if idx_element == 0:  # Condition indispensable pour ne l'afficher qu'une seule fois !
            from kivy.uix.label import Label
            from kivy.metrics import dp
            
            # Création de la ligne de texte de séparation compacte
            sep = Label(
                text=str(titre), 
                color=[0.8, 0.8, 0.85, 1], # Blanc cassé
                font_size="11sp", 
                bold=True,
                size_hint_y=None, 
                height=dp(22),
                halign="left"
            )
            # Liaison pour aligner scrupuleusement le texte à l'extrême gauche de la zone
            sep.bind(size=lambda instance, size: setattr(instance, 'text_size', size))
            
            conteneur_box.add_widget(sep)

    def modifier_offset_couche(self, texte_saisi: str, nom_axe: str, idx_couche: int):
        """
        📐 LE CONVERTISSEUR DE MICRONS (V_7.2) :
        Prend la saisie en mm (ex: '0.040'), la convertit en microns bruts (40)
        et met à jour la liste à 3 couches [Palpeur, Usure, Fine] en RAM.
        """
        # 1. Nettoyage de la chaîne de caractères (virgule d'atelier -> point informatique)
        texte_propre = str(texte_saisi).strip().replace(',', '.')
        
        # 2. Sécurité : Extraction de la valeur numérique en mm
        try:
            valeur_mm = float(texte_propre) if texte_propre else 0.0
        except ValueError:
            print(f"⚠️ [IHM Outils] Valeur incorrecte ignorée : '{texte_saisi}'")
            return

        # 3. Conversion en microns entiers (Mathématique d'atelier)
        valeur_micron = int(round(valeur_mm * 1000.0))

        if not self.cutter:
            return

        # 4. 🔀 Aiguillage chirurgical selon l'axe demandé
        if nom_axe == "vert": # L'axe vertical (X - Diamètre)
            if hasattr(self.cutter, 'offset_vert') and len(self.cutter.offset_vert) > idx_couche:
                # Écriture dans la couche demandée (0 = Palpeur, 2 = Ajustement)
                self.cutter.offset_vert[idx_couche] = valeur_micron
                print(f"RAM 💾 : Outil ID:{self.cutter.ident} - Axe X Layer {idx_couche} mis à jour : {valeur_micron} µm")

        elif nom_axe == "hor": # L'axe horizontal (Z - Longitudinal)
            if hasattr(self.cutter, 'offset_hor') and len(self.cutter.offset_hor) > idx_couche:
                self.cutter.offset_hor[idx_couche] = valeur_micron
                print(f"RAM 💾 : Outil ID:{self.cutter.ident} - Axe Z Layer {idx_couche} mis à jour : {valeur_micron} µm")

        # 5. 🚨 LE FLAG DE VEILLE : L'outil en RAM est devenu différent du JSON !
        self.cutter.modified_not_save = True
        
        # 🔄 REPEINTURE INSTANTANÉE EN CHAINE :
        # A. On secoue le magasin de gauche pour que son badge de ligne vire à l'orange [RAM] !
        self.refresh_cut_list()
        
        # B. On force la mise à jour immédiate de nos propres Properties Kivy pour recalculer les sommes
        self.offset_vert = list(self.cutter.offset_vert)
        self.offset_hor = list(self.cutter.offset_hor)

    def on_champ_click(self, widget_target, convert_func, write_action, label_abbr: str = None):
        """ 🎯 CHANGER LOCAL DE SECURITE ALLÉGÉ """

        # 1. 🔍 Extraction automatique des métadonnées (Nom et Unité) selon l'abréviation du .kv
        # Utilisation de .get() pour éviter tout crash si la clé n'existe pas (valeur de secours)
        metadata = self.label_abbr_dico.get(label_abbr, ("Champ Spécifique", None))
        label_cell = metadata[0]
        unit_cell = metadata[1]

        #print("on_click to label, steep 1")
        if not self.mode_edition_actif: 
            #print(f"on_click to {label_cell}, steep 1_stoped")
            #return TODO: Temporairement désactivé
            pass

            # 3. ⚡ Le protocole de rafraîchissement d'IHM (Le Callback de succès/échec)
            def run_ui_refresh(status_code: str):
                if status_code != "OK":
                    from part.draw_tool.popup_segment import ErrorInputPopup
                    # Si échec, on va chercher le texte fautif dans le calque éphémère
                    texte_errone = self.ids.input_text_floating.text if (unit_cell is None or not self.mode_tactile_actif) else "Saisie"
                    popup_erreur = ErrorInputPopup(txt_error=texte_errone, case_dest=label_cell, timer_off=4.0)
                    popup_erreur.open()
                    return

                # Si OK : Synchronisation nominale de la RAM locale de l'IHM
                print(f"✅ [IHM Outils] {label_cell} mis à jour avec succès en RAM.")
                #self.offset_vert = list(self.cutter.offset_vert)
                #self.offset_hor = list(self.cutter.offset_hor)
                self.cutter.modified_not_save = True

                if "dashboard_box" in self.ids:
                    dash = self.ids["dashboard_box"]
                    dash.property('ihm_initialisee').dispatch(dash)
                    
                self.refresh_cut_list()

        # 🚀 ON PASSE TOUTE LA PATATE CHAUDE À LA CLASSE MÈRE !
        self.open_floating_input(widget_target, widget_target.text, convert_func, write_action, run_ui_refresh, unit_cell, label_cell)

    def basculer_mode_edition(self, widget_bouton):
        """ 🎛️ LE MODE EDITION : Ouvre les vannes ou fige les cotes dans le JSON """
        self.mode_edition_actif = not self.mode_edition_actif

        if self.mode_edition_actif:
            print("IHM ⚙️ : Mode édition ACTIVÉ. TextInputs d'offsets ouverts.")
            self.set_status("EDITION") # Témoin général à l'orange réglage
            widget_bouton.text = "✅ Valider"
            widget_bouton.background_color = [0.1, 0.6, 0.2, 1] # Vert validation
        else:
            print("IHM ⚙️ : Mode édition DÉSACTIVÉ. Verrouillage des champs.")
            self.set_status("NOMINAL") # Témoin général repasse au vert nominal
            widget_bouton.text = "✏️ Éditer Burin"
            widget_bouton.background_color = [0.2, 0.4, 0.6, 1] # Bleu standard
            
            # 💾 SAUVEGARDE INDUSTRIELLE : Si l'outil a des modifs en RAM, on écrit sur le disque !
            if hasattr(self.cutter, 'modified_not_save') and self.cutter.modified_not_save:
                self.cutter.parent.save_library() # Écrit physiquement le JSON
                self.cutter.modified_not_save = False # On éteint l'alerte
                self.refresh_cut_list() # Le petit badge de gauche redevient gris/bleu propre
                print(f"JSON 💾 : Modifications du burin ID:{self.cutter.ident} gravées sur le disque.")

    def list_insert_for_spinner(self):
        # Charger la liste des plaquettes disponibles pour le Spinner du .kv
        if self.cutter.parent and hasattr(self.cutter.parent, 'insert_lib'):
            donnees_brutes = self.cutter.parent.insert_lib.get_all_insert_list()
            
            # On fabrique la liste de texte pour Kivy à partir des dictionnaires neutres
            valeurs_spinner = []
            for item in donnees_brutes:
                rayon_mm = item["radius"] / 1000.0
                # Exemple de mise en forme d'atelier : "1 - CCMT09 (R:0.400)"
                valeurs_spinner.append(f"{item['ident']} - {item['name']} (R:{rayon_mm:.3f})")
                
            return valeurs_spinner
        else:
            # Sécurité si les liens ne sont pas encore totalement initialisés en RAM
            return ["0 - Sans Plaquette"]

    def preparer_affichage_burin_complet(self, *args):
        """ 📐 RENDU CAO FILAIRE : Assemble le manche et la plaquette sous l'angle Multifix """
        import math
        
        if not self.body_data:
            self.canvas_points = []
            return

        # 1. Fusion de l'angle du manche (lead_angle) et de la tourelle (mount_angle)
        angle_total_milli = 45000   #self.mount_angle + getattr(self.cutter, 'lead_angle', 0)
        angle_rad = (angle_total_milli / 1000.0) * (math.pi / 180.0)
        
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Gestion du profil miroir gauche/droite
        facteur_miroir = -1.0 if getattr(self.cutter, 'lead_reverse', False) else 1.0
        echelle = 0.002 # Conversion microns -> pixels d'écran

        points_finaux_canvas = []
        
        # [A. Tracé cinématique du manche]
        for pt in self.body_data:
            z_brut = pt[0] * facteur_miroir
            x_brut = pt[1]
            
            z_rot = z_brut * cos_a - x_brut * sin_a
            x_rot = z_brut * sin_a + x_brut * cos_a
            
            # On décale de +150, +50 pour centrer proprement la tourelle dans la zone noire
            points_finaux_canvas.extend([150 + (z_rot * echelle), 50 + (x_rot * echelle)])

        # [B. Tracé cinématique de la plaquette connectée]
        if self.cutter.insert and hasattr(self.cutter.insert, 'drawing'):
            clear_z, clear_x = getattr(self.cutter, 'clearance', [0, 0])
            
            # On parcourt la liste d'objets CutInsertPntDraw créés par l'insert
            for pnt_ins in self.cutter.insert.drawing:
                # pnt_ins.brut_pos contient [Z, X] en microns de la plaquette
                z_ins_brut = (pnt_ins.brut_pos[0] + clear_z) * facteur_miroir
                x_ins_brut = pnt_ins.brut_pos[1] + clear_x

                z_ins_rot = z_ins_brut * cos_a - x_ins_brut * sin_a
                x_ins_rot = z_ins_brut * sin_a + x_ins_brut * cos_a

                points_finaux_canvas.extend([150 + (z_ins_rot * echelle), 50 + (x_ins_rot * echelle)])

        # Envoi direct au fichier .kv pour rafraîchir le tracé Line
        self.canvas_points = points_finaux_canvas

    def screen_focused(self):
        """
        RÉVEIL DE LA PAGE CUTTER : Appelée par le main.py quand la page prend le focus.
        S'assure que si un Popup volant a modifié un outil, la page se rafraîchit proprement.
        """

        # Actualisation de la liste des burins à l'écran
        self.available_inserts = self.list_insert_for_spinner()
        self.charger_burin_depuis_ident(self.active_tool_ident)
        
        #print(f"[PAGE CUTTER] Tourelle synchronisée en RAM.")
        #print(f"[PAGE CUTTER] outil courant: {self.active_tool_ident} ({self.cutter.cadran}), icône cadran: {self.cutter.get_icone_cadran()}.")
        #print(f"[PAGE CUTTER] outil nom dans CutterManager(): {self.cutter.name}")

    def update_axes_val(self, donnees_fraiches: dict):
        """
        ⚙️ PASSERELLE DE RÉCEPTION ESP32 (60Hz) :
        Appelée en continu par le main.py lorsque cet écran a le focus.
        (si l'horloge 60Hz activée)
        """
        # 1. 🛡️ FILTRE DE SÉCURITÉ AUTOMATIQUE (Votre excellente idée !)
        # Si la machine est à None ou absente, on ignore complètement le paquet
        if not hasattr(self, 'machine') or self.machine is None:
            return

        # 2. 🧠 PRÉPARÉ POUR LE FUTUR :
        # C'est ici que viendra votre logique pour le "Probe" (Palpeur d'outils)
        # On pourra lire les cotes en direct : donnees_fraiches["Z_absolu"], etc.
        pass

    def ico_idx_dro(self, arg_x, arg_z, list_for_main = False):
        radius = self.cutter.insert.drawing[0].radius_base
        x_val = z_val = 0
        if arg_x == 1:
            x_val = -radius
        elif arg_x == 2:
            x_val = radius
        if arg_z == 1:
            z_val = -radius
        elif arg_z == 2:
            z_val = radius
        icone = f"bitmaps/tool_offset_{str(arg_x)}_{str(arg_z)}.png"

        # TODO: Ne fonctionne pas !!!
        if 'btn_dro_ofst'  in self.ids["dashboard_box"].ids:
            self.ids["dashboard_box"].ids["btn_dro_ofst"].source_image = icone

        if list_for_main:
            return [x_val, z_val, True, icone]

        return icone

    def ouvrir_popup_ofst_bec(self):
        app = App.get_running_app()
        # On récupère les valeurs actuelles depuis votre structure JSON
        # Exemple: [0, 0, False]
        #coord_actuelles = self.donnees_outil["tourelle_def"]["idx_dro"]
        coord_actuelles = self.cutter.grp_offset["idx_dro"]
        
        # Ouverture du Popup en lui passant la fonction de callback
        popup = OfstBecPopup(coord_actuelles=coord_actuelles, callback_validation=self.set_ofst_bec)
        popup.open()

    def set_ofst_bec(self, x, y, valide, img):
        app = App.get_running_app()
        # 1. Mise à jour de votre structure de données JSON
        #self.donnees_outil["tourelle_def"]["idx_dro"] = [x, y, valide]
        self.cutter.grp_offset["idx_dro"] = [x, y, valide]
        app.dro_visual_offset_cut = self.ico_idx_dro(x, y, True)
        
        # 2. Optionnel: Forcer le rafraîchissement de l'image de votre bouton principal
        # Si app.dro_visual_offset_cut dépend de ces index, changez sa valeur ici.
        print(f"Données mises à jour dans le JSON: [{x}, {y}, {valide}]")

    def select_crant(self, name_option):
        if name_option == "vol":
            self.cutter.set_grp_offset("vol")
        else:
            self.cutter.set_grp_offset("def")

    # Fonction fantôme à analyser
    def rafraichir_liste_tourelle_tactile(self):
            """
            🔄 BOUTONNAGE DYNAMIQUE (En attente de montage) :
            Sert de filet de sécurité pour l'on_kv_post.
            C'est ici qu'on viendra boucler sur self.cutter.available_cutters_list.
            """
            pass # Ne fait rien pour l'instant, mais évite le crash !


from kivy.uix.popup import Popup
#from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.image import Image
#from kivy.uix.button import Button
#from kivy.properties import ListProperty, ObjectProperty

class OfstBecPopup(Popup):
    # Propriété pour stocker temporairement la sélection [X, Y] avant validation
    selection_temporaire = ListProperty([0, 0,False, "bitmaps/icone.png"])
    
    def __init__(self, coord_actuelles, callback_validation, **kwargs):
        super().__init__(**kwargs)
        self.title = "Décalage depuis le centre du bec de coupe du burin" #"Sélection du décalage DRO"
        self.size_hint = (0.3, 0.5) # Ajustable selon vos besoins
        self.callback_validation = callback_validation
        
        # On initialise la sélection avec les valeurs actuelles du JSON [X, Y]
        self.selection_temporaire = [coord_actuelles[0], coord_actuelles[1], coord_actuelles[2],"bitmaps/icone.png"]
        
        # Layout principal vertical
        layout_principal = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Grille 3x3 pour les 9 icônes
        grille = GridLayout(cols=3, rows=3, spacing=5, size_hint_y=0.8, width=self.height)
        
        # Génération des 9 boutons (Y de 0 à 2, X de 0 à 2)
        # Note: Ajustez l'ordre des boucles selon la disposition visuelle souhaitée (Haut/Bas/Gauche/Droite)
        for y in [1,0,2]:
            for x in [1,0,2]:
                chemin_icone = f"bitmaps/tool_offset_{x}_{y}.png"
                
                # Bouton de base "invisible" servant de zone de clic
                btn = ToggleButton(
                    group="dro_positions",
                    state="down" if [x, y] == [self.selection_temporaire[0], self.selection_temporaire[1]] else "normal",
                    #background_normal="", # Supprime le fond gris par défaut de Kivy
                    #background_down=""    # Supprime le fond bleu par défaut au clic
                )
                
                # Optionnel : Ajouter une bordure ou une couleur de fond pour le bouton sélectionné
                # (Kivy gère cela très bien si vous voulez tramer l'icône sélectionnée)
                
                # L'image imbriquée qui respecte le ratio d'origine sans déformation
                img_bouton = Image(
                    source=chemin_icone,
                    allow_stretch=True,
                    keep_ratio=True,
                    pos=btn.pos,
                    size=btn.size
                )
                # On force l'image à suivre la taille et la position du bouton
                btn.bind(pos=img_bouton.setter('pos'), size=img_bouton.setter('size'))
                btn.add_widget(img_bouton)
                # Association des coordonnées au bouton via une fonction lambda
                btn.bind(on_release=lambda instance, cx=x, cy=y: self.choisir_position(cx, cy))
                grille.add_widget(btn)
                
        layout_principal.add_widget(grille)
        
        # Ligne de boutons OK / Annuler
        action_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.2)
        
        btn_annuler = Button(text="Annuler", on_release=self.dismiss)
        btn_ok = Button(text="OK", on_release=self.valider)
        
        action_layout.add_widget(btn_annuler)
        action_layout.add_widget(btn_ok)
        
        layout_principal.add_widget(action_layout)
        self.content = layout_principal

    def choisir_position(self, x, y):
        self.selection_temporaire = [x, y,self.selection_temporaire[2], f"bitmaps/tool_offset_{x}_{y}.png"]

    def valider(self, instance):
        # Appelle la fonction de sauvegarde avec le résultat et True pour valider l'état
        self.callback_validation(self.selection_temporaire[0], self.selection_temporaire[1],True, self.selection_temporaire[3])
        self.dismiss()


class SelectionIndexPopup(Popup):
    def __init__(self, config_def, config_vol, angle_bridage, liste_multifix, callback_validation, **kwargs):
        super().__init__(**kwargs)
        self.title = "Configuration de l'indexation de l'outil (Multifix)"
        self.size_hint = (0.8, 0.95)
        self.callback_validation = callback_validation
        
        layout_principal = BoxLayout(orientation='vertical', spacing=15, padding=15)
        
        # --- 1. ZONE DES REFERENCES ENREGISTREES (DEFAUT / VOLANTE) ---
        refs_layout = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=0.14)
        
        # Calcul de l'accessibilité
        # Note: adaptateur selon votre choix d'avoir fusionné en angle_offset ou non
        ang_def = config_def.get("angle_machine", 0) 
        ang_vol = config_vol.get("angle_machine", 0)
        
        acc_def, idx_def, angle_def = self.check_angle_accessible(ang_def, angle_bridage, liste_multifix)
        acc_vol, idx_vol, angle_vol = self.check_angle_accessible(ang_vol, angle_bridage, liste_multifix)
        
        # Bouton DEFAUT
        txt_def = f"CONFIG. DEFAUT  réf: {ang_def}°\n" + (f"Index {idx_def+1}: {angle_def}° (Angle total: {ang_def}°)" if acc_def else "NON ACCESSIBLE")
        self.btn_def = Button(text=txt_def, disabled=not acc_def, halign="center")
        self.btn_def.bind(on_release=lambda instance: self.valider_choix("def", ang_def, idx_def, True))
        
        # Bouton VOLANTE
        txt_vol = f"CONFIG. VOLANTE  réf: {ang_vol}°\n" + (f"Index {idx_vol+1}: {angle_vol}° (Angle total: {ang_vol}°)" if acc_vol else "NON ACCESSIBLE")
        self.btn_vol = Button(text=txt_vol, disabled=not acc_vol, halign="center")
        self.btn_vol.bind(on_release=lambda instance: self.valider_choix("vol", ang_vol, idx_vol, True))
        
        refs_layout.add_widget(self.btn_def)
        refs_layout.add_widget(self.btn_vol)
        layout_principal.add_widget(refs_layout)
        
        # --- 2. SELECTION MANUELLE D'UN NOUVEL INDEX ---
        layout_principal.add_widget(Label(text="Ou choisir une autre position volante", size_hint_y=0.06))
        
        # Grille des index Multifix classés par quadrants (4 colonnes de 5 lignes pour vos 20 index)
        #grille_multifix = GridLayout(cols=4, spacing=8, size_hint_y=0.5)
        grille_multifix = BoxLayout(orientation= "horizontal", spacing=8, size_hint=(1,0.8))
        box_1ang= BoxLayout(orientation= "vertical", spacing=8, size_hint=(0.25,1))
        box_2ang= BoxLayout(orientation= "vertical", spacing=8, size_hint=(0.25,1))
        box_3ang= BoxLayout(orientation= "vertical", spacing=8, size_hint=(0.25,1))
        box_4ang= BoxLayout(orientation= "vertical", spacing=8, size_hint=(0.25,1))
        grille_multifix.add_widget(box_1ang)
        grille_multifix.add_widget(box_2ang)
        grille_multifix.add_widget(box_3ang)
        grille_multifix.add_widget(box_4ang)

        #for idx_angle in liste_multifix:
        for num_idx, idx_val_angle in enumerate(liste_multifix):
            angle_resultat = (angle_bridage + idx_val_angle + 180) % 360 - 180
            btn_idx = Button(text=f"Index {num_idx+1}  (Angle total: {angle_resultat}°)", halign="center", font_size="14sp")
            # Si on clique sur un index libre, on applique l'angle résultant, le mode devient "vol" et le flag de validation passe à False
            btn_idx.bind(on_release=lambda instance, a_res=angle_resultat, idx=num_idx: self.valider_choix("vol", a_res, idx, False))
            #grille_multifix.add_widget(btn_idx)
            ang_idx = (idx_val_angle) % 360
            if ang_idx <90:
                box_1ang.add_widget(btn_idx)
            elif ang_idx <180:
                box_2ang.add_widget(btn_idx)
            elif ang_idx <270:
                box_3ang.add_widget(btn_idx)
            else:
                box_4ang.add_widget(btn_idx)

            
        layout_principal.add_widget(grille_multifix)
        
        # Bouton Annuler tout en bas
        layout_principal.add_widget(Button(text="Annuler la sélection", size_hint_y=0.1, on_release=self.dismiss))
        
        self.content = layout_principal

    def check_angle_accessible(self, angle_recherche, angle_bridage_actuel, liste_index_multifix, tolerance=0.1):
        """
        Vérifie si un angle visé est atteignable.
        Optimisé : le modulo de la cible est calculé une seule fois avant la boucle.
        """
        # 🚀 OPTIMISATION : Calculé une seule fois ici !
        angle_cible_normalise = angle_recherche % 360
        
        for num_idx, idx_val_angle in enumerate(liste_index_multifix):
            angle_combine = (angle_bridage_actuel + idx_val_angle) % 360
            
            # Gestion de la topologie circulaire (écart entre 359° et 1°)
            ecart = abs(angle_combine - angle_cible_normalise)
            if ecart > 180:
                ecart = 360 - ecart

            if ecart <= tolerance:
                return True, num_idx, idx_val_angle
                
        return False, None, None


    def valider_choix(self, mode, angle_offset, idx_mount, valide):
        """ Envoie les données choisies au callback de l'écran principal """
        self.callback_validation(mode, angle_offset, idx_mount, valide)
        #def au_choix_configuration(mode, angle_offset, idx_mount, valide):
        self.dismiss()



