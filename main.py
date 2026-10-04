# main (définitif)
from kivy.config import Config
# Désactive la simulation multitouche (les fameux points oranges qui bloquent tout)
Config.set('input', 'mouse', 'mouse,disable_multitouch')
# Dimention par défaut à l'ouverture
Config.set('graphics', 'width', '1210')
Config.set('graphics', 'height', '600')

import sys
import os
from kivy.app import App
from pathlib import Path
import json

# Alignement du chemin d'importation
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, DictProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from configurator.config import format_unit, user_language, SETTINGS, save_json, SETTINGS_FILE
from cutting_tool.cut_insert_manager import CutInsertLib
from cutting_tool.cut_manager import CutterLib
from cutting_tool.cut_tool_data import CutterPageManager
from dro_viewer import DroManager
from part.draw_data import PointDrawEditor  # Import de l'éditeur CAO
from part.draw_pnt_manager import PointManager
from machine_tool.machine_data import MachineState
from reel_time.machine_mcu import CommManager
from i18n import set_language, tr, Tr, TR
# 🟢 On importe votre dictionnaire Hexa et votre fonction de normalisation d'atelier !
from ui_configurator.theme_manager import draw_line
from common_draw import normalize_color # Ajustez le chemin d'import selon votre arborescence

# Gestion de l'icône de l'application
BITMAPS_DIR = Path(__file__).resolve().parent / "bitmaps"
ICON_PATH = BITMAPS_DIR / "icone.ico"

# 🛠️ LA MOULINETTE DE PRE-CONVERSION : Transforme tout le dictionnaire Hexa en RGBA
# pour que Kivy n'ait aucun calcul de texte à faire en cours d'usinage.
rgba_theme_ready = {}
for clé, valeur in draw_line.items():
    if isinstance(valeur, str) and (valeur.startswith("#") or valeur == "def"):
        rgba_theme_ready[clé] = normalize_color(valeur)
    else:
        rgba_theme_ready[clé] = valeur # Laisse passer les épaisseurs (_w) intactes


