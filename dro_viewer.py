# dro_viewer.py à la racine du projet

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.metrics import dp
#from copy import deepcopy
import copy
from kivy.app import App
from kivy.lang import Builder
from part.draw_pnt_manager import PointManager
from cutting_tool.cutter import CutterManager
from machine_tool.machine_data import MachineState
from reel_time.machine_mcu import CommManager
from common_widgets import ClickableLabel
from common_draw import ProfilCanvas, DashedLineWidget
import config as conf
from config import AXIS_CONFIG  
from screen_base.common_screen import BaseScreenLayout

# class pur python sans .kv
class AxisBox(BoxLayout):
    status = NumericProperty(0)
    axe_ident = StringProperty(None)

    def __init__(self, status=0, height_line=70, wide=True, special=None, **kwargs):
        super().__init__(**kwargs)

        # --- Props internes ---
        self.status = status
        self.height_line = height_line
        self.wide = wide
        self.special = special
        self.clickable_cells: dict = {}
        # --- Layout ---
        self.orientation = "horizontal" if wide else "vertical"
        self.size_hint_y = None
        self.spacing = 30 if wide else 10
        self.padding = (8, 1, 8, 10)
        # --- Canvas ---
        with self.canvas.before:
            self.bg_color = Color(*self._compute_bg_color())
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[15])
            self.border_color = Color(1, 1, 1, 0.6)
            self.border_line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 15), width=2)
        # Bind de mise à jour du canvas
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self.bind(status=self._update_colors)

        # Création du contenu
        self.build()

    def build(self):
        # Base
        self.ax_dim = AxisDim(
            axe_ident=self.axe_ident,
            size_hint_y=None,
            height=self.height_line
        )
        self.add_widget(self.ax_dim)

        # Complément éventuel
        self.ax_compl = None
        if self.special == "Yplus":
            self.ax_compl = AxisYplus(
                self.axe_ident,
                size_hint_y=None,
                height=self.height_line
            )
            self.add_widget(self.ax_compl)

        elif self.special == "Splus":
            # Futur module
            pass

    def on_kv_post(self, base_widget):
        self.clickable_cells = self.ax_dim._dim_clickables.copy()
        if self.ax_compl and self.ax_compl._clickables:
            # TODO merge clics
            pass

    def on_axe_ident(self, instance, value):
            if self.ax_dim:
                self.ax_dim.axe_ident = value
            if self.ax_compl:
                self.ax_compl.axe_ident = value
            print(f"Le texte a changé : {value}")

    # ---- Helpers ----

    def _compute_bg_color(self):
        return (
            (0, 1, 0, 0.15) if self.status > 0 else
            (1, 0, 0, 0.3) if self.status < 0 else
            (0.4, 0.4, 0.4, 0.1)
        )

    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, 15
        )

    def _update_colors(self, *args):
        self.bg_color.rgba = self._compute_bg_color()


# class avec .kv
class AxisDim(BoxLayout):
     # === Propriétés Kivy ===
    axe_ident = StringProperty(None)
    name_txt = StringProperty("X")
    val_base = NumericProperty(0)       #integer
    value_txt = StringProperty("54'321.000")  #String
    angle_txt = StringProperty("123.45")  #String
    val_unit = StringProperty("dist")
    val_diam = BooleanProperty(False)
    # === Variables Python ===
    dro_manager = None
    disp_factor = 1000  # Display factor: facteur pour passer une valeur: de base à affiché
    disp_dec = 3        # Display nombre de décimals à afficher
    status = 0          # Status de class <0 = Erreur ; >0 = OK ; 0 = initialisation

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    #def on_kv_post(self, base_widget):
    def on_axe_ident(self, instance, value):
        """Appelé après le chargement KV — ici on peut accéder à axe_ident"""
        #print(f"-> -> -> 1 init HeaderAxis: axe_ident: {self.axe_ident}")
        self._dim_clickables = {    # dict d'action associé lors de click
            self.ids.btn_name: {"click": self.label_clicked, "dbl_click": self.config_clicked},
            self.ids.btn_value: {"click": self.label_clicked},
            self.ids.btn_config: {"click": self.config_clicked}
        }

        if self.axe_ident:
             # Ex: "hor": {"screen": "z", "factor": 1, "numerator": 5, "denumerator": 1, "type": "unit_distance", "info":"profondeur trainard, absolu"}
            self.axe_config = copy.deepcopy(AXIS_CONFIG.get(self.axe_ident, {}))
            #print("-> -> -> 2 init HeaderAxis")

            if self.axe_config:
                # Nom affiché (ex: "Z", "X", "Y")
                self.name_txt = self.axe_config.get("screen", "?")
                # Diamètre si factor == 2
                self.val_diam = (self.axe_config.get("factor", 1) == 2)
                print(f"-> -> -> 3 val_diam: {self.val_diam} / factor: {self.axe_config.get("factor", 1)}")
                
                # Type ou ident d’unité associé (unit_distance / unit_angle / mm / inch / ...)
                unit_type = self.axe_config.get("type", self.val_unit)
                # Reccupération de l'ident de l'unitée active
                self.unit_id = conf.get_unit_id(unit_type)
                # Actualiser les variables d'unité
                if self.unit_id:
                    self.changed_unit(self.unit_id, refresh=False)
                else:
                    self.status = -1    # Marquer l'erreur
            
                #self.canvas.ask_update()  # force la redessiner le canvas
        else:
            print("axisDim à pas de  axe_ident")

    def new_val(self, val_base=None):
        '''     (val_base → val_disp)
        Conversion et mise au format d'une valeur reçue
        en unité de base vers unité affichée.
        - Si val_base=None: converti juste avec la nouvelle unité
        '''

        if isinstance(val_base, (int, float)):
            self.val_base = int(val_base)
        # DEBUG: (juste pour le debug décommenter/commenter la partie "elif")
        #elif val_base is not None:
        # A TESTER: elif __debug__ and val_base is not None:
        #    print(f"[HeaderAxis] ⚠ Valeur invalide reçue : {val_base}")
        #    return

        # Conversion
        val_calc = self.val_base / self.disp_factor

        # Formatage pour affichage
        self.value_txt = f"{val_calc:,.{self.disp_dec}f}".replace(',', "'")

    def changed_unit(self, new_unit, refresh=True):
        """
        Met à jour l'unité courante de l'objet et recalcul les valeurs affichées.
        
        Args:
            new_unit (str): identifiant de la nouvelle unité (ex: 'mm', 'inch', 'deg', etc.)
        """
        try:
            # Récupération des infos de l'unité
            unit_data = conf.get_unit_config(new_unit)
                # unit_data = {
                #   "unit_id": str,  "type": str,
                #   "factor": float, "decimals": int,
                #   "label": str
                # }
                # OU: unit_data = "ValueError" Si pas résolu

            # Mise à jour des attributs
            self.val_unit = unit_data["label"]
            self.disp_factor = unit_data["factor"] * (0.5 if self.val_diam else 1.0)
            self.disp_dec = unit_data["decimals"]
            self.unit_id = unit_data["unit_id"]  # pratique pour conversions ultérieures
            if self.status < 1:
                self.status = 1

            # Rafraîchissement ou recalcul des valeurs affichées
            if refresh:
                self.new_val()

        except ValueError as e:
            # Cas où l'unité n'existe pas
            self.status = -1
            print(f"[Erreur changed_unit] Unité inconnue : {new_unit}")


    def label_clicked(self, widget):
        print(f"Label clicked: {self.name_txt} - {widget.text}")
    def config_clicked(self, widget):
        print(f"Config_clicked: id: {self.axe_ident}  name: {self.name_txt}")

