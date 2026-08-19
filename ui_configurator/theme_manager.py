# ui_configurator \ theme_manager.py

import os
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from screen_base.common_screen import BaseScreenLayout
#from ui_configurator.theme_ui import UiTheme
#from copy import deepcopy

#_current_theme = None  # Thème courant
#_fallback_theme = None  # Thème de secours en cas de bug

draw_line= {    # couleurs et épaisseur de dessin
    "liaison": "#838d83",
    "liaison_w": 2,
    "detail": "#11de1b",
    "detail_w": 3,
    "erreur_detail": "#ff0055",
    "erreur_detail_w": 4,
    "profil_save": "#fb96bd",
    "profil_save_w": 1.9,
    "erreur_profil_save": "#ff0055",
    "erreur_profil_save_w": 3,
    "profil_cao": "#3cb1ff",
    "profil_cao_w": 2.1,
    "erreur_profil_cao": "#ff0055",
    "erreur_profil_cao_w": 4,
    "profil_fao": "#ffd255",
    "profil_fao_w": 2.2,
    "erreur_profil_fao": "#ff0055",
    "erreur_profil_fao_w": 6,
    "profil_big_bbox": "#81ff5e",
    "profil_big_bbox_w": 1,
    "profil_bbox": "#a0ff86",
    "profil_bbox_w": 1,
    "detail_bbox": "#a0ff86",
    "detail_bbox_w": 1,
    "tool_profil": "#A6A6A6",   # contour: corp du burin
    "tool_profil_w": 4,
    "tool_profil_fill": "#eaea05",   # remplissage: plaquette carbure de coupe (pour les type: 'mesh' ou 'cercle')
    "offset": "#e5a3ff",   # couleur de ligne (inutile pour l'offset, mais à laisser pour la logique)
    "offset_w": 0,   # Epaisseur de ligne (inutile pour l'offset, mais à laisser pour la logique)
    "offset_fill": "#e5a3ff",   # remplissage: rond  représentant l'offset d'usinage autour de la pointe de l'outil
    # ci-dessous, à remplacer par ci-dessus
    "profil": "#3dd9f5",
    "profil_w": 2,
    "profil_fill": "#d2229491",   # remplissage: par défaut pour les type: 'mesh' ou 'cercle'
    "erreur_profil": "#ff0055",
    "erreur_profil_w": 4,

    # 🟢 COMPLÉTÉ : Votre Grille Premium à double étage Actif / Inactif (V_7.2)
    "status_ok_a":        "#33b34d",    # Vert éclatant (Onglet en cours et OK)
    "status_ok_ia":       "#1F6522",    # Vert éteint (Onglet en tâche de fond et OK)
    "status_warning_a":   "#ffd255",    # Jaune éclatant (Onglet en cours avec alerte basse)
    "status_warning_ia":  "#b3933b",    # Jaune éteint (Onglet en arrière-plan avec alerte basse)
    "status_modified_a":  "#c7661a",    # Orange éclatant (Onglet en cours modifié)
    "status_modified_ia": "#914a13",    # Orange éteint (Onglet en arrière-plan modifié)
    "status_error_a":     "#e22929",    # Rouge éclatant (Onglet en cours avec erreur homing)
    "status_error_ia":    "#9c1c1c",    # Rouge éteint (Onglet en arrière-plan avec erreur homing)
    "status_blue_a":      "#5bbbeb",    # Bleu pas utilisé, juste pour tester
    "status_blue_ia":     "#406fa9",
    # 🎨 Les Fonds de Boutons Standards (Onglets de Navigation)
    "btn_active_bg_a":    "#2e2e38",    # Fond de l'onglet sélectionné
    "btn_active_bg_ia":   "#1a1a20",    # Votre effet semi-reflet 3D
    "btn_inactive_bg_a":  "#1f1f24",    
    "btn_inactive_bg_ia": "#000000",
    # 🎛️ Le Thème Spécifique du Commutateur TACTILE (Différencié des onglets)
    "sw_active_bg_a":     "#212921",    # Fond teinté vert sombre si TACTILE est ON
    "sw_active_bg_ia":    "#141914",
    "sw_inactive_bg_a":   "#252129",    # Fond teinté bordeaux/gris éteint si TACTILE est OFF
    "sw_inactive_bg_ia":  "#171419",
    #new     # 🟢 LA VERSION LUXE : CADRES LED SPÉCIFIQUES POUR LE SWITCH TACTILE
    # Quand le tactile est OFF, il n'utilise plus le rouge ni l'orange, mais ce fameux vert pâle/olive très pro !
    "sw_status_ok_a":     "#33b34d",    # Vert vif quand Tactile est ON (Enclenché)
    "sw_status_ok_ia":    "#4E3F52",    # ➔ VERT PÂLE/OLIVE quand Tactile est OFF (Au repos, sans erreur) !

    # 🎨 COULEURS DE FOND (Les fameux "bg" / Beaux Gosses d'atelier)
    "btn_bg_a":           "#7D7D9A",    # Fond du bouton actif (sélectionné)
    "btn_bg_ia":          "#3f3f4d",    # Fond du bouton inactif (au repos)
    
    "sw_bg_a":            "#234123",    # Fond teinté vert si le Switch est actif (ON)
    "sw_bg_ia":           "#302828"    # Fond teinté sombre si le Switch est inactif (OFF)


}


Builder.load_file(os.path.join(os.path.dirname(__file__), "theme_manager.kv"))


class SettingsPageHeader(BoxLayout):
    """ En-tête textuel pour la page des préférences opérateur """
    pass

class SettingsPageDashboard(BoxLayout):
    """ Zone centrale temporaire 'En Construction' """
    pass

class SettingsPageManager(BaseScreenLayout):
    """ ⚙️ L'ÉCRAN DES RÉGLAGES UTILISATEUR (Thèmes, Langues, Unités) """
    active_screen_name = StringProperty("Configuration DRO")

    def on_kv_post(self, base_widget):
        if 'tools_bar' in self.ids:
            # Allumage du bouton de réglage si existant dans votre barre
            if hasattr(self.ids.tools_bar.ids, 'btn_setting'):
                self.ids.tools_bar.ids.btn_setting.status = 1

        header = SettingsPageHeader()
        # Injection avec votre nouvelle icône ico_tools.png !
        self.injecter_entete_specifique(header)
        
        dashboard = SettingsPageDashboard()
        self.injecter_corps_specifique(dashboard)

    def screen_focused(self):

        print("[PAGE SETTINGS] Focus reçu. Prêt pour le confort opérateur.")
        pass