class SmartDroApp(App):
    MODE_DEVELOPPEMENT_ACTIF = True   # 🛠️ FLAG DE DÉVELOPPEMENT (Passez à False pour masquer le simulateur en atelier)

    icon = "bitmaps/icone.ico"   # str(ICON_PATH)
    title = "DRO intelligent"    # Sera traduit dynamiquement dans build()

    mode_tactile_actif = BooleanProperty(True)    # CONTROLE DE SAISIE : False = Clavier PC direct | True = Calculatrice tactile
    theme_colors = DictProperty(rgba_theme_ready)    # COUPLAGE SUPRÊME CONVERT : Vos boutons reçoivent des listes RGBA pures et ultra-légères !

    # 🎯 POUR LES BOUTONS DE NAVIGATION: LE TABLEAU DE BORD DES COULEURS, ICÔNES - TEXTE (pour la barre de navigation de chaque écran)
    screen_actif = StringProperty("screen_FAO")# Le bouton de la barre d'outil à activer
    # Couleurs des témoins des bouttons de navigation
    screen_FAO = DictProperty({"icon": "bitmaps/icone.png", "text": "FAO", "status": "OK"})
    screen_CAO = DictProperty({"icon": "bitmaps/ico_CAO.png", "text": "CAO", "status": "OK"}) # "status": "MODIFIED"
    screen_CUTTER = DictProperty({"icon": "bitmaps/burin_select.png", "text": "TOOL", "status": "OK"})
    screen_OFFSET = DictProperty({"icon": None, "text": "OFFSET", "status": "OK"})
    screen_MCU = DictProperty({"icon": None, "text": "MCU", "status": "OK"})
    screen_PARAM = DictProperty({"icon": None, "text": "PARAM", "status": "OK"})
    screen_SETTING = DictProperty({"icon": None, "text": "ECRAN", "status": "OK"})
    sw_TACTILE = DictProperty({"icon": None, "text": "TACTILE", "status": "OK", "real_status": "BLUE"}) 

     # ----------------------------------------------------
    # 🛠️ SATUS MATERIEL: MACHINE, OUTIL, ... EN DIRECT(DONNÉES CENTRALES)
    # ----------------------------------------------------
    # L'offset DRO calculé en temps réel selon le cadran choisi et le rayon de l'outil. [Z(horisontal), X (vertical), Validate, icône]
    dro_visual_offset_cut = ListProperty([0, 0,False, "bitmaps/tool_offset_0_2.png"])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # URGENCE suite à un CRASH de Kivy
        self.machine = MachineState()   # Status de configuration et mesures de la machine
        self.calculator = CommManager(self.machine)  # chargement du profil d'usinage (porfil partagé avec le MCU)
        # fin de l'URGENCE === Poursuite de l'initialisation des gros blocs de valeurs ===
        self.machine.build_next_urgence()

        self.part = PointManager()      # Partagé entre l'IHM DRO et l'Éditeur Dessin !
        self.lib_insert = CutInsertLib()        # Bibliothèque des insertes de burin (Zonne tranchante)
        self.lib_cutter = CutterLib(insert_lib_instance=self.lib_insert)    # Bibliothèque des burins
        #self.cutter_actif = None        #  CutterManager() du burin actuellement utilisé

        # 🟢 V_7.2 : Pré-déclaration des poignées d'écrans pour la clarté de la RAM
        self.dro_manager_instance = None
        self.cutter_page_instance = None
        self.dessin_editor_instance = None
        self.offset_page_instance = None
        self.mcu_page_instance = None
        self.param_page_instance = None
        self.settings_page_instance = None       
        
        set_language(user_language)
        self.dro_clock = None  # Référence pour notre tick à 60Hz
        
    def build(self):
        self.title = tr("dro_intelligent_title")
        Window.bind(on_request_close=self.sauvegarde_de_fin_de_session)

        # 1. On crée le gestionnaire d'écrans EN PREMIER
        self.sm = ScreenManager()
        
        # Variables partagées pour l'outil de démarrage
        last_cut_ident, last_cut_angle_mont, last_cut_grp = SETTINGS["user_last_select"]["selected_tool"]
        self.lib_cutter.set_cutter_active(last_cut_ident, last_cut_angle_mont, last_cut_grp)

        self.mode_tactile_actif = SETTINGS["user_last_select"]["tactile_keyboard"]

        # =====================================================================
        # 🧱 INJECTION DES ÉCRANS (Ordonnés selon votre Barre d'outils)
        # =====================================================================
        # lien_btns_for_base_screen =[self.screen_FAO, self.screen_CAO, self,self.screen_CUTTER, self.screen_OFFSET, self.screen_MCU, self.screen_PARAM,self.screen_SETTING, self.sw_TACTILE]

        # 1️⃣ ÉCRAN : LE DRO PRINCIPAL (FAO)
        screen_dro = Screen(name="screen_FAO")
        self.dro_manager_instance = DroManager(self.part, self.lib_cutter.active_cutter, self.machine)
        screen_dro.add_widget(self.dro_manager_instance)
        screen_dro.on_enter = self.demarrer_horloge_dro
        screen_dro.on_leave = self.stopper_horloge_dro
        self.sm.add_widget(screen_dro)

        # 2️⃣ ÉCRAN : LA PAGE DES OUTILS (TOURELLE / CORRECTEURS ACTIFS)
        screen_outil = Screen(name="screen_CUTTER")
        self.cutter_page_instance = CutterPageManager(self.lib_cutter.active_cutter)
        self.cutter_page_instance.charger_burin_depuis_ident(tool_ident=last_cut_ident, crant_mont= last_cut_angle_mont,grp_ofst= last_cut_grp)
        screen_outil.add_widget(self.cutter_page_instance)
        self.sm.add_widget(screen_outil)

        # 3️⃣ ÉCRAN : LA CAO (DESSIN DE LA PIÈCE VIRTUELLE)
        screen_dessin = Screen(name="screen_CAO")
        self.dessin_editor_instance = PointDrawEditor(self.part)
        screen_dessin.add_widget(self.dessin_editor_instance)
        self.sm.add_widget(screen_dessin)

        # 4️⃣ 🟢 ÉCRAN : TABLE GLOBALE DES OFFSETS (Nouveau !)
        from configurator.dro_machine import OffsetPageManager
        screen_offset = Screen(name="screen_OFFSET")
        self.offset_page_instance = OffsetPageManager()
        screen_offset.add_widget(self.offset_page_instance)
        self.sm.add_widget(screen_offset)

        # 5️⃣ 🟢 ÉCRAN : DIAGNOSTIC MATÉRIEL / MCU (Nouveau !)
        from machine_tool.machine_data import McuPageManager
        screen_mcu = Screen(name="screen_MCU")
        self.mcu_page_instance = McuPageManager()
        screen_mcu.add_widget(self.mcu_page_instance)
        self.sm.add_widget(screen_mcu)

        # 6️⃣ 🟢 ÉCRAN : PARAMÈTRES CONSTRUCTEUR / CONFIG MACHINE (Nouveau !)
        from configurator.config_data import ParamPageManager
        screen_param = Screen(name="screen_PARAM")
        self.param_page_instance = ParamPageManager()
        screen_param.add_widget(self.param_page_instance)
        self.sm.add_widget(screen_param)

        # 7️⃣ 🟢 ÉCRAN : PRÉFÉRENCES OPÉRATEUR / SETTINGS (Nouveau !)
        from ui_configurator.theme_manager import SettingsPageManager
        screen_setting = Screen(name="screen_SETTING")
        self.settings_page_instance = SettingsPageManager()
        screen_setting.add_widget(self.settings_page_instance)
        self.sm.add_widget(screen_setting)

        # 8️⃣ 🔵 ÉCRAN PLEIN ÉCRAN GÉNÉRIQUE / NOMADE (Nouveau !)
        # C'est ta boîte vide interchangeable pour toutes les configurations matérielles lourdes
        from screen_base.common_screen import FullTactileScreenLayout
        screen_full_config = Screen(name="screen_FULL_UTILITY")
        self.full_page_instance = FullTactileScreenLayout()
        screen_full_config.add_widget(self.full_page_instance)
        self.sm.add_widget(screen_full_config)

        # =====================================================================
        # ASSEMBLAGE DE LA COQUILLE ET LANCEMENT
        # =====================================================================
        racine_app = BoxLayout(orientation='horizontal')
        racine_app.add_widget(self.sm)
        
        if self.MODE_DEVELOPPEMENT_ACTIF:
            from screen_base.simulateur import SimulationPanel
            le_simulateur = SimulationPanel(self.machine, size_hint=(0.2, 1))
            racine_app.add_widget(le_simulateur)

            # NOTE: J'arrive pas à changer le grandeur de la fenêtre avant l'ouverture !
                #Config.set["graphics"].width *= 1.2
                #Config.set["graphics"].height *= 0.8
                #Config.set('graphics', 'width', '1210')
                #Config.set('graphics', 'height', '400')
                #racine_app.size=[1210,400]

        Clock.schedule_once(lambda dt: self.changer_ecran("screen_FAO"), 0)
        return racine_app

    # --- Logique de Commutation et Horloge Visuelle ---
    def changer_ecran(self, nom_ecran, building=False):
        """ GÈRE LE SQUELETTE GLOBAL : Oriente l'IHM et réveille la bonne page """
        #ancien_ecran = self.sm.current if self.sm else "DÉMARRAGE"
        #print(f">>> [Changement de page] new page: {nom_ecran} <<<<<< old page: {ancien_ecran}")

        # Commutation de l'écran physique
        self.screen_actif = nom_ecran
        self.sm.current = nom_ecran

        # 🔄 ROUTAGE CHIRURGICAL DES RÉVEILS DE PAGES (screen_focused)
        if   nom_ecran == "screen_FAO":     self.dro_manager_instance.screen_focused()            
        elif nom_ecran == "screen_CUTTER":  self.cutter_page_instance.screen_focused()            
        elif nom_ecran == "screen_CAO":     self.dessin_editor_instance.screen_focused()
        elif nom_ecran == "screen_OFFSET":  self.offset_page_instance.screen_focused()
        elif nom_ecran == "screen_MCU":     self.mcu_page_instance.screen_focused()
        elif nom_ecran == "screen_PARAM":   self.param_page_instance.screen_focused()            
        elif nom_ecran == "screen_SETTING": self.settings_page_instance.screen_focused()

    def up_to_full_screen(self, instance_widget_formulaire, menu_screen="screen_CUTTER"):
        """
        🎯 LE PASSE-PARTOUT TECHNIQUE :
        Vide le conteneur plein écran, injecte le formulaire tactile demandé,
        mémorise d'où on vient, et bascule l'affichage sans aucune latence.
        """
        # 1. On mémorise l'écran d'origine pour pouvoir y retourner au clic sur "Retour"
        #self.ecran_retour_session = menu_screen
        self.full_page_instance.parent_target_screen = menu_screen
        
        # 2. Nettoyage absolu de la boîte
        self.full_page_instance.box_zone.clear_widgets()
        
        # 3. Injection du formulaire métrologique frais
        self.full_page_instance.box_zone.add_widget(instance_widget_formulaire)
        
        # 4. Saut visuel immédiat
        self.sm.current = "screen_FULL_UTILITY"

    def return_menu_screen(self):
        """ Appelé par le bouton 'Retour / Valider' présent dans ton formulaire plein écran """
        # On récupère l'écran d'origine mémorisé, ou par défaut le DRO principal
        #destination = getattr(self, 'ecran_retour_session', "screen_FAO")
        destination = self.full_page_instance.get('parent_target_screen', "screen_FAO")
        # On quitte l'écran plein écran pour retourner à l'IHM standard
        self.sm.current = destination
        
        # Optionnel : Nettoyage immédiat de la RAM pour libérer les ressources du dessin
        self.full_page_instance.box_zone.clear_widgets()
        self.full_page_instance.parent_target_screen = ""


    def demarrer_horloge_dro(self):
        if not self.dro_clock:
            print("[IHM] Activation du rafraîchissement écran DRO (60Hz)")
            self.dro_clock = Clock.schedule_interval(self.rafraichir_affichage_dro, 1.0 / 60.0)

    def stopper_horloge_dro(self):
        if self.dro_clock:
            print("[IHM] Désactivation de l'horloge DRO (Préservation CPU pour le dessin)")
            Clock.unschedule(self.dro_clock)
            self.dro_clock = None

    def rafraichir_affichage_dro(self, dt):
        """Prend les cotes fraîches du MachineState et arrose la page ACTUELLE à 60Hz."""
        donnees_fraiches = self.machine.generer_dictionnaire_dro()
        
        # 🚨 DISTRIBUTION INTELLIGENTE :
        # On regarde quel écran a le focus pour appeler sa propre boucle de rafraîchissement
        if self.sm.current == "screen_FAO":
            self.dro_manager_instance.update_axes_val(donnees_fraiches)
        elif self.sm.current == "screen_CUTTER":
            if hasattr(self, 'cutter_page_instance') and self.cutter_page_instance:
                if hasattr(self.cutter_page_instance, 'update_axes_val'):
                    self.cutter_page_instance.update_axes_val(donnees_fraiches)

    # --- Propagation des ordres de rafraîchissement (Hérité de main_test) ---
    def refresh_propage(self, source_name):
        if source_name == 'draw_editor':
            print("[MAIN] Ordre de refresh propagé vers l'éditeur de dessin")
            # Vous pourrez appeler ici les méthodes de mise à jour de dessin_editor_instance si nécessaire

    # --- Sauvegarde de Fin de Session ---
    def sauvegarde_de_fin_de_session(self, *args):
        """
        💾 EXTINCTION SÉCURISÉE :
        Fige les coordonnées absolues des 3 chariots mécaniques (X, Z, Y) 
        dans le dictionnaire avant de couper le moteur Kivy.
        """
        print("[FERMETURE] Enregistrement de l'état des axes dans user_settings.json...")
        try:
            # FIXATION DES 3 AXES PHYSIQUES RÉELS (En microns entiers)
            SETTINGS["axis"]["hor"]["last_position_micron"] = int(self.machine.z_machine)
            SETTINGS["axis"]["vert"]["last_position_micron"] = int(self.machine.x_machine)
            SETTINGS["axis"]["sup"]["last_position_micron"] = int(self.machine.y_machine)
            SETTINGS["user_last_select"]["tactile_keyboard"] = bool(self.mode_tactile_actif)
            actif_tool = [self.lib_cutter.active_cutter.ident, self.lib_cutter.act_cut_idx_tourelle, self.lib_cutter.act_cut_grp_ofst]
            SETTINGS["user_last_select"]["selected_tool"] = list(actif_tool)
            # 🚪 PORTE ENTROUVERTE : En commentaire car votre capteur TLE5012B est absolu !
            # SETTINGS["axis"]["s"]["last_position_micron"] = int(self.machine.spindle_machine)

            # Écriture propre sur le disque dur
            save_json(SETTINGS_FILE, SETTINGS)
            print("[FERMETURE] user_settings.json sauvegardé proprement. À bientôt dans l'atelier !")
            
        except Exception as e:
            print(f"❌ [FERMETURE ERROR] Échec du stockage automatique à la fermeture : {e}")
            
        return False  # Signifie à Kivy : 'C'est bon, tu peux détruire la fenêtre et quitter'

    def basculer_mode_tactile(self):
        """ 🎛️ COMMUTATEUR PUR DU MODE DE SAISIE (V_7.2 Épurée) """
        # 1. Inversion de l'interrupteur logique en RAM
        self.mode_tactile_actif = not self.mode_tactile_actif

        if self.mode_tactile_actif:
            print("📡 [DRO Config] Mode TACTILE enclenché (ON).")
        else:
            print("📡 [DRO Config] Mode CLAVIER physique enclenché (OFF).")



    
if __name__ == '__main__':
    SmartDroApp().run()