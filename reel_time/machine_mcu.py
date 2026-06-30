# reel_time/machine_mcu.py

import time
import struct
import socket
import threading
import serial  # Fourni par le package pyserial
import json
import os

from config import save_json_with_format


class CommManager():
    '''Réparassions et contrôle à faire pour l'envois et la receptions de msg:
    ====================================================================
    LISTE DES REPARATIONS ET OPTIMISATIONS - MOTEUR DE COMM DRO
    ====================================================================

    [ ] SECURITE / CYCLE DE VIE
        -> Ajouter 'self.calculator.stop()' dans la fonction 'sauvegarde_de_fin_de_session' 
        liée à 'on_request_close' de Kivy.
        -> Objectif : Envoyer un ordre d'arrêt (E-stop) et fermer proprement le port USB 
        et les sockets Wi-Fi avant que le processus Python ne soit tué.

    [ ] MATERIEL / PURGE INITIALE (FLUSH)
        -> Ajouter 'self.serial_port.reset_input_buffer()' juste après l'ouverture physique 
        du port 'serial.Serial' dans 'comm_mcu_on()'.
        -> Objectif : Éliminer les milliers de vieux octets accumulés dans le tampon du système 
        d'exploitation pendant le crash ou le chargement de l'IHM.

    [ ] RESEAU / WI-FI UDP NON BLOQUANT
        -> Encapsuler la lecture 'recvfrom' de 'receved_mcu()' dans un 'try/except BlockingIOError:'.
        -> Objectif : Retourner une trame vide proprement au lieu de faire cracher l'application 
        lorsque le casier réseau Wi-Fi est vide.

    [ ] MATERIEL / AJUSTEMENT USB-OTG NATIF
        -> Adapter la section USB de 'receved_mcu()' pour lire les blocs complets générés 
        par l'USB-OTG de l'ESP32-S3.
        -> Objectif : Dépiler l'agglomération de trames qui se crée en cas de micro-ralentissement 
        graphique de Kivy.

    [ ] PROTOCOLE / FILTRAGE MATHEMATIQUE CYCLIQUE
        -> Intégrer la formule 'distance = (compteur_recu - self.dernier_id_sequence_valide) % 256' 
        suivie du test 'if 0 < distance <= 128:'.
        -> Appliquer ce filtre de manière universelle sur l'USB ET le Wi-Fi dans 'traite_msg_mcu()'.
        -> Objectif : Éliminer instantanément les doublons et les trames Wi-Fi arrivant en retard 
        sans utiliser de liste d'historique lourde.

    [ ] PERFORMANCE / NETTOYAGE TEXTUEL (FONCTIONS ACTION)
        -> Remplacer tout usage de 'eval()' pour exécuter les chaînes d'action du catalogue par 
        la méthode native et ultra-rapide 'getattr(self, nom_action, None)'.

    [ ] CADENCEMENT / REGULATEUR TEMPOREL DE CROISIERE
        -> Modifier la fin de 'boucle_lecture_300hz()' pour calculer un 'temps_sommeil' dynamique 
        basé sur un chronomètre absolu 'time.perf_counter()'.
        -> Objectif : Éviter la dérive de 'time.sleep()' et garantir un rythme constant à 300Hz.

    [ ] THREAD-SAFETY / ALERTES ET POP-UPS KIVY
        -> Interdire l'ouverture directe de pop-ups ou la modification d'IHM dans le thread à 300Hz 
        (au niveau du compteur d'erreurs à 15).
        -> Utiliser impérativement 'Clock.schedule_once()' pour passer l'ordre d'affichage au 
        thread principal de Kivy.

    [ ] ARCHITECTURE / DOUBLE BUFFER D'EMISSION
        -> Séparer 'self.buffer_send' en deux listes distinctes : 'buffer_send_standard' et 'buffer_send_urgent'.
        -> Objectif : Éliminer la boucle 'for' de recherche d'urgence à chaque cycle en Phase 0.

    [ ] PROTOCOLE / EMPAQUETAGE STRUCT BINAIRE
        -> Remplacer le format texte, le 'split(":")' et le '.encode('utf-8')' par un traitement binaire 
        pur en utilisant 'struct.pack()' dès la mise en file d'attente des messages sortants.
    '''
    def __init__(self, machine_state):
        self.machine = machine_state
        self.start_comm = True  # True pendant la phase de démarrage ou lorsque le time de sécurité et dépassé
        self.error_comm_compt = 0
        self.buffer_binaire = bytearray()
        self.nb_segments_actifs = 0
        self.segments_fao = []
        
        self.serial_port = None
        self.socket_wifi = None
        self.thread_actif = False 

        # ====================================================================
        # CALCUL DYNAMIQUE DES TIMERS DE RÉSEAU
        # ====================================================================
        # Conversion Hz -> Intervalle en secondes (Ex: 1 / 300 = 0.0033s)
        self.intervalle_lecture = 1.0 / self.machine.freq_lecture_kivy
        self.intervalle_envoi_kivy = 1.0 / self.machine.freq_emission_kivy
        
        # Calcul automatique de la barrière de secours (3 messages MCU manqués)
        # Ex à 200Hz : (1 / 200) * 3 = 0.005s * 3 = 0.015 seconde
        self.delai_secours_usb = (1.0 / self.machine.freq_emission_mcu) * 3

        # Initialisation de vos chronomètres logiciels avec votre astuce négative
        # On recule le timer USB de plus que le délai de secours pour forcer l'écoute immédiate
        self.timer_usb = - (self.delai_secours_usb + 1.0)
        self.timer_wifi = - 10.0
        self.timer_global_confiance = time.perf_counter()
        

        # Poursuite logique d'activation...
        # 1. On ouvre le matériel SANS lancer le thread (Zéro collision possible)
        self.comm_mcu_on(lancer_thread=False)
        # 2. On charge la FAO de secours
        self._restaurer_fao_depuis_json()
        # 3. La boucle de boot écoute seule et tranquillement pendant 60ms maximum
        self.start_receved_mcu(False)
        # 4. Le verdict du boot est tombé. 
        # Si on doit travailler en ligne, on allume officiellement le thread permanent à 300Hz !
        # TODO: Ci-dessous peut-être un doublon avec la fin de "start_receved_mcu()" ?
        if self.machine.mcu_en_ligne_derniere_session or self.machine.mode_reprise_crash:
            # On relance comm_mcu_on avec lancer_thread=True par défaut
            self.comm_mcu_on() # TODO: Manque un lanceur d'envois de messages dans cette fonction qui de vrais appeler "ordonnanceur_emission_120hz" en boucle de 120Hz
        else:
            # Si le JSON demandait explicitement du hors-ligne ou si le boîtier est éteint
            self.comm_mcu_off()
    
    def comm_mcu_on(self, lancer_thread=True):
        """Ouvre proprement les connexions matérielles et gère l'allumage du Thread de croisière."""
        # 1. NETTOYAGE PRÉVENTIF : On ferme tout pour repartir à blanc
        self.comm_mcu_off()

        # 2. Réinitialisation naturelle du compteur de parasites de l'atelier
        # self.error_compt = 0 on peut aussi le laisser à ça valeur !

        # ====================================================================
        # 3. OUVERTURE PHYSIQUE DE L'USB
        # ====================================================================
        port_cible = self.machine.port_usb
        vitesse = self.machine.baudrate
        try:
            self.serial_port = serial.Serial(port_cible, vitesse, timeout=0.001)
            print(f"[COMM] Nouvelle liaison USB initialisée sur {port_cible}.")
        except Exception as e:
            print(f"[WARN] Port USB indisponible ({port_cible}) : {e}")
            self.serial_port = None

        # ====================================================================
        # 4. OUVERTURE PHYSIQUE DU WI-FI (Si actif dans les paramètres)
        # ====================================================================
        if self.machine.used_wifi:
            ip_cible = self.machine.ip_wifi
            port_cible = self.machine.port_wifi
            try:
                self.socket_wifi = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket_wifi.setblocking(False)
                self.socket_wifi.bind((ip_cible, port_cible))
                print(f"[COMM] Nouvelle liaison Wi-Fi UDP initialisée sur {ip_cible}:{port_cible}.")
            except Exception as e:
                print(f"[WARN] Échec ouverture socket Wi-Fi ({ip_cible}:{port_cible}) : {e}")
                self.socket_wifi = None

        # ====================================================================
        # 5. ALLUMAGE CONDITIONNEL DU THREAD PARALLÈLE (Votre idée de génie)
        # ====================================================================
        if lancer_thread:
            self.thread_actif = True
            self.fil_lecture = threading.Thread(target=self.boucle_lecture_300hz, daemon=True)
            self.fil_lecture.start()
            print("[COMM] 🚀 Moteur de croisière à 300Hz démarré en arrière-plan.")
        else:
            print("[COMM] 🛠️ Ouverture brute des canaux physiques effectuée (Thread en attente).")

    def comm_mcu_off(self):
        """Ferme proprement tous les tuyaux physiques ouverts et libère les ressources."""
        # 1. On coupe l'interrupteur maître du Thread de croisière
        self.thread_actif = False  
        
        # 2. Nettoyage immédiat des statuts pour l'IHM Kivy
        self.machine.mcu_en_ligne = False
        self.machine.canal_comm_actif = None
        
        # 3. Fermeture physique du port série USB
        if self.serial_port:
            try:
                if self.serial_port.is_open:
                    self.serial_port.close()
                print("[COMM] Liaison physique USB fermée proprement.")
            except Exception as e:
                print(f"[WARN] Erreur lors de la fermeture USB : {e}")
            self.serial_port = None

        # 4. Fermeture physique de la socket Wi-Fi
        if self.socket_wifi:
            try:
                self.socket_wifi.close()
                print("[WARN] Socket réseau Wi-Fi fermée proprement.")
            except Exception as e:
                print(f"[WARN] Erreur lors de la fermeture Wi-Fi : {e}")
            self.socket_wifi = None
        
    def start_receved_mcu(self, coupure_comm=False):
        """
        Écoute passive des flux binaires en phase de démarrage (max 60ms).
        Arbitrage sécurisé du mode Crash vs Froid uniquement après validation de la trame.
        """
        print(f"[BOOT] Analyse des IDs de démarrage (Coupure précédente : {coupure_comm})...")
        
        temps_depart = time.perf_counter()
        timeout_max = 0.060  # Fenêtre d'écoute de 60 millisecondes
        
        mcu_ident = None     # Stocke l'intention temporaire d'aiguillage ("crash", "normal" ou None)
        mcu_identifie = False

        while (time.perf_counter() - temps_depart) < timeout_max:
            # 1. Extraction physique des octets bruts des tampons (USB / Wi-Fi)
            trameUSB, trameWIFI = self.receved_mcu(start=True)

            idmsg_usb = -1
            idmsg_wifi = -1

            # 2. PRE-FILTRAGE : Lecture rapide de la signature du premier octet (l'ID)
            if trameUSB and len(trameUSB) >= 1:
                idmsg_usb = trameUSB[0]
                
            if trameWIFI and len(trameWIFI) >= 1:
                idmsg_wifi = trameWIFI[0]

            # 3. ARBITRAGE DES SCÉNARIOS (Vérification anticipée des IDs clés)
            if idmsg_usb == 25 or idmsg_wifi == 25:
                mcu_ident = "crash"
                mcu_identifie = True
                
            elif idmsg_usb == 248 or idmsg_wifi == 248: # (248 = ID de boot spécifique du mcu1)
                mcu_ident = "normal"
                mcu_identifie = True

            # 4. DECODAGE GÉNÉRIQUE ET VÉRIFICATION D'INTÉGRITÉ
            # Le watchdog ne s'amorce (True) que si un ID attendu est détecté, pour éviter les faux départs
            msg_recu = self.traite_msg_mcu(trameUSB, trameWIFI, time.perf_counter(), watchdog=mcu_identifie)

            # 5. DOUBLE VERROU DE SÉCURITÉ : On ne coupe la boucle que si l'ID est bon ET la trame intègre
            if mcu_identifie and msg_recu:
                break

            # Si le décodage a échoué (trame corrompue par un parasite), on réinitialise pour le cycle suivant
            mcu_ident = None
            mcu_identifie = False

            # Pause micro pour soulager le CPU de la tablette pendant la scrutation
            time.sleep(0.001)

        # ====================================================================
        # 6. VERDICT DÉFINITIF APRÈS LA SORTIE DU WHILE (Version Allégée)
        # ====================================================================
        if mcu_identifie and msg_recu and mcu_ident == "crash":
            # 🚨 REPRISE DE CRASH VALIDÉE
            print("[BOOT] 🚨 REPRISE DE CRASH VALIDÉE AVANT OUVERTURE DE L'ÉCRAN.")
            self.machine.mode_reprise_crash = True
            self.machine.mcu_en_ligne = True
            self.machine.last_timmer_comm = time.perf_counter()
            self.start_comm = False  # Libère le démarrage pour ouvrir l'IHM directement sur l'usinage

            # TODO: Ajouter les choses primordial à faire avant même le démarrage de l'écran pour sauver l'usinage
            
        else:
            # 🛠️ CAS STANDARD : Pas de crash détecté pendant les 60ms (Tour éteint ou boot à froid)
            # TODO: Contrôler que cette séquence ne rentre par en conflit avec la proccédure de démarrage standard

            print("[BOOT] Pas de crash détecté.")
            self.machine.mode_reprise_crash = False
            self.start_comm = False  # Libère le démarrage pour ouvrir l'IHM
            
            # On vérifie si la dernière session était configurée en mode Hors ligne / Dessin autonome
            if not self.machine.mcu_en_ligne_derniere_session:
                print("[BOOT] 📲 Mode Hors ligne détecté dans le JSON -> Coupures des canaux physiques.")
                # comm_mcu_off ferme l'USB, le réseau et bascule mcu_en_ligne à False proprement
                self.comm_mcu_off()
            else:
                # La dernière session était connectée, le tour est juste éteint pour l'instant.
                # On ne touche à rien. Le watchdog à 300Hz va détecter le silence au tout premier cycle
                # et gérera l'affichage "Déconnecté" de manière totalement centralisée.
                print("[BOOT] Le tour était connecté au dernier arrêt. Recherche passive activée.")
                
                # Si on a intercepté un démarrage à froid valide (ID 248), on force l'injection des cotes
                if mcu_ident == "normal":
                    print("[BOOT] 🟢 DÉMARRAGE À FROID CONFIRMÉ. Envoi de la trame d'initialisation (ID 31).")
                    self.forcer_coordonnees_json_vers_mcu()

    def boucle_lecture_300hz(self):
        """ 
        Cette fonction tourne en boucle en arrière-plan à 300Hz 
        sans JAMAIS bloquer l'interface graphique Kivy. 
        """
        while self.thread_actif:

            # 1. LECTURE ET TRAITEMENT DES PORTS COMM (Routage + Watchdog automatique)
            # Appeler receved_mcu() sans argument applique start=False par défaut
            traitementOK = self.receved_mcu() 
            
            # 2. LOGIQUE DE COMPTEUR DE TOLÉRANCE AUX PARASITES (0 à 15)
            if traitementOK:
                # Un message valide a été décodé, on descend vers 0 pour assainir la ligne
                self.error_compt = max(self.error_compt - 1, 0)
            else:
                # Le cycle a manqué ou la trame était corrompue, on grimpe vers la barrière des 15
                self.error_compt = min(self.error_compt + 1, 15)
                
                # TODO: Ajouter une pop-up pour signaler que le port comm n'est pas stable ou fortement parasité
                if self.error_compt == 15:
                    # Pop-Up ou allumer_témoins à ajouter ici
                    pass
            
            # 3. PAUSE DE CADENCEMENT TEMPOREL (3.33ms pour tenir les 300Hz)
            time.sleep(self.intervalle_lecture)

    def receved_mcu(self, start=False):
        """
        Contrôle les flux binaires. Priorité à l'USB.
        Purge et filtre entièrement le casier mémoire Wi-Fi à chaque cycle (300Hz).
        """
        trameUSB = None
        trameWIFI = None
        timer_start = time.perf_counter()

        # 1. ESSAI RELEVÉ USB (Lecture brute du buffer série)
        if self.serial_port and self.serial_port.is_open:
            try:
                nb_octets = self.serial_port.in_waiting
                if nb_octets > 0:
                    trameUSB = self.serial_port.read(nb_octets)
            except Exception as e:
                print(f"[COMM] Erreur lecture physique USB : {e}")

        # 2. ESSAI RELEVÉ WI-FI UDP (Purge complète anti-latence)
        if self.machine.used_wifi and self.socket_wifi:
            while True:
                try:
                    donnees, adresse = self.socket_wifi.recvfrom(1024)
                    if adresse and len(adresse) > 0:
                        ip_emetteur = adresse[0]
                        
                        # SÉCURITÉ : Filtrage par la liste blanche
                        if ip_emetteur in self.machine.ip_wifi_mcu:
                            trameWIFI = donnees
                except BlockingIOError:
                    break
                except Exception as e:
                    print(f"[COMM] Erreur de vidage du buffer Wi-Fi : {e}")
                    break

        # 3. ROUTAGE AU BOOT (start_receved_mcu récupère les octets bruts pour analyser l'ID)
        if start:
            return trameUSB, trameWIFI
        
        # ⚡ ENVOI DIRECT VERS VOTRE ROUTEUR LOGIQUE DE CROISIÈRE
        return self.traite_msg_mcu(trameUSB, trameWIFI, timer_start, watchdog=True)
       
    def traite_msg_mcu(self, trameUSB, trameWIFI, timer_msg, watchdog=True):    
        """
        Décodeur et routeur logique des trames reçues.
        Priorité USB, bascule et double lecture Wi-Fi simplifiée par offset mathématique.
        ---
        Ps: le code d'erreur (réponce de "self.traiter_trame_croisiere_normal()") peut avoir un offset de 300 si 
            le décriptage de la trâme WIFI doit être effectué directement après celui de la trâme USB
        """

        msgOK = False   
        source = None   
        besoin_double_lecture_wifi = False

        # ------------------------------------------------------------
        # 1. PRIORITÉ ABSOLUE À L'USB
        # ------------------------------------------------------------
        if trameUSB:    
            res_usb = self.traiter_trame_croisiere_normal(trameUSB, "USB")
            
            # LA LOGIQUE : Si res_usb > 0 (erreur ou offset 300), on force le Wi-Fi !
            if res_usb > 0:
                besoin_double_lecture_wifi = True
                code_reel_usb = res_usb % 300  # Isole l'erreur de base (0 si c'était juste l'offset 300)
            else:
                code_reel_usb = res_usb

            # Si le code réel de base est 0, l'USB a réussi. On valide immédiatement le cycle !
            if code_reel_usb == 0:
                msgOK = True
                source = "USB"

        # ------------------------------------------------------------
        # 2. TRAITEMENT DU WI-FI (Si USB muet OU si le code USB exigeait la double lecture)
        # ------------------------------------------------------------
        if (not msgOK or besoin_double_lecture_wifi) and trameWIFI:
            res_wifi = self.traiter_trame_croisiere_normal(trameWIFI, "WIFI")
            
            if res_wifi > 0:
                code_reel_wifi = res_wifi % 300
            else:
                code_reel_wifi = res_wifi

            # Si la trame Wi-Fi a réussi son décodage (code 0)
            if code_reel_wifi == 0:
                # Si l'USB avait déjà validé le cycle, on le conserve comme source d'IHM,
                # sinon c'est la liaison Wi-Fi qui sauve le cycle de mesure
                if not msgOK:
                    msgOK = True
                    source = "WIFI"

        # ------------------------------------------------------------
        # 3. MISE À JOUR DU CHIEN DE GARDE de fréquence des messages entrant
        # ------------------------------------------------------------
        if watchdog:
            self.machine.alerte_time_msg_in(timer_msg, source)

        return msgOK

    def traiter_trame_croisiere_normal(self, trame_brute, source="USB"):
        """
        ====================================================================
        LEXIQUE DES CODES DE RETOUR PROTOCOLE (DIAGNOSTIC TEMPS RÉEL)
        ====================================================================
        Code 0      : SUCCÈS - La trame est intègre, décodée et enregistrée.
        Code 1      : ERREUR - Trame brute inexistante, vide ou nulle.
        Code 2      : ERREUR - ID de message inconnu (absent du catalogue IN).
        Code 4      : ERREUR - Rejet par l'action spéciale en phase amont (Pre-Hook).
        Code 5      : ERREUR - Taille de payload incorrecte (Trame coupée/parasitée).
        Code 6      : ERREUR - Échec du dépaquetage matériel binaire (struct.unpack).
        Code 7      : ERREUR - Le sous-catalogue de bits n'a pas pu décoder l'entier.
        Code +300   : ÉVÉNEMENT - Ajoute 300 au code, car exige lecture Wi-Fi.
        Code X (>9) : ERREUR - Code d'anomalie spécifique renvoyé par l'action.
        ====================================================================
        """
        # On prépare le calcul de l'offset dynamique Windows-Style (+300 si flag actif)
        offset_wifi = 300 if self.machine.nbr_attentes_wifi_actives > 0 else 0

        # Code 1 : Sécurité structurelle amont
        if not trame_brute or len(trame_brute) < 1:
            return 1 + offset_wifi

        # 1. Extraction de l'ID (Le premier octet) et du Payload
        msg_id = trame_brute[0]
        payload = trame_brute[1:]

        # Code 2 : Filtrage par la légitimité du catalogue unifié
        if msg_id not in CommProtocol.MESSAGES_IN:
            return 2 + offset_wifi

        config = CommProtocol.MESSAGES_IN[msg_id]
        liste_attributs = config["valeurs"]
        nb_champs = len(liste_attributs)

        # ====================================================================
        # 🧠 1.5 INTERCEPTION AVANT DÉCODAGE (Appel Spécial - Start=True)
        # ====================================================================
        nom_action = config.get("action")
        poursuivre_decodage = True
        methode_action = None

        if nom_action:
            methode_action = getattr(self, nom_action, None)
            if methode_action:
                # L'action amont renvoie obligatoirement : (statut_texte, code_numérique)
                statut_action, code_fonct = methode_action(msg_id, payload, start=True, source=source)               
                
                if statut_action == "FINISH":           # ==> La fonction c'est occupée du décodage complet, pas la paine de poursuivre cette fonction
                    return code_fonct + offset_wifi # Renvoie directement 0 si succès, ou le code erreur
                elif statut_action == "SKIP_DECODE":    # ==> La fonction c'est occupée du décodage de la trâme, sauter cette étape
                    if code_fonct != 0:                 # ERREUR : L'action bloque le cycle suite à une anomalie
                        return code_fonct + offset_wifi
                    poursuivre_decodage = False
                elif statut_action == "CONTINUE":       # ==> Poursuivre le décodage standard, la fonction ne sais pas occupée des valeurs reçues
                    if code_fonct != 0:                 # ERREUR : L'action bloque le cycle suite à une anomalie
                        return code_fonct + offset_wifi

        # ====================================================================
        # 2. CONTRÔLE DE SÉCURITÉ DE TAILLE ET DÉPAQUETAGE (Si autorisé)
        # ====================================================================
        if poursuivre_decodage and nb_champs > 0:
            taille_attendue_octets = nb_champs * 4
            
            if len(payload) != taille_attendue_octets:
                print(f"[COMM] Trame ID {msg_id} rejetée sur {source} : Taille incorrecte ({len(payload)}/{taille_attendue_octets} octets).")
                return 5 + offset_wifi

            try:
                # Dépaquetage au format universel Little-Endian int32_t (<Ni)
                fmt_dynamique = f"<{nb_champs}i"
                valeurs_deballees = struct.unpack(fmt_dynamique, payload)
                
                # Distribution indexée (avec déroutement magique des bits à l'intérieur)
                code_retour_inscription = self.inscrire_valeurs_dans_machine(msg_id, liste_attributs, valeurs_deballees)
                if code_retour_inscription != 0:
                    return code_retour_inscription + offset_wifi # Remonte l'erreur de bits (Code 7)
                    
            except Exception as e:
                print(f"[COMM] Erreur struct.unpack sur ID {msg_id} : {e}")
                return 6 + offset_wifi

        # ====================================================================
        # 3. INTERCEPTION APRÈS DÉCODAGE / FIN DE MESSAGE (Start=False)
        #    Utile par exemple pour répondre instantanément à un ACK du MCU !
        # ====================================================================
        if nom_action and methode_action:
            _, code_fonct = methode_action(msg_id, payload, start=False, source=source)            
            # On superpose l'offset de diagnostic au code renvoyé par la fonction
            return code_fonct + offset_wifi
        
        # Le cycle s'est déroulé de manière nominale standard (0 défaut) + offset
        return 0 + offset_wifi

    def decode_bool_msg(self, msg_id, int32_bool):
        """ Décompresse l'entier numérique et distribue les statuts dans Kivy. """
        if msg_id not in CommProtocol.CATALOGUE_BITS_IN:
            return 7 # Renvoie l'erreur 7 si l'ID n'a pas de table de bits associée

        table_bits = CommProtocol.CATALOGUE_BITS_IN[msg_id]
        
        for bit_index, nom_variable in table_bits.items():
            est_vrai = (int32_bool & (1 << bit_index)) != 0
            setattr(self.machine, nom_variable, est_vrai)
            
        return 0 # Succès

    """Fonctions spécial messages entrants"""
    def action_in_pong(self, msg_id, payload_binaire, start=True, source="USB"):
        """
        Action Dédiée (ID 255) : Intercepte le Pong binaire asymétrique compact du MCU.
        Format du payload (5 octets) : [1 octet uint8_t d'ID origine] + [4 octets int32_t de clé].
        """
        # ====================================================================
        # 🧠 PHASE AMONT (Pre-Hook : start=True)
        # ====================================================================
        if start:
            # 1. Contrôle précoce de la taille physique (5 octets fixes sur le câble)
            if len(payload_binaire) != 5:
                return "FINISH", 5  # Erreur de taille (Trame coupée ou incomplète)
            
            # 2. Dépaquetage matériel chirurgical via emporte-pièce asymétrique
            try:
                # '<' = Little-Endian, 'B' = uint8_t (1 octet), 'i' = int32_t (4 octets)
                id_origine, code_secret_recu = struct.unpack("<Bi", payload_binaire)
            except Exception:
                return "FINISH", 6  # Erreur de déballage matériel binaire
                
            # 3. Nettoyage et routage par métadonnées de la file buffer_retry
            # On parcourt la liste à l'envers pour sécuriser les index en cas de pop()
            for i in range(len(self.buffer_retry) - 1, -1, -1):
                paquet_retry = self.buffer_retry[i]
                
                # Double verrouillage d'intégrité : l'ID correspond ET le code secret unique
                # généré par time.perf_counter() figure dans le texte du message stocké
                if paquet_retry["id"] == id_origine and str(code_secret_recu) in paquet_retry["trame"]:
                    
                    # 🧠 FILTRE DE SOURCE NON POLLUANT (Streaming synchrone ESP32 à 200Hz) :
                    # Si le paquet attend le Wi-Fi, mais qu'on capte l'écho en premier sur l'USB,
                    # on refuse de détruire le Retry. On dit "SKIP_DECODE" pour forcer le routeur
                    # à aller purger instantanément la socket Wi-Fi sans lever d'erreur.
                    if paquet_retry.get("wifi_seul", False) and source == "USB":
                        # DEBUG: print(f"[ROUTAGE] Écho ID {id_origine} capté sur l'USB. En attente de la trame Wi-Fi jumelle.")
                        # sécurité supplémentaire pour forcer le décodage WIFI
                        if self.machine.nbr_attentes_wifi_actives < 1 :
                            self.machine.nbr_attentes_wifi_actives = 1
                            print("[SÉCURITÉ] Compteur Wi-Fi réaligné de force à 1 suite à détection d'écho.")
                        return "FINISH", 300   # ici on Force le décodage WIFI dans ce cycle sans d'éclarer d'erreur
                    
                    # --- CAS VALIDE (Ligne Wi-Fi confirmée ou Ping universel acquitté) ---
                    paquet_supprime = self.buffer_retry.pop(i)
                    
                    # Ajustement mathématique automatique du compteur d'état de double écoute
                    if paquet_supprime.get("wifi_seul", False):
                        self.machine.nbr_attentes_wifi_actives = max(0, self.machine.nbr_attentes_wifi_actives - 1)
                        print(f"[🟢 RECEV] Canal Wi-Fi validé. Compteur d'attentes descend à : {self.machine.nbr_attentes_wifi_actives}")
                    else:
                        print(f"[🟢 RECEV] Acquittement standard validé sur la source : {source}")
                        
                    # 🧠 LE BREAK BIEN PENSÉ : le message unique est trouvé et acquitté,
                    # on coupe immédiatement le scan du buffer pour ce cycle.
                    break 
            
            # On informe le décodeur général que le travail est fini avec succès (Zéro défaut = 0)
            return "FINISH", 0

        # ====================================================================
        # 🧠 PHASE AVAL DE FIN (Post-Hook : start=False)
        # ====================================================================
        else:
            # Cette phase ne s'exécutera pas pour l'ID 255 car on renvoie "FINISH"
            # au start=True, mais elle reste alignée sur la signature de "traiter_trame_croisiere_normal()".
            return "CONTINUE", 0
    """Fin de fonctions spécial messages entrants"""

    def inscrire_valeurs_dans_machine(self, msg_id, liste_attributs, valeurs_deballees):
        """ Écrit les int32 et déroute le mot-clé magique vers le décompresseur de bits. """
        for i in range(len(liste_attributs)):
            nom_attribut = liste_attributs[i]
            valeur_brute = valeurs_deballees[i]
            
            if nom_attribut == "DECODE_BOOL_24":
                # On intercepte et on vérifie si le décodage de bits réussit
                erreur_bits = self.decode_bool_msg(msg_id, valeur_brute)
                if erreur_bits != 0:
                    return 7 # Code 7 : Problème de catalogue de bits introuvable
            else:
                setattr(self.machine, nom_attribut, valeur_brute)
        return 0 # Tout s'est bien passé (Code 0)


    ''' Envois de msgs ver MCU'''
    def ordonnanceur_emission_120hz(self):
        """ 
        Moteur d'émission circulaire à 3 phases (Round-Robin).
        Version optimisée par short-circuit evaluation et cadencement garanti.
        """
        maintenant = time.perf_counter()
        trame_a_envoyer = None
        msg_id_associe = None

        # ====================================================================
        # PHASE 0 : TRAITEMENT DES URGENCES + DU BUFFER STANDARD
        # ====================================================================
        if self.cycle_msg == 0 or self.msg_urgent:
            index_send = -1
            nbr_urgences_restantes = 0
            
            if self.msg_urgent:
                for i in range(len(self.buffer_send)):
                    if self.buffer_send[i]["id"] < 10:
                        nbr_urgences_restantes += 1
                        if index_send < 0:
                            index_send = i
                        elif nbr_urgences_restantes > 1:
                            break
                self.msg_urgent = True if nbr_urgences_restantes > 1 else False

            if index_send == -1 and self.cycle_msg == 0:
                if self.buffer_send:
                    index_send = 0

            if index_send >= 0:
                paquet = self.buffer_send.pop(index_send)
                trame_a_envoyer = paquet["trame"]
                msg_id_associe = paquet["id"]
                
                config = CommProtocol.MESSAGES_OUT.get(msg_id_associe, {})
                exige_double_ecoute = False
                
                if config.get("essais", 0) > 0:
                    if msg_id_associe == 200:
                        exige_double_ecoute = self.analyser_bit_12_wifi_emission(trame_a_envoyer)

                    if exige_double_ecoute:
                        self.machine.nbr_attentes_wifi_actives += 1

                    self.buffer_retry.append({
                        "id": msg_id_associe,
                        "trame": trame_a_envoyer,
                        "essais_restants": config["essais"],
                        "wifi_seul": exige_double_ecoute,  
                        "tempo_sec": config["tempo"] / 1000.0,
                        "next_time_send": maintenant + (config["tempo"] / 1000.0)
                    })

            # On prépare pour le cycle suivant ou si phase 0 à échoué
            self.cycle_msg = 1

        # ====================================================================
        # PHASE 1 : DIFFUSION DU BUFFER DE RETRY + SURVEILLANCE DE MSG SANS REPONSE
        # ====================================================================
        if self.cycle_msg == 1 and not trame_a_envoyer:
            if self.buffer_retry:
                nb_elements = len(self.buffer_retry)
                
                # GARDE-FOU UNIQUE ET CENTRALISÉ : Réalignement préventif de l'index
                if self.next_buffer_retry >= nb_elements:
                    self.next_buffer_retry = 0
                
                # Extraction de la ligne courante (L'unique cible du Gardien ce cycle)
                current_idx = self.next_buffer_retry
                last_idx = current_idx + 1  # Par défaut, on pointera sur la case suivante
                paquet_retry = self.buffer_retry[current_idx]
                
                # --------------------------------------------------------
                # 🧠 CAS A : LE GARDIEN UNIQUE PAS-À-PAS (Répétition == 0)
                # --------------------------------------------------------
                if paquet_retry["essais_restants"] == 0:
                    limite_securite_temps = paquet_retry["tempo_sec"] * 5.0
                    
                    if maintenant - paquet_retry["next_time_send"] > limite_securite_temps:
                        print(f"[🚨 ALERTE] ID {paquet_retry['id']} bloqué à 0 essai sans réponse. Éjection de la file.")
                        
                        self.buffer_retry.pop(current_idx)
                        
                        #  RECALAGE DE RÉTRACTATION : la liste s'est resserrée, 
                        # on maintient le pointeur ici pour le message suivant qui a glissé
                        last_idx = current_idx
                        
                        if paquet_retry.get("wifi_seul", False):
                            self.machine.nbr_attentes_wifi_actives = max(0, self.machine.nbr_attentes_wifi_actives - 1)

                # --------------------------------------------------------
                # CAS B : LE MESSAGE ACTIF EST A REPETER (Répétition > 0)
                # --------------------------------------------------------
                elif paquet_retry["essais_restants"] > 0 and maintenant >= paquet_retry["next_time_send"]:
                    trame_a_envoyer = paquet_retry["trame"]
                    msg_id_associe = paquet_retry["id"]
                    
                    if paquet_retry["essais_restants"] < 999:
                        paquet_retry["essais_restants"] -= 1
                    
                    paquet_retry["next_time_send"] = maintenant + paquet_retry["tempo_sec"]

                # Recalcul de la taille réelle pour le scan de secours
                nb_elements_actuels = len(self.buffer_retry)

                # --------------------------------------------------------
                # CAS C : LA LIGNE N'ÉTAIT PAS PRÊTE -> FOR DE SECOURS RÉACTIF
                # --------------------------------------------------------
                if not trame_a_envoyer and nb_elements_actuels > 1:
                    for offset in range(1, nb_elements_actuels):
                        check_idx = (current_idx + offset) % nb_elements_actuels
                        paquet_secours = self.buffer_retry[check_idx]
                        
                        if paquet_secours["essais_restants"] > 0 and maintenant >= paquet_secours["next_time_send"]:
                            trame_a_envoyer = paquet_secours["trame"]
                            msg_id_associe = paquet_secours["id"]
                            
                            if paquet_secours["essais_restants"] < 999:
                                paquet_secours["essais_restants"] -= 1
                            
                            paquet_secours["next_time_send"] = maintenant + paquet_secours["tempo_sec"]
                            last_idx = check_idx + 1
                            break 

                # SIMPLIFICATION : Assignation linéaire brute ! Le nettoyage de sécurité se fera au début du prochain tour de Phase 1.
                self.next_buffer_retry = last_idx

            # Passage à la Phase 2 (Came electronic / FAO)
            self.cycle_msg = 2

        # ====================================================================
        # PHASE 2 : EXPÉDITION DE LA CAME ÉLECTRONIQUE OBLIGATOIRE
        # ====================================================================
        if self.cycle_msg == 2 and not trame_a_envoyer:
            if self.machine.mcu_mode == "PROFIL":
                id_p, id_a, id_s = self.determiner_les_3_segments_critiques_fao()
                trame_a_envoyer = f"26:{id_p}:{id_a}:{id_s}"
                msg_id_associe = 26

            # On prépare pour le cycle suivant
            self.cycle_msg = 0


        # ====================================================================
        # EXPÉDITION PHYSIQUE SUR LES DEUX CANAUX TEXTE
        # ====================================================================
        if trame_a_envoyer:
            flux_octets = trame_a_envoyer.encode('utf-8')
            
            if self.serial_port and self.serial_port.is_open:
                try: self.serial_port.write(flux_octets + b"\n")
                except Exception: pass
                
            if self.machine.used_wifi and self.socket_wifi:
                try: self.socket_wifi.sendto(flux_octets, (self.machine.ip_wifi, self.machine.port_wifi))
                except Exception: pass

    def analyser_bit_12_wifi_emission(self, texte_trame):
        """ Découpe la trame 200 et renvoie True si le Bit 12 (pong_wifi) est levé. """
        morceaux = texte_trame.split(":")
        if len(morceaux) >= 2:
            try:
                bits_compactes = int(morceaux[1])
                return (bits_compactes & (1 << 12)) != 0
            except ValueError:
                pass
        return False
    
    def ajouter_au_buffer_standard(self, msg_id, texte_trame):
        """ Permet à l'IHM d'ajouter une commande texte dans la file d'attente. """
        self.buffer_send.append({"id": msg_id, "trame": texte_trame})
        if msg_id < 10:
            self.msg_urgent = True


    ''' End envois de msgs ver MCU'''

    def compiler_et_sauvegarder_profil_machine(self, point_manager):
        """
        Prend la liste 'profil_segments' du PointManager, génère le JSON de secours,
        remplit la liste 'self.segments_fao' pour Kivy et prépare le buffer binaire.
        """
        # Par sécurité, on passe temporairement le flag de synchonisation à faux, il sera màj à vrai à la fin de l'envois si tous ok
        point_manager.mcu_synchronise = False

        self.segments_fao = [] # On vide la liste de recherche précédente
        buffer_binaire_final = bytearray()
        ligne_index = 0 # Le numéro de ligne universel (0, 1, 2, 3...)

        # 1. PARCOURS ET NETTOYAGE GÉOMÉTRIQUE
        for seg in point_manager.profil_segments:
            if seg["type"] not in ["line", "arc"]:
                continue

            # Extraction des coordonnées (Microns réels au RAYON)
            az, ax = int(seg["start"]), int(seg["start"])
            bz, bx = int(seg["end"]), int(seg["end"])
            
            bbox_zmin = int(seg["bbox"])
            bbox_xmin = int(seg["bbox"])
            bbox_zmax = int(seg["bbox"])
            bbox_xmax = int(seg["bbox"])

            if seg["type"] == "line":
                type_mcu = 0
                cz, cx, rayon = 0, 0, 0
            else:  # "arc"
                type_mcu = 1 if seg["cw"] else 2
                cz, cx = int(seg["center"]), int(seg["center"])
                rayon = int(seg["radius"])

            # Le dictionnaire épuré avec l'INDEX DE LIGNE pour la recherche à 60Hz
            clean_dict = {
                "ligne": ligne_index, # 👈 L'identifiant universel Kivy/MCU !
                "type_mcu": type_mcu,
                "bbox": [[bbox_zmin, bbox_xmin], [bbox_zmax, bbox_xmax]],
                "A": [az, ax],
                "B": [bz, bx],
                "C": [cz, cx],
                "rayon": rayon
            }
            self.segments_fao.append(clean_dict)
            ligne_index += 1 # On passe à la ligne suivante

            # 2. EMPAQUETAGE BINAIRE C++ (60 octets)
            bloc_binaire = struct.pack('15i',
                type_mcu,
                bbox_zmin, bbox_xmin, bbox_zmax, bbox_xmax,
                az, ax, bz, bx, cz, cx, rayon,
                0, 0, 0
            )
            buffer_binaire_final.extend(bloc_binaire)

        # ====================================================================
        # 3. SAUVEGARDE JSON STRUCTURÉE
        # ====================================================================
        chemin_json = os.path.join("part", "profil_machine_actif.json")
        json_final_avec_memo = {
            "info": "Généré par : class CommManager -> compiler_et_sauvegarder_profil_machine",
            "segments": self.segments_fao
        }

        try:
            keys_compacted = [("info", True), ("bbox", True), ("A", True), ("B", True), ("C", True)]
            save_json_with_format(chemin_json, json_final_avec_memo, keys_compacted)
            print(f"[FAO] Profil de secours enregistré avec succès : {chemin_json}")
        except Exception as e:
            print(f"[WARN] Impossible d'écrire le JSON de debug : {e}")

        # On retourne le nombre de lignes et les octets
        return len(self.segments_fao), buffer_binaire_final
    def OBSOLET_a_controler__send_profil_to_mcu(self, point_manager):
        self.nb_segments_actifs, self.buffer_binaire = self.compiler_et_sauvegarder_profil_machine(point_manager)
        
        # ... (votre code d'envoi physique USB ou Wi-Fi) ...
        envoi_reussi = True 

        if envoi_reussi:
            point_manager.mcu_synchronise = True
            print("[COMM] Synchronisation matérielle validée avec le MCU.")

    #Restauration rapide (au démarrage) depuis le json existant pour continuer l'usinage en cas de crach de Kivy
    def _restaurer_fao_depuis_json(self):
        """
        Tente de recharger la liste FAO de secours au démarrage de l'application
        pour garantir la continuité de la barrière virtuelle en cas de crash de Kivy.
        """
        chemin_json = os.path.join("part", "profil_machine_actif.json")
        
        if os.path.exists(chemin_json):
            try:
                with open(chemin_json, "r", encoding="utf-8") as f:
                    donnees_sauvegardees = json.load(f)
                    
                # Rappel : notre structure JSON contient une clé "info" et une clé "segments"
                if "segments" in donnees_sauvegardees:
                    self.segments_fao = donnees_sauvegardees["segments"]
                    self.nb_segments_actifs = len(self.segments_fao)
                    print(f"[REPRISE] Tâche de secours : {self.nb_segments_actifs} segments rechargés dans self.segments_fao.")
                    
                    # On prépare aussi le buffer binaire au cas où le MCU le réclamerait au reboot
                    self._reconstruire_buffer_binaire_depuis_fao()
                    
            except Exception as e:
                print(f"[WARN] Échec du rechargement de la table FAO de secours : {e}")
                self.segments_fao = []
                self.nb_segments_actifs = 0

    def _reconstruire_buffer_binaire_depuis_fao(self):
        """Reconstruit le buffer binaire à partir de la liste FAO (rechargée)."""
        self.buffer_binaire = bytearray()
        for seg in self.segments_fao:
            # On extrait les valeurs qui ont été aplaties dans le JSON
            type_mcu = seg["type_mcu"]
            bbox_zmin, bbox_xmin = seg["bbox"][0]
            bbox_zmax, bbox_xmax = seg["bbox"][1]
            az, ax = seg["A"]
            bz, bx = seg["B"]
            cz, cx = seg["C"]
            rayon = seg["rayon"]

            # On ré-empaquette au format binaire C++ strict (60 octets)
            bloc_binaire = struct.pack('15i',
                type_mcu,
                bbox_zmin, bbox_xmin, bbox_zmax, bbox_xmax,
                az, ax, bz, bx, cz, cx, rayon,
                0, 0, 0
            )
            self.buffer_binaire.extend(bloc_binaire)


