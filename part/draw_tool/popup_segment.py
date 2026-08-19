# point_draw/ popups.py
    # Anciennement: popup_segment.py

import math
import copy
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput

from common_widgets import MyLabel, Separator, GroupHeader, LabeledCell, InputCell, InputCellLabel, CustomSpinner, STATUS_NEUTRE, STATUS_INACTIF, STATUS_ERREUR, STATUS_VALIDE, STATUS_TRANSLICIDE
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from configurator.config import parse_user_input, get_unit_id, get_unit_config, switch_unit, get_all_units_for_type, AXIS_CONFIG


class CalculatorPopup(Popup):
    '''
    PopUp servant à écrire de nouvelle dimensions
    dans un Input en tenant compe des unitées,
    mais aussi avec posibilité de débuire la valeur d'opération simple comme :
        (l'addition, soustraction, multiplication, divison)
    Vérifie aussi que les valeurs à écrires son dans un format accéptable par le logiciel
    '''
    
    #BT_VALIDATE = "ENTER" + " ➔  "  # VErsion traducteur: TR("enter") + " ➔  "    # Désignation du bouton de validation de l'oppération en cours

    # 🎨 PALETTE DE COULEURS
    BRUN_ORANGE   = (0.788, 0.502, 0.024, 1)    # Fonctions mathématiques
    BLEU_BOUTON   = (0.459, 0.722, 0.969, 1)    # Compléments (+/-, .)
    GRIS_BOUTON   = (0.812, 0.784, 0.737, 1)    # Chiffres actifs
    DESACT_BOUTON = (0.220, 0.180, 0.180, 1)    # Inactifs (Bordeaux éteint)
    VERT_VALIDER  = (0.3, 0.7, 0.3, 1)          # Validation OK
    ROUGE_ANNULER = (0.8, 0.3, 0.3, 1)          # Correction locale CE

    BUTTONS_COLORS = [      # boutons de la grille de la calculatrice
        GRIS_BOUTON, GRIS_BOUTON, GRIS_BOUTON, BRUN_ORANGE,     #  7  |  8  |  9  |  /  ||  END
        GRIS_BOUTON, GRIS_BOUTON, GRIS_BOUTON, BRUN_ORANGE,     #  4  |  5  |  6  |  *  ||   C
        GRIS_BOUTON, GRIS_BOUTON, GRIS_BOUTON, BRUN_ORANGE,     #  1  |  2  |  3  |  -  ||   CE  || Unit_spinner
        BLEU_BOUTON, GRIS_BOUTON, BLEU_BOUTON, BRUN_ORANGE      # +/- |  0  |  .  |  +  ||   =
    ]

    def __init__(self, current_value, current_unit, update_value_callback, case_desgn="", **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', (600, 250)) # Votre taille de base idéale pour le 400x680        
        super().__init__(**kwargs)

        self.title = f"Modifier la valeur de : {case_desgn}"
        self.update_value_callback = update_value_callback

        # ─── 1. BLINDAGE ET INITIALISATION DES DONNÉES GÉOMÉTRIQUES ───
        unit_parsed = get_unit_id(current_unit)
        if not unit_parsed: unit_parsed = get_unit_id("dist")   # valeur de secour si current_unit inexploitable, utiliser l'unité par défaut de distance !
        self.unit_list = get_all_units_for_type(unit_parsed, with_labels=True)
        if not self.unit_list: self.unit_list = [(unit_parsed, unit_parsed)]
            # Valeurs reçues: STRUCTURES 3 COLONNES
        self.original_data = parse_user_input(current_value, current_unit)      # -1: Start : Reçues à l'ouverture de la popup, ne bouge jamais
        if isinstance(self.original_data, str):   # Contrôle du parse failed
            self.original_data = parse_user_input(current_value, unit_parsed)
            if isinstance(self.original_data, str):   # Contrôle du parse_2 failed
                self.original_data = [0.0, unit_parsed, unit_parsed]    # A ce stade original_data à des valeurs exptoitable par la calculation

        # ─── 2. VARIABLES POUR LA CALCULATION (STRUCTURES 3 COLONNES) ───
        self.base_data = copy.deepcopy(self.original_data)      # -2: L'Ancre : Calculs cumulés validés (Verrouillé en unité origine)
        self.return_data = copy.deepcopy(self.original_data)    # -3: Panier de sortie (Renvoyé au callback final), comme base_data mais en unités actuels.
        self.input_data = [0.0, self.return_data[1], self.return_data[2]]    # -4: La Saisie (Bloc 3) : Init en unité retour
        self.preview_data = [self.base_data[0], self.return_data[1], self.return_data[2]] # -5: La Prévisualisation (Bloc 4) Valeur en unit_original et unit_id + unit_lbl en unitée de retour
            # Relevé des propriétés d'affichage des unités     Returns:{"unit_id": str,"type": str,"factor": float,"decimals": int,"label": strs}
        self.unit_origine_Property = get_unit_config(self.base_data[1])
        self.unit_return_Property = get_unit_config(self.return_data[1])
        self.unit_preview_Property = get_unit_config(self.preview_data[1])
        self.unit_input_Property = get_unit_config(self.input_data[1])
            # États et versions textes pour Kivy
        self.saisie_active = False   # True dès que l'opérateur tape un chiffre (Gère le duel END / CE)
        self.calcul_validable = False # True uniquement si l'opération peut être validée par la touche (=)
        self.is_calculating = None  # None pour entrée directe, ou "+", "-", "*", "/"
        self.operator_text = "Remplacer" if self.is_calculating is None else self.is_calculating # Texte de l'opérateur (Bloc 2)
        self.input_text = ""        # Version chaîne pour le pavé numérique (Bloc 3)
        val_transposee = switch_unit(self.preview_data[0], self.base_data[1], self.preview_data[1])
        self.preview_text = f"{val_transposee[0]:0.{self.unit_preview_Property['decimals']}f} {val_transposee[2]}" 

        # ─── 3. ASSEMBLAGE DES ZONES DE L'ÉCRAN ───
        layout_principal = BoxLayout(size_hint=(1,1), orientation='horizontal', padding=10, spacing=0)
        self.touches_calculatrice = {} # Dictionnaire pour mémoriser les boutons

       # 1 ═> GAUCHE : LE PAVÉ NUMÉRIQUE  ═══
        grid_gauche = GridLayout(size_hint_x=0.50, cols=4, spacing=(5, 5))
        buttons = ['7',  '8',  '9',  '/',      # 'END' <== ici grid_centre (l'autre colonne de boutons)
                   '4',  '5',  '6',  '*',      # 'C'
                   '1',  '2',  '3',  '-',      # 'CE'
                   '+/-','0',  '.',  '+']      # '='
        for i, button in enumerate(buttons):
            btn = Button(text=button, on_press=self.on_button_press, background_normal="", background_color=self.BUTTONS_COLORS[i], background_disabled_normal="", disabled_color=(0.4, 0.4, 0.4, 1),
                font_size='28sp', bold=True, color=(0.15, 0.15, 0.15, 1))
            btn.background_color_enabled = btn.background_color; btn.background_color_disabled = self.DESACT_BOUTON # Devient bordeaux éteint si désactivé
            self.touches_calculatrice[button] = btn
            grid_gauche.add_widget(btn)
        
        # 3 ═> CENTRE : ACTIONS DE RESETS / VAALIDATIONS ═══
        grid_centre = GridLayout(size_hint_x=0.125, cols=1, spacing=(5, 5))
        btn_close = Button(text="END", on_press=self.on_closed, background_normal="", background_color=self.VERT_VALIDER, background_disabled_normal="", disabled_color=(0.4, 0.4, 0.4, 1),
                font_size='28sp', bold=True, color=(0.15, 0.15, 0.15, 1))
        btn_close.background_color_enabled = btn_close.background_color;  btn_close.background_color_disabled = self.DESACT_BOUTON
        btn_c = Button(text="C", on_press=self.on_button_press, background_normal="", background_color=self.ROUGE_ANNULER, background_disabled_normal="", disabled_color=(0.4, 0.4, 0.4, 1),
                font_size='28sp', bold=True, color=(0.15, 0.15, 0.15, 1))
        btn_c.background_color_enabled = btn_c.background_color; btn_c.background_color_disabled = self.DESACT_BOUTON
        btn_ce = Button(text="CE", on_press=self.on_button_press, background_normal="", background_color=self.BRUN_ORANGE, background_disabled_normal="", disabled_color=(0.4, 0.4, 0.4, 1),
                font_size='28sp', bold=True, color=(0.15, 0.15, 0.15, 1))
        btn_ce.background_color_enabled = btn_ce.background_color;  btn_ce.background_color_disabled = self.DESACT_BOUTON
        btn_ok = Button(text="=", on_press=self.on_click_enregistrer_intermediaire, background_normal="", background_color=self.BRUN_ORANGE, font_size='28sp', bold=True, color=(0.15, 0.15, 0.15, 1)) 
        btn_ok.background_color_enabled = btn_ok.background_color;  btn_ok.background_color_disabled = self.DESACT_BOUTON
        grid_centre.add_widget(btn_close); self.touches_calculatrice["END"] = btn_close #; btn_close.disabled = False
        grid_centre.add_widget(btn_c);     self.touches_calculatrice["C"]   = btn_c     # ce seraplus logique d'appeler la fonction de surveillance à la fin du init pour cela ?;    btn_c.disabled = True
        grid_centre.add_widget(btn_ce);    self.touches_calculatrice["CE"]  = btn_ce    #;    btn_ce.disabled = True
        grid_centre.add_widget(btn_ok);    self.touches_calculatrice["="]   = btn_ok    #;    btn_ok.disabled = True       

        # 4 ═> DROITE : AFFICHAGE NUM?ERIQUE, ;-) TICKET DE CAISSE ═══
        box_droite = BoxLayout(orientation='vertical', size_hint_x=0.40, padding=1, spacing=1)
            # Organisation des box_lignes (largeurs des colonnes)
        label_hint=0.36; valeur_hint=0.48; unit_hint=0.16; label_font= "16sp"; valeur_font="22sp"; unit_font="18sp"
                # Ligne 1 : Rappel de la valeur à l'ouverture de la popup
        droite_l1 = BoxLayout(orientation='horizontal', size_hint_y=0.2, padding=10, spacing=5)
        old_value_label = MyLabel(text= "Valeur original :", size_hint_x=label_hint, color=(0.6, 0.6, 0.6, 1),font_size=label_font)
        self.old_value_value = MyLabel(text=f"{self.original_data[0]:0.{self.unit_origine_Property['decimals']}f}", size_hint_x=valeur_hint, bold=True, color=(0.6, 0.6, 0.6, 1), halign="right", font_size=valeur_font)
        self.old_value_unit = MyLabel(text=f"{self.original_data[2]}", size_hint_x=unit_hint, color=(0.6, 0.6, 0.6, 1), bold=True, halign="right", font_size=unit_font)
        droite_l1.add_widget(old_value_label); droite_l1.add_widget(self.old_value_value); droite_l1.add_widget(self.old_value_unit)
        box_droite.add_widget(droite_l1); box_droite.add_widget(Separator(margin=1)); box_droite.add_widget(Separator(margin=1))
                # Ligne 2 : Dernière valeur valide (valeur retournée + val de départ pour opération)       
        droite_l2 = BoxLayout(orientation='horizontal', size_hint_y=0.2, padding=10, spacing=5)
        new_value_label = MyLabel(text="Nouvelle valeur :", size_hint_x=label_hint, color=(0.8, 1.0, 0.8, 1),font_size=label_font)
        self.new_value_value = MyLabel(text=f"{self.return_data[0]:0.{self.unit_return_Property['decimals']}f}", size_hint_x=valeur_hint, bold=True, color=(0.8, 1.0, 0.8, 1), halign="right", font_size=valeur_font)
        self.new_value_unit = MyLabel(text=f"{self.return_data[2]}", size_hint_x=unit_hint, color=(0.8, 1.0, 0.8, 1), bold=True, halign="right", font_size=unit_font)
        droite_l2.add_widget(new_value_label); droite_l2.add_widget(self.new_value_value); droite_l2.add_widget(self.new_value_unit)
        box_droite.add_widget(droite_l2)
                # Ligne 3 : désignation de l'opération à calculer 
        droite_l3 = BoxLayout(orientation='horizontal', size_hint_y=0.2, padding=10, spacing=5)
        operator_label = MyLabel(text="Signe :", size_hint_x=label_hint, color=(0.6, 0.6, 0.6, 1),font_size=label_font)
        self.operator_value = MyLabel(text=self.operator_text, size_hint_x=valeur_hint, bold=True, color=(0.6, 0.6, 0.6, 1), halign="right", font_size=valeur_font)
        self.operator_value.bind(text=self.on_text_change)
        no_unit = MyLabel(text="", size_hint_x=unit_hint, color=(0.6, 0.6, 0.6, 1), bold=True, halign="right", font_size=unit_font)
        droite_l3.add_widget(operator_label); droite_l3.add_widget(self.operator_value); droite_l3.add_widget(no_unit)
        box_droite.add_widget(droite_l3)
                # Ligne 4 : valeur et unité à utiliser     
        self.droite_l4 = BoxLayout(orientation='horizontal', size_hint_y=0.2, padding=10, spacing=5)
        clac_label = MyLabel(text="valeur :", size_hint_x=label_hint, color=(0.6, 0.6, 0.6, 1),font_size=label_font)
        #self.calc_input = InputCell(text="", status=STATUS_TRANSLICIDE, size_hint_x=valeur_hint, font_size=valeur_font)
        #self.calc_input = InputCell(text="", status=STATUS_VALIDE, size_hint_x=valeur_hint, font_size=valeur_font)
        #self.calc_input.foreground_color = (0.6, 0.6, 0.6, 1) # Appliqué après l'init, 100% sécurisé et sans crash !
        self.calc_input = MyLabel(text="", size_hint_x=valeur_hint, bold=True, color=(0.6, 0.6, 0.6, 1), halign="right", font_size=valeur_font)
        self.calc_input.bind(text=self.on_text_change)
        self.calc_spinner = Spinner(text=str(self.return_data[2]), values=[label for uid, label in self.unit_list], size_hint_x=unit_hint, background_normal="", background_color=self.BRUN_ORANGE, font_size=unit_font)
        self.calc_spinner.bind(text=self.on_text_change)
        self.spinner_placeholder = Widget(size_hint_x=unit_hint)    # 🎯 AJOUT : On crée un widget invisible de remplacement qui a exactement la même taille (unit_hint)
        self.droite_l4.add_widget(clac_label); self.droite_l4.add_widget(self.calc_input); self.droite_l4.add_widget(self.calc_spinner)
        box_droite.add_widget(self.droite_l4); box_droite.add_widget(Separator())
                # Ligne 5 : la prévisualisation du résultat
        droite_l5 = BoxLayout(orientation='horizontal', size_hint_y=0.5, padding=10, spacing=5)
        preview_label = MyLabel(text="Résultat :", size_hint_x=label_hint, color=(0.6, 0.6, 0.6, 1),font_size=label_font)
        self.preview_value = MyLabel(text=f"{self.preview_data[0]:0.{self.unit_preview_Property['decimals']}f}", size_hint_x=valeur_hint, bold=True, color=(0.6, 0.6, 0.6, 1), halign="right", font_size=valeur_font)
        self.preview_unit = MyLabel(text=f"{self.preview_data[2]}", size_hint_x=unit_hint, color=(0.6, 0.6, 0.6, 1), bold=True, halign="right", font_size=unit_font)
        droite_l5.add_widget(preview_label); droite_l5.add_widget(self.preview_value); droite_l5.add_widget(self.preview_unit)
        box_droite.add_widget(droite_l5)


        layout_principal.add_widget(grid_gauche)
        layout_principal.add_widget(Widget(size_hint_x=0.04))    # 2 ═> SCPACEUR : ESPACEUR ENTRE LES DEUX GRILLES DE BOUTONS
        layout_principal.add_widget(grid_centre)
        layout_principal.add_widget(Widget(size_hint_x=0.01))    # 2 ═> SCPACEUR : ESPACEUR ENTRE LES DEUX GRILLES DE BOUTONS
        layout_principal.add_widget(box_droite)

        self.add_widget(layout_principal)

        # ─── FIN DE L'__INIT__ : BRANCHEMENT DU CLAVIER PC (WINDOWS) ───
        from kivy.core.window import Window    
        # 🔗 On connecte l'intercepteur de touches physique
        Window.bind(on_key_down=self._on_keyboard_down)       
        # 🛡️ SÉCURITÉ : Quand la popup se ferme, on coupe TOUJOURS l'intercepteur 
        # pour éviter que le clavier ne reste bloqué sur la calculatrice une fois fermée
        self.bind(on_dismiss=lambda *args: Window.unbind(on_key_down=self._on_keyboard_down))

        
        self.rafraichir_previsualisation()

    def on_button_press(self, instance):
        """Gère l'appui sur les touches de la grille et du bouton de reset 'C' tout en haut."""
        button_text = instance.text
        
        # ─── 1. GESTION DE L'ANNULATION GLOBALE (Bouton C hors grille) ───
        if button_text == "C" or button_text == "Reset":
            self.base_data = copy.deepcopy(self.original_data)
            self.return_data = copy.deepcopy(self.original_data)
            
            # Mise à jour de la configuration d'unité pour que la ligne 2 retrouve ses décimales d'origine
            self.unit_return_Property = get_unit_config(self.return_data[1])
            nb_dec_ret = self.unit_return_Property["decimals"]
            self.new_value_value.text = f"{self.return_data[0]:0.{nb_dec_ret}f}"
            self.new_value_unit.text = str(self.return_data[2])
            
            self.nettoyer_bloc_saisie()
            self.rafraichir_previsualisation()
            return

        # ─── 2. GESTION DE LA TOUCHE CE (CORRECTION COMMANDE LOCALE) ───
        elif button_text == "CE":
            self.nettoyer_bloc_saisie()
            self.rafraichir_previsualisation()
            return

        # ─── 3. GESTION DES CHIFFRES (0 à 9) ET SIGNES ───
        elif button_text in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            self.input_text += button_text # On ajoute le caractère dans notre variable de texte brute
            
        elif button_text == ".":
            # Si le champ est vide, on force "0." par convention d'atelier
            self.input_text = "0." if not self.input_text else self.input_text + "."
                
        elif button_text == "+/-":
            if self.input_text:
                self.input_text = self.input_text[1:] if self.input_text.startswith("-") else "-" + self.input_text
            else: 
                self.input_text = "-" # Prêt à recevoir un chiffre négatif

        # ─── 4. GESTION DES OPÉRATEURS MATHÉMATIQUES (+, -, *, /) ───
        elif button_text in ["+", "-", "*", "/"]:
            # RÈGLE DE CUMUL CONTEXTUELLE : Si l'opérateur enchaîne un calcul sans presser l'égal intermédiaire,
            # on fait monter le résultat précédent dans l'Ancre automatiquement pour le laisser continuer.
            if self.is_calculating is not None and self.input_text:
                self.on_click_enregistrer_intermediaire(None)
            
            self.is_calculating = button_text # Enregistrement de l'opération (Bloc 2)
            self.operator_value.text = button_text # 🔄 CORRIGÉ : b2_val -> operator_value
            self.input_text = "" # Le Bloc 3 se vide, prêt pour la suite
            
            # 🎯 CONTINUITÉ D'UNITÉ : On force le Spinner à s'aligner sur le texte de l'Ancre (index 2)
            unite_ancre_texte = self.base_data[2]
            
            # 🔄 CORRIGÉ : unit_spinner -> calc_spinner & on_unit_spinner_changed -> on_text_change
            self.calc_spinner.unbind(text=self.on_text_change)
            self.calc_spinner.text = str(unite_ancre_texte)
            self.calc_spinner.bind(text=self.on_text_change)
            
            # Mise à jour manuelle des touches (car self.input_text passe à "" sans déclencher on_text_change)
            self.actualiser_verrouillage_touches()
            self.rafraichir_previsualisation()

        # ─── 🎯 TRANSFERT DU TEXTE VERS KIVY ───
        # On injecte la chaîne dans l'InputCell. Cela réveille automatiquement l'événement
        # on_text_change qui va lancer le pré-calcul et verrouiller les boutons impossibles !
        if button_text not in ["+", "-", "*", "/"]:
            self.calc_input.text = self.input_text

    def on_text_change(self, instance, value):
        """La douane centrale : filtre toutes les entrées et met à jour les registres indexés."""
        unit_spin_base = None
        self.saisie_active = False

        # 🎯 CAS 1 : C'est la cellule de saisie (Ligne 4 du Ticket - Chiffres)
        if instance == self.calc_input:
            texte_nettoye = value.strip()
            
            # Si le texte est incomplet, on passe la valeur pure à None
            if texte_nettoye in ["", "-", "."]:
                self.input_data[0] = None
            else:
                try:
                    val_saisie = float(texte_nettoye)
                    # switch_unit renvoie [val_convertie, unit_id, unit_lbl]
                    # On convertit de l'unité active du Spinner vers l'unité de l'Ancre
                    res_switch = switch_unit(val_saisie, self.unit_input_Property["unit_id"], self.base_data[1])
                    self.input_data[0] = res_switch[0]
                except ValueError:
                    self.input_data[0] = None # Sécurité anti-lettre au clavier
                    self.saisie_active = True

        # 🎯 CAS 2 : C'est le menu déroulant des unités (Ligne 4 du Ticket - Spinner)
        # ⚠️ NOTE : Pensez à lier votre spinner dans l'__init__ via : self.calc_spinner.bind(text=self.on_text_change)
        elif instance == self.calc_spinner:
            #from config import get_unit_id, get_unit_config
            uid = get_unit_id(value)
            self.unit_input_Property = get_unit_config(uid)
            
            # Mise à jour des tiroirs d'identification de l'unité de saisie
            self.input_data[1] = self.unit_input_Property["unit_id"]
            self.input_data[2] = self.unit_input_Property["label"]

            texte_actuel = self.calc_input.text.strip()
            if texte_actuel in ["", "-", "."]:
                self.input_data[0] = None
            else:
                try:
                    val_saisie = float(texte_actuel)
                    res_switch = switch_unit(val_saisie, self.unit_input_Property["unit_id"], self.original_data[1])
                    self.input_data[0] = res_switch[0]
                except ValueError:
                    self.input_data[0] = None
                    self.saisie_active = True

                # màj du selécteur d'unité
            if self.is_calculating in ["+","-"]:
                unit_spin_base = True   # on va utiliser les unité du Spinner
            else:
                unit_spin_base = False   # on va utiliser les unité de return_data[1]

        # 🎯 CAS 3 : C'est le texte de l'opérateur (Ligne 3 du Ticket - Signe)
        # ⚠️ NOTE : Pensez à lier votre étiquette dans l'__init__ via : self.operator_value.bind(text=self.on_text_change)
        elif instance == self.operator_value:
            if value == "Remplacer":
                self.is_calculating = None
            else:
                self.is_calculating = value

            # màj du selécteur d'unité
            if self.is_calculating in ["+","-"]:
                unit_spin_base = True   # on va utiliser les unité du Spinner
            else:
                unit_spin_base = False   # on va utiliser les unité de return_data[1]
        
        if unit_spin_base is not None:
            last_unit = self.preview_data[1]
            if unit_spin_base == True:
                self.preview_data[1], self.preview_data[2], = self.input_data[1], self.input_data[2]
            else:
                self.preview_data[1], self.preview_data[2], = self.return_data[1], self.return_data[2]
            
            if self.preview_data[1] != last_unit:
                self.preview_data[0] = switch_unit(self.preview_data[0], last_unit, self.preview_data[1])
                self.unit_preview_Property = get_unit_config(self.preview_data[1])
                if self.preview_data[0] is not None:    # on ne touche pas les ERREURs
                   # self.preview_data[0] = Ici je m'en fous, c'est rafraichir_previsualisation() qui va mettre à jour !
                    pass
        
        if self.input_data[0] is not None or self.is_calculating is not None or self.input_data[1] != self.return_data[1]:
            self.saisie_active = True

        # 🚀 TOUT EST TRIPLEMENT FILTRÉ : On envoie les structures d'arrière-plan au moteur pur
        self.rafraichir_previsualisation()

    def rafraichir_previsualisation(self):
        """Moteur pur : effectue le calcul sur l'index [0] et anime la Ligne 5 du Ticket."""
        
        # 1. Initialisation par défaut de votre système de flags centralisé
        self.calcul_validable = False 
        
        # Variables locales pour capturer les textes exacts en cas d'anomalie
        erreur_msg = "INVALIDE"
        erreur_print = "Erreur de calculation"

        # 🎯 1. LE GARDE-FOU MAÎTRE (Votre excellente idée d'aiguillage par Flag !)
        # Si la calculatrice est au repos total,, on nettoie visuellement la Ligne 5
        if not self.saisie_active:
            self.input_data[0] = None
            self.preview_value.text = ""  # Ligne 5 jaune devient parfaitement blanche/vide
            self.preview_unit.text = ""   # On efface aussi l'étiquette de l'unité
            self.actualiser_verrouillage_touches() # Le gardien va éteindre le bouton =
            return # On quitte immédiatement,, pas de calcul sur du vide !

        # 🎯 2. SÉCURITÉ SÉQUENTIELLE SUR LE NONE : On filtre selon l'opérateur en cours
        if self.input_data[0] is None:
            # Si on est en train de préparer une addition ou une soustraction,, on laisse passer
            # pour que la ligne 5 affiche la valeur de départ (Ancre + 0)
            if self.is_calculating in ["+", "-"]:
                pass
            else:
                # Pour les autres modes (*, /, Remplacer),, si la saisie est à None,, on gèle l'affichage
                self.preview_value.text = ""
                self.preview_unit.text = ""
                self.actualiser_verrouillage_touches()
                return 

        # 🚀 3. LA CUISINE MATHÉMATIQUE (Sécurisée contre les NoneType de Python)
        # On utilise une variable locale pour isoler proprement la valeur numérique de saisie
        val_saisie_safe = self.input_data[0] if self.input_data[0] is not None else 0.0

        if self.is_calculating == "+":
            self.preview_data[0] = self.base_data[0] + val_saisie_safe
        elif self.is_calculating == "-":
            self.preview_data[0] = self.base_data[0] - val_saisie_safe
        elif self.is_calculating == "*":
            self.preview_data[0] = self.base_data[0] * val_saisie_safe
        elif self.is_calculating == "/":
            # Sécurité Division par Zéro (Uniquement si l'opérateur a tapé un vrai 0.0)
            if val_saisie_safe == 0.0:
                self.preview_value.text = "DIV / 0 !"
                self.preview_unit.text = ""
                self.actualiser_verrouillage_touches()
                return
            self.preview_data[0] = self.base_data[0] / val_saisie_safe
        else:
            # Mode "Remplacer" direct par défaut : prend la valeur saisie filtrée
            self.preview_data[0] = val_saisie_safe

        # 🎯 4. EXTRACTION ET TRANSPOSITION VISUELLE SUR LE TICKET (Ligne 5)
        try:
            if self.preview_data[0] is None:
                erreur_msg = "DONNÉE ABSENTE"
                erreur_print = "Erreur : preview_data[0] est None"
                raise ValueError()

            # Appel dans le sens naturel : switch_unit(valeur_brute, depuis_Ancre, vers_Preview)
            val_transposee = switch_unit(self.preview_data[0], self.base_data[1], self.preview_data[1])
            
            # Contrôle strict du type de retour (doit être une liste [val, id, lbl])
            if not isinstance(val_transposee, list):
                erreur_msg = f"CONV. IMPOSSIBLE"
                erreur_print = f"Erreur switch_unit : retour invalide [{val_transposee}]"
                raise TypeError()

            # Tout est OK : Rafraîchissement des deux labels de votre Ligne 5
            nb_dec = self.unit_preview_Property["decimals"]
            self.preview_value.text = f"{val_transposee[0]:0.{nb_dec}f}"
            self.preview_unit.text = str(val_transposee[2]) # Affiche le libellé exact (mm, in, rpm...)
            
            # 🚩 Le calcul s'est terminé sans encombre,, la touche = devient valide !
            self.calcul_validable = True
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            # 🛡️ INTERCEPTION UNIQUE ET DÉBOGAGE
            print(f"[DEBUG_Calculator] ⚠️ {erreur_print} | Détails système : {str(e)}")
            
            # On peint le message d'erreur textuel local sur la Ligne 5 du Ticket
            self.preview_value.text = erreur_msg
            self.preview_unit.text = "" 

        # 🎯 5. SURVEILLANCE AUTOMATIQUE
        # Vos drapeaux d'états étant à jour,, le gardien central ré-aligne l'état et la couleur de vos boutons !
        self.actualiser_verrouillage_touches()

    def actualiser_verrouillage_touches(self):
        """Gère l'activation physique (disabled) et visuelle (couleur) en fonction des flags maîtres."""
        texte_saisie = self.calc_input.text.strip()

        # ─── REGLE 1 : Verrouillage des opérateurs mathématiques (+, -, *, /) ───
        # Si l'opérateur a déjà choisi un signe, on bloque les autres pour éviter la casse syntaxique
        if self.is_calculating is not None:
            for op in ["+", "-", "*", "/"]:
                if op in self.touches_calculatrice:
                    self.touches_calculatrice[op].disabled = True
                    self.touches_calculatrice[op].background_color = self.DESACT_BOUTON
        else:
            for op in ["+", "-", "*", "/"]:
                if op in self.touches_calculatrice:
                    self.touches_calculatrice[op].disabled = False
                    self.touches_calculatrice[op].background_color = self.BRUN_ORANGE

        # ─── REGLE 2 : Masquage intelligent du Spinner d'unité ───
        if self.is_calculating in ["*", "/"]:
            if self.calc_spinner in self.droite_l4.children:        # Si le spinner est encore dans la ligne, on le remplace par le vide
                self.droite_l4.remove_widget(self.calc_spinner)
                self.droite_l4.add_widget(self.spinner_placeholder)
        else:
            if self.spinner_placeholder in self.droite_l4.children:    # Si c'est le placeholder qui est présent, on remet le spinner fonctionnel
                self.droite_l4.remove_widget(self.spinner_placeholder)
                self.droite_l4.add_widget(self.calc_spinner)

        # ─── REGLE 3 : Verrouillage du point décimal ───
        if "." in texte_saisie:
            if "." in self.touches_calculatrice:
                self.touches_calculatrice["."].disabled = True
                self.touches_calculatrice["."].background_color = self.DESACT_BOUTON
        else:
            if "." in self.touches_calculatrice:
                self.touches_calculatrice["."].disabled = False
                self.touches_calculatrice["."].background_color = self.BLEU_BOUTON

        # ─── REGLE 4 : VOS FLAGS MAÎTRES SUR LES BOUTONS D'ACTION (C, CE, =, END) ───
        btn_c = self.touches_calculatrice.get("C")
        btn_ce = self.touches_calculatrice.get("CE")
        btn_egal = self.touches_calculatrice.get("=")
        btn_close = self.touches_calculatrice.get("END")
        # Le Reset global (C) s'allume UNIQUEMENT si l'Ancre a dévié de la valeur originale
        if btn_c:
            ancre_a_change = self.original_data[0] != self.base_data[0]
            btn_c.disabled = not ancre_a_change
            btn_c.background_color = self.ROUGE_ANNULER if ancre_a_change else self.DESACT_BOUTON            
        # Le Reset partiel (CE) s'allume uniquement si une saisie brute est en cours d'écriture
        if btn_ce:
            btn_ce.disabled = not self.saisie_active
            btn_ce.background_color = self.BRUN_ORANGE if self.saisie_active else self.DESACT_BOUTON           
        # Le bouton de fermeture (END) se verrouille si une saisie est en cours pour forcer une décision
        if btn_close:
            btn_close.disabled = self.saisie_active
            btn_close.background_color = self.DESACT_BOUTON if self.saisie_active else self.VERT_VALIDER
        # La touche de calcul [=] obéit au flag de calculabilité du moteur mathématique
        if btn_egal:
            btn_egal.disabled = not self.calcul_validable
            btn_egal.background_color = self.BRUN_ORANGE if self.calcul_validable else self.DESACT_BOUTON

    def on_click_enregistrer_intermediaire(self, instance=None):
        """
        Déclenchée par la touche (=). Fait monter le calcul validé de la ligne 5 (Aperçu)
        vers la ligne 2 (Nouvelle valeur de base) et réinitialise le bloc de saisie.
        """
        # Sécurité : Si le drapeau maître dit que ce n'est pas validable, on rejette l'action
        if not self.calcul_validable or self.preview_data[0] is None:
            return

        # ─── 1. TRANSFERT MAÎTRE DES REGISTRES D'ARRIÈRE-PLAN ───
        # Le résultat calculé devient la nouvelle Ancre de calcul (exprimée dans l'unité d'origine)
        self.base_data[0] = self.preview_data[0]
        
        # Le panier de sortie (return_data) prend la même valeur numérique, mais dans l'unité à retourner
        self.return_data = switch_unit(self.preview_data[0], self.base_data[1], self.preview_data[1])
        self.unit_return_Property = get_unit_config(self.return_data[1])

        # ─── 2. MISE À JOUR STRATÉGIQUE DES TEXTES DU TICKET (Lignes 2 & 3) ───
        # Ligne 2 : On formate la nouvelle valeur de base avec ses décimales et son unité
        nb_dec_ret = self.unit_return_Property["decimals"]
        self.new_value_value.text = f"{self.return_data[0]:0.{nb_dec_ret}f}"
        self.new_value_unit.text = str(self.return_data[2])

        # Ligne 3 : L'opération est consommée, on nettoie le signe
        self.is_calculating = None
        self.operator_value.text = "Remplacer"

        # ─── 3. NETTOYAGE EN CASCADE ET RÉALIGNEMENT DES FLAGS MAÎTRES ───
        # Cette fonction s'occupe de repasser l'opérateur à "Remplacer", de vider les inputs
        self.nettoyer_bloc_saisie()

    def nettoyer_bloc_saisie(self):
        """
        Fonction mutualisée pour CE et la fin de calcul (=).
        Utilise la cascade naturelle des événements Kivy dans un ordre 
        strictement sécurisé pour l'atelier.
        """
        # 1. 🛡️ SÉCURITÉ MAXIMUM : On coupe immédiatement l'opérateur mathématique.
        self.operator_value.text = "Remplacer"    # En repassant en mode "Remplacer", on désactive instantanément les risques liés à la division.

        # 2. 🧹 NETTOYAGE NUMÉRIQUE : On vide l'écran ET la mémoire tampon du pavé numérique.
        self.input_text = self.calc_input.text = ""

        # 3. 🎯 HARMONISATION : On remet l'unité du Spinner au propre en dernier.
        self.calc_spinner.text = str(self.return_data[2])

    def on_closed(self, instance):
        """
        Gère la fermeture finale (Bouton END/OK).
        Transmet un dictionnaire complet (Texte, Float, Unité) au callback de la CAO.
        """
        # 🛡️ Blindage de sécurité : On s'assure que return_data est exploitable
        if not self.return_data or self.return_data[0] is None:
            self.dismiss()
            return

        try:
            # 1. Préparation du texte formaté avec les décimales dynamiques
            dec = self.unit_return_Property.get('decimals', 2)
            val_formatee = f"{self.return_data[0]:0.{dec}f}"
            chaine_cao_retour = f"{val_formatee}{self.return_data[2]}" # Ex: "50.80mm"
            
            # 🎯 LE PACK COMPLET : On prépare les 4 informations pour la CAO
            pack_data = {
                "text": chaine_cao_retour,           # La chaîne formatée (ex: "50.80mm")
                "value": float(self.return_data[0]), # Le float pur (ex: 50.8)
                "unit_id": self.return_data[1],      # L'ID technique (ex: "dist")
                "unit_label": self.return_data[2]    # Le label d'affichage (ex: "mm")
            }
            
            # 2. Envoi du dictionnaire complet au moteur de la CAO
            if self.update_value_callback:
                self.update_value_callback(pack_data)
                
        except Exception as e:
            print(f"[DEBUG_Calculator] ⚠️ Erreur lors du packaging CAO : {str(e)}")
            
        # 3. Fermeture et déverrouillage de l'interface
        self.dismiss()

    def _on_keyboard_down(self, window, key, scancode, codepoint, modifiers):
        """Intercepte les touches du vrai clavier PC et simule un appui tactile."""
        # déjà en entête de fichier: from kivy.uix.button import Button

        # Dictionnaire complet : Opérateurs ET Chiffres du pavé numérique
        TRADUCTION_WINDOWS = {
            # Opérateurs (Pavé numérique et clavier principal)
            43: '+', 42: '*', 47: '/', 46: '.', 45: '+/-', 269: '+/-',    # 45: '-'
            # Chiffres du pavé numérique (NumLock activé)
            256: '0', 257: '1', 258: '2', 259: '3', 260: '4',
            261: '5', 262: '6', 263: '7', 264: '8', 265: '9',
            266: '.' # Point/Virgule du pavé numérique
        }
        caractere = None

        # 1. On vérifie d'abord si la touche pressée est une touche physique connue (Pavé numérique / Opérateur)
        if key in TRADUCTION_WINDOWS:
            caractere = TRADUCTION_WINDOWS[key]            
        # 2. Si ce n'est pas le cas, on se rabat sur le codepoint (Chiffres du clavier principal)
        elif codepoint in ['0','1','2','3','4','5','6','7','8','9','.']:
            caractere = codepoint
        # 13 = Touche Entrée (clavier principal), 271 = Touche Entrée (Pavé numérique)
        elif key in [13, 271]: 
            self.on_click_enregistrer_intermediaire()
            return True
        # 27 = Touche Échap / Escape (ferme la popup sans valider)
        elif key == 27: 
            self.on_closed(None)
            return True
        # 8 = Backspace / Retour arrière, 127 = Delete / Suppr (Simule la touche CE)
        elif key in [8, 127]:
            caractere="CE"
        
        # 3. Si on a intercepté un caractère valide, on l'envoie à votre méthode tactile
        if caractere:
            self.on_button_press(Button(text=caractere))
            return True
            
        return False

class SegmentPopupContent(BoxLayout):
    """
    PopUp pour confugurer des valeurs d'axes selon une calculation par déduction (angle, distance, ...)
        utilisée par "l" et "alpha" dans CAO
    """
    def __init__(self, data, key_changed, on_confirm, key_target, **kwargs):
        super().__init__(orientation='vertical', spacing=10, padding=10, **kwargs)

        self.data = data
        self.result_data = copy.deepcopy(data)
        self.key_changed = key_changed or {}
        self.last_ref_changed = None
        self.started_hor2 = self.data.hor2.value
        self.started_vert2 = self.data.vert2.value
        self.key_target = key_target  # 'l' ou 'alpha'
        self.ref_key = None
        self.on_confirm = on_confirm
        self.parent_popup = None


        self.inputs = {}  # : InputCell
        self.ref_buttons = {}  # : ToggleButton

        self._build_ui()
        self._select_initial_reference()
        self._update_reference_selection(force=True)

    def _build_ui(self):
        self.clear_widgets()

        if self.key_target not in ('l', 'alpha'):
            self._popup_erreur(TR("error") + ' _build_ui', f"{Tr('invalid_key')} : {self.key_target}")
            return

        self.inputs = {}
        self.ref_buttons = {}

        # === Layout principal
        root = BoxLayout(orientation='vertical', spacing=15, padding=10)  #, size_hint_y=None)

        # === Groupe Références
        root.add_widget(GroupHeader(Tr("choose_reference"), thickness=1))
        rows_ref = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        rows_ref.bind(minimum_height=rows_ref.setter('height'))

        ref_keys = ['vert2', 'hor2'] + (['alpha'] if self.key_target == 'l' else ['l'])
        toggle_group = 'ref_group'

        for i, key in enumerate(ref_keys):            
            label = AXIS_CONFIG.get(key, {}).get("screen", key) 

            row = BoxLayout(orientation='horizontal', spacing=50, size_hint_y=None, height=50)

            title_lbl = MyLabel(
                text=" " if i > 0 else Tr("choose_reference"),
                halign="center", size_hint_x=1, height=40
            )
            btn = ToggleButton(text=label, group=toggle_group, size_hint_x=1)
            btn.bind(on_press=lambda inst, k=key: self._select_axis(k))

            inp = InputCell(
                text=self.data.__getattribute__(key).val_formatted(with_unit=True),
                size_hint_x=1,
                disabled=False
            )
            inp.bind(text=self._on_input_change)
            inp.bind(focus=self._on_input_focus)

            self.ref_buttons[key] = btn
            self.inputs[key] = inp

            # Conteneur pour bouton + champ input
            input_box = BoxLayout(orientation='horizontal', spacing=20, size_hint_x=1)
            input_box.add_widget(btn)
            input_box.add_widget(inp)

            #row.add_widget(title_lbl)
            row.add_widget(input_box)

            rows_ref.add_widget(row)

        root.add_widget(rows_ref)
        #root.add_widget(Separator())

        # === Groupe Cible
        root.add_widget(GroupHeader(Tr("target_value"), thickness=1))
        row_target = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=50)

        #title_target = MyLabel(text=Tr("target_value"), halign="center", size_hint_x=1, height=40)
        label = AXIS_CONFIG.get(self.key_target, {}).get("screen", self.key_target)
        title_target = MyLabel(text=label, halign="right", size_hint_x=1, height=40, padding=(0, 0, dp(20), 0))


        inp_targ = InputCell(
            text=self.data.__getattribute__(self.key_target).val_formatted(with_unit=True),
            width=260, disabled=False
        )
        inp_targ.bind(text=self._on_input_change)
        inp_targ.bind(focus=self._on_input_focus)

        btn_targ = ToggleButton(text="+/-", size_hint_x=0.2)
        btn_targ.bind(on_press=self._reverse_target_value)

        input_box_targ = BoxLayout(orientation='horizontal', spacing=20, size_hint_x=1)
        input_box_targ.add_widget(inp_targ)
        input_box_targ.add_widget(btn_targ)

        self.inputs[self.key_target] = inp_targ

        row_target.add_widget(title_target)
        row_target.add_widget(input_box_targ)

        root.add_widget(row_target)
        #root.add_widget(Separator())

        # === Groupe Résultats
        root.add_widget(GroupHeader(Tr("results"), thickness=1))
        rows_result = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None) 
        rows_result.bind(minimum_height=rows_result.setter('height'))

        #title_result = MyLabel(text=Tr("results"), halign="center", size_hint_x=1, height=40)
        title_result1 = MyLabel(text=AXIS_CONFIG.get("vert2", {}).get("screen", "vertical"), halign="right", size_hint_x=1, height=40, padding=(0, 0, dp(20), 0))  # (padding_left, top, right, bottom))
        title_result2 = MyLabel(text=AXIS_CONFIG.get("hor2", {}).get("screen", "horizontal"), halign="right", size_hint_x=1, height=40, padding=(0, 0, dp(20), 0))
        #vide_result = MyLabel(text=" ", size_hint_x=1, height=40)

        #self.label_vert = Label(text=self._format_result('vert2'), markup=True, height=40, size_hint_x=1)
        txt_lbl_vert = f"[i]{self.result_data.__getattribute__('vert2').val_formatted(with_unit=True)}[/i]"
        self.label_vert = Label(text=txt_lbl_vert, markup=True, height=40, size_hint_x=1)
        #self.label_hor = Label(text=self._format_result('hor2'), markup=True, height=40, size_hint_x=1)
        txt_lbl_hor = f"[i]{self.result_data.__getattribute__('hor2').val_formatted(with_unit=True)}[/i]"
        self.label_hor = Label(text=txt_lbl_hor, markup=True, height=40, size_hint_x=1)

        

        row_result1 = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=50)
        #row_result1.add_widget(title_result)
        row_result1.add_widget(title_result1)
        row_result1.add_widget(self.label_vert)

        row_result2 = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=50)
        #row_result2.add_widget(vide_result)
        row_result2.add_widget(title_result2)
        row_result2.add_widget(self.label_hor)

        rows_result.add_widget(row_result1)
        rows_result.add_widget(row_result2)

        root.add_widget(rows_result)

        # === Boutons Valider / Annuler
        root.add_widget(Separator(thickness=1))
        btn_ok = Button(text=Tr("validate"), size_hint_x=0.5, height=50)
        btn_cancel = Button(text=Tr("cancel"), size_hint_x=0.5, height=50)

        btn_ok.bind(on_press=self._confirm)
        btn_cancel.bind(on_press=self._dismiss)

        grp_btns = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=60)
        grp_btns.add_widget(btn_cancel)
        grp_btns.add_widget(btn_ok)

        root.add_widget(grp_btns)

        # === Ajout final
        self.add_widget(root)

    def _format_result(self, key):
        return f"[i]{key.upper()} : {self.result_data.__getattribute__(key).val_formatted(with_unit=True)}[/i]"

    def _select_initial_reference(self):
        for key in ('vert2', 'hor2', 'alpha', 'l'):
            if self.key_changed.get(key) and key in self.ref_buttons:
                self.ref_buttons[key].state = 'down'
                self._select_axis(key)
                return
        # Par défaut : premier bouton disponible
        for key, btn in self.ref_buttons.items():
            if btn:
                btn.state = 'down'
                self._select_axis(key)
                return

    def _update_reference_selection(self, *args, force=False):
        for key, btn in self.ref_buttons.items():
            active = btn.state == 'down'
            self.inputs[key].disabled = not active
            if active:
                self.ref_key = key

        if self.ref_key:
            self._update_valeurs(key=self.ref_key, instance=self.inputs[self.ref_key], force=force)
    def _select_axis(self, key):
        self.ref_key = key

        # Forcer visuellement le bouton à rester "enfoncé"
        for k, btn in self.ref_buttons.items():
            btn.state = 'down' if k == key else 'normal'

        # Activer ou désactiver les champs en fonction du bouton actif
        for k, input_field in self.inputs.items():
            input_field.disabled = (k != key and k != self.key_target)

        self._update_valeurs(
            key=key,
            instance=self.inputs[key],
            force=True
        )


    def _on_input_change(self, instance, _):
        for key, inp in self.inputs.items():
            if inp == instance:
                self._update_valeurs(key=key, instance=inp)
                break

    def _on_input_focus(self, instance, focused):
        if not focused:
            for key, inp in self.inputs.items():
                if inp == instance:
                    instance.text = self.data.__getattribute__(key).val_formatted(with_unit=True)
                    break

    def _update_valeurs(self, key=None, instance=None, force=False):
        if not self.ref_key or self.key_target not in ('l', 'alpha'):
            return

        change = False

        # Mise à jour de la valeur cible (key_target)
        val_obj = self.data.__getattribute__(self.key_target)
        if key == self.key_target:
            change = val_obj.set_from_input(self.inputs[self.key_target].text)
            #print(f"DEBUG__update_valeurs: key_target_input: {self.inputs[self.key_target].text}, objet_target_valeur: {val_obj.value}{val_obj.get_unit_type()}")
        #val_target = val_obj.convert_to("mm" if val_obj.get_unit_type() == "unit_distance" else "rad")  # conversion en mm ou rad pour calcul
        targ_base_unit = "mm" if val_obj.get_unit_type() == "unit_distance" else "rad"
        val_target = val_obj.convert_to(targ_base_unit)  # conversion en mm ou rad pour calcul
        #print(f"DEBUG__update_valeurs: val_target: {val_target}{targ_base_unit}")

        # Référence
        ref_obj = self.data.__getattribute__(self.ref_key)
        if key == self.ref_key:
            change = ref_obj.set_from_input(self.inputs[self.ref_key].text)
            #print(f"DEBUG__update_valeurs: key_ref_input: {self.inputs[self.ref_key].text}, objet_ref_valeur: {ref_obj.value}{ref_obj.get_unit_type()}")
            self.last_ref_changed = self.ref_key

        #ref_val = ref_obj.convert_to("mm" if val_obj.get_unit_type() == "unit_distance" else "rad")
        ref_base_unit = "mm" if ref_obj.get_unit_type() == "unit_distance" else "rad"
        ref_val = ref_obj.convert_to(ref_base_unit)
        #print(f"DEBUG__update_valeurs: val_ref: {ref_val}{ref_base_unit}")
        #print(f"DEBUG_PopUp_Update: TargetVal: {val_target} {targ_base_unit} || RéfVal: {ref_val} {ref_base_unit}")

        if change in ('invalid_format', 'invalid_unit'):
            if instance:
                instance.set_status(STATUS_ERREUR)
            return
        if instance:
            instance.set_status(None)
        if not change and not force:
            return

        # Calcul Horizontal2 / vertical2
        new_hor = new_vert = '-.-'
        if self.key_target == 'l':
            l = val_target
            if self.ref_key == 'vert2':
                vert2 = ref_val
                if abs(vert2) <= abs(l):
                    hor2 = math.sqrt(l ** 2 - vert2 ** 2)
                    if l < 0:
                        hor2 = -hor2
                    new_hor, new_vert = hor2, vert2
                else:
                    instance.set_status(STATUS_ERREUR)
                    return
            elif self.ref_key == 'hor2':
                hor2 = ref_val
                if abs(hor2) <= abs(l):
                    vert2 = math.sqrt(l ** 2 - hor2 ** 2)
                    if l < 0:
                        vert2 = -vert2
                    new_hor, new_vert = hor2, vert2
                else:
                    instance.set_status(STATUS_ERREUR)
                    return
            elif self.ref_key == 'alpha':
                angle = ref_val
                new_vert = math.sin(angle) * l
                new_hor = math.cos(angle) * l

        elif self.key_target == 'alpha':
            angle = val_target
            if self.ref_key == 'vert2':
                vert2 = ref_val
                new_hor = vert2 / math.tan(angle) if abs(math.tan(angle)) > 1e-6 else 0
                new_vert = vert2
            elif self.ref_key == 'hor2':
                hor2 = ref_val
                new_vert = math.tan(angle) * hor2
                new_hor = hor2
            elif self.ref_key == 'l':
                l = ref_val
                new_vert = math.sin(angle) * l
                new_hor = math.cos(angle) * l

        # Mise à jour des résultats
        if isinstance(new_vert, float):
            self.result_data.vert2.set_converted_from(new_vert, "mm")
        if isinstance(new_hor, float):
            self.result_data.hor2.set_converted_from(new_hor, "mm")

        #self.label_vert.text = self._format_result('vert2')
        self.label_vert.text = self.result_data.__getattribute__('vert2').val_formatted(with_unit=True)
        #self.label_hor.text = self._format_result('hor2')
        self.label_hor.text = self.result_data.__getattribute__('hor2').val_formatted(with_unit=True)

    def _reverse_target_value(self, *args):
        key = self.key_target
        val_obj = self.data.__getattribute__(key)

        val_obj.value *= -1  # Inversion directe, sans conversion

        self.inputs[key].text = val_obj.val_formatted(with_unit=True)

        # Recalcul des résultats
        self._update_valeurs(key=key, instance=self.inputs[key], force=True)

    def _confirm(self, *args):
        if not self.on_confirm:
            self._dismiss()
            return

        def _neutral_key_changed():
            for for_key in self.key_changed:
                if self.key_changed[for_key] == True:
                    self.key_changed[for_key] = None

        if self.ref_key == 'vert2':
            if abs(self.data.vert2.value - self.started_vert2) >1e-8:
                _neutral_key_changed()
                self.key_changed['vert2'] = True
        elif self.ref_key == 'hor2':
            if abs(self.data.hor2.value - self.started_hor2) >1e-8:
                _neutral_key_changed()
                self.key_changed['hor2'] = True
        elif self.ref_key == 'l':
            if abs(self.data.l.value - self.result_data.l.value) >1e-8:
                _neutral_key_changed()
                self.key_changed['l'] = True
        elif self.ref_key == 'alpha':
            if abs(self.data.alpha.value - self.result_data.alpha.value) >1e-6:
                _neutral_key_changed()
                self.key_changed['alpha'] = True
                
        if self.key_target == 'l':
            if abs(self.data.l.value - self.result_data.l.value) >1e-8:
                self.key_changed['l'] = True
        elif self.key_target == 'alpha':
            if abs(self.data.alpha.value - self.result_data.alpha.value) >1e-6:
                self.key_changed['alpha'] = True

        # Toujours transmettre key_target comme signal
        self.on_confirm(
            self.result_data.hor2.value,
            self.result_data.vert2.value,
            key=self.key_target
        )
        self._dismiss()

    def _dismiss(self, *args):
        if self.parent_popup:
            self.parent_popup.dismiss()

    def _popup_erreur(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(None, None), size=(400, 200))
        popup.open()

