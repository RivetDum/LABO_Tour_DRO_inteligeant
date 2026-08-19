# common_screen/common_screen.py

import os
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image

import part.draw_tool.popup_segment as pop


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

    page_status_alert = StringProperty("OK")    # Stocke en permanence le statut de santé local de l'écran ("OK", "MODIFIED", "WARNING", "ERROR").
    icon_page = StringProperty("")              # Stocke l'icône de la page pour la màj auto de son kv kv
    associated_target_screen = StringProperty("")

    def on_kv_post(self, base_widget):
        app = App.get_running_app()
        if app and self.associated_target_screen:
            # 📡 On branche l'écoute automatique sur le dictionnaire du main()
            app.bind(**{self.associated_target_screen: self._auto_sync_from_main})
            self._auto_sync_from_main()

    def _auto_sync_from_main(self, *args):
        app = App.get_running_app()
        if app and self.associated_target_screen:
            dict_main = getattr(app, self.associated_target_screen, None)
            if dict_main:
                self.icon_page = str(dict_main.get("icon", ""))
                self.page_status_alert = str(dict_main.get("status", "OK"))

    def injecter_entete_specifique(self, widget_entete):
            """Clipse un bandeau d'infos personnalisé dans la ligne du haut."""
            if not widget_entete:
                return

            self.ids.header_zone.add_widget(widget_entete)

    def injecter_corps_specifique(self, widget_corps):
        """Clipse le formulaire métier (DRO, CAO, etc.) dans la zone de droite."""
        if widget_corps:
            # 🎯 Cible le tiroir body_zone
            self.ids.body_zone.clear_widgets()
            self.ids.body_zone.add_widget(widget_corps)

# Dans screen_base/common_screen.py -> classe BaseScreenLayout

    def open_floating_input(self, widget_target, init_text: str, convert_func, write_action, on_success_callback, unit=None, label_name: str = ""):
        """
        🎛️ THE SMART INTERFACE DISPATCHER (V_7.2) :
        Analyse l'argument 'unit' et le mode tactile pour ouvrir automatiquement 
        le champ texte Excel-Style ou la calculatrice industrielle CalculatorPopup.
        """
        app = App.get_running_app()

        # On met les fonctions de rappel au chaud dans les casiers secrets pour le mode clavier
        self._convert_func = convert_func
        self._write_action = write_action
        self._on_success = on_success_callback
        self._label_name = label_name

        # 🔀 CONCEPT DU CAFÉ VALIDÉ : AIGUILLAGE AUTOMATIQUE SELON L'UNITÉ
        if app.mode_tactile_actif and (unit is not None or unit != "" or unit != "txt"):
            # 🎯 CAS A : C'est une valeur physique numérique et l'opérateur demande le tactile !
            print(f"📡 [DRO Engine] Opening CalculatorPopup for unit: '{unit}' on field '{label_name}'")
            
            # Recette de cuisine spécifique pour décoder le dictionnaire 'pack_data' de votre Calculatrice
            def callback_calculatrice(pack_data):
                # On extrait la valeur float pure reçue de la calculatrice (ex: 0.040)
                # Comme la calculatrice renvoie déjà un float propre, on la passe à votre convertisseur local
                # (votre méthode mm_to_microns va en faire un entier 40)
                valeur_string_brute = str(pack_data["value"])
                processed_val = self._convert_func(valeur_string_brute)
                
                if processed_val is None:
                    if on_success_callback: on_success_callback("KO")
                    return
                
                # Écriture directe en RAM via le lambda du .kv
                self._write_action(processed_val)
                
                # Signal de rafraîchissement d'IHM nominal
                if on_success_callback: on_success_callback("OK")

            # 🚀 Lancement de VOTRE composant existant de calculatrice d'atelier !
            # current_value = texte actuel, current_unit = unité, update_value_callback = notre recette
            calc_popup = pop.CalculatorPopup(
                current_value=init_text,
                current_unit=unit,
                update_value_callback=callback_calculatrice,
                case_desgn=label_name,
                size_hint= (None, None),
                size= (1400, 600) 
            )
            calc_popup.open()
            
        else:
            # 🎯 CAS B : C'est du texte brut (unit=None) ou le mode clavier physique est actif
            print("📡 [DRO Engine] Deploying floating text-input layer (Excel-Style).")
            
            # Métrologie des pixels pour aligner le calque éphémère (Option 2)
            win_x, win_y = widget_target.to_window(*widget_target.pos)
            local_x, local_y = self.to_local(win_x, win_y)

            float_box = self.ids.float_input_box
            float_box.size = widget_target.size
            float_box.pos = (local_x, local_y)

            # Déverrouillage et réactivation du champ
            champ = self.ids.input_text_floating
            champ.disabled = False
            champ.text = str(init_text)
            champ.padding = [10, (widget_target.height - widget_target.font_size) / 2]
            champ.focus = True

# Dans screen_base/common_screen.py -> classe BaseScreenLayout

    def save_floating_input(self):
        """ 💾 PROCESSES, WRITES RAM AND RETURNS STATUS 'OK' OR 'KO' (V_7.2) """
        float_box = self.ids.float_input_box
        champ = self.ids.input_text_floating
        
        if float_box.width == 0:    # Associer à float_box.size = (0, 0) qui suit directement, sert de bedounce pour les double validation ( [ENTER] + perte focus)
            return
        float_box.size = (0, 0)
        float_box.pos = (-1000, -1000)

        raw_text = champ.text.strip()

        # Verrouillage complet du focus et masquage immédiat du FloatLayout parent
        champ.focus = False
        champ.disabled = True

        # A. 🟢 CONVERSION (Gérée au sommet par la classe mère)
        processed_val = self._convert_func(raw_text)
        
        # 🚨 CAS D'ÉCHEC (Votre concept KO)
        if processed_val is None:
            print("🚨 [DRO Engine] Input validation failed. RAM protected.")
            
            # Sauvegarde locale du callback avant de vider les casiers
            on_success_func = self._on_success
            
            # Nettoyage méticuleux des casiers secrets pour la prochaine saisie
            self._convert_func = None
            self._write_action = None
            self._on_success = None
            
            # Retour à l'envoyeur avec le badge "KO" !
            if on_success_func:
                on_success_func("KO")
            return

        # B. 🟢 WRITING RAM (Si le traitement est OK)
        self._write_action(processed_val)

        # C. ⚡ REFRESH GRAPHIC (Votre concept OK)
        if hasattr(self, '_on_success') and self._on_success:
            on_success_func = self._on_success
            
            # Nettoyage des casiers secrets
            self._convert_func = None
            self._write_action = None
            self._on_success = None
            
            # Retour à l'envoyeur avec le badge "OK" !
            on_success_func("OK")