# Dans reel_time/machine_mcu.py ou dans un fichier protocol.py séparé
class CommProtocol:
    # ====================================================================
    # 📥 CATALOGUE DES MESSAGES ENTRANTS : MCU -> KIVY (Espace IN)
    # ====================================================================
    # TOUTES les valeurs sont des int32_t (4 octets), sauf celle traîté spécialement par une fonction "action"
    # Le décodeur générique calcule le format d'après le nombre d'éléments.
    MESSAGES_IN = {
        # 🚨 ALERTES ET PANNE SÉCURITÉ
        0:   {"valeurs": ["code_erreur_mcu"], "action": "action_in_arret_urgence"},
        1:   {"valeurs": ["mode_reprise_crash"], "action": None},
        2:   {"valeurs": ["code_defaut_moteur_y"], "action": "action_in_moteur_hs"},

        # 🛠️ FLUX DE MESURE HAUTE FRÉQUENCE (200 Hz)
        25:  {"valeurs": ["z_machine", "x_machine", "y_machine", "spindle_machine", "DECODE_BOOL_24"], "action": None},
        30:  {"valeurs": [], "action": "action_in_json_segments_mcu"},
        
        # ⚙️ MAINTENANCE ET BOOT PASSIF
        248: {"valeurs": ["z_machine", "x_machine", "y_machine", "spindle_machine"], "action": None},
        255: {"valeurs": ["Id_msg_ping", "ping_key"], "action": "action_in_pong"}  # Format valeurs : "<Bi" (uint8_t, int32_t)
    }

    # --- SOUS-CATALOGUE DE BITS ENTRANTS ---
    # Clé = ID du message, Valeur = Dictionnaire {Numéro_du_bit: "Attribut_Kivy_Destination"}
    CATALOGUE_BITS_IN = {
        25: {
            # 💡 Si vous n'avez pas de fin de course sur un axe, vous commentez juste la ligne :
            0: "fin_course_x_min",  
            1: "fin_course_x_max",  
            # 2: "fin_course_z_min",  # Commenté = Ignoré par le décodeur sans décaler le reste
            # 3: "fin_course_z_max",  
            4: "moteur_y_actif",    
            5: "moteur_y_defaut",   
            6: "arrosage_statut",   
            
            # Plus besoin de rajouter des "None" à la suite jusqu'à 23 !
            12: "capteur_futur_axe_broche" 
        },
        
        40: {
            0: "broche_en_rotation",
            1: "sens_horaire",
            2: "vcc_stabilisee"
        }
    }

    # ====================================================================
    # 📤 CATALOGUE DES MESSAGES SORTANTS : KIVY -> MCU (Espace OUT)
    # ====================================================================
    MESSAGES_OUT = {
        # ID: {"essais": X, "tempo": ms, "valeurs": [...]}
        0:   {"essais": 999, "tempo": 10,  "valeurs": ["err_code"]}, 
        26:  {"essais": 0,   "tempo": 999, "valeurs": ["id_prev", "id_act", "id_next"]},
        31:  {"essais": 2,   "tempo": 25,  "valeurs": ["z_m", "x_m", "y_m", "s_m"]},
        200: {"essais": 5,   "tempo": 300, "valeurs": ["wifi_flags", "ping_key"]},
        201: {"essais": 5,   "tempo": 301, "valeurs": ["new_baud"]},
        254: {"essais": 0,   "tempo": 999, "valeurs": ["ping_time"]}
    }

    # --- SOUS-CATALOGUE DE BITS SORTANTS ---
    # Clé = ID du message, Valeur = Dictionnaire {Numéro_du_bit: "Attribut_Kivy_Source"}
    CATALOGUE_BITS_OUT = {
        200: {
            0: "wifi_status_desire",         # 0 = Demande Off, 1 = Demande On
            1: "wifi_change_configuration",  # 0 = Simple test, 1 = Appliquer le changement d'état matériel
            11: "pong",                      # Ordre d'écho universel (L'ESP répond sur USB et Wi-Fi)
            12: "pong_wifi"                  # Pong exclusif Wi-Fi (Vérification de la liaison sans fil bidirectionnelle)
        }
    }



