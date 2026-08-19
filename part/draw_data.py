#   draw_tool/   draw_data.py

import os
from kivy.clock import Clock
from kivy.app import App
from kivy.properties import ListProperty
from kivy.metrics import dp
import math
import copy
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.splitter import Splitter
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.lang import Builder

from common_widgets import LabeledCell, InputCell, MyLabel, Separator
from screen_base.common_screen import BaseScreenLayout
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from configurator.config import get_unit_id, parse_user_input, AXIS_CONFIG
from part.draw_tool.popup_segment import SegmentPopupContent, PartManagerPopup, CalculatorPopup
from part.draw_pnt_manager import PointValue, PointData, ColumnDefaultSpec
from part.shapes.shape_editor import ShapeEditor    # part/shapes/shape_editor.py
from common_draw import ProfilCanvas, DashedLineWidget


# Ordre et identifiants uniques des colonnes (Clés d'axes ou de fonctions)
COL_KEYS = ['vert', 'hor', 'vert2', 'hor2', 'l', 'alpha', 'forme']
# Configuration globale des colonnes
COL_WIDTHS = [240, 240, 240, 240, 240, 180, 480]
COL_PROPORTIONS = [1, 1, 1, 1, 1, 0.75, 2]
COL_SPACING = 5
COL_TOTAL_WIDTH = sum(COL_WIDTHS) + COL_SPACING * (len(COL_WIDTHS) - 1)


