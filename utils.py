#   utils.py

import json
import os
import copy


#> Partie mise en forme du json(String)
def save_json_with_format(filepath, data, compact_keys=None, indent=4):
    '''
    Enregistre un fichier JSON en appliquant une mise en forme personnalisée selon les clés.

    Args:
        filepath (str): Chemin de destination du fichier JSON.
        data (dict | list): Données JSON à écrire.
        compact_keys (list[tuple[str, bool]]): Liste de paires (clé, booléen), où :
            - True  → force l’affichage de la valeur sur une seule ligne.
            - False → force un affichage multi-lignes (par élément enfant, un seul niveau).
            Exemple : [("points", False), ("pos", True)]
        indent (int): Nombre d’espaces utilisés pour l’indentation (défaut : 4).

    Exemple:
        save_json_with_format(
            "exemple.json",
            data=my_data,
            compact_keys=[("points", False), ("pos", True)],
            indent=4
        )

    Returns:
        None – écrit directement le fichier sur le disque.
    '''

    compact_keys = normalize_compact_keys(compact_keys or [], default=False)

    # processed_data est une liste de lignes déjà indentées
    processed_lines = process_json_keys(data, compact_keys, indent=indent)

    with open(filepath, "w", encoding="utf-8") as f:
        for line in processed_lines:
            f.write(line + "\n")

def process_json_keys(data, keys_to_process, level=0, indent=4):
    output_lines = []
    spacing = " " * (indent * level)
    spacing_next = spacing + (" " * indent)
    keys_to_process_dict = dict(keys_to_process)

    if isinstance(data, dict):
        output_lines.append(spacing + "{")
        items = list(data.items())
        
        for idx, (key, value) in enumerate(items):
            is_last = idx == len(items) - 1
            key_str = json.dumps(key, ensure_ascii=False) + ": "

            if key in keys_to_process_dict:
                u = keys_to_process_dict[key]
                output_lines.extend(format_compact_key(key, value, uniline=u, is_last=is_last, level=level+1, indent=indent))
            elif isinstance(value, (dict, list)):
                formatted_lines = process_json_keys(value, keys_to_process, level + 1, indent)
                output_lines.append(spacing_next + key_str)
                output_lines.extend(formatted_lines)
                #output_lines.extend(formatted_lines[:-1])
                #last_line = formatted_lines[-1] + ("," if not is_last else "")
                #output_lines.append(last_line)
            else:
                val_str = json.dumps(value, ensure_ascii=False)
                #output_lines.append(spacing_next + key_str + val_str + ("," if not is_last else ""))
                output_lines.append(spacing_next + key_str + val_str)

            if not is_last: output_lines[-1] += ","
        
        output_lines.append(spacing + "}")

    elif isinstance(data, list):
        output_lines.append(spacing + "[")
        
        for idx, item in enumerate(data):
            is_last = idx == len(data) - 1
            
            if isinstance(item, (dict, list)):
                lines = process_json_keys(item, keys_to_process, level + 1, indent)
                output_lines.extend(lines)
                #output_lines.extend(lines[:-1])
                #last_line = lines[-1] + ("," if not is_last else "")
                #output_lines.append(last_line)
            else:
                output_lines.append(spacing_next + json.dumps(item, ensure_ascii=False))
                #output_lines.append(spacing_next + json.dumps(item, ensure_ascii=False) + ("," if not is_last else ""))
            
            if not is_last: output_lines[-1] += ","

        output_lines.append(spacing + "]")

    else:
        output_lines.append(spacing + json.dumps(data, ensure_ascii=False))

    return output_lines

def format_compact_key(key, value, uniline, is_last, level, indent):
    lines = []
    spacing = " " * (indent * level)
    spacing_next = spacing + (" " * indent)
    key_str = json.dumps(key, ensure_ascii=False) + ": "
    compact = uniline
    type_data = "primitive"
    start_str = ""
    end_str = ""
    
    if isinstance(value, dict):
        type_data = "dict"
        start_str = "{"
        end_str = "}"
        items = list(value.items())  # → [(key1, val1), (key2, val2), ...]
    elif isinstance(value, list):
        type_data = "list"
        start_str = "["
        end_str = "]"
        items = [(None, v) for v in value]  # Tu ajoutes une clé fictive `None` pour avoir une structure uniforme
    else:
        compact = True
        items = [(None, value)]  # Encore une fois, une valeur simple emballée
        
    if compact is False:
        lines.append(spacing + key_str + start_str)
        for idx, (k, v) in enumerate(items):
            comma = "," if idx < len(items) - 1 else ""
            if type_data == "dict":
                k_str = json.dumps(k, ensure_ascii=False) + ": "
            else:
                k_str = ""  # ← vide si liste ou primitive

            v_str = json.dumps(v, ensure_ascii=False, separators=(',', ': '))
            lines.append(spacing_next + k_str + v_str + comma)

        #if type_data != "primitive": lines.append(spacing + end_str)
        lines.append(spacing + end_str)

    else:
        compact_json = json.dumps(value, ensure_ascii=False, separators=(',', ': '))
        lines.append(spacing + key_str + compact_json)   # + ("," if not is_last else "") + end_str)
    
    #if not is_last: lines[-1] += ","
    
    return lines

def normalize_compact_keys(compact_keys, default=False):
    """
    Transforme une liste de clés ou de tuples (clé, bool) en une liste de tuples (clé, bool)
    """
    normalized = []
    for item in compact_keys:
        if isinstance(item, tuple):
            normalized.append(item)
        else:
            normalized.append((item, default))
        #print(f"normalize_compact_keys: {item}")
    return normalized
#< END Partie mise en forme du json(String)

#> Widjet
#< END Widjet