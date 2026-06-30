#   draw_tool/   draw_data.py

from kivy.app import App
from kivy.properties import ListProperty
import math
import copy
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup

from common_widgets import LabeledCell, InputCell, MyLabel, Separator
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from config import AXIS_CONFIG
from part.draw_tool.popup_segment import SegmentPopupContent, PartManagerPopup
from part.draw_pnt_manager import PointValue, PointData, ColumnDefaultSpec
from part.shapes.shape_editor import ShapeEditor    # part/shapes/shape_editor.py

# Configuration globale des colonnes
COL_WIDTHS = [240, 240, 240, 240, 240, 180, 480]
COL_PROPORTIONS = [1, 1, 1, 1, 1, 0.75, 2]
COL_SPACING = 5
COL_TOTAL_WIDTH = sum(COL_WIDTHS) + COL_SPACING * (len(COL_WIDTHS) - 1)


class HeaderRow(BoxLayout):
    def __init__(self, on_unit_click=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.spacing = COL_SPACING
        self.size_hint_y = None
        self.size_hint_x = 1
        self.height = 45 + COL_SPACING * 2
        self.padding = [0, 0, 0, COL_SPACING*2]  # 10 pixels en bas pour le décoller

        # Map colonne -> clé (doit correspondre à ColumnDefaultSpec)
        self.col_keys = ['vert', 'hor', 'vert2', 'hor2', 'l', 'alpha', 'forme']

        # Génère dynamiquement les titres depuis AXIS_CONFIG ou utilise une fallback
        titles = []
        for key in self.col_keys:
            if key == "forme":
                titles.append(Tr("shape"))  # Traduction pour la colonne forme
            else:
                title = AXIS_CONFIG.get(key, {}).get("screen", key)
                titles.append(title)

        # Création des cellules d’en-tête
        for i, (title, key) in enumerate(zip(titles, self.col_keys)):
            cell_class = LabeledCell if key == 'forme' else HeaderCell
            kwargs_cell = {
                'text': title,
                'halign': 'center',
                'bold': True,
                'bg_color': (0.8, 0.8, 0.8, 1),
                'text_color': (0, 0, 0, 1),
                'size_hint_x': COL_PROPORTIONS[i],
                'width': None,
            }

            # Pour HeaderCell : ajoute le `key` et `on_click`
            if key != 'forme':
                kwargs_cell.update({'key': key, 'on_click': on_unit_click})

            lbl = cell_class(**kwargs_cell)
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
                type_str, subtype_str = map(str, shape)
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
        input_row = BoxLayout(orientation='horizontal', spacing=COL_SPACING, size_hint_y=None, size_hint_x = 1, height=60)

        # Les clés correspondantes à chaque PointValue dans PointData
        editable_keys = ['vert', 'hor', 'vert2', 'hor2', 'l', 'alpha']
        all_keys = editable_keys + ['forme']  # ← Tu peux remplacer 'forme' si tu l’utilises

        for i, key in enumerate(all_keys):
            if key == 'forme':
                shape = self.entry.raw.get("shape", None)
                if self.index == 0 or self.index + 1 >= len(self.parent_editor.points_part.entries):
                    val = "- pas possible"
                elif isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
                    type_str, subtype_str = map(str, shape)
                    val_def = f"{type_str} / {subtype_str}"
                    val = self.entry.raw.get("shape_label") or val_def
                else:
                    val = tr("no_shape")

                self.inpf = InputCell(text=str(val), status=0, halign='left', size_hint_x=COL_PROPORTIONS[i], width=None)  #width=COL_WIDTHS[i]
                if self.index != 0:
                    self.inpf.bind(focus=lambda inst, foc: self.open_shape_editor(inst, foc))
                input_row.add_widget(self.inpf)
                continue

            # Accès à la valeur formatée pour l'édition
            pv: PointValue = getattr(self.entry.data, key)
            formatted_val = pv.val_formatted(with_unit=True)

            # Création du champ modifiable
            inp = InputCell(text=formatted_val, status=0, size_hint_x=COL_PROPORTIONS[i], width=None)  #width=COL_WIDTHS[i]
            if key == 'l' and self.index != 0:
                inp.bind(focus=lambda inst, foc: self.on_focus_segment(inst, foc, 'l'))
            elif key == 'alpha' and self.index != 0:
                inp.bind(focus=lambda inst, foc: self.on_focus_segment(inst, foc, 'alpha'))
            else:
                inp.bind(focus=self.on_input_focus(key))
                inp.bind(text=self.on_input_changed(key))

            self.inputs[key] = inp
            input_row.add_widget(inp)

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
                self.refresh_inputs(key, forced=refresh_text)

        except ValueError:
            instance.foreground_color = (1, 0, 0, 1)  # Erreur = rouge

    def on_focus_segment(self, instance, focused, key):
        if not focused or getattr(self, 'popup_open', False):
            return

        self.popup_open = True
        self.display_blocked = True
        self.focus_key = key  # ← 'l' ou 'alpha'

        popup_content = SegmentPopupContent(
            data=copy.deepcopy(self.entry.data),
            key_changed=self.key_changed,
            on_confirm=self.on_segment_popup_confirm,
            key_target=key
        )

        popup = Popup(
            title=f"{TR("segment_config_title")} {key.upper()}",
            content=popup_content,
            size_hint=(None, None),
            size=(800, 900),
            auto_dismiss=False
        )
        popup_content.parent_popup = popup

        def on_close(*args):
            self.popup_open = False
            self.display_blocked = False
            self.focus_key = None

        popup.bind(on_dismiss=on_close)
        popup.open()
    
    def on_input_focus(self, key):
        def callback(instance, value):
            self.selct_input_focus(key, value, instance)
        return callback
    
    def selct_input_focus(self, key, value, instance):
        if value:
            # Gagne le focus : bloquer le refresh
            self.display_blocked = True
            self.focus_key = key
        else:
            # Perd le focus : déblocage possible
            self.display_blocked = False
            self.focus_key = None

            # Remettre le formatage correct après édition
            if key in self.inputs:
                pv = getattr(self.entry.data, key)
                self.inputs[key].text = pv.val_formatted(with_unit=False)

    def open_shape_editor(self, instance, focused):    
        '''
        Ouvre le formulaire de configuration de la terminaison à appliquer sur ce point

        ShapeEditor(arg: )
            - point_raw:     PointEntry:   Le point sur lequel travailler (contient toutes les informations actuelles et futures)
            - prev_pnt_raw:  PointEntry[raw]   Le point précédent pour définir le segment arrivant à ce point
            - next_pnt_raw:  PointEntry[raw]   Le point suivant pour définir le segment partant à ce point
            - copied_shape_data: PointEntry[raw] Comme pointeur pour le copier/coller
            - on_done :         Fonction de callback
        '''
        if not focused or getattr(self, 'popup_open', False):
            return
        self.popup_open = True 

        prev_pnt_raw = self.parent_editor.points_part.entries[self.index - 1].raw if self.index > 0 else None
        next_pnt_raw = self.parent_editor.points_part.entries[self.index + 1].raw if self.index + 1 < len(self.parent_editor.points_part.entries) else None  # Point suivant sécurisé
        if prev_pnt_raw is None or next_pnt_raw is None:
            print("Création de terminaison impossible")
            return
        
        editor = ShapeEditor(
            point_b=self.entry,
            prev_pnt_raw=prev_pnt_raw,  # Point précédent
            next_pnt_raw=next_pnt_raw,  # Point suivant
            copied_shape_data=self.parent_editor.copied_shape,  # Presse-papier partagé
            mirror_z=self.parent_editor.mirror_z,
            on_done=self.shape_edit_done  # Callback
        )

        def on_close_shape(*args):
            self.popup_open = False
            shape = self.entry.raw.get("shape", None)
            if isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
                type_str, subtype_str = map(str, shape)
                val_def = f"{type_str} / {subtype_str}"
                val = self.entry.raw.get("shape_label") or val_def
            else:
                val = tr("no_shape")
            self.inpf.text=str(val)        


        editor.bind(on_dismiss=on_close_shape)
        editor.open()
        
    def shape_edit_done(self):
        ''' Callback à la fermeture de ShapeEditor()'''
        self.refresh_shape_cell()
        # TODO: Contrôler si à completter

#    def validate(self, *args):
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
                input_cell.foreground_color = (1, 0, 0, 1)
            else:
                input_cell.foreground_color = (0.3, 0.3, 0.3, 1)

            if (key == exclude_key or key == self.focus_key) and not forced:
                continue  # Ne pas toucher à l'input en cours d'édition, sauf si c'est forced

            pv: PointValue = getattr(self.entry.data, key)
            input_cell.text = pv.val_formatted(with_unit=False)
    
    def refresh_shape_cell(self):
        if "forme" in self.inputs:
            shape = self.entry.raw.get("shape")
            shape_label = self.entry.raw.get("shape_label")

            if isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
                type_str, subtype_str = map(str, shape)
                val_def = f"{type_str} / {subtype_str}"
                val = shape_label or val_def
            else:
                val = tr("no_shape")

            self.inputs["forme"].text = val

    def refresh_profil_segments(self, index, large=False):
        self.parent_editor.points_part.prof_seg_pnt_recompute(index, changed_pos=large)
    
class PointDrawEditor(BoxLayout):
    def __init__(self, part_points, **kwargs):
        super().__init__(**kwargs)
        self.points_part = part_points  # class PointManager()
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = COL_SPACING
        
        self.mirror_z = False
        self.editing_index = None
        self.copied_entry = None    # ← copie de PointEntry (pour copier/coller)
        self.copied_shape = {"shape": None, "shape_label": None, "shape_params": {}}    # ← copie de shape et shape_params (pour copier/coller uniquement la terminaison)       
        #self.original_data = None   # ← copie de PointData avant édition pour comparaison
        self.original_entry = None   # ← copie de PointEntry avant édition pour comparaison et UNDO:
        self.disp_refresh_blocked = False

        '''Et remplacer ceci:
        self.points_part.load(load_data=True)  # Charge/recharge les points depuis le .json et les metent à jour avec load_data
         par:'''
        self.points_part.data_loaded=True
        self.points_part.update_entries_data()



        self.display_rows = []  # list des lignes affichées

        # Top bar with toggle button
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=80, width = COL_TOTAL_WIDTH, spacing= 5)

        self.toggle_mirror = ToggleButton(text=f"{Tr("mirror")} Z: {TR("off")}", state='normal', size_hint=(None,None), height=80, width = COL_TOTAL_WIDTH / 4, pos_hint={'center_y': 0.5})
        self.toggle_mirror.bind(on_press=self.on_toggle_mirror)

        part_name_txt = self.points_part.get_part_name()
        self.part_name_lbl = LabeledCell(text=part_name_txt, halign='center', bold=True,
                            bg_color=(0.4, 0.6, 0.4, 0.5),
                            #text_color=(0, 0, 0, 1),
                            height=60,
                            font_size = 48,
                            width = COL_TOTAL_WIDTH / 4,
                            #size_hint_x=COL_PROPORTIONS[i], width=None),
                            #on_click=self.open_part_manager_popup 
                            on_click=self.open_part_popup
                        )

        top_bar.add_widget(self.part_name_lbl)
        top_bar.add_widget(Widget())
        top_bar.add_widget(self.toggle_mirror)
        top_bar.add_widget(Widget())
        self.add_widget(top_bar)

        self.add_widget(HeaderRow(on_unit_click=self.on_header_unit_click))

        self.scroll = ScrollView(size_hint=(1, 1))
        self.display_rows = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.display_rows.bind(minimum_height=self.display_rows.setter('height'))
        self.scroll.add_widget(self.display_rows)
        self.add_widget(self.scroll)

        self.refresh()

    def __del__(self):
        """Ferme l'éditeur et désactive le chargement des données"""
        #print("Fermeture de l'éditeur")
        self.points_part.data_loaded = False  # Désactive le chargement des données à la fermeture

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
        def part_update(id_part=None, save_last= False, reload_json = False):
            """
            Met à jour ou change la pièce active :
            - id_part : change de pièce si précisé
            - save_last : sauvegarde la pièce courante avant de changer
            - reload_json : recharge les points depuis le JSON sinon recalcule depuis raw
            """
                
            # 0. Vérifie la validité de l'index
            index = self.points_part.storage.part_id_actif if id_part is None else id_part
            all_names = self.points_part.get_part_all_names()
            if not (0 <= index < len(all_names)):
                print(f"[Erreur] Index de pièce invalide : {index}")
                return

            # 1. Sauvegarde la pièce courante (points + nom si modifié)
            if save_last:
                self.save_points_to_data()  # ← déjà existant
                self.points_part.commit_part_names()  # ← si noms modifiés

            # 2. Change l'index actif dans le stockage
            self.points_part.storage.set_selected_index(index)

            # 3. Recharge les points de la nouvelle pièce
            if reload_json:
                self.points_part.load(load_data=True)
            else:
                self.points_part.update_entries_data()  # recalculer tous les points (depuis leur PointEntry.raw)

            # 4. Réinitialise l'état local
            self.editing_index = None   # si un point et en édition on sort du mode édition (sans enregistrer).
            #self.original_data = None   # ré-initialise pour la prochainne édition d'un point
            self.original_entry = None

            # 5. Met à jour le nom affiché de la pièce
            self.part_name_lbl.text = self.points_part.get_part_name()

            # 6. Rafraîchit l'affichage
            self.refresh()
        
        # 🆕 Met à jour le label à la fermeture, même sans clic
        def on_popup_dismiss(*_):
            self.part_name_lbl.text = self.points_part.get_part_name()

        popup = PartManagerPopup(manager=self.points_part, refresh_callback=part_update)
        popup.bind(on_dismiss=on_popup_dismiss)

        popup.open()

    def refresh(self, forced_disp = False):
        # Appel au contrôleur principal pour notifier un changement
        App.get_running_app().refresh_propage("draw_editor")

        # Met à jour l'affichage texte uniquement si pas en édition
        if forced_disp or self.disp_refresh_blocked != True:
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

    def update_row_data(self, index, new_hor, new_vert, refresh=True):
        # Créé un nouveau pos en unité de base
        new_pos = [int(round(new_hor)), int(round(new_vert))]

        entry = self.points_part.entries[index]
        prev_data = self.points_part.entries[index - 1].data if index > 0 else None
        next_data = self.points_part.entries[index + 1].data if index + 1 < len(self.points_part.entries) else None
        prev_pos = [prev_data.hor.val_base(), prev_data.vert.val_base()] if prev_data else None
        next_pos = [next_data.hor.val_base(), next_data.vert.val_base()] if next_data else None
        
        # Mets à jour .data uniquement, pas .raw
        entry.data.recompute(pos=new_pos, prev_pos=prev_pos)
        if next_pos:
            self.points_part.entries[index + 1].data.recompute(pos=next_pos, prev_pos=new_pos)

        # Si vrai reconstruit toutes les linges du formulaire
        if refresh:
            self.refresh()

    def _on_row_touch_wrapper(self, instance, touch, index):
        if not instance.collide_point(*touch.pos):
            return False  # Ne rien faire si le clic n’est pas dans la ligne
        if self.editing_index is not None and self.editing_index != index:
            #self.cancel_edit()
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
        #self.refresh()
        self.edit_row(None)

    def data_pos_to_raw(self, index):
        entry = self.points_part.entries[index]
        if entry.data is None:
            return
        # Conversion des valeurs affichées vers valeurs à sauver
        hor_base = entry.data.hor.val_base()
        vert_base = entry.data.vert.val_base()
        if self.mirror_z:
            hor_base = -hor_base

        entry.raw["pos"] = [hor_base, vert_base]
        entry.modified_data = True

        self.save_points_to_data()
        self.edit_row(None)

    def save_points_to_data(self):
        # Mets à jour la pièce dans le fichier
        self.points_part.save()      

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
        unit_type, current_unit = self.points_part.unit_spec.get_unit(key)
        
        spec = self.points_part.unit_spec.unit_map.get(key).unit_id # Accéder directement au `unit_map` pour obtenir la clé
        options = self.points_part.get_units_for_type(unit_type, with_labels=True)

        def on_unit_select(unit_id):
            self.points_part.unit_spec.set_unit(key, unit_id)
            self.points_part.update_entries_data()  # ← recalcul les valeurs avec les nouvelles unités
            self.refresh(forced_disp=True)

        self.open_unit_selection_popup(key, options, on_unit_select, current_unit=spec)

    def open_unit_selection_popup(self, key, options, on_select_callback, current_unit=None):
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
                selected_unit['unit_id'] = None if unit_id == 'default' else unit_id
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
