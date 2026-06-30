# point_draw_popups.py
    # Anciennement: popup_segment.py

import math
import copy
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput

from common_widgets import MyLabel, Separator, GroupHeader, LabeledCell, InputCell, InputCellLabel, CustomSpinner, STATUS_NEUTRE, STATUS_INACTIF, STATUS_ERREUR, STATUS_VALIDE
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from config import parse_user_input, get_unit_config, get_all_units_for_type, AXIS_CONFIG


class CalculatorPopup(Popup):
    '''
    PopUp servant à écrire de nouvelle dimensions
    dans un Input en tenant compe des unitées,
    mais aussi avec posibilité de débuire la valeur d'opération simple comme :
        (l'addition, soustraction, multiplication, divison)
    Vérifie aussi que les valeurs à écrires son dans un format accéptable par le logiciel
    '''
    def __init__(self, current_value, current_unit, update_value_callback, **kwargs):
        super().__init__(**kwargs)
        self.title = "Modifier la valeur"
        self.size_hint = (None, None)
        self.size = (400, 500)
        self.update_value_callback = update_value_callback

        # je vais garder tois étages de valeurs:
        # -1: original_value : Valeur de démarrage pour réinitialisation complète
        self.original_value = parse_user_input(current_value, current_unit)
        if isinstance(self.original_value,(str)):
            # TODO: peut-être juste un popUp de ratrapage pour les non valide ???
            return f"{current_value} {current_unit}"
        # -2: result_last: dernier résultat valide, dans l'unité de la dernière oppération
        self.result_last = self.original_value
        # -3: result : comme result_last, mais dans l'unité en cours d'utilisation
        self.result =  self.original_value
        self.result_str = f"{self.result[0]} {self.result[2]}" # Le résultat pour l'affichage

        # Variables de travail
        self.unit_list= self.get_all_units_for_type(current_unit, True) # Liste des unitées selctionables [unit_id, unit_label]
        # TODO: A Renommer
        self.is_calculating = False  # Stock l'opération en cours ("+ - * /") ou False pour entré direct

        # === POUR L'AFFICHAGE ===

        # Label pour afficher la valeur original (original_value)
        self.old_value_label = Label(text=f"Ancienne valeur: {self.original_value[0]} {self.original_value[2]}")

        # Label pour afficher la valeur actuel, avant calcul (result_last)
        self.actif_value_label = Label(text=f"Valeur actuel: {self.result_last[0]} {self.result_last[2]}")
        
        # TextInput pour afficher la valeur et l'unité En cours de traitement
        self.clac_input = InputCell(text="", status=STATUS_NEUTRE)
        #self.calc_input.bind(on_text_validate=self.on_validate)
        self.calc_input.bind(text=self.on_text_change)

        # Label pour afficher le résultat temporaire après traitement
        self.new_value_label = Label(text=f"Nouvelle valeur: {self.result[0]} {self.result[2]}")
        
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.old_value_label)
        layout.add_widget(self.actif_value_label)
        layout.add_widget(Label(text="Entrez la nouvelle valeur:"))
        layout.add_widget(self.calc_input)
        
        # Grille de la calculatrice
        grid = GridLayout(cols=4, spacing=(5, 6))
        
        buttons = ["", "", "CE", "C",
                   '7', '8', '9', '/',
                   '4', '5', '6', '*',
                   '1', '2', '3', '-',
                   '0', '.', '+/-', '+']
        
        BRUN_ORANGE = (0.788, 0.502, 0.024, 1)
        BLEU_BOUTON = (0.459, 0.722, 0.969, 1)
        GRIS_BOUTON = (0.812, 0.784, 0.737, 1)
        bt_color=[
            None,None,BLEU_BOUTON,BLEU_BOUTON,
            GRIS_BOUTON,GRIS_BOUTON,GRIS_BOUTON, BRUN_ORANGE,
            GRIS_BOUTON,GRIS_BOUTON,GRIS_BOUTON, BRUN_ORANGE,
            GRIS_BOUTON,GRIS_BOUTON,GRIS_BOUTON, BRUN_ORANGE,
            GRIS_BOUTON,GRIS_BOUTON,BLEU_BOUTON, BRUN_ORANGE]
        
        for i, button in enumerate(buttons):
            if button == "":
                grid.add_widget(Label(text=" "))
            else:
                btn = Button(
                    text=button,
                    on_press=self.on_button_press,
                    background_normal="",
                    background_color=bt_color[i] if bt_color[i] else (1, 1, 1, 1)
                )
                grid.add_widget(btn)

        layout.add_widget(grid)
        layout.add_widget(self.new_value_label)

        # Boutons de validation et réinitialisation
        button_layout = BoxLayout(size_hint=(1, 0.2))
        
        # Bouton d'unité
        self.unit_button = Button(text=f"Unité: {self.last_unit}", on_press=self.change_unit, size_hint_y=0.5, background_normal="", background_color=BRUN_ORANGE)
        # Bouton de réinitialisation (CE)
        #clear_button = Button(text="CE", on_press=self.clear_input)
        # Bouton de validation (ou Enter)
        self.confirm_button = Button(text="Enter", on_press=self.on_validate, size_hint_y=0.5, background_normal="", background_color=BRUN_ORANGE)
        
        #button_layout.add_widget(clear_button)
        button_layout.add_widget(self.unit_button)
        button_layout.add_widget(self.confirm_button)
        
        layout.add_widget(button_layout)
        self.add_widget(layout)

    #TODO: Adapter à on_button_press
    def on_text_change(self, instance, value):
        print(f"Dernier texte : {value}")
        if value:
            last_char = value[-1]
            print(f"Dernier caractère saisi : {last_char}")
            # Tu peux déclencher des actions selon la touche (ex: calcul, validation, etc.)    
    def on_button_press(self, instance):
        current_text = self.calc_input.text.strip()
        button_text = instance.text
        
        if button_text == "+/-":
            # Inverser le signe de la valeur
            self.calc_input *= -1
        elif button_text == "C":
            self.clear_input()
        elif button_text == "CE":
            self.init_calcul()
        elif button_text == "=":
            # Quand "=" est appuyé, on valide le calcul
            self.on_calcul(None)
        elif button_text == "ENTER":
            # Quand "=" est appuyé, on valide la saisie
            self.on_validate(None)
        elif button_text in ["+", "-", "*", "/"]:
            if self.is_calculating is None:
                self.calc_input.text = f"{button_text} {current_text}"
                self.confirm_button.text = "="
            else:
                self.calc_input.text = f"{button_text}{current_text.split()[-1]}"  # effacer le premier caractère avant d'ajouter le nouveau
            self.is_calculating = button_text
        elif button_text == ".":
            if "." not in current_text.split()[-1]:
                self.calc_input.text += button_text
        else:
            self.calc_input.text += button_text
    
    def on_calcul(self, instance):
        # Appel direct à la fonction parse_user_input_calc pour valider la saisie
        __val = self.calc_input.text.strip()
        _val = _val if self.is_calculating is None else _val.split()[-1]
        val = float(_val)
        if self.is_calculating == "+":
            self.result[0] += val
        elif self.is_calculating == "-":
            self.result[0] -= val
        elif self.is_calculating == "*":
            self.result[0] *= val
        elif self.is_calculating == "/":
            self.result[0] /= val
        else:
            self.init_calcul()
            self.calc_input.text = "Oppération pas disponible."
            return
        
        result_last = parse_user_input(self.result[0], self.result[2])
        if isinstance(result_last, str):  # Erreur par ex: en cas de division par 0
           self.init_calcul() 
           self.calc_input.text = "Entrée invalide. Réessayez."
        else:
            self.result_last = result_last
            self.actif_value_label.text = f"{self.result_last[0]} {self.result_last[2]}"
            self.init_calcul()

    def on_validate(self, instance):
        # Appel direct à la fonction parse_user_input_calc pour valider la saisie
        parsed_value = parse_user_input(self.calc_input.text, self.result[2])
        
        # Si c'est une valeur valide, on appelle la fonction de mise à jour
        if isinstance(parsed_value, list):
            self.update_value_callback(parsed_value)
            self.dismiss()  # Fermer le pop-up
        else:
            # Sinon, on affiche une erreur à l'utilisateur
            self.init_calcul() 
            self.calc_input.text = "Entrée invalide. Réessayez."
        
    def change_unit(self, instance):
        # Changer l'unité en mode édition
        unit_ids = [u[0] for u in self.unit_list]    # Extraire la liste des unit_id (colonne [0])
        current_index = unit_ids.index(self.result[1])    # Trouver l'index de l'unité actuelle
        next_unit = self.unit_list[(current_index + 1) % len(self.unit_list)]  # Passer à l'unité suivante
        # convertir result_ avec la nouvelle unitée
        self.result = self.switch_unit(self.result_last[0], self.result_last[1],next_unit)
        # Rafraichir l'affichage
        self.result_str = f"{self.result[0]} {self.result[2]}"
        self.new_value_label.text = self.result_str
        
    def init_calcul(self):
        self.result = self.result_last
        self.actif_value_label.text = f"{self.result_last[0]} {self.result_last[2]}"
        self.calc_input.text = ""
        self.is_calculating = None

    def clear_input(self, instance):
        # Réinitialiser l'entrée (similaire à "CE")
        self.result_last = self.original_value
        self.result = self.result_last_value
        self.actif_value_label.text = f"{self.result_last[0]} {self.result_last[2]}"
        self.init_calcul()


class SegmentPopupContent(BoxLayout):
    """
    PopUp pour confugurer des valeurs d'axes selon une calculation par déduction (angle, distance, ...)
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
        layout.add_widget(Button(text=Tr("save"), on_release=lambda *a: self.manager.save()))
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
