#   configurator/ config_data.py

import os
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout

from screen_base.common_screen import BaseScreenLayout


Builder.load_file(os.path.join(os.path.dirname(__file__), "config_data.kv"))

class ParamPageHeader(BoxLayout):
    pass

class ParamPageDashboard(BoxLayout):
    pass

class ParamPageManager(BaseScreenLayout):
    """ 🛠️ L'ÉCRAN DES PARAMÈTRES CONSTRUCTEUR (Résolution axes, com, Soft Limits) """
    
    def on_kv_post(self, base_widget):
        header = ParamPageHeader()
        # Injection avec l'icône de la roue dentée mécanique !
        self.injecter_entete_specifique(header)
        
        dashboard = ParamPageDashboard()
        self.injecter_corps_specifique(dashboard)

    def screen_focused(self):

        print("[PAGE PARAM] Focus reçu. Accès aux variables d'usine sécurisé.")
        pass
