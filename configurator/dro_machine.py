# configurator/ dro_machine.py

import os
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from screen_base.common_screen import BaseScreenLayout


Builder.load_file(os.path.join(os.path.dirname(__file__), "dro_machine.kv"))

class OffsetPageHeader(BoxLayout):
    pass

class OffsetPageDashboard(BoxLayout):
    pass

class OffsetPageManager(BaseScreenLayout):
    """ 📐 L'ÉCRAN DE LA TABLE GLOBALE DES CORRECTEURS D'OUTILS (1 à 199) """
    
    def on_kv_post(self, base_widget):
        header = OffsetPageHeader()
        # Injection avec l'icône de mesure de jauge !
        self.injecter_entete_specifique(header)
        
        dashboard = OffsetPageDashboard()
        self.injecter_corps_specifique(dashboard)

    def screen_focused(self):

        print("[PAGE OFFSETS] Focus reçu. Table globale synchronisée.")
        pass
