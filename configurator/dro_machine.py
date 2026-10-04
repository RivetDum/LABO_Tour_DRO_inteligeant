# configurator/ dro_machine.py

import os
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty, ObjectProperty, DictProperty
from kivy.uix.boxlayout import BoxLayout
from screen_base.common_screen import BaseScreenLayout


Builder.load_file(os.path.join(os.path.dirname(__file__), "dro_machine.kv"))

class OffsetPageHeader(BoxLayout):
    pass

class OffsetPageDashboard(BoxLayout):
    pass

class OffsetPageManager(BaseScreenLayout):
    """ 📐 L'ÉCRAN DE LA TABLE GLOBALE DES CORRECTEURS D'OUTILS (1 à 199) """


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.axe_y_angle = [45000, True]
        self.tourelle_angle = [0, False]
    
    def on_kv_post(self, base_widget):
        header = OffsetPageHeader()
        # Injection avec l'icône de mesure de jauge !
        self.injecter_entete_specifique(header)
        
        dashboard = OffsetPageDashboard()
        self.injecter_corps_specifique(dashboard)

    def screen_focused(self):

        print("[PAGE OFFSETS] Focus reçu. Table globale synchronisée.")
        pass

    '''########## EBAUCHE de fonctions:
    def compenser_rotation_chariot_y(angle_y_deg: float, centre_rotation: list):
        """
        📐 LE COMPENSATEUR MAGIQUE :
        Calcule le décalage de l'origine pièce généré par le pivotement de Y.
        angle_y_deg est lu en direct depuis l'ESP32.
        """
        angle_rad = math.radians(angle_y_deg)
        
        # Centre de rotation mémorisé dans les paramètres [Z_pivot, X_pivot]
        z_p, x_p = centre_rotation[0], centre_rotation[1]
        
        # Matrice de rotation 2D appliquée sur le bras de levier
        # (Calcule où s'est déplacé le nez de la tourelle dans l'espace machine)
        delta_z = z_p * (1 - math.cos(angle_rad)) + x_p * math.sin(angle_rad)
        delta_x = -z_p * math.sin(angle_rad) + x_p * (1 - math.cos(angle_rad))
        
        return [delta_z, delta_x] # Renvoie les microns exacts à soustraire au DRO !
    '''