__all__ = ["SegmentPopupContent"]


class PartManagerPopup(Popup):
    '''
    PopUp pour la configuration de la pièce
    - Choix de la pièce active
    - Renommer la pièce active
    - sauvgarder
    - Recharger depuis la sauvgarde
    - Copier depuis une autre pièce (possible seulement dans une pièce vide)
    - Supprimer (vider) la pièce active
    '''
    def __init__(self, manager, refresh_callback, **kwargs):
        super().__init__(title=Tr("part_management"), size_hint=(None, None), size=(700, 1000), **kwargs)
        self.manager = manager
        self.refresh_callback = refresh_callback  # pour redessiner TopBar/table si nécessaire
        self.build_content()

    def build_content(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Groupe : Sélection
        #layout.add_widget(Label(text="[b]Sélection[/b]", markup=True))
        layout.add_widget(GroupHeader(Tr("selection")))
        self.spinner = Spinner(
            #text=self.manager.get_part_all_names()[self.manager.storage.part_id_actif],
            text = self.manager.get_part_name(),
            values=self.manager.get_part_all_names()
        )
        self.spinner.bind(text=self.on_change_part)
        layout.add_widget(self.spinner)
        #layout.add_widget(Separator())

        # Groupe : Renommage
        #layout.add_widget(Label(text="[b]Paramètres[/b]", markup=True))
        layout.add_widget(GroupHeader(Tr("settings")))
        self.name_input = TextInput(text=self.spinner.text, multiline=False)
        self.name_input.bind(text=self.on_name_input_changed)
        layout.add_widget(self.name_input)
        layout.add_widget(Button(text=Tr("save_rename"), on_release=self.rename_part))
        #layout.add_widget(Separator())

        # Groupe : Fichier
        #layout.add_widget(Label(text="[b]Fichier[/b]", markup=True))
        layout.add_widget(GroupHeader(Tr("file")))
        #layout.add_widget(Button(text=Tr("save"), on_release=lambda *a: self.manager.save()))
        layout.add_widget(Button(text=Tr("save"), on_release=self.save_part))
        layout.add_widget(Button(text=Tr("reload"), on_release=self.reload_part))
        self.copy_from_btn = Button(text=Tr("copy_from_another_part"))
        if self.manager.entries and len(self.manager.entries) > 1:
            self.copy_from_btn.disabled = True
        self.copy_from_btn.bind(on_release=self.open_copy_spinner)
        layout.add_widget(self.copy_from_btn)
        #layout.add_widget(Separator())

        # Danger Zone
        #layout.add_widget(Label(text="[b][color=ff0000]Danger Zone[/color][/b]", markup=True))
        layout.add_widget(GroupHeader(Tr("danger_zone"), color=(0.8, 0.2, 0.2, 1), thickness=2))
        layout.add_widget(Button(text=Tr("delete_part"), background_color=(1, 0, 0, 1), on_release=self.delete_part))

        self.content = layout

    def on_change_part(self, spinner, text):
        index = self.manager.get_part_all_names().index(text)

        def do_change_part(*_):
            self.manager.storage.set_selected_index(index)
            self.refresh_callback(reload_json=True)
            self.update_buttons_state()
            self.dismiss()

        if self.manager.has_unsaved_changes():
            self.show_save_changes_popup(confirm_callback=do_change_part)
        else:
            do_change_part()
            
    def show_save_changes_popup(self, confirm_callback):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f"{Tr("unsaved_changes")}.\n{Tr("save_before_changing_part")}"))
        
        button_box = BoxLayout(size_hint_y=None, height=44, spacing=10)
        
        def on_save_and_continue(*_):
            self.manager.save()
            confirm_callback()
            popup.dismiss()

        def on_continue_without_saving(*_):
            confirm_callback()
            popup.dismiss()

        def on_cancel(*_):
            self.spinner.unbind(text=self.on_change_part)
            self.spinner.text = self.manager.get_part_name()    # Revenir à la sélection précédente
            self.spinner.bind(text=self.on_change_part)
            popup.dismiss()

        button_box.add_widget(Button(text=Tr("save"), on_release=on_save_and_continue))
        button_box.add_widget(Button(text=Tr("dont_save"), on_release=on_continue_without_saving))
        button_box.add_widget(Button(text=Tr("cancel"), on_release=on_cancel))

        content.add_widget(button_box)

        popup = Popup(title=TR("unsaved_changes"), content=content, size_hint=(None, None), size=(1000, 300))
        popup.open()

    def rename_part_OLD(self, *args):
        index = self.manager.get_part_all_names().index(self.spinner.text)
        new_name = self.name_input.text.strip()
        if new_name:
            self.manager.set_part_names(new_name, index)
            self.manager.commit_part_names()
            self.refresh_callback(reload_json = False)
            self.dismiss()
    def on_name_input_changed(self, instance, value):
        self.manager.set_part_names(value.strip())
    def rename_part(self, *args):
        new_name = self.name_input.text.strip()
        if new_name:
            #self.manager.set_part_names(new_name)
            self.manager.commit_part_names()
            self.refresh_callback(reload_json = False)
            self.dismiss()            

    def reload_part(self, *args):
        self.manager.load()
        self.refresh_callback(reload_json = True)
        self.update_buttons_state()
        self.dismiss()

    def save_part(self,*args):
        self.manager.save()
        self.reload_part(*args)

    def open_copy_spinner(self, *args):
        dropdown = DropDown()

        current_name = self.manager.get_part_name()
        part_names = self.manager.get_part_all_names()

        def copy_from(source_name):
            dropdown.dismiss()
            source_index = self.manager.get_part_all_names().index(source_name)
            self.manager.copy_part_from_index(source_index)
            self.refresh_callback(reload_json = False)
            self.dismiss()

        entries = [(Tr("cancel_copy2"), lambda btn: dropdown.dismiss())]

        for name in part_names:
            if name != current_name:
                entries.append((name, lambda btn, name=name: copy_from(name)))

        for label, action in entries:
            btn = Button(text=label, size_hint_y=None, height=44)
            btn.bind(on_release=action)
            dropdown.add_widget(btn)

        dropdown.open(self.copy_from_btn)

    def delete_part(self, *args):
        self.manager.reset_part_in_memory()                # <-- réinitialise la pièce
        self.refresh_callback(reload_json = False)         # <-- met à jour l'affichage
        self.update_buttons_state()
        self.dismiss()

    def update_buttons_state(self):
        """Met à jour dynamiquement l'état des boutons en fonction du contenu de la pièce actuelle."""
        is_empty = not self.manager.entries or len(self.manager.entries) <= 1
        self.copy_from_btn.disabled = not is_empty


