# part/shapes/shape_editor.py

import copy
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.popup import Popup
#from param_form import ParamForm  # ← import de ta classe ci-dessus
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.stencilview import StencilView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import Spinner
#from .base_shape import BaseShape  # on à aura besoin pour par ex: les listes de types, les valeurs par défaut, ...
from i18n import tr, Tr, TR  # La fonction de traduction importée tr>> tel que la traduction; Tr première lettre en majuscule; TR tous en majuscule
from .shape_manager import ShapeManager  # on à aura besoin pour par ex: les listes de types, les valeurs par défaut, ...
import part.shapes.shape_registry as sr

from kivy.clock import Clock



from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.metrics import dp


class ParamForm(BoxLayout):
    '''
    Boxe contenant le formulaire d'édition spécifique à forme_type ET forme_subtype,
    ou des boxes par défaut.
    '''
    def __init__(self, on_cancel, on_apply, on_copy, on_paste=None, shape_editor=None, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(30), padding=dp(5), **kwargs)

        self.shape_editor = shape_editor  # Lien vers ShapeEditor(): La class mère
        self.on_cancel = on_cancel
        self.on_apply = on_apply
        self.on_copy = on_copy
        self.on_paste = on_paste
        
        # === ZONE GAUCHE : Affichage graphique ===
        self.left_column = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=dp(6))

        # -- HEADER : faux spinners visibles --
        self.spinner_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30), spacing=dp(10)) #,padding=(dp(10), dp(10), dp(10), dp(10)))
        self.fake_spinner_type_btn = Button(text='Type', size_hint_x=1)
        self.fake_spinner_type_btn.bind(on_release=self.open_type_spinner)
        self.fake_spinner_subtype_btn = Button(text='Sous-type', size_hint_x=1)
        self.fake_spinner_subtype_btn.bind(on_release=self.open_subtype_spinner)
        self.spinner_row.add_widget(self.fake_spinner_type_btn)
        self.spinner_row.add_widget(self.fake_spinner_subtype_btn)
        # ~~ VRAIS spinners (hors UI, mais nécessaires pour les listes)
        self.spinner_type = Spinner(text='Type', values=[], size_hint=(None, None), size=(dp(150), dp(40)))
        self.spinner_subtype = Spinner(text='Sous-type', values=[], size_hint=(None, None), size=(dp(150), dp(40)))
        
        # -- Zone affichage dessin graphique --
        self.graphic_box = BoxLayout(orientation='vertical', size_hint_x=1, spacing=dp(0), padding=dp(0), size_hint_y=0.95)
        stencil = StencilView(size_hint=(1, 1))
        self.float_wrapper = FloatLayout()

        self.graphic_box.bind(
            size=lambda *_: setattr(self.float_wrapper, 'size', (self.graphic_box.width - 60, self.graphic_box.height - 60)),
            pos=lambda *_: setattr(self.float_wrapper, 'pos', (self.graphic_box.x + 30, self.graphic_box.y + 30)),
        )

        if hasattr(self.shape_editor.shape_form, "box_draw_shape"):
            draw_box = self.shape_editor.shape_form.box_draw_shape
            self.float_wrapper.add_widget(draw_box)
            self.float_wrapper.bind(pos=draw_box.setter('pos'), size=draw_box.setter('size'))
        else:
            self.float_wrapper.add_widget(Label(text="ERROR LOAD", size_hint_y=None, height=dp(80)))

        stencil.add_widget(self.float_wrapper)
        self.graphic_box.add_widget(stencil)

        # -- FOOTER --
        self.footer = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(32), spacing=dp(10))
        width_footer_btn = dp(80)

        self.btn_copy = Button(text=Tr("copy"), size_hint_x=None, width=width_footer_btn)
        self.btn_copy.bind(on_release=lambda *_: self.on_copy() if self.on_copy else None)

        self.btn_paste = Button(text=Tr("paste"), size_hint_x=None, width=width_footer_btn)
        self.btn_paste.bind(on_release=lambda *_: self.on_paste() if self.on_paste else None)

        self.btn_cancel = Button(text=Tr("cancel"), size_hint_x=None, width=width_footer_btn)
        self.btn_cancel.bind(on_release=lambda *_: self.on_cancel() if self.on_cancel else None)

        self.btn_apply = Button(text=TR("close"), size_hint_x=None, width=width_footer_btn)
        self.btn_apply.bind(on_release=lambda *_: self.on_apply() if self.on_apply else None)

        self.footer.add_widget(self.btn_copy)
        self.footer.add_widget(self.btn_paste)
        self.footer.add_widget(Widget())
        self.footer.add_widget(self.btn_cancel)
        self.footer.add_widget(self.btn_apply)

        # -- Assemblage final de la colonne gauche --
        self.left_column.add_widget(self.spinner_row)
        self.left_column.add_widget(self.graphic_box)
        self.left_column.add_widget(self.footer)
        self.add_widget(self.left_column)


        # === ZONE DROITE ===
        self.right_column = BoxLayout(orientation='vertical', size_hint_x=0.5, spacing=dp(15))
        
        # -- SCROLLVIEW qui contiendra le formulaire de configuration --
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True,do_scroll_y=True, bar_width=dp(10),)  # s'étend sur l'éespace disponible dans le parent
        self.scroll.bind(size=self.update_config_box_size) # màj en cas de changement
        wrapper =  BoxLayout(orientation='vertical', size_hint=(None, None))    # Box intérmédiaire pour le centrage
        wrapper.bind(size=self.update_wrapper_size)

        # Injecte directement la config_box si disponible (comme pour box_draw_shape)
        if hasattr(self.shape_editor.shape_form, "shape_config_box"):  # Rechercher si la fonction est accésible
            config_box = self.shape_editor.shape_form.shape_config_box()    # Taille selon widget transmis
            config_box.bind(size=self.update_config_box_size) # Suivre les changements de taille
        else:
            config_box = Label(text="(Aucune configuration disponible)",size_hint_y=None,height=dp(40)) #Hauteur Fixe
        
        wrapper.add_widget(config_box)
        self.scroll.add_widget(wrapper)

        # -- Assemblage final de la colonne droite --
        self.right_column.add_widget(self.scroll)
        self.add_widget(self.right_column)
        

    def inject_shape_config(self, config_box=None):
        """Injecte un formulaire spécifique dans la zone centrale (ou un placeholder si None)."""

        # Supprimer l'ancien widget
        wrapper =  self.scroll.children[0]
        wrapper.clear_widgets()

        if config_box is None:
            # Par défaut, afficher un message simple
            add_config_box = Label(
                text="(Aucune configuration disponible)",
                size_hint_y=None,
                height=dp(40)
            )
        else:
            add_config_box = config_box

        wrapper.add_widget(add_config_box)
        self.update_config_box_size()
        add_config_box.bind(size=self.update_config_box_size) # Suivre les changements de taille futurs

    def update_config_box_size(self, *args):
        """Met à jour les paddings en fonction de la taille de config_box par rapport à scroll."""
        
        # Sécurité : éviter les erreurs si aucun widget n’est encore ajouté
        if not self.scroll.children:
            return
        wrapper = self.scroll.children[0]
        if not wrapper.children:
            wrapper.padding = (0, 0, 0, 0)
            return
        
        config_box = wrapper.children[0]

        # màj de la taille de config_box      
        if hasattr(config_box, 'update_size_from_parent'):  # Appelle la méthode de mise à jour si elle existe
            config_box.update_size_from_parent(self.scroll.size)
                    
        # Récupère la taille de config_box et de scroll
        scroll_w , scroll_h = self.scroll.size
        c_box_w , c_box_h = wrapper.children[0].size

        # Calculer la différence de hauteur disponible
        EPSILON = 2  # Tolérance anti-scrollbar
        w_disp = scroll_w - c_box_w - EPSILON
        h_disp = scroll_h - c_box_h - EPSILON
 
        # Si la différence est positive, on peut appliquer du padding
        w_padd = max(0, w_disp/2)
        h_padd = max(0, h_disp/2)
       
        # Appliquer les nouveaux: tailles et paddings
        self.update_wrapper_size(wrapper, 0)
        wrapper.padding = (w_padd, h_padd, w_padd, h_padd)
    def update_wrapper_size(self, instance, value):
        w_scro, h_scro = self.scroll.size
        w_box, h_box = instance.children[0].size
        instance.size = (max(w_scro, w_box), max(h_scro, h_box))

    def open_type_spinner(self, instance_btn):
        def set_selected_type(value):
            #new_type = (value, self.spinner_subtype.text) # En tuple avec les valeurs des deux spinner
            val_to_send = value if value != "aucune terminaison" else ""
            new_type = (val_to_send, "") # En tuple avec les valeurs des deux spinner
            
            # Comparer au type de la forme actuellement utilisée
            comparator = self.shape_editor.shape_form.shape_type
            if not isinstance(comparator , (list, tuple)):  # (comparator == None)
                send_to_type = [val_to_send, ""]    # C'est déjà un fallbak, ne pas en créer de nouveau
                comparator = ""
            else:
                send_to_type = [val_to_send, None]    # Ce n'est pas un fallbak, créer un fallbak
                comparator = comparator[0]

            if new_type[0] != comparator: #on contrôle que c'est bien un type/subtype différent de celui de la forme
                self.shape_editor.shape_type_changed(send_to_type) # on déclanche un changement de type

                # Auto-ouvrir le sous-type uniquement si ce n'est pas "aucune terminaison"
                if val_to_send != "":
                    self.open_subtype_spinner(self.fake_spinner_subtype_btn)  # on simule le clic sur le bouton du sous-type

        pos = instance_btn.to_window(*instance_btn.pos)
        test_pos = (pos[0], pos[1])
        self.show_floating_spinner(self.spinner_type, test_pos, set_selected_type, ref_btn=instance_btn)

    def open_subtype_spinner(self, instance_btn):
        def set_selected_subtype(value):
            new_type = (self.spinner_type.text, value)
            if new_type != self.shape_editor.shape_form.shape_type: #on contrôle que c'est bien un type/subtype différent de celui de la forme
                self.shape_editor.shape_type_changed(new_type) # comme open_type_spinner

        pos = instance_btn.to_window(*instance_btn.pos)
        self.show_floating_spinner(self.spinner_subtype, pos, set_selected_subtype, ref_btn=instance_btn)

    def show_floating_spinner(self, spinner_instance, pos, callback, ref_btn=None):
        overlay = FloatLayout(size=Window.size)
        values = spinner_instance.values

        item_height = dp(40)
        item_spacing = dp(4)
        total_height = (item_height + item_spacing) * len(values) - item_spacing

        # Largeur = largeur du bouton déclencheur (ou défaut)
        width = ref_btn.width if ref_btn else dp(150)

        # Ajuste la position Y pour afficher *en dessous* du bouton
        btn_x, btn_y = pos
        offset_extra = dp(20)  # ~1/2 de la hauteur bouton (40dp)
        n_btn_y = btn_y - total_height + item_height - offset_extra
        n_btn_x = btn_x + offset_extra
        box_pos = (n_btn_x, n_btn_y if n_btn_y > 0 else 0)

        # Zone clickable transparente derrière les boutons (fermeture si clic à côté)
        def on_background_touch(instance, touch):
            if not box.collide_point(*touch.pos):
                Window.remove_widget(overlay)
                return True
            return False

        background = Button(size=overlay.size, opacity=0)
        background.bind(on_touch_down=on_background_touch)
        overlay.add_widget(background)

        # Conteneur des options
        box = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(width, total_height),
            pos=box_pos,
            spacing=item_spacing
        )

        # Créer les boutons
        for val in values:
            btn = ToggleButton(
                text=val,
                size_hint_y=None,
                height=item_height,
                group="popup_selector"  # exclusif
            )
            # Active automatiquement le bouton si c'est la valeur actuelle
            if ref_btn and val == ref_btn.text:
                btn.state = 'down'

            def on_select(instance, val=val):
                callback(val)
                Window.remove_widget(overlay)
            btn.bind(on_release=on_select)
            box.add_widget(btn)

        overlay.add_widget(box)
        Window.add_widget(overlay)

    def reload_graphic_box(self):
        """Rafraîchit dynamiquement le dessin dans la partie graphique (à gauche)."""
        self.float_wrapper.clear_widgets()
        if hasattr(self.shape_editor.shape_form, "box_draw_shape"):
            draw_box = self.shape_editor.shape_form.box_draw_shape
            self.float_wrapper.add_widget(draw_box)

            self.float_wrapper.bind(pos=draw_box.setter('pos'), size=draw_box.setter('size'))
            
            draw_box.pos = self.float_wrapper.pos
            draw_box.size = self.float_wrapper.size
        else:
            self.float_wrapper.add_widget(Label(text="ERROR LOAD", ize_hint_y=None, height=dp(80)))


