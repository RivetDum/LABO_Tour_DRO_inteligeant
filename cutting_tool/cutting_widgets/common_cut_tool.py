# cutting_tool/cutting_widgets/ - common_cut_tool.py     # Outils communs aux dossier cutting_tool/
    # et pour l'import: from cutting_tool.cutting_widgets  import common_cut_tool as cut_tool

import common_draw as cdraw


def traiter_geometrie_generique(data_forme):
    """
    Prend une configuration brute de forme et génère les entités 
    en indexant tout sur le centre du bec du sommet a0 (si n > 2).
    
    Retourne :
        tuple : (
            point_fillet,   # liste de dict {"pos":[x,y], "radius": valeur} . "pos" avec la valeur déplacée
            arc_net,        # Liste d'angles sous forme de congé (pour [ceate_drawing_mesh()])
            ref_centre      # L'INVERSE du décalage appliqué (format [x,y])
            )
    """
    sommets = data_forme["points"]
    n = len(sommets)
    
    # 1. Calcul des congés (fillets) bruts pour chaque sommet
    arcs_bruts = []
    for i in range(n):
        # Nouvelle structure : sommets[i][0] est la liste [x, y], sommets[i][1] est le radius
        p_before = sommets[i - 1][0]
        p_intersect = sommets[i][0]
        radius = sommets[i][1]
        p_after = sommets[(i + 1) % n][0]
        
        # Pour faire un congé, il faut au moins 3 points (une intersection entre deux lignes)
        if radius > 0 and n > 2:
            arc = cdraw.create_fillet(p_before, p_intersect, p_after, radius)
        else:
            arc = {"type": "None", "center": p_intersect, "radius": radius}
            
        arc["pnt_pos"] = p_intersect
        arcs_bruts.append(arc)
        
    # 2. SUBTILITÉ : Si len est 1 ou 2, pas de déplacement. L'origine reste à [0.0, 0.0]
    if n <= 2:
        ref_centre = [0.0, 0.0]
    else:
        # Sinon, le point (0,0) repose sur le centre du bec du premier sommet (index 0)
        ref_centre = arcs_bruts[0]["center"] if arcs_bruts[0] else sommets[0][0]
            
    def pnt_minus(p, ref): 
        return [p[0] - ref[0], p[1] - ref[1]]

    # 3. Translation (si applicable) et formatage final
    arc_net = []        # Les valeurs de points des congés relatives au centre outil (0,0)
    point_fillet = []   # Les points théoriques d'arêtes relatives au centre outil (0,0)
    
    for i, arc in enumerate(arcs_bruts):
        if arc is None:
            continue

        point_fillet.append({
            "pos": pnt_minus(arc["pnt_pos"], ref_centre), 
            "radius": arc["radius"]
        })
        
        c_trans = pnt_minus(arc["center"], ref_centre)
        
        if arc["type"] == "arc":
            s_trans = pnt_minus(arc["start"], ref_centre)
            e_trans = pnt_minus(arc["end"], ref_centre)
            arc_net.append({"type": "arc", "center": c_trans, "start": s_trans, "end": e_trans, "radius": arc["radius"]})
        else:
            arc_net.append({"type": "None", "center": c_trans, "radius": arc["radius"]})
        
    return (point_fillet, arc_net, [ref_centre[0]*-1,ref_centre[1]*-1])


# Fonction pour le dessin à l'écran (Prête pour alimenter Kivy)
#def ceate_drawing_mesh(arcs_net): ==>> Déplacé dans common_draw