class HeaderRow(BoxLayout):
    def __init__(self, columns_config, on_unit_click=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.spacing = COL_SPACING
        self.size_hint_y = None
        self.size_hint_x = 1
        self.height = 50 + COL_SPACING
        self.padding = [0, 0, 0, COL_SPACING] # Décolle l'en-tête du tableau en dessous

        # 🎯 Sauvegarde de la configuration nettoyée reçue de la mère
        self.columns_config_list = columns_config

        # 🎯 CRÉATION ULTRA-RAPIDE DES CELLULES
        for config in self.columns_config_list:
            key = config["key"]
            
            # Détermination du texte et de la classe selon le type de colonne
            if config["unit_type"] == "shape":
                title_text = config["title"]
                cell_class = LabeledCell
            else:
                # Formatage industriel multi-lignes standardisé (ex: "Ø X\n[mm]")
                title_text = f"{config['title']}\n[{config['unit_label']}]"
                cell_class = HeaderCell

            # Configuration des propriétés graphiques et des proportions
            kwargs_cell = {
                'text': title_text,
                'halign': 'center',
                'valign': 'middle', # Aligne parfaitement le texte sur deux lignes
                'bold': True,
                'bg_color': (0.8, 0.8, 0.8, 1),
                'text_color': (0, 0, 0, 1),
                'size_hint_x': config["size_hint_x"], # Récupéré de COL_PROPORTIONS via la mère
                'width': None,
            }

            # Si ce n'est pas la colonne 'forme', on injecte la clé et l'événement de clic
            if config["unit_type"] != "shape":
                kwargs_cell.update({'key': key, 'on_click': on_unit_click})

            # Instanciation de la cellule
            lbl = cell_class(**kwargs_cell)
            
            # Sécurité Kivy : recalcule le centrage strict pour le texte multi-lignes (\n)
            lbl.bind(size=lambda instance, val: setattr(instance, 'text_size', val))
            
            self.add_widget(lbl)

class HeaderCell(ButtonBehavior, LabeledCell):
    def __init__(self, key, on_click, **kwargs):
        super().__init__(**kwargs)
        self.key = key 
        self.on_click = on_click
        self.bind(on_release =self._on_release)

    def _on_release(self, *args):
        if self.on_click:
            self.on_click(self.key)

class ClickableRow(ButtonBehavior, BoxLayout):
    pass

class PointRow(ClickableRow):
    def __init__(self, index, entry, is_start=False, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.spacing = COL_SPACING
        self.size_hint_y = None
        self.size_hint_x = 1
        self.height = 45
        self.index = index

        if is_start:
            # Affichage minimal pour les points de départ
            values = [
                entry.data.vert.val_formatted(with_unit=True),
                entry.data.hor.val_formatted(with_unit=True),
            ] + ["-.-"] * 4 + ["- - -"]
            aligns = ['right', 'right'] + ['center'] * 5
        else:
            shape = entry.raw["shape"]
            if isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
                type_str, subtype_str = str(shape[0]), str(shape[1])
                val_def = f"{type_str} / {subtype_str}"
                val = entry.raw.get("shape_label") or val_def
            else:
                val = tr("no_shape")

            values = entry.as_display_row(with_unit=True)
            values.append(str(val))  # Ou entry.extra.forme si tu gères ça
            aligns = ['right'] * 6 + ['center']

        for i, (val, halign) in enumerate(zip(values, aligns)):
            self.add_widget(LabeledCell(text=val, halign=halign, size_hint_x=COL_PROPORTIONS[i], width=None))   # width=COL_WIDTHS[i]

        self.bind(on_press=self.on_row_click)

    def on_row_click(self, *args):
        #print(f"PointRow {self.index} clicked")
        pass

class RowEditor(BoxLayout):
    def __init__(self, index, entry, original_data, display_blocked, on_closed, on_cancel, on_insert, on_delete, parent_editor=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = 3
        self.size_hint_y = None
        self.size_hint_x = 1
        self.height = 120

        self.index = index
        self.entry = entry
        self.original_data = original_data
        self.parent_editor = parent_editor      # lien vers le parent PointDrawEditor
        self.disp_refresh_blocked = display_blocked
        self.focus_key = None
        #self.on_validate = on_validate
        self.exit = on_closed
        self.on_cancel = on_cancel
        self.on_insert = on_insert
        self.on_delete = on_delete

        self.inputs = {}
        self.key_changed = {k: None for k in ['vert', 'hor', 'vert2', 'hor2', 'l', 'alpha']}

        self.build_input_row()
        self.build_button_row()

    def build_input_row(self):
        input_row = BoxLayout(orientation='horizontal', spacing=COL_SPACING, size_hint_y=None, size_hint_x=1, height=60)
        editable_keys = ['vert', 'hor', 'vert2', 'hor2', 'l', 'alpha']
        all_keys = editable_keys + ['forme']

        for i, key in enumerate(all_keys):
            if key == 'forme':
                shape = self.entry.raw.get("shape", None)
                if self.index == 0 or self.index + 1 >= len(self.parent_editor.points_part.entries):
                    val = "- pas possible"
                elif isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
                    val = self.entry.raw.get("shape_label") or f"{str(shape[0])} / {str(shape[1])}"
                else: val = tr("no_shape")

                self.inpf = InputCell(text=str(val), status=0, halign='left', size_hint_x=COL_PROPORTIONS[i], width=None)
                # 🎯 LE TRIP CONCENTRE : La cellule forme s'abonne elle aussi à l'aiguillage unique !
                self.inpf.bind(focus=lambda inst, foc, k=key: self._on_cell_focus_dispatcher(inst, foc, k))
                self.inputs[key] = self.inpf
                input_row.add_widget(self.inpf)
                continue

            # Accès à la valeur formatée pour l'édition des axes numériques
            pv = getattr(self.entry.data, key)
            formatted_val = pv.val_formatted(with_unit=True)

            # Création du champ modifiable
            inp = InputCell(text=formatted_val, status=0, size_hint_x=COL_PROPORTIONS[i], width=None)
            
            # 🎯 L'UNIFICATION ABSOLUE : Toutes les colonnes numériques appellent le dispatcher privé !
            inp.bind(focus=lambda inst, foc, k=key: self._on_cell_focus_dispatcher(inst, foc, k))
            
            # On conserve par sécurité le changement de texte
            inp.bind(text=self.on_input_changed(key))

            self.inputs[key] = inp; input_row.add_widget(inp)

        self.add_widget(input_row)

    def build_button_row(self):
        btn_row = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=60)
        
        btn_row.add_widget(Widget())

        btn_row.add_widget(Button(text=Tr("delete"), on_press=self.delet_point))
        btn_row.add_widget(Button(text=Tr("add"), on_press=self.insert_point))
        # Boutons Copier / Coller
        btn_row.add_widget(Button(text=Tr("copy"), on_press=lambda instance: self.copy_point()))
        self.btn_paste = Button(text=Tr("paste"), on_press=lambda instance: self.paste_point())
        self.btn_paste.disabled = (self.parent_editor.copied_entry is None)
        btn_row.add_widget(self.btn_paste)

        btn_row.add_widget(Widget())

        btn_row.add_widget(Button(text=Tr("cancel"), on_press=self.cancel))
        #btn_row.add_widget(Button(text=Tr("validate"), on_press=self.validate))
        btn_row.add_widget(Button(text=TR("ok"), on_press=self.on_exit))

        btn_row.add_widget(Widget())

        self.add_widget(btn_row)

    def _on_cell_focus_dispatcher(self, instance, focused, key):
        """
        Aiguillage unique pour TOUTES les cellules du tableau (Axes, Segments, Formes).
        Gère l'interverrouillage global, le focus fantôme et applique votre nomenclature d'axes.
        """
        # Flag pour l'utilisation tacitle de la calculette de sésie
        mode_tactile = getattr(App.get_running_app(), 'mode_tactile_actif', False)
        
        # 💨 CAS 1 : LA PERTE DE FOCUS (L'opérateur valide, annule la popup ou change de case)
        if not focused:
            self.display_blocked, self.focus_key = False, None                        
            # 🎯 NETTOYAGE D'OFFICE POUR TOUS LES MODES (Bureau et Tactile)
            if key in self.inputs and key != 'forme':
                pv = getattr(self.entry.data, key)
                # Remet la cellule propre à l'écran avec son formatage officiel
                instance.text = pv.val_formatted(with_unit=True)
            # Supprime la surbrillance bleue instantanément
            if hasattr(instance, 'cancel_selection'):
                instance.cancel_selection()

            return

        # 🛡️ BARRIÈRE DE SÉCURITÉ : Si une popup est déjà ouverte, on rejette le focus de réception
        if getattr(self, 'popup_open', False):
            return

        popup = None
        total_points = len(self.parent_editor.points_part.entries) # Mesure en direct de la liste FAO

        # Préparation des paramètres (Uniquement pour les colonnes cartésiennes)
        if key in ['hor', 'vert', 'hor2', 'vert2']:
            default_unit = getattr(self.entry.data, key).unit_id if hasattr(self.entry.data, key) else "dist"
            parsed_text = parse_user_input(instance.text.strip(), default_unit)
            if isinstance(parsed_text, str):   
                current_unit = default_unit    
                current_str_val = getattr(self.entry.data, key).val_formatted(with_unit=False)
            else:    
                current_unit = parsed_text[1]
                current_str_val = str(parsed_text[0])
                
            arg_calculator_popup = {
                "current_value": current_str_val, "current_unit": current_unit,
                "case_desgn": AXIS_CONFIG.get(key, {}).get("screen", key),    
                "update_value_callback": lambda pack_data: self.on_calculateur_confirm(key, pack_data, instance),
                "size_hint": (None, None),
                "size" : (1400, 600) 
            }

        # ─── 📦 GROUPE A : COORDONNÉES ABSOLUES ───
        if key in ['hor', 'vert']:
            if mode_tactile:
                popup = CalculatorPopup(**arg_calculator_popup)
            else:
                pass    # on laisse ce fermer la fonction pour le mode clavier

        # ─── 📦 GROUPE B : COORDINATIONS RELATIVES / DELTAS (Interdites sur l'index 0) ───
        elif key in ['hor2', 'vert2', 'l', 'alpha'] and self.index != 0:
            if key in ['l', 'alpha']:   # Oblique longueur ou angle
                popup_content = SegmentPopupContent(
                    data=copy.deepcopy(self.entry.data), key_changed=self.key_changed,
                    on_confirm=self.on_segment_popup_confirm, key_target=key
                )
                popup = Popup(title=f"{TR('segment_config_title')} {key.upper()}", content=popup_content, size_hint=(None, None), size=(800, 900), auto_dismiss=False)
                popup_content.parent_popup = popup
            else:   # Cartésienne relative
                if mode_tactile:
                    popup = CalculatorPopup(**arg_calculator_popup)

        # ─── 📦 GROUPE C : TERMINAISONS / RACCORDEMENTS (Forme géométrique) ───
        elif key == "forme" and self.index != 0 and (self.index + 1) < total_points:
            prev_pnt_raw = self.parent_editor.points_part.entries[self.index - 1].raw
            next_pnt_raw = self.parent_editor.points_part.entries[self.index + 1].raw
            popup = ShapeEditor(
                point_b=self.entry, prev_pnt_raw=prev_pnt_raw, next_pnt_raw=next_pnt_raw,
                copied_shape_data=self.parent_editor.copied_shape, mirror_z=self.parent_editor.mirror_z,
                on_done=self.shape_edit_done
            )

        # ─── 📦 GROUPE D : CELLULES INACCESSIBLES OU VERROUILLÉES ───
        else:
            self.popup_open, self.display_blocked, self.focus_key = False, False, None
            instance.focus = False
            return 

        # ─── MÉCANIQUE UNIQUE DE FERMETURE DES POPUPS (GROUPES A, B, C) ───
        def on_close_any_popup(*args):
            self.popup_open, self.display_blocked, self.focus_key = False, False, None
            instance.focus = False # 🔓 JOKER 1 : Tue définitivement le rebond du focus fantôme !
            
            if key == "forme": 
                shape = self.entry.raw.get("shape", None)
                if isinstance(shape, (list, tuple)) and len(shape) == 2 and shape is not None:
                    testtext = self.entry.raw.get("shape_label") or f"{shape[0]} / {shape[1]}"
                    self.inpf.text = f"TEST-{testtext}"
                else: self.inpf.text = tr("no_shape")
                # 2. On force la FAO locale à recalculer l'arc ou le chanfrein à partir 
                # des nouveaux paramètres validés par la Pop-up, et on redessine l'écran !
                self.parent_editor.refresh_drawing(recalc=True, idx=self.index, new_pos=None)

        # ─── 🏁 LE VÉRITABLE AIGUILLAGE FINAL ───
        if popup:
            # 📱 OPTIONS TACTILES OU FORMES GÉOMÉTRIQUES : On verrouille tout et on lance la popup
            self.popup_open, self.display_blocked, self.focus_key = True, True, key
            popup.bind(on_dismiss=on_close_any_popup)
            popup.open()
            
            # Nettoyage préventif de la sélection bleue pour le mode tactile
            if hasattr(instance, 'cancel_selection'):
                instance.cancel_selection()
                
            instance.focus = False # 🔓 JOKER 2 : N'agit QUE si une popup est réellement ouverte !
            return
        else:   
            # 🖥️ OPTION CLAVIER DIRECT (BUREAU) : Pas de popup créée
            # On active les verrous géométriques, mais on laisse la popup_open à False
            self.popup_open = False
            self.display_blocked = True
            self.focus_key = key

    def on_calculateur_confirm(self, key, pack_data, instance_input):
        """
        Intercepte le pack 3-en-1 renvoyé par la calculatrice à sa fermeture.
        Injecte la chaîne texte directement dans le moteur PointValue de la cellule.
        """
        valeur_texte_fao = pack_data["text"] # Extraction de la chaîne formatée (ex: "50.800mm")
        
        # Récupération de l'objet PointValue correspondant à la colonne (ex: self.entry.data.vert)
        pv = getattr(self.entry.data, key)
        
        # CONTRÒLE DES CHANGEMENTS
        instance_parsed = parse_user_input(instance_input.text, pv.unit_id)
        if not isinstance(pack_data, dict):
            statut_modification = "ERROR"
            print(f"[DEBUG RowEditor] ⚠️ pack_data invalide (pas un dict). Annulation.")
        elif not isinstance(instance_parsed, str):
            if pack_data["value"] != instance_parsed[0] or pack_data["unit_id"] != instance_parsed[1]:
                statut_modification = True
            else:
                statut_modification = False
        else:   # ici si la valeur d'écran et invalide, on force la re-calculation
            statut_modification = True
        
        if statut_modification is True:
            #print(f"DEBUG RowEditor_row=469: pack_data.text {pack_data["text"]} / instance_input.text {instance_input.text}")
            # Si la valeur a changé, on applique votre formatage officiel pour la cellule visuelle
            instance_input.text = valeur_texte_fao #pv.val_formatted(with_unit=True)
            
            # On marque la ligne comme "dirty" pour signaler qu'un recalcul FAO est obligatoire
            self.entry.modified_data = True
            
            # Appel en cascade de votre fonction de traitement d'origine pour les autres axes reliés
            self.process_input_change(key, valeur_texte_fao, instance_input)
        #else:
            #print(f"DEBUG RowEditor/on_calculateur_confirm: valeur modifié = FAUX")
        
        # 🎯 NETTOYAGE SÉLECTION : On force Kivy à effacer la sélection bleue sur cette case
        if hasattr(instance_input, 'cancel_selection'):
            instance_input.cancel_selection()

    def on_input_changed(self, key):
        self.display_blocked = True
        def callback(instance, value):
            self.process_input_change(key, value, instance)
        return callback

    def on_segment_popup_confirm(self, new_vert2, new_hor2, key='l'):
        # Convertir float → str si nécessaire
        vert2_disp = str(new_vert2) if isinstance(new_vert2, (int, float)) else new_vert2
        hor2_disp = str(new_hor2) if isinstance(new_hor2, (int, float)) else new_hor2

        # Met à jour la bonne cellule et les données selon key
        if key == 'alpha':
            # Mise à jour spécifique pour alpha
            instance_this = self.inputs.get('alpha')
        else:
            # Cas général, par défaut segment l
            instance_this = self.inputs.get('l')

        if instance_this:
            self.process_input_change(key, vert2_disp, instance_this, hor2_disp)

    def process_input_change(self, key, value, instance, value2=None):
        # NOTE : set_from_input attend une str, donc conversion nécessaire en amond de value et value2
        ''' pour la pop_up de "l" et "alpha"'''
        try:
            new_update = False
            refresh_text = False
            change = changeh = changep = False

            # PointValue correspondant à la clé principale
            pv = getattr(self.entry.data, key)
            pv_vert2 = pv_hor2 = pv

            # Cas spécial où on modifie 2 valeurs en même temps (ex: 'l' modifie h et p)
            if value2 is not None:
                changeh = self.entry.data.vert2.set_from_input(value)
                pv_vert2 = getattr(self.entry.data, 'vert2')
                changep = self.entry.data.hor2.set_from_input(value2)
                pv_hor2 = getattr(self.entry.data, 'hor2')

                # Si aucune valeur n'a changé, on arrête là
                if not (changeh or changep):
                    return
                
            else:    # Modification classique d'une seule valeur
                change = pv.set_from_input(value)

                # Si l'entrée est invalide (ex: utilisateur en train de taper), on colore et on attend
                if change in ('invalid_unit', 'invalid_format'):
                    instance.background_color = (1, 0.8, 0.8, 1)  # rose clair
                    return

                # Sinon, on remet la couleur normale
                instance.background_color = (1, 1, 1, 1)

                # Si la valeur n'a pas changé, on sort
                if not change:
                    return
                
            # Gestion des mises à jour selon la clé modifiée ou changement détecté sur h/p
            if key == 'vert2' or changeh:
                old_vert2 = self.original_data.vert2.convert_to(self.original_data.vert.get_id_unit())
                new_vert2 = pv_vert2.convert_to(self.entry.data.vert.get_id_unit())
                self.entry.data.vert.value = self.original_data.vert.value - old_vert2 + new_vert2
                #print(f"DEBUG: h calc-> New_X {self.entry.data.x.value}")
                if self.focus_key == key:
                    self.key_changed['vert2'] = abs(new_vert2 - old_vert2) > 1e-8
                    if self.key_changed['vert']:
                        self.key_changed['vert'] = None
                    new_update = True   # pour key=='l' ordoné par if key=='l'

            if key == 'hor2' or changep:
                old_hor2 = self.original_data.hor2.convert_to(self.original_data.hor.get_id_unit())
                new_hor2 = pv_hor2.convert_to(self.entry.data.hor.get_id_unit())
                self.entry.data.hor.value = self.original_data.hor.value - old_hor2 + new_hor2
                #print(f"DEBUG: p calc-> New_Z {self.entry.data.z.value}")
                if self.focus_key == key:
                    self.key_changed['hor2'] = abs(new_hor2 - old_hor2) > 1e-8
                    if self.key_changed['hor']:
                        self.key_changed['hor'] = None
                    new_update = True

            elif key == 'vert':
                #print(f"DEBUG: vert calc-> New_Vert {self.entry.data.vert.value}")
                if self.focus_key == key:
                    self.key_changed['vert'] = abs(self.original_data.vert.value - self.entry.data.vert.value) > 1e-8
                    if self.key_changed['vert2']:
                        self.key_changed['vert2'] = None
                    new_update = True

            elif key == 'hor':
                #print(f"DEBUG: hor calc-> New_Hor {self.entry.data.hor.value}")
                if self.focus_key == key:
                    self.key_changed['hor'] = abs(self.original_data.hor.value - self.entry.data.hor.value) > 1e-8
                    if self.key_changed['hor2']:
                        self.key_changed['hor2'] = None
                    new_update = True

            if key == 'l' or key == 'alpha':
                #print(f"DEBUGprocess_input_change: calc-> New_X {self.entry.data.x.value} : calc-> New_Z {self.entry.data.z.value} || focus_key: {self.focus_key}")
                if self.focus_key == key:
                    refresh_text = True
                    new_update = True

            # Mise à jour finale si nécessaire  #recalcul et mise à jour des valeurs de ce point et du suivant
            if new_update:
                self.parent_editor.update_row_data(
                    self.index,
                    self.entry.data.hor.val_base(),
                    self.entry.data.vert.val_base(),
                    False
                )
                # Mise à jour des autres champs (sauf celui en cours d'édition)
                
                print(f"DEBUG RowEditor_ligne590: new_update = vrai (process_input_change)")
                self.refresh_inputs(key, forced=refresh_text)

        except ValueError:
            instance.foreground_color = (1, 0, 0, 1)  # Erreur = rouge

    def shape_edit_done(self):
        ''' Callback à la fermeture de ShapeEditor()'''
        # 1. On met à jour le texte visuel de la cellule dans le tableau Kivy
        self.refresh_shape_cell()
        
        # 2. On force la FAO locale à recalculer l'arc ou le chanfrein à partir 
        # des nouveaux paramètres validés par la Pop-up, et on redessine l'écran !
        self.parent_editor.refresh_drawing(recalc=True, idx=self.index, new_pos=None)
        
    def on_exit(self, *args):
        try:
            #self.on_validate(self.index)
            self.exit(None)
        except Exception as e:
            print(Tr("error_validation").format(error=e))

    def cancel(self, *args):
        self.on_cancel()

    def insert_point(self, *args):
        try:
            self.on_insert(self.index)
        except Exception as e:
            print(Tr("error_insertion").format(error=e))

    def delet_point(self, *args):
        self.on_delete(self.index)
    
    def copy_point(self):
        """
        Copie le point à l'index donné pour un futur collage.
        """
        if self.entry.data is None:
            return
        self.parent_editor.copied_entry = copy.deepcopy(self.entry)
        self.btn_paste.disabled = False

    def paste_point(self):
        """
        Colle un nouveau point après l'index donné, basé sur self.copied_entry.
        """
        if self.parent_editor.copied_entry is None:
            return  # Rien à coller
        self.parent_editor.insert_point(self.index, self.parent_editor.copied_entry)

    def refresh_inputs(self, exclude_key=None, forced=False):      
        """
        Réactualise les champs visuels (texte et couleur) de tous les inputs,
        sauf le texte de celui actuellement en cours de modification, si pas forced.
        """
        for key, input_cell in self.inputs.items():
            # Optionnel : coloration si modifié
            if self.key_changed.get(key):
                input_cell.foreground_color = (1.0, 0.55, 0.0, 1)
                input_cell.bold = True
            else:
                input_cell.foreground_color = (0.3, 0.3, 0.3, 1)
                input_cell.bold = False

            if (key == exclude_key or key == self.focus_key) and not forced:
                continue  # Ne pas toucher à l'input en cours d'édition, sauf si c'est forced

            if key == "forme": continue

            pv: PointValue = getattr(self.entry.data, key)
            input_cell.text = pv.val_formatted(with_unit=False)
    
    def refresh_shape_cell(self):
        if "forme" in self.inputs:
            shape = self.entry.raw.get("shape")
            shape_label = self.entry.raw.get("shape_label")
            print(f">>> Shape label: {shape_label}")
            print(f">>> Shape raw: {shape}")

            if isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
                type_str, subtype_str = str(shape[0]), str(shape[1])
                val_def = f"{type_str} / {subtype_str}"
                val = shape_label or val_def
            else:
                val = tr("no_shape")

            self.inputs["forme"].text = val
        else:
            print("C'est la m...")


chemin_kv = os.path.join(os.path.dirname(__file__), "caograph.kv")
if os.path.exists(chemin_kv):
    Builder.load_file(chemin_kv)
else:
    print(f"[⚠️ WARN] Impossible de trouver le fichier graphique : {chemin_kv}")

class CaoGraph(BoxLayout):
    def __init__(self, **kwargs):
        self.scale = 0.0025              
        self.mirror_hor = False
        self.mirror_vert = True
        self.offset_base = [0.5, 0.5]   
        self.offset_screen = [0.0, 0.0] 
 
        # ON INSTANCIE LE CANVAS APRÈS LE SUPER POUR S'ASSURER DES IDS
        self.canvas_piece = ProfilCanvas(
            box=None, 
            scale=self.scale, 
            mirror_hor=self.mirror_hor, 
            mirror_vert=self.mirror_vert, 
            A_outline_width=1.5, 
            A_fill_color=(0.1, 0.3, 0.1, 0.4)
        )

        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        """ 🎯 DÉCLENCHEUR SÉCURISÉ : Les IDs Kivy sont prêts, on prépare le terrain. """
        if not hasattr(self, 'ids') or not self.ids or 'zone_decoupe' not in self.ids:
            return

        stencil = self.ids.zone_decoupe
        repere_calcul = self.ids.box_calcul_gauche  
        
        if stencil and repere_calcul:
            # 1️⃣ Injection de l'axe blanc
            self.axe_central = DashedLineWidget(
                line_color=[1.0, 1.0, 1.0, 0.8], line_width=1.0,
                dash_pattern=[dp(30), dp(5)], dash_spacing=dp(12)
            )
            stencil.add_widget(self.axe_central, index=0)            

            # 2️⃣ Connexion et injection du canvas de la pièce
            self.canvas_piece.box_dest = repere_calcul
            stencil.add_widget(self.canvas_piece)
            
            # 🚀 3️⃣ CADENCEUR ASYNCHRONE DE DÉMARRAGE :
            # On attend exactement 1/10ème de seconde (0.1s) pour que Kivy ait fini 
            # de dessiner les fenêtres et que repere_calcul.size possède ses vrais pixels machine !
            Clock.schedule_once(self.initialiser_dessin_test, 0.1)

    def initialiser_dessin_test(self, dt):
        """ Éteint l'écran noir et force le premier tracé au format utile. """
        # On appelle votre méthode d'injection qui contient les cercles de tests
        self.set_profil_pieces()
        #print("[CaoGraph] Premier tracé de test initialisé avec succès.")

    def set_profil_pieces(self, fao_list=None, cao_list=None, saved_list=None, box=None):
        """
        L'INJECTEUR DOUBLE CALQUE FAO/CAO FINAL :
        Affiche la vraie pièce en cours d'édition (Vert/Bleu) par-dessus 
        la pièce d'origine sauvegardée (Rose) avec un auto-scale pleine page.
        """
        #TODO: à réparrer
        #repere_calcul = box if box is not None else self.ids.box_calcul_gauche
        repere_calcul = self.ids.box_calcul_gauche

        # SÉCURITÉ DE CAPTURE DES LISTES DU MANAGER :
        active_profile = cao_list if cao_list is not None else fao_list
        
        # Si la liste de sauvegarde n'est pas fournie, on va la chercher à la source
        if saved_list is None:
            from kivy.app import App
            app = App.get_running_app()
            if hasattr(app, "part") and hasattr(app.part, "saved_profile_seg_net"):
                saved_list = app.part.saved_profile_seg_net

        # 📐 APPEL À VOTRE METHODE AUTO-ZOOM SUR LES VRAIS SEGMENTS DE LA PIÈCE
        self.canvas_piece.update_entities_auto_scale_auto_center(
            box_dest=repere_calcul,
            a_entities=active_profile or [],  # La pièce verte (dessus)
            b_entities=saved_list or [],     # La pièce rose (dessous)
            code_entities="A+b",
            save_code=True,
            margin=[0.1,0.1]
        )

        # TRACÉ DE LA LIGNE D'AXE TOTALEMENT SÉCURISÉ (Plus de liste + float !)
        if hasattr(self.canvas_piece, 'offset_0') and len(self.canvas_piece.offset_0) > 1:
            y_axis_pos = self.canvas_piece.offset_0[1] # On prend la hauteur Y pixels
            
            x_debut = repere_calcul.pos[0]
            x_fin = repere_calcul.pos[0] + repere_calcul.width
            
            self.axe_central.redraw_pos(
                [x_debut, y_axis_pos], 
                [x_fin, y_axis_pos]
            )

    def zoom_all_in_piece(self):
        """ ZOOM AUTO PLEIN CADRE : Ré-aligne la loupe sur la vraie pièce mécanique """
        from kivy.app import App
        app = App.get_running_app()
        manager = app.part if (hasattr(app, 'part') and app.part) else None
        
        if manager and hasattr(manager, "curent_profile_seg_net"):
            # On appelle la fonction en lui injectant explicitement les vraies listes à jour !
            self.set_profil_pieces(
                cao_list=manager.curent_profile_seg_net,
                saved_list=manager.saved_profile_seg_net
            )
        else:
            # Sécurité si aucune pièce n'est chargée (Appel à vide d'origine)
            self.set_profil_pieces()


class PointDrawEditor(BaseScreenLayout):  # 🛠️ Héritage direct du Châssis !
    def __init__(self, part_points, **kwargs):
        # 1️⃣ PROPRIÉTÉS ET CONSTANTES GÉOMÉTRIQUES CAO
        self.points_part = part_points  # instance de PointManager()
        self.mirror_z = False
        self.editing_index = None
        self.copied_entry = None    
        self.copied_shape = {"shape": None, "shape_label": None, "shape_params": {}}    
        self.original_entry = None   
        self.disp_refresh_blocked = False

        # Chargement et initialisation optimisée des données CAO
        self.points_part.data_loaded = True
        self.points_part.update_entries_data()

        self.display_rows_list = []  # Renommé pour éviter le conflit avec le widget GridLayout
        
        # On appelle le constructeur du châssis parent
        super().__init__(**kwargs)

    def on_kv_post(self, base_widget):
        """
        DÉCLENCHEUR SÉCURISÉ : Clipse la barre d'outils CAO en haut 
        et le tableau de points dans le corps de droite de manière rectiligne.
        """
        self.columns_config_list = self._build_columns_config() # configuration partagée des colonnes
        # =====================================================================
        # 🧱 MODULE A : DESSIN DE L'ENTÊTE HAUTE SPÉCIFIQUE CAO
        # =====================================================================
        # Remplacement de l'ancien top_bar par un layout adapté au header_zone
        top_bar = BoxLayout(
            orientation='horizontal', 
            size_hint=(1, 1), # Prend 100% de la place du header_zone
            padding=[dp(15), dp(5), dp(15), dp(5)], 
            spacing=dp(10)
        )

        # Bouton Toggle Miroir Normalisé
        self.toggle_mirror = ToggleButton(
            text=f"{Tr('mirror')} Z: {TR('off')}", 
            state='normal', 
            size_hint=(None, None), 
            height=dp(50), 
            width=dp(180), 
            pos_hint={'center_y': 0.5}
        )
        self.toggle_mirror.bind(on_press=self.on_toggle_mirror)

        # Label cliquable du nom de la pièce normalisé
        part_name_txt = self.points_part.get_part_name()
        self.part_name_lbl = LabeledCell(
            text=part_name_txt, 
            halign='center', 
            bold=True,
            bg_color=(0.4, 0.6, 0.4, 0.5),
            height=dp(50),
            size_hint=(None, None),
            width=dp(300),
            pos_hint={'center_y': 0.5},
            on_click=self.open_part_popup
        )

        # Assemblage de l'entête CAO
        top_bar.add_widget(self.part_name_lbl)
        top_bar.add_widget(Widget()) # Espaceur élastique central
        top_bar.add_widget(self.toggle_mirror)

        # =====================================================================
        # 🧱 MODULE B : DESSIN DU CORPS DE FORMULAIRE À DEUX ÉTAGES (Splitter)
        # =====================================================================
        # Conteneur principal qui va être injecté dans le châssis
        corps_cao = BoxLayout(orientation='vertical', spacing=dp(5))

        # --- 🏢 ÉTAGE SUPÉRIEUR : Le Tableau de Points ---
        # On regroupe l'en-tête et le ScrollView dans un bloc vertical dédié
        bloc_tableau = BoxLayout(orientation='vertical', spacing=dp(5), padding=[dp(1), dp(1), dp(1), 0])
        bloc_tableau.add_widget(HeaderRow(columns_config=self.columns_config_list, on_unit_click=self.on_header_unit_click))
        
        self.scroll = ScrollView(size_hint=(1, 1),bar_width=dp(20))
        # 2. On assigne les autres propriétés "en ligne" juste après    # Kivy les interceptera sans lever d'erreur de dictionnaire
        self.scroll.scroll_type = ['bars']
        self.scroll.bar_state = 'normal'    # L'INTELLIGENCE KIVY : Visible SEULEMENT si le défilement est nécessaire, mais reste fixe et affiché en permanence tant qu'il y a du scroll possible !
        self.scroll.bar_inactive_width = dp(10) # On verrouille pour éviter que la barre ne rétrécisse si on la lâche
        self.display_rows = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.display_rows.padding = [0, 0, 0, dp(15)]
        self.display_rows.bind(minimum_height=self.display_rows.setter('height'))
        self.scroll.add_widget(self.display_rows)
        bloc_tableau.add_widget(self.scroll)

        # 🎯 LE COMPOSANT SÉPARATEUR DE KIVY : Splitter
        # On encapsule le tableau dans le Splitter. strip_size définit l'épaisseur de la barre grise.
        splitter_tableau = Splitter(
            sizable_from='bottom',  # La barre grise sera en bas du tableau et glissera vers le bas
            size_hint_y=1.0,        # Par défaut, 2 = prend 2/3 de la hauteur de l'écran
            min_size=dp(100),       # Hauteur minimale pour ne pas étouffer le tableau
            strip_size=dp(7)       # Épaisseur de la barre grise déplaçable
        )
        splitter_tableau.add_widget(bloc_tableau)

        # --- 🛠️ ÉTAGE INFÉRIEUR PUR ET NET ---
        # 🚀 PLUS AUCUN BLOC INFÉRIEUR COMPLEXE ! 
        # CaoGraph prend 100% de la largeur sous le séparateur et embarque ses propres boutons.
        graphbox = CaoGraph(size_hint=(1, 1)) 
        corps_cao.add_widget(splitter_tableau)
        corps_cao.add_widget(graphbox)

        # =====================================================================
        # 🎯 CLIPSAGE FINAL
        # =====================================================================
        self.injecter_entete_specifique(top_bar)
        self.injecter_corps_specifique(corps_cao)

        self.ids["graph_box"] = graphbox
        self.ids["splitter_top"] = splitter_tableau
        self.refresh()
        
        '''# Optionnel : Charger le dessin initial de ta pièce dans la vue inférieure
        graphbox.set_profil_pieces(
            box=True, 
            saved_list=self.points_part.saved_profile_seg_net, 
            cao_list=self.points_part.curent_profile_seg_net
        )'''

    def __del__(self):
        """Ferme l'éditeur et désactive le chargement des données"""
        #print("Fermeture de l'éditeur")
        self.points_part.data_loaded = False  # Désactive le chargement des données à la fermeture

    def _build_columns_config(self):
        """
        🎯 LA MATRICE DU TABLEAU NETTOYÉE :
        Exploite la fonction globale get_unit_config pour assembler 
        les propriétés d'affichage et de configuration du tableau.
        """
        from configurator.config import AXIS_CONFIG, get_unit_config
        
        columns_config_list = []

        for i, key in enumerate(COL_KEYS):
            if key == "forme":
                config = {
                    "key": key,
                    "title": Tr("shape"),
                    "unit_label": "",
                    "unit_type": "shape",
                    "is_diameter": False,
                    "size_hint_x": COL_PROPORTIONS[i],
                    "decimals": 0,
                    "long_name": ""
                }
            else:
                # 1. Lecture brute de l'axe dans le JSON
                axis_data = AXIS_CONFIG.get(key, {})
                axis_label = axis_data.get("screen", key)
                # 🎯 LE GRAAL : Appel direct de votre fonction unifiée !
                unit_cfg = get_unit_config(axis_data.get("unit", "unit_distance"))
                #unit_family = axis_data.get("type", "unit_distance") # ex: "unit_distance"
                #json_unit_target = axis_data.get("unit", unit_family) # ex: "unit_distance" ou "inch"

                '''# 2. Traduction de la cible pour vos outils d'analyse d'alias
                alias_map = {
                    "unit_distance": "dist",
                    "unit_angle": "ang",
                    "unit_speed": "speed"
                }
                recherche_key = alias_map.get(json_unit_target, json_unit_target)
                '''

                # 3. Gestion cosmétique du diamètre automatique
                is_diameter = (axis_data.get("factor") == 2)
                full_title = f"Ø {axis_label}" if is_diameter else axis_label

                # 4. Stockage unifié dans la matrice
                config = {
                    "key": key,
                    "title": full_title,
                    "unit_label": unit_cfg["label"],       # ex: "mm"
                    "unit_type": axis_data.get("unit", "unit_distance"),
                    "is_diameter": is_diameter,
                    "size_hint_x": COL_PROPORTIONS[i],
                    "decimals": unit_cfg["decimals"],     # ex: 3
                    "long_name": unit_cfg["long_name"]     # ex: "Millimètre"
                }
            
            columns_config_list.append(config)
                
        return columns_config_list

    def on_toggle_mirror(self, btn):
        if self.editing_index is not None:
            self.cancel_edit()

        self.mirror_z = (btn.state == 'down')
        btn.text = f'{Tr("mirror")} Z: {TR("on") if self.mirror_z else TR("off")}'

        self.points_part.set_mirror(self.mirror_z)
        self.points_part.update_entries_data()  # <<< recalculer toutes les données visibles
        
        if self.editing_index is not None:
            self.cancel_edit()
        else:
            self.refresh()

    def open_part_popup(self, *args):
        def part_update(id_part=None, save_last=False, reload_json=False):
            """
            Met à jour ou change la pièce active de manière étanche.
            """
            # 0. Vérifie la validité de l'index dans le catalogue
            index = self.points_part.storage.part_id_actif if id_part is None else id_part
            all_names = self.points_part.get_part_all_names()
            if not (0 <= index < len(all_names)):
                print(f"[Erreur] Index de pièce invalide : {index}")
                return

            # 1. Sauvegarde la pièce courante uniquement si l'opérateur l'a demandé
            if save_last:
                self.save_current_profile_to_json()  
                self.points_part.commit_part_names()  

            # 2. On mémorise si l'opérateur change réellement de numéro de pièce
            has_changed_part = (index != self.points_part.storage.part_id_actif)

            # Change l'index actif dans le module de stockage
            self.points_part.storage.set_selected_index(index)

            # 3. 🚀 SÉCURITÉ DE CHARGEMENT :
            # Si on change de pièce OU si le rechargement est forcé, on appelle obligatoirement .load().
            # Cela vide la mémoire, charge les nouveaux points et initialise le fond rose de la nouvelle pièce.
            if reload_json or has_changed_part:
                self.points_part.load(load_data=True)
            else:
                # Simple rafraîchissement local (ex: changement d'unités de colonnes)
                self.points_part.update_entries_data()  

            # 4. Réinitialise complètement l'état local d'édition pour la nouvelle pièce
            self.editing_index = None   
            self.original_entry = None

            # 5. Met à jour le libellé du nom de la pièce en haut du formulaire
            self.part_name_lbl.text = self.points_part.get_part_name()

            # 6. Rafraîchit l'affichage complet (Tableau textuel + Dessin du bas)
            self.refresh()
        
        def on_popup_dismiss(*_):
            self.part_name_lbl.text = self.points_part.get_part_name()

        popup = PartManagerPopup(manager=self.points_part, refresh_callback=part_update)
        popup.bind(on_dismiss=on_popup_dismiss)
        popup.open()

    def refresh(self, forced_disp=False):
        """
        🎯 LE HUB DE CENTRALISATION IHM RAPIDE :
        Met à jour le dessin CAO en temps réel à chaque frappe de caractère,
        mais gèle le tableau textuel pour empêcher la perte de focus du clavier.
        """
        #print(">>>>>>>>>>>>>>>>> REFRESH PointDraw <<<<<<<<<<<<<<<<<<<<<<<<<<<<")

        # 1️⃣ Notification vers le main.py (votre code)
        App.get_running_app().refresh_propage("draw_editor")

        # 2️⃣ 🚀 LE TRACÉ GÉOMÉTRIQUE EN DIRECT À LA FRAPPE
        self.refresh_drawing(recalc=False)

        # 3️⃣ 🛡️ LE BOUCLIER THERMIQUE DU CLAVIER (Focus)
        # Si le rafraîchissement est bloqué (IHM en cours d'édition textuelle active),
        # ON S'ARRÊTE NET ICI. On s'interdit de reconstruire le tableau de lignes 
        # pour que le RowEditor ne soit pas détruit sous les doigts de l'opérateur.
        if self.disp_refresh_blocked and not forced_disp:
            return  # 🚀 BLOCAGE STRATÉGIQUE DU TEXTE UNIQUEMENT

        # 4️⃣ Reconstruction propre du tableau textuel (uniquement en sortie de case ou si forcé)
        self.refresh_display()

    def refresh_display(self):
        from functools import partial
        self.display_rows.clear_widgets()

        entries = self.points_part.entries

        for i, entry in enumerate(entries):
            if entry.data is None:
                continue  # Ne rien afficher si pas de data

            # Détecter les doublons pour marquer le "start"
            is_start = (i == 0)
            if i > 0:
                curr = entry.data
                prev = entries[i - 1].data
                if prev and math.isclose(curr.hor.val_base(), prev.hor.val_base()) and math.isclose(curr.vert.val_base(), prev.vert.val_base()):
                    is_start = True

            if self.editing_index == i:
                editor = RowEditor(
                    index=i,
                    entry=entry,
                    #original_data=self.original_data,
                    original_data=self.original_entry.data,
                    display_blocked=self.disp_refresh_blocked,
                    #on_validate=self.data_pos_to_raw,
                    on_closed=self.edit_row,
                    on_cancel=self.cancel_edit,
                    on_insert=self.insert_point,
                    on_delete=self.delete_point,
                    parent_editor=self  # ← ICI tu passes PointDrawEditor
                )
                self.display_rows.add_widget(editor)
            else:
                row = PointRow(index=i, entry=entry, is_start=is_start)
                
                row.bind(on_touch_down=partial(self._on_row_touch_wrapper, index=i))
                self.display_rows.add_widget(row)

    def refresh_drawing(self, recalc=True, idx=None, new_pos=None):
        if recalc:
            self.points_part.refresh_drawing(idx, new_pos)
        elif idx and new_pos:
            self.points_part.entries[idx].raw["pos"] = new_pos
            self.points_part.entries[idx].modified_data = True
        # Injection immédiate dans le canvas OpenGL de votre CaoGraph
        if 'graph_box' in self.ids and self.ids['graph_box']:
            self.ids['graph_box'].set_profil_pieces(
                box=True, 
                fao_list=[], 
                cao_list=self.points_part.curent_profile_seg_net # La ligne verte se déforme en direct !
            )

    def update_row_data(self, index, new_hor, new_vert, refresh=True):
        """Mise à jour d'une rangée via l'IHM tactile (Boutons +/-, molettes ou raccourcis)."""

        print(f"[DEBUG update_row_data] idx {index} >> new_hor:{new_hor}  new_vert:{new_vert}  refresh:{refresh}")

        new_pos = [int(round(new_hor)), int(round(new_vert))]

        entry = self.points_part.entries[index]
        prev_data = self.points_part.entries[index - 1].data if index > 0 else None
        next_data = self.points_part.entries[index + 1].data if index + 1 < len(self.points_part.entries) else None
        prev_pos = [prev_data.hor.val_base(), prev_data.vert.val_base()] if prev_data else None
        next_pos = [next_data.hor.val_base(), next_data.vert.val_base()] if next_data else None
        
        # 1. Mise à jour de la couche d'IHM textuelle (.data)
        entry.data.recompute(pos=new_pos, prev_pos=prev_pos)
        if next_pos:
            self.points_part.entries[index + 1].data.recompute(pos=next_pos, prev_pos=new_pos)

        # 🚀 2. ALIGNEMENT GÉOMÉTRIQUE : On synchronise également le .raw de la mémoire vive        
        # On demande au manager de recalculer la trigo locale (N-1, N, N+1)
        self.refresh_drawing(recalc=True, idx=index, new_pos=new_pos)

        # 3. Si vrai, reconstruit toutes les lignes du formulaire et le dessin
        if refresh:
            self.refresh()

    def _on_row_touch_wrapper(self, instance, touch, index):
        if not instance.collide_point(*touch.pos):
            return False  # Ne rien faire si le clic n’est pas dans la ligne
        if self.editing_index is not None and self.editing_index != index:
            #self.cancel_edit()
            self.edit_row(None)
            try:
                self.data_pos_to_raw(self.editing_index)
            except Exception as e:
                print(f"[Erreur validation] {e}")
        return self._on_row_touched(instance, touch, index)
    
    def _on_row_touched(self, instance, touch, idx):
        if instance.collide_point(*touch.pos):
            self.edit_row(idx)
        
    def edit_row(self, index):
        if self.editing_index != index:
            if index is None:
                self.editing_index = None
                #self.original_data = None
                self.original_entry = None
            else:
                self.editing_index = index
                #self.original_data = copy.deepcopy(self.points_part.entries[index].data)
                self.original_entry = copy.deepcopy(self.points_part.entries[index])
            self.refresh()

    def cancel_edit(self):
        index = self.editing_index
        if self.original_entry and index is not None:
            self.points_part.entries[index] = self.original_entry

        #if index is not None:
        #    self.points_part.update_entry_data(index)
        #else:
        #    self.points_part.update_entries_data()
        #self.editing_index = None
        self.edit_row(None)
        #self.refresh()

    def data_pos_to_raw(self, index):
        """🚀 VALIDATION LOCALE : Transfère les cotes IHM dans la mémoire vive (.raw)"""
        # 1. On remet la variable de blocage à False avant de reconstruire !
        self.disp_refresh_blocked = False

        entry = self.points_part.entries[index]
        if entry.data is None:
            return
            
        hor_base = entry.data.hor.val_base()
        vert_base = entry.data.vert.val_base()

        # 1. On applique les changements dans le dictionnaire de travail
        entry.raw["pos"] = [hor_base, vert_base]
        entry.modified_data = True

        # 2. On demande au PointManager de recalculer le voisinage géométrique en microns
        self.points_part.update_entry_data(index)

        # 3. On ferme la ligne d'édition (ZÉRO SAUVEGARDE SUR LE DISQUE ICI !)
        self.edit_row(None)

    def save_current_profile_to_json(self):
        """
        💾 ACTION OPÉRATEUR VOLONTAIRE : 
        Écrit concrètement l'état actuel de la mémoire vive sur le disque dur,
        et fige la nouvelle silhouette de référence dans le calque de fond rose.
        """
        # Appelle la méthode .save() du PointManager que nous avons écrite ensemble
        # (C'est elle qui écrit le JSON et synchronise le calque rose)
        self.points_part.save()  
        
        # On force un rafraîchissement global pour caler les calques à l'écran
        self.refresh(forced_disp=True)    

    def insert_point(self, index, entry_paste=None):
        """
        Insère un point après le point sélectionné (index + 1). (voir-> [add_entry()])
        - entry_paste==None : copie position depuis le point courant, sans forme.
        - entry_paste donné : copie position et forme depuis l'entrée spécifiée.
        """
        entry = copy.deepcopy(self.points_part.entries[index] if entry_paste is None else entry_paste)

        if entry.data is None:
            return
        hor = entry.data.hor.val_base()
        vert = entry.data.vert.val_base()
        if self.mirror_z:
            hor = -hor
        
        if entry_paste is None:
            self.points_part.add_entry(index, hor, vert)
        else:
            shape = entry.raw.get("shape", None)
            shape_label = entry.raw.get("shape_label", None)
            shape_params = entry.raw.get("shape_params", None)
            self.points_part.add_entry(index, hor, vert, shape, shape_label, shape_params)
        self.edit_row(index + 1)

    def delete_point(self, index):
        if index == 0:
            self.show_first_point_warning()
            return
        if 0 <= index < len(self.points_part.entries):
            del self.points_part.entries[index]
            self.points_part.save()
            #self.refresh()
            self.edit_row(None)

    # En tête
    def on_header_unit_click(self, key):
        """
        🎯 LE DÉCLENCHEUR DU POPUP CENTRALISÉ :
        Déduit la famille d'unité de la colonne cliquée, génère les options enrichies
        (avec long_name) pour le choix tactile, et orchestre la sauvegarde persistante.
        """
        from configurator.config import get_unit_type, get_all_units_for_type
        
        # 1. On extrait la configuration de la colonne depuis la matrice de la mère
        col_cfg = next((c for c in self.columns_config_list if c["key"] == key), None)
        if not col_cfg:
            return

        current_target = col_cfg["unit_type"] # ex: "unit_distance" ou "inch"

        # 2. Utilisation de vos fonctions globales sécurisées
        family_type = get_unit_type(current_target) or current_target
        
        # 🎯 ON ACTIVE LES DEUX FLAGS : Pour obtenir les paires (id, "label (Nom Long)")
        options = get_all_units_for_type(family_type, with_labels=True, with_long_names=True)

        # 3. Logique exécutée uniquement si l'opérateur clique sur "Valider"
        def on_unit_select(selected_uid):
            from configurator.config import SETTINGS, save_json
            
            # Si l'opérateur choisit 'default', on réassocie la famille globale ("unit_distance")
            if selected_uid == 'default':
                SETTINGS["axis"][key]["unit"] = family_type
            else:
                # Sinon on verrouille l'unité choisie en dur ('inch', 'mm', etc.)
                SETTINGS["axis"][key]["unit"] = selected_uid
                
            # Sauvegarde physique dans user_settings.json
            save_json()
            
            # 🔄 RECONSTRUCTION DE LA MATRICE : Recalcule immédiatement les nouveaux labels
            self.columns_config_list = self._build_columns_config()
            
            # Recalcul des valeurs de vos points CAO (conversion de cotes)
            self.points_part.update_entries_data()
            
            # Rafraîchissement complet de l'affichage de l'écran
            self.refresh(forced_disp=True)

        # 4. Déclenchement du Popup tactile
        # Si l'unité est celle par défaut, on passe None pour activer la case 'default'
        popup_current_unit = None if current_target == family_type else current_target
        self.open_unit_selection_popup(key, options, on_unit_select, unit_type=family_type, current_unit=popup_current_unit)

    def open_unit_selection_popup(self, key, options, on_select_callback, unit_type, current_unit=None):
        """
        Affiche un popup Kivy pour sélectionner une unité avec boutons en bas :
        Annuler | Valider
        Option 'Par défaut' ajoutée en haut de la liste des options.
        """

        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.togglebutton import ToggleButton
        from kivy.uix.button import Button

        # Ajout option "Par défaut" en tête
        full_options = [('default', Tr("default_in"))] + options

        popup_content = BoxLayout(orientation='vertical', spacing=10, padding=10, size_hint_y=None)
        popup_content.bind(minimum_height=popup_content.setter('height'))

        options_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        options_box.bind(minimum_height=options_box.setter('height'))

        toggle_group = f"unit_select_{key}"
        selected_unit = {'unit_id': current_unit if current_unit is not None else 'default'}

        def on_option_press(unit_id):
            def callback(instance):
                selected_unit['unit_id'] = unit_type if unit_id == 'default' else unit_id
            return callback

        for uid, label in full_options:
            btn = ToggleButton(
                text=label,
                group=toggle_group,
                size_hint_y=None,
                height=50,
                #background_normal='',  # nécessaire si tu veux changer la couleur background_color
                # background_down='...', # ici tu peux préciser une image ou couleur personnalisée
            )
            # Définir l’état initial du bouton sélectionné
            if (current_unit is None and uid == 'default') or (uid == current_unit):
                btn.state = 'down'

            btn.bind(on_press=on_option_press(uid))
            options_box.add_widget(btn)

        popup_content.add_widget(options_box)

        btn_box = BoxLayout(size_hint_y=None, height=50, spacing=10)
        btn_cancel = Button(text=Tr("cancel"))
        btn_validate = Button(text=Tr("validate"))

        def on_cancel(instance):
            popup.dismiss()

        def on_validate(instance):
            popup.dismiss()
            on_select_callback(selected_unit['unit_id'])

        btn_cancel.bind(on_press=on_cancel)
        btn_validate.bind(on_press=on_validate)

        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_validate)

        popup_content.add_widget(Separator(margin=10))
        popup_content.add_widget(btn_box)

        max_height = 800

        def update_popup_size(*args):
            h = min(popup_content.height + 150, max_height)
            popup.height = h

        popup_content.bind(height=update_popup_size)

        popup = Popup(
            title=TR("unit_selection_for_column"),
            content=popup_content,
            size_hint=(None, None),
            width=500,
            height=min(popup_content.height, max_height),  # initial
            auto_dismiss=False,
        )        

        popup.open()

    def show_first_point_warning(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=Tr("first_point_cannot_be_deleted")))

        btn = Button(text=TR("ok"), size_hint=(1, None), height=40)
        popup = Popup(title=Tr("deletion_not_allowed"),
                    content=content,
                    size_hint=(None, None),
                    size=(800, 400),
                    auto_dismiss=False)
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)

        popup.open()

    # Écran
    def screen_focused(self):
        """
        RÉVEIL INTERNE CAO : Appelée par le main.py quand la page prend le focus.
        Gère la synchronisation de ses propres onglets et de son tableau.
        """
        
        self.refresh()
        
        print("[PAGE CAO] Réveil et reconstruction autonome du tableau de points.")


Builder.load_file("part/draw_data.kv")