class AxisYplus(BoxLayout): pass


# A supprimer, OBSOLETTE ou inutilisé
class AxisBox_OLD(BoxLayout):
    status = NumericProperty(0)
    axe_ident = StringProperty(None)

    def __init__(self, status=0, height_line=80, wide=True, special=None, **kwargs):
        super().__init__(**kwargs)

        self.status = status
        self.height_line = height_line
        self.wide = wide
        self.special = special

        self.clickable_cells: dict = {}

        self.orientation = "horizontal" if wide else "vertical"
        self.spacing = 30 if wide else 10
        self.padding = (8, 15)

        # === Canvas ===
        with self.canvas.before:
            # --- Fond ---
            self.bg_color = Color(*self._compute_bg_color())
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[15]
            )
            # --- Bordure ---
            self.border_color = Color(1, 1, 1, 0.6)
            self.border_line = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, 15
                ),
                width=2
            )
        # Recalcul des tailles/positions quand le widget bouge
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self.bind(status=self._update_colors)
        self.build()
    
    def build(self):
        self.ax_dim = AxisDim(self.axe_ident, heigt=self.height_line)
        self.ax_compl = None
        self.add_widget(self.ax_dim)
        if self.special == "Yplus":
            self.ax_compl = AxisYplus(self.axe_ident, heigt=self.height_line)
            self.add_widget(self.ax_compl)
        elif self.special == "Splus":
            #TODO: A faire: self.ax_compl = AxisSplus(self.axe_ident, heigt=self.height_line)
            #TODO: A faire: self.add_widget(self.ax_compl)
            pass
    
    def on_kv_post(self, base_widget):
        # completter le dict des cellules cliquables et leurs actions associées
        self.clickable_cells = self.ax_dim._dim_clickables.copy()
        if self.ax_compl and self.ax_compl._clickables :
            #TODO: Ajouter une copy de ax_compl._clickables au dict self.clickable_cells
            pass


    # Mise en forme
    def _compute_bg_color(self):
        return (
            (0, 1, 0, 0.15) if self.status > 0 else
            (1, 0, 0, 0.3) if self.status < 0 else
            (0.4, 0.4, 0.4, 0.1)
        )
    
    def _update_canvas(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

        self.border_line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, 15
        )
class AxisFrame(Widget): pass
class HeaderAxis(AxisDim, AxisFrame):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clickable_cells: dict = {}

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)  # AxisDim on_kv_post s'exécute → _dim_clickables créé
        self.clickable_cells = self._dim_clickables.copy()
        #return super().on_kv_post(base_widget)
class DroAxis(AxisDim, AxisFrame):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clickable_cells: dict = {}

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)  # AxisDim on_kv_post s'exécute → _dim_clickables créé
        self.clickable_cells = self._dim_clickables.copy()
        #return super().on_kv_post(base_widget)
class DroYAxis(AxisDim, AxisYplus, AxisFrame):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clickable_cells: dict = {}

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)  # AxisDim on_kv_post s'exécute → _dim_clickables créé
        self.clickable_cells = self._dim_clickables.copy()
class DroAxisBase(Widget): pass
class DroAxis(DroAxisBase): pass
class DroAxis_Y(DroAxisBase): pass
class DroAxis_S(DroAxisBase): pass
#class DroAxis_R(DroAxisBase): pass
# fin de à supprimer

class DroHeader(BoxLayout): 
    dro_manager = None
    pass

