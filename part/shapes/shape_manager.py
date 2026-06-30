# part/shapes/shape_manager.py

from .base_shape import BaseShape
import part.shapes.shape_registry as sr

class ShapeManager:
    def __init__(self):
        self.shape_registry_list = sr.shape_templates

    #def create_shape(self, pos_a, entry_b, pos_c, shape_typ=None, params=None, mirror_z=False):
    def create_shape(self, pos_a, entry_b, pos_c, shape_typ=None, shape_params={}, mirror_z=False):
        """
        Crée une forme selon le type et sous-type, et retourne l'objet de la forme.
        """
        #màj de entry_b >> raw >> "shape" et "shape_params"
        entry_b.raw["shape"] = shape_typ
        entry_b.raw["shape_params"] = shape_params

        # Si aucun type de forme n'est spécifié, on retourne une forme vide (BaseShape)  
        if shape_typ is None:     
            self.shape_form_link = BaseShape(
                point_a=pos_a, entry_b=entry_b, point_c=pos_c, 
                mirror_z=mirror_z, registry=self.shape_registry_list
            )
            self.shape_form_link.satus = 0
            self.shape_form_link.shape_type = [None, {}]
            return self.shape_form_link
        
        shape_grp1, shape_grp2 = shape_typ  # Ex : ('filet_gorge', 'ISO')

        # Vérification de la présence du groupe dans sr.shape_templates
        shape_info = self.shape_registry_list.get(shape_grp1)
        if shape_info is None:
            self.shape_form_link = BaseShape(
                point_a=pos_a, entry_b=entry_b, point_c=pos_c, 
                mirror_z=mirror_z, registry=self.shape_registry_list
            )
            self.shape_form_link.satus = 1
            self.shape_form_link.shape_type = [None, {}]
            print(f"create_shape: Le groupe de forme {shape_grp1} est inexistant ou incomplet.")
            return self.shape_form_link

        # Vérification de la présence du sous-type
        subtype_info = shape_info.get('subtypes', {}).get(shape_grp2)
        if subtype_info is None:
            self.shape_form_link = BaseShape(
                point_a=pos_a, entry_b=entry_b, point_c=pos_c, 
                mirror_z=mirror_z, registry=self.shape_registry_list
            )
            
            self.shape_form_link.satus = 2
            self.shape_form_link.shape_type = [shape_grp1, {}]
            print(f"create_shape: Le sous-type {shape_grp2} n'existe pas pour le groupe {shape_grp1}.")
            return self.shape_form_link

        # Récupération de la classe de la forme et création de l'objet
        shape_class = subtype_info.get('class')
        if shape_class is None:
            self.shape_form_link = BaseShape(
                point_a=pos_a, entry_b=entry_b, point_c=pos_c, 
                mirror_z=mirror_z, registry=self.shape_registry_list
            )            
            self.shape_form_link.satus = 3
            self.shape_form_link.shape_type = [shape_grp1, shape_grp2]
            print(f"create_shape: Class pour {shape_grp1}/{shape_grp2} : invalide ou introuvable.")
            return self.shape_form_link
        
        # Création de l'instance de la forme avec ou sans paramètres supplémentaires
        self.shape_form_link = shape_class(
            point_a=pos_a, entry_b=entry_b, point_c=pos_c, 
            mirror_z=mirror_z   #, registry=self.shape_registry_list
        )
        self.shape_form_link.satus = 95
        self.shape_form_link.shape_type = [shape_grp1, shape_grp2]
        return self.shape_form_link

    def get_all_types(self):
        return sr.get_all_shape_type()

    def get_subtypes_for(self, shape_type):
        return sr.get_all_shape_subtype(shape_type)

'''
    @classmethod
    def register(cls, type_name, subtype_name, shape_class):
        if type_name not in cls._registry:
            cls._registry[type_name] = {}
        cls._registry[type_name][subtype_name] = shape_class

    @classmethod
    def get_all_types(cls):
        return list(cls._registry.keys())

    @classmethod
    def get_all_subtypes(cls, type_name):
        return list(cls._registry.get(type_name, {}).keys())

    @classmethod
    def get_shape_class(cls, type_name, subtype_name):
        return cls._registry.get(type_name, {}).get(subtype_name)
'''