# dro_viewer.py à la racine du projet

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from copy import deepcopy
from kivy.lang import Builder
from part.draw_pnt_manager import PointManager
from cutting_tool.cutter import CutterManager
from machine_tool.machine_data import MachineState
from reel_time.machine_mcu import CommManager
from common_widgets import ClickableLabel
import config as conf
from config import AXIS_CONFIG  

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
            self.axe_config = deepcopy(AXIS_CONFIG.get(self.axe_ident, {}))
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

class DroToolBar(BoxLayout): pass
class DroDro(BoxLayout): pass
class DroGraph(BoxLayout):pass
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
    pass


class DroManager(BoxLayout):
    def __init__(self,part, cutter, machine, **kwargs):
        self.part:    PointManager  = part    #PointManager()
        self.cutter:  CutterManager = cutter  #CutterManager()
        self.machine: MachineState  = machine #MachineState()
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        # Maintenant, self.ids est complètement prêt !        
        header = self.ids.header_box  # Accès au DroHeader
        drobox = self.ids.dro_box  # Accès au DroDro
        self.axes_head = {
            "vert": header.ids.header_vert,
            "hor": header.ids.header_hor,
            "sup": header.ids.header_sup
        }
        self.axes_dro = {
            #"X": drobox.ids.dro_x,
            #"Z": drobox.ids.dro_z,
            #"Y": drobox.ids.dro_y,
        }

        # Injecter le pointeur du manager dans chaque HeaderAxis
        header.dro_manager = self
        for axis in self.axes_head.values():
            axis.dro_manager = self

        # TEST:
        #self.update_axes_val({"vert": 7890000, "hor": -123, "sup": 7890123})
        
        # REMPLACEMENT DU TEST : Chargement des positions réelles au démarrage
        # Celles-ci proviennent de user_settings.json via MachineState()
        positions_initiales = self.machine.generer_dictionnaire_dro()
        self.update_axes_val(positions_initiales)

    def update_axes_val(self, data):
        # Exemple: data = {"X": 789, "Y": 7890123, "Z": -123}
        for name, val in data.items():
            if name in self.axes_head:
                self.axes_head[name].ax_dim.new_val(val)
                #print(f"TEST update_axes_val: axes_head {self.axes_head[name].ax_dim.name_txt} value: {self.axes_head[name].ax_dim.value_txt} {self.axes_head[name].ax_dim.val_unit} / diam: {self.axes_head[name].ax_dim.val_diam}")
            if name in self.axes_dro:
                # TODO: à màj une fois la box faite
                pass


Builder.load_file("dro_viewer.kv")