# Dans screen_base/common_screen.py (ou votre module d'infrastructure UI)

class ErrorInputPopup(Popup):
    """
    🚨 POP-UP D'ALERTE DE SAISIE INCORRECTE (Version 7.2) :
    Boîte de dialogue modale réutilisable sur toutes les pages du DRO.
    Embarque un disjoncteur temporel (Timer) pour s'effacer automatiquement.
    """
    def __init__(self, txt_error: str, case_dest: str = None, timer_off: float = 3.5, **kwargs):
        """
        Args:
            txt_error (str): La chaîne brute saisie par l'opérateur (ex: '0.000a' ou '').
            case_dest (str, optional): Désignation explicite de la cellule cible (ex: 'Nom de l'outil'). 
                                       Si None, le message s'adapte de façon générique.
            timer_off (float): Temps limite en secondes avant fermeture automatique.
        """
        kwargs.setdefault('title', "⚠️ ALERTE : SAISIE REFUSÉE")
        kwargs.setdefault('size_hint', (None, None))
        kwargs.setdefault('size', ("420dp", "210dp"))
        kwargs.setdefault('auto_dismiss', True)
        super().__init__(**kwargs)

        self.timer_event = None
        layout_principal = BoxLayout(orientation='vertical', padding="12dp", spacing="10dp")

        # 🟢 VERIFICATION DU CHAMP VIDE (Votre Traitement Spécial !)
        is_empty = not str(txt_error).strip()

        # 🏗️ CONSTRUCTION DYNAMIQUE DU TEXTE UNIVERSEL (Avec le mot 'valeur')
        if is_empty:
            if case_dest:
                message_texte = (
                    f"Le champ [color=66ccff][b]{case_dest}[/b][/color] ne peut pas rester vide.\n"
                    f"La modification est annulée, l'ancienne valeur est conservée."
                )
            else:
                message_texte = (
                    f"La saisie est restée vide.\n"
                    f"La mémoire de la machine conserve sa configuration d'origine."
                )
        else:
            # Cas d'un texte parasite (ex: '0.000a')
            if case_dest:
                message_texte = (
                    f"La valeur [color=ff6666][b]{txt_error}[/b][/color] est incorrecte.\n"
                    f"Le champ [color=66ccff][b]{case_dest}[/b][/color] conserve sa valeur d'origine."
                )
            else:
                message_texte = (
                    f"La valeur saisie [color=ff6666][b]{txt_error}[/b][/color] n'est pas valide.\n"
                    f"La mémoire vive (RAM) de la machine reste protégée."
                )

        # Ajout du grand Label texturé avec Markup
        lbl_message = Label(
            text=message_texte,
            markup=True,
            halign='center',
            valign='middle',
            font_size="13sp"
        )
        lbl_message.bind(size=lambda inst, sz: setattr(inst, 'text_size', sz))
        layout_principal.add_widget(lbl_message)

        # Petit bandeau d'infos pour le Timer
        if timer_off and timer_off > 0:
            self.lbl_timer = Label(
                text=f"Fermeture automatique dans {timer_off:.1f}s...",
                font_size="10sp",
                color=[0.5, 0.5, 0.5, 1],
                size_hint_y=None,
                height="15dp"
            )
            layout_principal.add_widget(self.lbl_timer)
            self.timer_restant = timer_off
            self.timer_event = Clock.schedule_interval(self._tick_timer, 0.1)

        # Bouton manuel d'acquittement d'erreur pour l'opérateur
        btn_ok = Button(
            text="Acquitter l'erreur",
            size_hint_y=None,
            height="40dp",
            background_normal="",
            background_color=[0.7, 0.2, 0.2, 1],
            bold=True,
            font_size="13sp"
        )
        btn_ok.bind(on_release=self.dismiss)
        layout_principal.add_widget(btn_ok)

        self.content = layout_principal

    def _tick_timer(self, dt):
        self.timer_restant -= dt
        if self.timer_restant <= 0:
            self.dismiss()
        else:
            if hasattr(self, 'lbl_timer'):
                self.lbl_timer.text = f"Fermeture automatique dans {self.timer_restant:.1f}s..."

    def on_dismiss(self):
        if self.timer_event:
            Clock.unschedule(self.timer_event)
            self.timer_event = None
        super().on_dismiss()