class DroDro(BoxLayout): pass
#class DroGraph(BoxLayout):pass
class DroGraph(BoxLayout):
    """
    ========================================================================
    🛠️ FEUILLE DE ROUTE : LOGIQUE DE FONCTIONNEMENT DU GRAPHIQUE DRO (À FAIRE)
    ========================================================================
    
    1. LE MOTEUR GRAPHIQUE (Toile blanche) :
       Utiliser notre classe 'cd.ProfilPiece(Widget)' comme instance indépendante 
       dédiée à l'écran DRO. En tant que Widget pur, elle nous donne un accès direct 
       au canvas de la carte graphique pour un tracé instantané à 60Hz sans lag.
       >> Ps: modifier cette class pour quel accepte : (contrôler ce qui existe déjà !)
        - des offsets (jusqu'au point 0,0 (sans scale) et la position machine(avec scale))
        - l'échelle (scale)
        - une deuxième liste de segments et l'épaisseur de trait pour chaque liste (voir une troisième si l'on compte le dessin du burin !)
       >> ne pas oublier que cette class sert aussi ailleur (dessin de détail pour les Shapes), donc adapté le reste des appels!
       
    2. LE PRÉPARATEUR DE SÉGMENTS (Uniformisation) :
       Utiliser notre fonction dédiée 'cd.create_entities_for_profil' pour mouliner 
       nos listes brutes. Elle ignore les couleurs de surbrillance locale du pop-up 
       pour uniformiser tout le profil, tout en conservant 'origin_color' intacte.

    3. LE CONTENEUR DE SÉCURITÉ (Fichier .kv) :
       Remplacer le 'BoxLayout' actuel par un 'StencilView' directement dans le .kv.
       Cela servira de masque de découpage pour couper proprement tout le dessin 
       qui déborde de notre cadre bleu nuit lors des déplacements des axes du tour.
       
    4. LES VARIABLES D'ANIMATION (__init__) :
       Déclarer dans le constructeur nos manettes de contrôle :
       - self.scale = 2.5        # Échelle/Zoom de départ (pixels par mm)
       - self.offset_base_x = 0  # Décalage X à la souris (Glisser-Déposer)
       - self.offset_base_y = 0  # Décalage Y à la souris
       
    5. LE REPÈRE DE CONSTRUCTION (Le secret mathématique) :
       Fixer l'origine absolue (X=0, Y=0) PILE sur la pointe de notre burin (l'outil).
       - Le burin reste fixe au point d'ancrage de la boîte + l'offset de la souris.
       - La pièce tourne et se déplace autour de ce point 0,0 en fonction des axes.
       
    6. LA FORMULE MATHÉMATIQUE ULTRA-OPTIMISÉE (Avant la boucle de dessin) :
       Pour éviter les calculs répétitifs à chaque déplacement, on regroupe les 
       offsets constants AVANT de passer en revue la liste de points :
       
       Pixel_X = Position_Boite_X + Offset_Base_X_pixels + (Machine_X + Piece_X) * scale
       
    7. LE DOUBLE TRAIT COMPARAISON (Usinage vs Dessin) :
       Pour voir les modifications en direct sans polluer l'écran, on dessine DEUX FOIS :
       - COUCHE 1 (Dessous) : Appel de 'create_entities_for_dro' sur la liste machine.
         Couleur rouge foncé, épaisseur large (width=2.5).
       - COUCHE 2 (Dessus) : Appel de 'create_entities_for_dro' sur la liste dessin.
         Couleur verte, épaisseur plus fine (width=1.5).
         
       Résultat : Si c'est identique, le vert cache le rouge (ligne verte liseré rouge).
       Si c'est différent (ex: gorge modifiée), l'ancien profil réapparaît en rouge vif !
       
    8. BOUTON RECENTRE :
       Si le dessin sort de l'écran, reset l'offset de base au centre de la boîte.
    ========================================================================
    """
    """
    ========================================================================
    🛠️ NOTES DE ROUTE : MODE CINÉMATIQUE INTERACTIF (BOÎTE DE TRANSFERT)
    ========================================================================
    
    1. LE COMMUTATEUR DE SIGNAL ('move_mode') :
       Géré par le formulaire principal (Chef d'orchestre), ce bouton poussoir
       possède deux statuts exclusifs pour l'usinage et l'inspection :
       - 'Piece_Mobile' : Le burin reste fixe à l'écran, la pièce glisse (Usinage standard).
       - 'Burin_Mobile' : La pièce est ancrée sur l'écran, le burin glisse (Inspection).

    2. LE SECRET DE LA TRANSITION "SANS SECOUSSE" :
       Au moment précis du clic sur 'move_mode', l'image à l'écran ne doit pas sauter.
       On réalise un transfert de référentiel mathématique en jouant sur les offsets :
       
       -> Passage vers 'Piece_Mobile' :
          - On fige le burin : calque_outil.offset_add += calque_outil.offset_move
          - On coupe son moteur dynamique : calque_outil.offset_move = [0, 0]
          - On compense la pièce : calque_piece.offset_add -= position_actuelle_regles_pixels
          - On active son moteur dynamique : calque_piece.offset_move = position_actuelle_regles_pixels
          
       -> Passage vers 'Burin_Mobile' :
          - On fige la pièce : calque_piece.offset_add += calque_piece.offset_move
          - On coupe son moteur dynamique : calque_piece.offset_move = [0, 0]
          - On compense le burin : calque_outil.offset_add -= position_actuelle_regles_pixels
          - On active son moteur dynamique : calque_outil.offset_move = position_actuelle_regles_pixels

    3. LES 3 POUSSOIRS COMPLÉMENTAIRES DE L'INTERFACE :
       - Bouton 'Auto-Zoom' : Calcule le scale idéal "Pleine page" de la pièce, l'inscrit 
         dans self.scale, le synchronise sur le burin, puis repasse immédiatement en Manuel.
       - Bouton 'Auto-Centre' : Si actif, calcule les min/max géométriques de la pièce 
         pour forcer un décalage self.offset_0 centré au milieu du cadran.
       - Bouton 'Zoom-Def' & 'Recentrer' : Restaurations de secours. En mode suivi outil,
         'Recentrer' réinjecte self.offset_0_def pour caler le burin à 1/3 haut et 2/3 droite.

    4. SYNTAXE PYTHON EXTRÊME :
       - Remplacer tous les anciens dict{None} par [] (listes d'entités géométriques).
       - La clé "pos" à l'intérieur de self.offsettool_entities prend obligatoirement des guillemets.
       - Utiliser 'is not None' pour autoriser [] (vider la machine) et rejeter None (ignorer la mise à jour).
    ========================================================================
    """

    # Couleur dessin
    COLOR_CAO = (0.5, 0.8, 0.1, 0.8)
    COLOR_FAO = (0.1, 0.8, 0.1, 1)
    # LE COMMUTATEUR DE SIGNAL : False = Burin_Mobile (Inspection) | True = Piece_Mobile (Usinage standard)
    move_mode = BooleanProperty(True)

    def __init__(self, **kwargs):
        # 1. Variables d'animation centralisées (Territoire Écran)
        self.scale = 0.0025              # Echelle de l'affichage [en px/µm]
        self.mirror_hor = True
        self.mirror_vert = True

        # Les offsets:
        self.offset_base = [0.5, 0.5]   # Décalage du pnt 0,0 dans la box d'affichage [en %(de la taille de la box)]
        self.offset_screen = [0.0, 0.0] # Décallage de l'affichage par la souris [en pixels]
        self.offset_move = [0.0, 0.0]   # Position [hor, vert] reçue depuis les régles de la machine [en µm]
        self.pos_change_move_mode = [0.0, 0.0]  # Décalage succésif des basculements de move_mode [en µm] (pièce mobile vs burin_mobile)

        # Instanciation "à blanc" de tes deux ProfilCanvas
        self.canvas_outil = ProfilCanvas(box=None, scale=self.scale, mirror_hor=self.mirror_hor, mirror_vert=self.mirror_vert, A_outline_width=2.5, A_fill_color=(0.4, 0.1, 0.1, 0.8))
        self.canvas_piece = ProfilCanvas(box=None, scale=self.scale, mirror_hor=self.mirror_hor, mirror_vert=self.mirror_vert, A_outline_width=1.5, A_fill_color=(0.1, 0.3, 0.1, 0.4))

        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        """DÉCLENCHEUR SÉCURISÉ : Les ID sont prêts, on effectue le premier ancrage de boîte."""
        container_global = self.ids.zone_globale
        stencil = self.ids.zone_decoupe
        repere_calcul = self.ids.box_calcul_gauche # Ta Case 1 (75%)
        
        if container_global and stencil and repere_calcul:
            # 1️⃣ Instanciation de l'axe de référence
            self.axe_central = DashedLineWidget(
                line_color=[0.8, 0.8, 1.0, 0.4], # Bleu cyan transparent
                line_width=dp(1.0),
                dash_pattern=[dp(30), dp(5)]
            )
            # 2️⃣ INJECTION SOUS LES AUTRES DESSINS
            # index=0 force Kivy à le placer en arrière-plan absolu du FloatLayout
            container_global.add_widget(self.axe_central, index=0)            

        if stencil and repere_calcul:
            self.canvas_outil.box_dest = repere_calcul
            self.canvas_piece.box_dest = repere_calcul
            
            stencil.add_widget(self.canvas_outil)
            stencil.add_widget(self.canvas_piece)
            
            # 🎯 VRAIE MÉTHODE : On passe par update_size_entities pour le premier calcul d'offset_0
            self.canvas_outil.update_size_entities(box_dest=repere_calcul)
            self.canvas_piece.update_size_entities(box_dest=repere_calcul)
            
        print(f"TEST: DROGRAPH / on_kv_post(): end fonction")

    def set_profil_pieces(self, fao_list=None, cao_list=None, box=None):
        """🎯 TON IDÉE GÉNIALE DE REPEINTURE : Filtre les listes et les envoie via la vanne officielle."""
        import common_draw as cdraw

        fao_prepares = None
        if fao_list is not None and len(fao_list) > 0:
            fao_prepares = cdraw.re_paint_entities(fao_list, reverse=False, default_color=self.COLOR_FAO)
        elif fao_list is not None:
            fao_prepares = []

        cao_prepares = None
        if cao_list is not None and len(cao_list) > 0:
            cao_prepares = cdraw.re_paint_entities(cao_list, reverse=False, default_color=self.COLOR_CAO, error_color=(1, 0, 0, 1))
        elif cao_list is not None:
            cao_prepares = []

        # 🎯 VRAIE MÉTHODE : On utilise la fonction d'usine officielle de ta classe
        # pour changer les entités sans toucher au zoom ou à l'offset actuel !
        self.canvas_piece.update_size_entities(box_dest=box, a_entities=fao_prepares, b_entities=cao_prepares)

    def OLD_distribuer_mouvements_canvas(self, current_esp32_microns):
        """ Utilise move_axes_machine() pour pousser les microns de l'ESP32. (calculation simplifié)"""
        self.offset_move = current_esp32_microns

        if self.move_mode:
            derniere_pos_piece = [  # La pièce glisse, on calcule la soustraction index par index
                self.pos_change_move_mode[0] - self.offset_move[0],
                self.pos_change_move_mode[1] - self.offset_move[1]
            ]
            self.canvas_piece.move_axes_machine(derniere_pos_piece, not_calc_new=False) 
            # hauteur axe = derniere_pos_piece[1]
            self.canvas_outil.move_axes_machine(self.pos_change_move_mode, not_calc_new=False) 

        else:    # MODE : Burin Mobile (Inspection)
            derniere_pos_outil = [  # Le burin glisse, on calcule l'addition index par index
                self.pos_change_move_mode[0] + self.offset_move[0],
                self.pos_change_move_mode[1] + self.offset_move[1]
            ]
            # hauteur axe = derniere_pos_outil[1]
            self.canvas_piece.move_axes_machine(self.pos_change_move_mode, not_calc_new=False) 
            self.canvas_outil.move_axes_machine(derniere_pos_outil, not_calc_new=False)
    def distribuer_mouvements_canvas(self, current_esp32_microns):
        """ Pousse les microns de l'ESP32 et aligne l'axe sur le calcul des pièces. """
        self.offset_move = current_esp32_microns
        repere_calcul = self.ids.box_calcul_gauche

        # 🎯 1. POSITION DU POINT[0,0]
        if hasattr(self.canvas_piece, 'offset_0') and len(self.canvas_piece.offset_0) > 1:
            y_axis_screen = self.canvas_piece.offset_0[1]
        else:
            y_axis_screen = self.ids.box_calcul_gauche.center_y

        # 🎯 2. APPLICATION DES MODES
        if self.move_mode:
            # 🟢 MODE PIÈCE MOBILE : La pièce et son axe glissent ensemble
            derniere_pos_piece = [
                self.pos_change_move_mode[0] - self.offset_move[0],
                self.pos_change_move_mode[1] - self.offset_move[1]
            ]
            derniere_pos_outil = self.pos_change_move_mode
            
        else:
            # 🔵 MODE BURIN MOBILE : L'axe et la pièce restent fixes à l'écran
            derniere_pos_outil = [
                self.pos_change_move_mode[0] + self.offset_move[0],
                self.pos_change_move_mode[1] + self.offset_move[1]
            ]
            derniere_pos_piece = self.pos_change_move_mode
            

        # Application directe de votre idée (Microns finaux -> Pixels)
        y_axis_pos = y_axis_screen + derniere_pos_piece[1] * self.scale

        # 🎯 3. MISE À JOUR DE LA LIGNE D'AXE DE ROTATION (En dessous)
        #self.axe_central.start = [0, y_axis_pos]
        #self.axe_central.end = [repere_calcul.width, y_axis_pos]
        self.axe_central.redraw_pos([0, y_axis_pos], [self.width, y_axis_pos])

        # 🎯 4. REDESSINER LES PROFILS (Pièce et outil)
        self.canvas_piece.move_axes_machine(derniere_pos_piece, not_calc_new=False) 
        self.canvas_outil.move_axes_machine(derniere_pos_outil, not_calc_new=False) 

    def change_move_mode(self):
        """
        Bascule le mode cinématique interactif.
        Fige les structures une bonne fois pour toutes pour soulager la boucle 60Hz.
        """
        offset_move = self.offset_move.copy()

        if self.move_mode:
            # 🔄 PASSAGE VERS : "Burin_Mobile" (Inspection): Le burin va bouger en mode direct : on pré-compense sa base
            new_offset = [
                self.pos_change_move_mode[0] - offset_move[0],
                self.pos_change_move_mode[1] - offset_move[1]
            ]
            # La pièce s'immobilise : on fige sa position définitive
            self.pos_change_move_mode = new_offset
            self.move_mode = False
        else:
            # 🔄 REVIENT VERS : "Piece_Mobile" (Usinage standard): Le burin s'immobilise : on fige sa position définitive
            new_offset = [
                self.pos_change_move_mode[0] + offset_move[0],
                self.pos_change_move_mode[1] + offset_move[1]
            ]
            # La pièce va bouger en mode inversé : on pré-compense sa base
            self.pos_change_move_mode = new_offset
            self.move_mode = True


    ''' OLD
    def on_touch_move(self, touch):
        """🎯 VRAIE MÉTHODE : Utilise update_offset() pour répercuter le Glisser-Déposer souris."""
        repere_gauche = self.ids.get("box_calcul_gauche")
        
        if repere_gauche and repere_gauche.collide_point(*touch.pos) and 'initial_pos' in touch.ud:
            dx = touch.x - touch.ud['initial_pos'][0]
            dy = touch.y - touch.ud['initial_pos'][1]
            
            self.offset_screen[0] += dx
            self.offset_screen[1] += dy
            
            # 🎯 VRAIE MÉTHODE : On passe par la fonction d'usine de ton ProfilCanvas !
            # Elle va recalculer l'offset_0 et lancer self.up_drawing() de manière propre.
            self.canvas_outil.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
            self.canvas_piece.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
            
            touch.ud['initial_pos'] = touch.pos
            return True
        return super().on_touch_move(touch)
    def zoom_all_in_piece(self):
        """applique un niveau de zoom pour faire tenir toute lapièce dans le cadre,
            sans activer le zoom_automatique (action unique, pas automatique!)
        """
        new_scale = self.canvas_piece.search_auto_scale(code_entities="A + B", margin=[0.1, 0.1])
        self.canvas_piece.set_scale(new_scale,auto_scale=False)
        #ici, il faut retourner l'échelle au parent pour qu'il l'applique au autres Canvas !
        return new_scale
    def declencher_auto_zoom(self):
        """🎯 VRAIE MÉTHODE : Utilise set_scale() et update_offset() pour le bouton physique."""
        # 1. On calcule l'échelle maximale par rapport à la géométrie de la pièce
        scale_ideale = self.canvas_piece.search_auto_scale()
        self.scale = scale_ideale
        
        # 2. On injecte l'échelle via la méthode d'usine (auto_scale=False coupe le mode automatique interne)
        self.canvas_piece.set_scale(scale=scale_ideale, auto_scale=False)
        self.canvas_outil.set_scale(scale=scale_ideale, auto_scale=False)
        
        # 3. On calcule le recentrage géométrique au milieu de l'écran utile
        offset_calcule = self.canvas_piece.search_auto_offset()
        self.offset_screen = offset_calcule
        
        # 4. On propage l'offset de centrage via la méthode d'usine officielle
        self.canvas_piece.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
        self.canvas_outil.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
        print(f"[GRAPHIC] Auto-Scale exécuté via set_scale : {scale_ideale:.6f} Px/µm")
    def declencher_recentrage(self):
        """🎯 VRAIE MÉTHODE : Utilise update_offset() pour ramener la pièce au milieu."""
        # On recalcule l'offset de centrage basé exclusivement sur l'échelle en cours
        offset_calcule = self.canvas_piece.search_auto_offset()
        self.offset_screen = offset_calcule
        
        # On propage l'offset via la vanne d'usine officielle
        self.canvas_piece.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
        self.canvas_outil.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
        print("[GRAPHIC] Recentrage de l'origine exécuté via update_offset.")       

    def OLD_distribuer_mouvements_canvas(self, current_esp32_microns):
        """
        Distributeur à 60Hz : Les deux canvas reçoivent not_calc_new=False 
        pour forcer le rafraîchissement synchrone des calques sans recalculer les microns.
        """
        offset_move = current_esp32_microns

        if self.move_mode:
            # 🛠️ MODE : Pièce Mobile (Usinage standard)
            # L'outil est fixe
            self.derniere_pos_outil = self.last_move_t
            self.canvas_outil.move_axes_machine(self.derniere_pos_outil, not_calc_new=False) # 🎨 Dessine le fixe
            
            # La pièce glisse
            self.derniere_pos_piece = [
                self.last_move_p[0] - offset_move[0],
                self.last_move_p[1] - offset_move[1]
            ]
            self.canvas_piece.move_axes_machine(self.derniere_pos_piece, not_calc_new=False) # 🎨 Dessine le mobile

        else:
            # 📱 MODE : Burin Mobile (Inspection)
            # La pièce est fixe
            self.derniere_pos_piece = self.last_move_p
            self.canvas_piece.move_axes_machine(self.derniere_pos_piece, not_calc_new=False) # 🎨 Dessine le fixe
            
            # Le burin glisse
            self.derniere_pos_outil = [
                self.last_move_t[0] + offset_move[0],
                self.last_move_t[1] + offset_move[1]
            ]
            self.canvas_outil.move_axes_machine(self.derniere_pos_outil, not_calc_new=False) # 🎨 Dessine le mobile

    def on_touch_down(self, touch):
        # On va chercher la case virtuelle de gauche
        repere_gauche = self.ids.get("box_calcul_gauche")
        
        # 🛡️ DOUANE : On n'agit que si le clic s'est produit dans les 75% de gauche
        if repere_gauche and repere_gauche.collide_point(*touch.pos):
            # Mémorisation du point de départ du geste directement dans le dictionnaire du touch
            touch.ud['initial_pos'] = touch.pos
            return True # On intercepte l'événement (il ne traversera pas vers d'autres calques)
            
        # Si c'est à droite, on laisse Kivy propager le clic normalement vers les boutons
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        repere_gauche = self.ids.get("box_calcul_gauche")
        
        # Si on glisse dans la zone de gauche et qu'on a un point de départ valide
        if repere_gauche and repere_gauche.collide_point(*touch.pos) and 'initial_pos' in touch.ud:
            # Calcul de l'incrément en pixels purs
            dx = touch.x - touch.ud['initial_pos'][0]
            dy = touch.y - touch.ud['initial_pos'][1]
            
            # Application directe sur notre manette écran (Zéro transfert de variable complexe !)
            self.offset_screen[0] += dx
            self.offset_screen[1] += dy
            
            # Transmission instantanée à nos deux moteurs de tracés indépendants
            self.canvas_outil.update_offset(offset_screen=self.offset_screen)
            self.canvas_piece.update_offset(offset_screen=self.offset_screen)
            
            # Mise à jour de la position de référence pour la prochaine frame du glisser
            touch.ud['initial_pos'] = touch.pos
            return True
            
        return super().on_touch_move(touch)

    def OLD_set_profil_pieces(self, fao_list=None, cao_list=None):
        """
        DISTRIBUTEUR GÉOMÉTRIQUE : Injecte et re-peint les entités via le canal officiel.
        Utilise update_size_entities() pour respecter le format (None=inchangé, []=vider)
        et préserve STRICTEMENT le zoom (scale) et l'offset actuel de l'opérateur.
        """
        import common_draw as cdraw # Ton module géométrique

        # 🟢 1. COUCHE DESSUS : LE PROFIL DE PRODUCTION (FAO)
        fao_prepares = None
        if fao_list is not None:
            if len(fao_list) > 0:
                # La liste contient des segments -> on applique ton pistolet à peinture VERT
                fao_prepares = cdraw.re_paint_entities(
                    raw_list=fao_list,
                    reverse=False,
                    default_color=(0.1, 0.8, 0.1, 1), # Vert fluo DRO
                    error_color=(1, 0, 0, 1)          # Rouge de sécurité
                )
            else:
                # La liste reçue est explicitement vide [] -> on prépare un tableau vide []
                fao_prepares = []

        # 🔴 2. COUCHE DESSOUS : LE MODÈLE THÉORIQUE DE RÉFÉRENCE (CAO)
        cao_prepares = None
        if cao_list is not None:
            if len(cao_list) > 0:
                # La liste contient des segments -> on applique ton pistolet à peinture ROUGE
                cao_prepares = cdraw.re_paint_entities(
                    raw_list=cao_list,
                    reverse=False,
                    default_color=(0.5, 0.1, 0.1, 0.8), # Rouge bordeaux
                    error_color=(1, 0, 0, 1)            # Rouge vif
                )
            else:
                # La liste reçue est explicitement vide [] -> on prépare un tableau vide []
                cao_prepares = []

        # 🎯 3. INJECTION OFFICIELLE VIA LES ENTONNOIRS DE PROFILCANVAS
        self.canvas_piece.update_size_entities(box_dest=None, a_entities=fao_prepares, b_entities=cao_prepares)

        print("[GRAPHIC] Profils synchronisés via update_size_entities (Zoom & Pan préservés).")

    '''


    # =====================================================================
    # 🎛️ LES MANETTES D'ACTIONS DU PANNEAU DROIT (BOUTONS .KV CONNECTÉS)
    # =====================================================================
    def zoom_all_in_piece(self):
        """
        Action unique : calcule le niveau de zoom optimal pour faire tenir 
        le double profil (A + B) dans le cadre, et l'impose à TOUS les canvas.
        """
        # 1. Calcul de l'échelle idéale sur l'unique photo géométrique
        new_scale = self.canvas_piece.search_auto_scale(code_entities="A + B", margin=[0.1, 0.1])
        
        if new_scale:
            # 2. 🎯 ALLIGNEMENT TOTAL : On distribue la même échelle aux deux canvas d'un coup !
            self.canvas_piece.set_scale(new_scale, auto_scale=False)
            self.canvas_outil.set_scale(new_scale, auto_scale=False)
            
            # 3. Synchronisation de la variable maîtresse locale
            self.scale = new_scale
            
        return new_scale

    def declencher_recentrage(self, ratio=None):   
        """
        Action unique : recentre le dessin selon le mode actif.
        - Piece_Mobile (True) : Fixe le point 0,0 du burin sur le ratio écran.
        - Burin_Mobile (False) : Fixe le centre géométrique de la pièce sur le ratio écran.
        """
        # 1️⃣ Gestion et mémorisation du ratio d'écran demandé (ex: [0.5, 0.5] ou [0.75, 0.25])
        if ratio is not None:
            self.offset_base = ratio
        elif not hasattr(self, 'offset_base') or self.offset_base is None:
            self.offset_base = [0.5, 0.5]

        # 2️⃣ Réinitialisation propre des mouvements de la souris
        self.offset_screen = [0.0, 0.0]

        # 3️⃣ AIGUILLAGE CINÉMATIQUE CONFORME À TES ÉQUATIONS 60Hz
        if self.move_mode:
            # MODE USINAGE (Piece_Mobile = True): Le burin revient pile sur le 0,0 de l'ancrage écran (offset_0)
            self.pos_change_move_mode = [0.0, 0.0]
            print(f"[DRO] Recentrage Usinage : Burin calé sur le ratio {self.offset_base}. Pièce mobile.")
            
        else:
            # MODE INSPECTION (Burin_Mobile = False)
            # On extrait le centre géométrique réel de la pièce en microns (par-rapport au pnt [0,0])
            infos_centre = self.canvas_piece.get_center_draw()
            inv_center_um = [infos_centre["center_um"][0] * -1.0, infos_centre["center_um"][1] * -1.0]
            
            # On recule l'accumulateur du calque de la valeur exacte du centre
            self.pos_change_move_mode = inv_center_um
            print(f"[DRO] Recentrage Inspection : Centre pièce [{infos_centre['center_um'][0]}, {infos_centre['center_um'][1]}] calé au milieu. Burin mobile.")

        # 4️⃣ TRANSMISSION SYNCHRONE AUX DEUX CALQUES GRAPHIC
        # On remet à plat la souris (0,0) et on impose le ratio. 
        # update_offset va forcer la peinture immédiate de ton ProfilCanvas.
        self.canvas_piece.update_offset(offset_screen=self.offset_screen, offset_base=self.offset_base, not_calc_new=False)
        self.canvas_outil.update_offset(offset_screen=self.offset_screen, offset_base=self.offset_base, not_calc_new=False)

        #print("[GRAPHIC] Recentrage global exécuté sur tous les calques.")
        print(f"[Recentrage offset] base: {self.offset_base}; screen: {self.offset_screen}; move: {self.offset_move}")
        print(f" liste des segments:\n{self.canvas_piece.b_entities}")

    # =====================================================================
    # 🖱️ CAPTURE CENTRALISÉE DE L'IHM (MOLETTE SOURIS / CLICK / TACTILE)
    # =====================================================================
    def on_touch_down(self, touch):
        # On va chercher la case virtuelle de gauche (85%) ("Le BoxLayoute")
        repere_gauche = self.ids.get("box_calcul_gauche")
        
        # 🛡️ DOUANE : On n'agit que si l'action s'est produite dans la zone utile de gauche
        if repere_gauche and repere_gauche.collide_point(*touch.pos):
            
            # 🔍 CAS A : L'OPÉRATEUR FAIT TOURNER LA MOLETTE VERS LE HAUT (Zoom +)
            if touch.is_mouse_scrolling and touch.button == 'scrollup':
                nouvelle_echelle = self.canvas_piece.scale * 1.10
                
                # 🎯 DISTRIBUTION SYNCHRONE SUR LES DEUX CALQUES
                self.canvas_piece.set_scale(scale=nouvelle_echelle, auto_scale=False)
                self.canvas_outil.set_scale(scale=nouvelle_echelle, auto_scale=False)
                
                self.scale = self.canvas_piece.scale
                return True 

            # 🔍 CAS B : L'OPÉRATEUR FAIT TOURNER LA MOLETTE VERS LE BAS (Zoom -)
            elif touch.is_mouse_scrolling and touch.button == 'scrolldown':
                nouvelle_echelle = self.canvas_piece.scale * 0.90
                
                # 🎯 DISTRIBUTION SYNCHRONE SUR LES DEUX CALQUES
                self.canvas_piece.set_scale(scale=nouvelle_echelle, auto_scale=False)
                self.canvas_outil.set_scale(scale=nouvelle_echelle, auto_scale=False)
                
                self.scale = self.canvas_piece.scale
                return True

            # 🔍 CAS C : CLIC STANDARD / COMMENCEMENT D'UN GESTE TACTILE
            else:
                # Mémorisation du point de départ du geste dans le touch
                touch.ud['initial_pos'] = touch.pos
                return True 
            
        # Si c'est à droite (panneau fumé), on laisse Kivy propager normalement vers les boutons
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        repere_gauche = self.ids.get("box_calcul_gauche")
        
        # Si on glisse dans la zone de gauche et qu'on a un point de départ valide
        if repere_gauche and repere_gauche.collide_point(*touch.pos) and 'initial_pos' in touch.ud:
            # Calcul de l'incrément en pixels purs
            dx = touch.x - touch.ud['initial_pos'][0]
            dy = touch.y - touch.ud['initial_pos'][1]
            
            # Application directe sur notre manette écran locale index par index
            self.offset_screen[0] += dx
            self.offset_screen[1] += dy
            
            # 🎯 DISTRIBUTION SYNCHRONE ET FORCEE SUR LES DEUX MOTEURS DE TRACÉS
            # On passe par la méthode officielle de ta classe ProfilCanvas !
            self.canvas_piece.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
            self.canvas_outil.update_offset(offset_screen=self.offset_screen, not_calc_new=False)
            
            # Mise à jour de la position de référence pour la prochaine frame du glisser
            touch.ud['initial_pos'] = touch.pos
            return True
            
        return super().on_touch_move(touch)


