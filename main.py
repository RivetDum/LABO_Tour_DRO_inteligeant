# main (définitif)

from kivy.config import Config
Config.set('graphics', 'width', '1010')
Config.set('graphics', 'height', '600')

import sys
import os
from pathlib import Path
import json

# Alignement du chemin d'importation
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import format_unit, USER_LANGAGE, SETTINGS, save_json, SETTINGS_FILE
from part.draw_pnt_manager import PointManager
from cutting_tool.cutter import CutterManager
from machine_tool.machine_data import MachineState
from reel_time.machine_mcu import CommManager
from dro_viewer import DroManager
from part.draw_data import PointDrawEditor  # Import de l'éditeur CAO

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.clock import Clock
from i18n import set_language, tr, Tr, TR

# Gestion de l'icône de l'application
BITMAPS_DIR = Path(__file__).resolve().parent / "bitmaps"
ICON_PATH = BITMAPS_DIR / "icone.ico"

class SmartDroApp(App):
    icon = str(ICON_PATH)
    title = "DRO intelligent"  # Sera traduit dynamiquement dans build()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.machine = MachineState()   # Status de configuration et mesures de la machine
        self.calculator = CommManager(self.machine)  # chargement du profil d'usinage (porfil partagé avec le MCU)
        # === Poursuite de l'initialisation des gros blocs de valeurs ===
        self.part = PointManager()      # Partagé entre l'IHM DRO et l'Éditeur Dessin !
        self.cutter = CutterManager()   
        
        
        set_language(USER_LANGAGE)
        self.dro_clock = None  # Référence pour notre tick à 60Hz

    def build(self):        
        # Traduction à la volée du titre de la fenêtre au démarrage
        self.title = tr("dro_intelligent_title") 

        # Liaison de la fonction de sauvegarde à la fermeture de l'application
        Window.bind(on_request_close=self.sauvegarde_de_fin_de_session)

        # 1. Création du gestionnaire d'écrans (Le classeur principal)
        self.sm = ScreenManager()

        # 2. PAGE A : L'ÉCRAN DRO
        screen_dro = Screen(name="ecran_dro")
        self.dro_manager_instance = DroManager(self.part, self.cutter, self.machine)
        screen_dro.add_widget(self.dro_manager_instance)
        
        # Événements de page pour allumer/éteindre l'horloge automatique
        screen_dro.on_enter = self.demarrer_horloge_dro
        screen_dro.on_leave = self.stopper_horloge_dro
        self.sm.add_widget(screen_dro)

        # 3. PAGE B : L'ÉCRAN DE DESSIN CAO
        screen_dessin = Screen(name="ecran_dessin")
        # On passe notre 'self.part' unique pour que le dessin modifie la même pièce que la DRO !
        self.dessin_editor_instance = PointDrawEditor(self.part) 
        screen_dessin.add_widget(self.dessin_editor_instance)
        self.sm.add_widget(screen_dessin)

        # 4. BOUTONS DE COMMUTATION TEMPORAIRES (À intégrer dans vos menus KV plus tard)
        btn_vers_dessin = Button(text="[ CAO DESSIN ]", size_hint=(None, None), size=(140, 35), pos=(10, 10))
        btn_vers_dessin.bind(on_release=lambda x: self.changer_ecran("ecran_dessin"))
        self.dro_manager_instance.add_widget(btn_vers_dessin)

        btn_vers_dro = Button(text="[ RETOUR DRO ]", size_hint=(None, None), size=(140, 35), pos=(10, 10))
        btn_vers_dro.bind(on_release=lambda x: self.changer_ecran("ecran_dro"))
        self.dessin_editor_instance.add_widget(btn_vers_dro)

        print('STARTED_SmartDroApp (Unified DRO + CAO)')
        
        # Chargement de l'écran DRO par défaut à l'ouverture
        self.sm.current = "ecran_dro"
        return self.sm

    # --- Logique de Commutation et Horloge Visuelle ---
    def changer_ecran(self, nom_ecran):
        self.sm.current = nom_ecran

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
        """Prend les cotes fraîches du MachineState (Rayons/Microns) et rafraîchit l'IHM."""
        donnees_fraiches = self.machine.generer_dictionnaire_dro()
        self.dro_manager_instance.update_axes_val(donnees_fraiches)

    # --- Propagation des ordres de rafraîchissement (Hérité de main_test) ---
    def refresh_propage(self, source_name):
        if source_name == 'draw_editor':
            print("[MAIN] Ordre de refresh propagé vers l'éditeur de dessin")
            # Vous pourrez appeler ici les méthodes de mise à jour de dessin_editor_instance si nécessaire

    # --- Sauvegarde Industrielle de Fin de Session (Mach3 Style) ---
    def sauvegarde_de_fin_de_session(self, *args):
        print("[FERMETURE] Enregistrement de l'état des axes dans user_settings.json...")
        try:
            # Enregistrement des vrais microns physiques du modèle
            SETTINGS["axis"]["hor"]["last_position_micron"] = int(self.machine.z_machine)
            SETTINGS["axis"]["vert"]["last_position_micron"] = int(self.machine.x_machine)
            SETTINGS["axis"]["sup"]["last_position_micron"] = int(self.machine.y_machine)
            SETTINGS["axis"]["s"]["last_position_micron"] = int(self.machine.spindle_machine)

            # Écriture propre respectant votre formateur humain save_json_with_format
            save_json(SETTINGS_FILE, SETTINGS)
            print("[FERMETURE] user_settings.json sauvegardé proprement.")
            
        except Exception as e:
            print(f"[ERROR] Échec du stockage automatique à la fermeture : {e}")
            
        return False # Confirme la fermeture de la fenêtre Kivy

if __name__ == '__main__':
    SmartDroApp().run()