# common_screen/common_screen.py

from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
import os

# 🎯 L'INJECTION SECURISEE : On charge le .kv du même dossier
# (Fonctionne peu importe d'où est lancé le main.py de l'application)
chemin_kv = os.path.join(os.path.dirname(__file__), "common_screen.kv")
Builder.load_file(chemin_kv)


class BaseScreenToolBar(BoxLayout):
    """La barre latérale de boutons de navigation de l'atelier."""
    pass


class BaseScreenLayout(BoxLayout):
    """
    GABARIT CHÂSSIS UNIVERSEL :
    Fournit l'entête haute (header_zone), la barre d'outils (tools_bar) 
    et la zone de contenu (body_zone).
    """
    def injecter_entete_specifique(self, widget_entete):
        """Clipse un bandeau d'infos personnalisé dans la ligne du haut."""
        if widget_entete:
            # 🎯 Cible le tiroir header_zone
            self.ids.header_zone.clear_widgets()
            self.ids.header_zone.add_widget(widget_entete)

    def injecter_corps_specifique(self, widget_corps):
        """Clipse le formulaire métier (DRO, CAO, etc.) dans la zone de droite."""
        if widget_corps:
            # 🎯 Cible le tiroir body_zone
            self.ids.body_zone.clear_widgets()
            self.ids.body_zone.add_widget(widget_corps)