class DroManager(BaseScreenLayout):  # 🛠️ Héritage direct du Châssis !
    def __init__(self, part, cutter, machine, **kwargs):
        self.part = part        
        self.cutter = cutter    
        self.machine = machine  
        
        # Initialisation des dictionnaires pour ton code historique
        self.axes_head = {}
        self.axes_dro = {}
        
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        """
        DÉCLENCHEUR SÉCURISÉ : Le châssis de base .kv est prêt en mémoire.
        On injecte nos modules spécifiques en pur Python sans risquer de bug .kv !
        """
        # 1️⃣ CRÉATION DES WIDGETS EN PUR PYTHON
        header = DroHeader()
        drobox = DroDro()
        graphbox = DroGraph() # (Tu pourras lui passer des arguments si besoin plus tard)
        
        corps_fao = BoxLayout(orientation="vertical", spacing=1)    # Création du bloc vertical de droite qui va accueillir les compteurs et le dessin
        # Empilage dans le bloc vertical de droite
        corps_fao.add_widget(drobox)
        corps_fao.add_widget(graphbox)

        # 2️⃣ CLIPSAGE INDUSTRIEL DANS LES TIROIRS DU CHÂSSIS PARENT
        self.injecter_entete_specifique(header)
        self.injecter_corps_specifique(corps_fao)

        # 3️⃣ LIAISON DES IDENTIFIANTS DE TON CODE HISTORIQUE
        # Puisque les widgets ont été créés en Python, on mappe leurs boutons/champs manuellement
        self.axes_head = {
            "vert": header.ids.header_vert,
            "hor": header.ids.header_hor,
            "sup": header.ids.header_sup
        }
        
        # Injection du pointeur du manager dans chaque HeaderAxis
        header.dro_manager = self
        for axis in self.axes_head.values():
            axis.dro_manager = self

        # Cartographie de ton boîtier de compteurs numériques (DroDro)
        self.axes_dro = {
            "hor": drobox.ids.dro_z,
            "vert": drobox.ids.dro_x,
            "sup": drobox.ids.dro_y,
        }

        # 🎯 CRUCIAL : On sauvegarde manuellement graphbox et drobox dans le dictionnaire self.ids
        # de DroManager. Ainsi, toutes tes autres fonctions (comme update_axes_val ou tes boutons)
        # continueront de trouver "self.ids.graph_box" et "self.ids.dro_box" sans changer une seule ligne !
        self.ids["graph_box"] = graphbox
        self.ids["dro_box"] = drobox
        self.ids["header_box"] = header

        # 4️⃣ CHARGEMENT INITIAL DES VALEURS DU TOUR
        if 'graph_box' in self.ids:
            graph = self.ids['graph_box']
            # 🎯 STRATÉGIE TRANSITOIRE SANS PROFIL MCU :
            # - fao_list=[]  -> On passe une liste vide explicite pour cadenasser le canal vert à vide.
            # - cao_list=... -> On injecte ton profil CAO réel pour voir ta pièce en rouge au démarrage.
            graph.set_profil_pieces(
                box=True, 
                fao_list=[], 
                cao_list=App.get_running_app().part.profil_segments
            )
        positions_initiales = self.machine.generer_dictionnaire_dro()
        self.update_axes_val(positions_initiales)

    def update_axes_val(self, data):
        """Boucle de rafraîchissement à 60Hz appelée par le main.py."""
        for name, val in data.items():
            # A. Mise à jour des petits pavés de l'en-tête haute
            if name in self.axes_head:
                # L'en-tête délègue directement à son sous-composant ax_dim
                if hasattr(self.axes_head[name], 'ax_dim') and self.axes_head[name].ax_dim:
                    self.axes_head[name].ax_dim.new_val(val)
                
            # B. 🎯 CORRIGÉ POUR L'AXISBOX DU MILIEU : 
            # On va chercher l'objet ax_dim caché à l'intérieur de ton AxisBox (self.axes_dro[name])
            if name in self.axes_dro:
                box_axe = self.axes_dro[name]
                
                # Sécurité : On s'assure que l'AxisBox est construite et que son ax_dim est opérationnel
                if hasattr(box_axe, 'ax_dim') and box_axe.ax_dim:
                    # On injecte la valeur brute dans le moteur de conversion de l'AxisDim
                    box_axe.ax_dim.new_val(val)

        # C. PROPAGATION DES MICRONS VERS LE DESSIN DRO (Ton DroGraph)
        microns_hor = data.get("hor", 0.0)
        microns_vert = data.get("vert", 0.0)
        self.ids.graph_box.distribuer_mouvements_canvas([microns_hor, microns_vert])

    #ÉCRAN
    def screen_focused(self):
        """
        RÉVEIL INTERNE DRO : Appelée par le main.py quand la page prend le focus.
        Actualise les étiquettes et injecte de force la liste longue du PointManager 
        via le canal officiel pour conserver le zoom et les offsets de l'opérateur.
        """
        app_vivante = App.get_running_app()
        
        # 1️⃣ SYNCHRONISATION VISUELLE DE L'ONGLET LATÉRAL DE LA BARRE COMMUNE
        if 'tools_bar' in self.ids:
            tb = self.ids.tools_bar
            if 'btn_fao' in tb.ids: tb.ids.btn_fao.set_status(1) # DRO s'allume en vert clair
            if 'btn_cao' in tb.ids: tb.ids.btn_cao.set_status(0) # CAO repasse au neutre

        # 2️⃣ GESTION ET MISE À JOUR DU VISUALISEUR GRAPHIQUE
        if 'graph_box' in self.ids:
            graph = self.ids['graph_box']
            
            # A. Rafraîchissement textuel du nom de la pièce CAO dans le panneau droit (15% fumé)
            if 'cao_name_lbl' in graph.ids:
                graph.ids.cao_name_lbl.text = app_vivante.part.get_part_name()

            # B. 🎯 L'INJECTION OFFICIELLE (Le chaînon manquant à jour !)
            # On prend la liste longue de ton PointManager et on l'envoie au distributeur
            if hasattr(app_vivante.part, 'profil_segments'):
                # On passe la liste dans la zone FAO (premier argument). 
                # Ton DroGraph se chargera de la repeindre en vert et de l'injecter via update_size_entities
                graph.set_profil_pieces(box=True, fao_list=None, cao_list=app_vivante.part.profil_segments)

            # C. Relance instantanée du pinceau rapide à 60Hz pour ré-aligner les microns machine
            donnees_initiales = self.machine.generer_dictionnaire_dro()
            microns_hor = donnees_initiales.get("hor", 0.0)
            microns_vert = donnees_initiales.get("vert", 0.0)
            graph.distribuer_mouvements_canvas([microns_hor, microns_vert])
            
        print("[PAGE DRO] Réveil autonome exécuté via set_profil_pieces (Zoom & Pan préservés).")


    #OLD
    def OLD_update_axes_val(self, data):
        # Exemple: data = {"X": 789, "Y": 7890123, "Z": -123}
        for name, val in data.items():
            if name in self.axes_head:
                self.axes_head[name].ax_dim.new_val(val)
                #print(f"TEST update_axes_val: axes_head {self.axes_head[name].ax_dim.name_txt} value: {self.axes_head[name].ax_dim.value_txt} {self.axes_head[name].ax_dim.val_unit} / diam: {self.axes_head[name].ax_dim.val_diam}")
            if name in self.axes_dro:
                # TODO: à màj une fois la box faite
                pass
    def NEWOLD_update_axes_val(self, data):
        """Boucle de rafraîchissement à 60Hz appelée par le main.py."""
        # A. Mise à jour des petits pavés de l'en-tête haute
        for name, val in data.items():
            if name in self.axes_head:
                self.axes_head[name].ax_dim.new_val(val)
                
            # B. Mise à jour des gros chiffres du boîtier DroDro
            if name in self.axes_dro:
                self.axes_dro[name].new_val(val)

        # 🎯 C. PROPAGATION DES MICRONS VERS LE DESSIN DRO (Ton DroGraph)
        microns_hor = data.get("hor", 0.0)
        microns_vert = data.get("vert", 0.0)
        self.ids.graph_box.distribuer_mouvements_canvas([microns_hor, microns_vert])
   


Builder.load_file("dro_viewer.kv")
