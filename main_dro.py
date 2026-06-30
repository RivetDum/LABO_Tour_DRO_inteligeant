# main_dro.py à la racine du projet

from kivy.config import Config
Config.set('graphics', 'width', '1010')
Config.set('graphics', 'height', '600')
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import format_unit, USER_LANGAGE
from part.draw_pnt_manager import PointManager
from cutting_tool.cutter import CutterManager
from machine_tool.machine_data import MachineState
from reel_time.machine_mcu import CommManager
from dro_viewer import DroManager

from kivy.app import App
from kivy.core.window import Window
from i18n import set_language, tr, Tr, TR
from part.draw_data import PointDrawEditor  # Import absolu depuis le package "part"

from pathlib import Path

import json

BITMAPS_DIR = Path(__file__).resolve().parent / "bitmaps"
ICON_PATH = BITMAPS_DIR / "icone.ico"
#ICON_PATH = BITMAPS_DIR / "icone2.jpg"


class DroApp(App):
    icon =  str(ICON_PATH)               # icône de l'application
    title = "DRO intelligent"      # 👈 titre de la fenêtre <-  ici je peux déjà mettre une traduction ?

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # === Les 3 blocs de données ===
        self.part = PointManager()      # Géométrie, contours, points, trajectoires, unités
        self.cutter = CutterManager()   # Outils, diamètres, offsets
        self.machine = MachineState()   # État de la machine (coordonnées, homing, état axes)
        self.calculator = CommManager(self.machine) # Communication MCU, lecture/synchro temps réel, thread séparé
        
        set_language(USER_LANGAGE)
    
    def build(self):        
        # On attache la fonction de sauvegarde lors de la demande de fermeture
        Window.bind(on_request_close=self.sauvegarde_de_fin_de_session)

        print('STARTED_DROApp')
        return DroManager(self.part, self.cutter, self.machine)

    def sauvegarde_de_fin_de_session(self, *args):

        print("[FERMETURE] Enregistrement de l'état de la DRO...")
        
        chemin_config = "user_settings.json"
        
        try:
            # 1. Lire le fichier de configuration existant pour ne pas corrompre le reste
            with open(chemin_config, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # 2. Récupérer les positions actuelles (en microns bruts depuis votre DRO / PointManager)
            # Remplacer par vos vraies variables d'acquisition
            config_data["axis"]["hor"]["last_position_micron"] = int(self.root.position_Z_actuelle)
            config_data["axis"]["vert"]["last_position_micron"] = int(self.root.position_X_actuelle)
            config_data["axis"]["sup"]["last_position_micron"] = int(self.root.position_Y_actuelle)
            
            # Sauvegarder aussi le dernier état de la broche si nécessaire
            config_data["axis"]["s"]["last_position_micron"] = int(self.root.position_Spindle_actuelle)

            # 3. Ré-écrire proprement le fichier JSON mis à jour
            with open(chemin_config, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
                
            print("[FERMETURE] user_settings.json mis à jour avec succès.")
            
        except Exception as e:
            print(f"[ERROR] Échec de la sauvegarde automatique à la fermeture : {e}")
            
        # IMPORTANT : Retourner False permet à Kivy de fermer la fenêtre normalement.
        # Retourner True bloquerait la fermeture de l'application.
        return False 

if __name__ == '__main__':
    DroApp().run()

