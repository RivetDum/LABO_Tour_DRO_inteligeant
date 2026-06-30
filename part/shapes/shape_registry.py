# part/shapes/shape_registry.py

from .thread_relief_iso import ThreadReliefISOShape
from .round_corner import RoundedCornerShape, RoundedShape
from .chamfer import ChamferShape

shape_templates = {
    'standard':{
        'name_txt': 'Simple',
        'subtypes': {
            'Chanfrein': {
                'class': ChamferShape,
                'plugin_id': None
            },
            'Congé': {
                'class': RoundedCornerShape,
                'plugin_id': None
            },
        }

    },
    'rond': {
        'name_txt': 'Rond',
        'subtypes': {
            'Congé': {
                'class': RoundedCornerShape,
                'plugin_id': None
            },    
   
            
            'Arc_rayon': {
                'class': RoundedShape,
                'plugin_id': None
            }
        }
    },
    'filet_gorge': {
        'name_txt': 'Filet Gorge',
        'subtypes': {
            'ISO': {
                'class': ThreadReliefISOShape,
                'plugin_id': None
            }
        }
    }
}

def register_shape_type(type_name, subtype_name, shape_class, shape_name_txt):
    """Enregistre un type et sous-type de forme avec sa classe associée."""
    if type_name not in shape_templates:
        shape_templates[type_name] = {'subtypes': {}}
    shape_templates[type_name]['subtypes'][subtype_name] = {'class': shape_class}
    shape_templates[type_name]['subtypes'][subtype_name] = {'name_txt': shape_name_txt}

def get_shape_class(type_name, subtype_name):
    """Retourne la classe de la forme pour un type et sous-type donnés."""
    return shape_templates.get(type_name, {}).get('subtypes', {}).get(subtype_name, {}).get('class', None)

def get_shape_name(type_name, subtype_name):
    """Retourne la dénomination de la forme pour un type et sous-type donnés."""
    return shape_templates.get(type_name, {}).get('subtypes', {}).get(subtype_name, {}).get('name_txt', f"{type_name}-{subtype_name}")

def get_all_shape_type():
    """Retourne la liste de tous les types."""
    return list(shape_templates.keys())

def get_all_shape_subtype(type_name):
    """Retourne la liste de tous les sous-types du type fourni."""
    return list(shape_templates.get(type_name, {}).get('subtypes', {}).keys())