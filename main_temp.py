# main_test.py à la racine du projet
from kivy.config import Config
Config.set('graphics', 'width', '1010')
Config.set('graphics', 'height', '600')
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import format_unit, USER_LANGAGE
from part.draw_pnt_manager import PointManager

from kivy.app import App
from i18n import set_language
from part.draw_data import PointDrawEditor  # Import absolu depuis le package "part"

class TestApp(App):
    def build(self):
        # Fichier principal ou contrôleur
        self.part_point_manager = PointManager()
        set_language(USER_LANGAGE)
        self.title = "Dessiner le profil par points"  # 👈 titre de la fenêtre <-  ici je peux déjà mettre une traduction ?
        print('STARTED_TestApp')

        '''TEST: 
        #from kivy.uix.button import Button
        # Définir la couleur de fond
        #color = [1, 0, 0, 1]  # Rouge, avec une opacité de 1
        # Appliquer la couleur à la classe Button
        #setattr(Button, 'background_color', color)
        # Maintenant, tous les boutons créés auront cette couleur de fond
        #button1 = Button(text="Bouton 1")
        #print(f"Boutton color{button1.background_color}")  # Affiche [1, 0, 0, 1]
        # Avant modif: Boutton color[1, 1, 1, 1]
        # Après modif: Boutton color[1, 0, 0, 1]
        # Après suppression de la modif: Boutton color[1, 1, 1, 1]'''

        return PointDrawEditor(self.part_point_manager)

    def refresh_propage(self, source_name):
        if source_name == 'draw_editor':
            # ici ce que PointDrawEditor doit rafraichir:
            print("TestApp: Le main() ordonne un refresh draw_editor")
        else:
            pass

if __name__ == '__main__':
    TestApp().run()