class ShapeEditor(Popup):
    def __init__(self, point_b, prev_pnt_raw, next_pnt_raw, copied_shape_data, mirror_z= False, on_done=None, **kwargs):
        '''
        Gère le formulaire de définition et d'édition des terminaisons de point:
            - premet de sélectionner une forme à appliquer (en deux étapes: type et sub_type)
            - affiche le formulaire d'édition et éventuellement un graphique pour faciliter la définition des valeurs
        '''
        super().__init__(title="Édition de forme", size_hint=(0.95, 0.9), auto_dismiss=False, **kwargs)

        self.point_b = point_b
        self.mirror_z = mirror_z
        self.copied_shape_data = copied_shape_data  # variable avec effet de bord pour copier/coller
        self.on_done = on_done  # callback à appeler quand l'édition est finie
        self.original_data = copy.deepcopy(self.point_b)   # Copipie du point avant modifications (pour btn_Annuler)
        
        a_pos = prev_pnt_raw.get("pos", None)
        b_pos = point_b.raw.get("pos", None)
        c_pos = next_pnt_raw.get("pos", None)
        shape_type = point_b.raw.get("shape", None)
        shape_params = point_b.raw.get("shape_params", {})
        
        print(f"DEBUG_ShapeEditor_init: params{shape_params}")


        self.shape_manager = ShapeManager()    # initialise ShapeManager()
        self.shape_form = self.shape_manager.create_shape(  # initialise la forme actuellement sélectionnée
            pos_a=a_pos, entry_b=point_b, pos_c=c_pos,
            shape_typ=shape_type, shape_params = shape_params, mirror_z= mirror_z
            )
        
        self.form = ParamForm(
            on_cancel=self.cancel,
            on_apply=self.apply,
            on_copy=self.on_copy_shape,
            on_paste=self.on_paste_shape,
            # supprimé: data_form=self.shape_form,
            shape_editor=self
        )

        self.reload_list_spinner_shape(shape_type)
        #self.load_from_point(point_b.raw)
        self.content = self.form

    def load_from_point(self, raw):
        pos = raw.get("pos", [0, 0])
        shape = raw.get("shape")
        params = raw.get("shape_params", {})

        if isinstance(shape, (list, tuple)) and len(shape) == 2 and shape[0] is not None:
            type_str, subtype_str = map(str, shape)
        else:
            type_str, subtype_str = "not shape", ""

        # sous formulaire de configuration pour la forme sélect.
        interface = self.form.shape_config_interface
        if interface:
            #interface.set_spinner_selection(type_str, subtype_str)
            interface.set_spinner_options(type_str, subtype_str)
            self.form.preview_area.text = f"Aperçu: {type_str} / {subtype_str}"
        else:
            # Formulaire injecté — il faut voir s’il expose une interface équivalente
            # TODO: Ici la logique à appliquer si c'est un sous-formulaire fourni par une class de forme
            pass

    def apply(self):
        # Enregistre les modifications dans point_raw depuis la forme
        #if hasattr(self.shape_form,"update_params"):
        #    self.shape_form.update_params(self.shape_form.params)
        print(f"DEBUG_ShapeEditor_apply: params{self.shape_form.params} | {self.point_b.raw.get("shape_params", {})}")

        # TODO : extraire les vraies valeurs depuis le formulaire (quand c’est dynamique)
            # --> A compléter / modifier / valider
        self.dismiss()
        if self.on_done:
            self.on_done()

    def cancel(self):
        # Rétablir les anciennes valeurs
        self.point_b.raw["shape"] = copy.deepcopy(self.original_data.raw.get("shape"))
        self.point_b.raw["shape_label"] = copy.deepcopy(self.original_data.raw.get("shape_label"))
        self.point_b.raw["shape_params"] = copy.deepcopy(self.original_data.raw.get("shape_params"))

        # Recharger la forme complètement
        self.shape_type_changed(
            new_type=self.point_b.raw.get("shape"),
            shape_params=self.point_b.raw.get("shape_params"),
            mirror_z=self.mirror_z
        )
        
        #self.apply()   # Fermeture automatique (+màj)

    def on_copy_shape(self, *args):
        self.copied_shape_data["shape"] = copy.deepcopy(self.point_b.raw.get("shape"))
        self.copied_shape_data["shape_label"] = copy.deepcopy(self.point_b.raw.get("shape_label"))
        self.copied_shape_data["shape_params"] = copy.deepcopy(self.point_b.raw.get("shape_params"))

    def on_paste_shape(self, *args):
        type_changed = False
        shape = self.copied_shape_data["shape"]
        if shape is None:
            return  # Rien à coller
    
        shape_label = self.copied_shape_data["shape_label"]
        shape_params = self.copied_shape_data["shape_params"]
        if shape:
            if shape != self.point_b.raw["shape"]:
                self.point_b.raw["shape"] = copy.deepcopy(shape)
                type_changed = True
            self.point_b.raw["shape_label"] = copy.deepcopy(shape_label)
            self.point_b.raw["shape_params"] = copy.deepcopy(shape_params)
            # Recalcul / rafraîchissement visuel si nécessaire
        if type_changed:
            self.shape_type_changed(shape, shape_params)
        else:
            #self.load_from_point(self.point_b.raw)
            self.shape_type_changed(shape, shape_params)

    def shape_type_changed(self, new_type, shape_params={}, mirror_z=None):
        a_pos = self.shape_manager.shape_form_link.point_a
        c_pos = self.shape_manager.shape_form_link.point_c
        point_b = self.point_b
        mirror_z = mirror_z if mirror_z is not None else self.mirror_z

        # 1. Recréer la forme avec les nouvelles infos
            # Ps: Avec shape_params= {} on réinitialise la forme avec ses paramètres par défauts
        #shape_type = new_type if new_type[0] != "" else None
        if not isinstance(new_type, (tuple, list)):
            new_type = ["", ""]     # A l'initialisation new_type peux être à None, donc quand même créer un fallbak vièrge
            shape_type = None
        elif new_type[1] == "" :    # On garde le fallback actuel
            shape_type = False
        elif new_type[1] == None :  # On créait un nouveau fallback vièrge
            shape_type = None
            new_type[1] = "" # Préparation pour les spinner (voir: point 4)
        else:                       # On créait la forme correspondante
            shape_type = new_type

        if shape_type != False:
            self.shape_form = self.shape_manager.create_shape(
                pos_a=a_pos, entry_b=point_b, pos_c=c_pos,
                shape_typ=shape_type, shape_params=shape_params, mirror_z=mirror_z
            )

            # 2. Recharger tout
            #self.load_from_point(self.point_b.raw)  # recharge .box_draw_shape etc
            self.form.reload_graphic_box()

            # 3. Recharger la box de config (dans la colonne de droite)
            if hasattr(self.shape_form, "shape_config_box"):
                config_box = self.shape_form.shape_config_box()
                self.form.inject_shape_config(config_box)
            else:
                self.form.inject_shape_config(None)
                
        # 4. Mise à jour des spinners
        self.reload_list_spinner_shape(new_type)

    def reload_list_spinner_shape(self, new_type):
        """
        Met à jour les valeurs des spinners en fonction du type donné,
        et ajuste les textes affichés dans les boutons visibles.
        """
        if new_type is None:
            new_type = ["",""]
        type_shape, subtype_shape = new_type
        type_fake = type_shape
        subtype_fake = subtype_shape

        type_list = self.shape_manager.get_all_types()

        if type_shape in type_list:
            subtypes_list = self.shape_manager.get_subtypes_for(type_shape)
            if subtype_shape not in subtypes_list:
                subtype_fake = "select-subtype"
                subtype_shape = ""
        else:
            type_fake = "aucune terminaison"
            type_shape = ""
            subtypes_list = []
            subtype_fake = "- . -"
            subtype_shape = ""

        # Mise à jour ds spinners type et subtype
        self.form.spinner_type.values = ["aucune terminaison"] + type_list
        self.form.spinner_type.text = type_shape
        self.form.spinner_subtype.values = subtypes_list
        self.form.spinner_subtype.text = subtype_shape

        # Mise à jour des boutons visibles
        self.form.fake_spinner_type_btn.text = type_fake
        self.form.fake_spinner_subtype_btn.text = subtype_fake



