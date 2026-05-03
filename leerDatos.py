import sys
import threading
import socket
import time
import os
from queue import Queue

import customtkinter as ctk
import numpy as np
from scipy.io import loadmat, savemat

# ----------------------------------------------------------------------
# 1. IMPORTAR EL MÓDULO DE LA INTERFAZ
# ----------------------------------------------------------------------
import interfaz_pau as ui_app

# Archivo .mat donde guardarDatos.py va escribiendo
MAT_FILE = "speller_selections.mat"

# =================================================================
# I. VARIABLES GLOBALES E INICIALIZACIÓN
# =================================================================

DATA_STATE = ui_app.DATA_STATE
UI_QUEUE = ui_app.UI_QUEUE

# Map de notas
NOTA_MAP = {
    "D": "D",
    "R": "R",
    "M": "M",
    "F": "F",
    "S": "S",
    "L": "L",
    "I": "I",
    "O": "O"  # DO agudo
}

# Configuración TCP opcional con robot
#ROBOT_IP = "127.0.0.1"
ROBOT_IP = "192.168.125.1"
ROBOT_PORT = 7000
socket_robot = None

# Control de backend
running = True
last_index_mat = 0

# Historial de composiciones
COMPOSITIONS = []
CURRENT_COMPOSITION = []
COMPOSITION_NAME = ""
WAITING_FOR_NAME = False

# Canciones predefinidas para Neurify
# Canciones predefinidas para Neurify
PREDEFINED_SONGS = {
    "C": {
        "title": "Cumpleaños Feliz", 
        "artist": "Tradicional", 
        "lyrics": "Cumpleaños feliz, cumpleaños feliz...\nTe deseamos todos, cumpleaños feliz.",
        "notes": [
            "D", "D", "R", "D", "S", "F",    # Cumpleaños feliz (DO DO RE DO SOL FA)
            "D", "D", "R", "D", "L", "S",    # Cumpleaños feliz (DO DO RE DO LA SOL)
            "D", "D", "O", "L", "F", "M", "R", # Te deseamos todos (DO DO DO_AGUDO LA FA MI RE)
            "I", "I", "L", "F", "S", "F"     # Cumpleaños feliz (SI SI LA FA SOL FA)
        ]
    },
    "N": {
        "title": "Noche de Paz", 
        "artist": "Tradicional", 
        "lyrics": "Noche de paz, noche de amor...\nTodo duerme en derredor.",
        "notes": [
            "S", "L", "S", "M", "S", "L", "S", "M", # Sol La Sol Mi, Sol La Sol Mi
            "R", "R", "O", "I", "R", "R", "O", "I" # Re Re Do_Agu Si, Re Re Do_Agu Si
        ]
    },
    "V": {
        "title": "Feliz Navidad", 
        "artist": "Tradicional", 
        "lyrics": "Feliz Navidad, Feliz Navidad...\nFeliz Navidad, próspero año y felicidad.",
        # (Aquí irían las notas correspondientes si quieres que el robot la toque)
        "notes": [] 
    }
}

# Contador para IDs únicos de composiciones
COMPOSITION_COUNTER = 0

# =================================================================
# II. FUNCIONES DE BACKEND
# =================================================================

def read_new_mat_values():
    """Lee speller_selections.mat y devuelve las nuevas selecciones desde la última lectura"""
    global last_index_mat
    if not os.path.exists(MAT_FILE):
        return []

    try:
        data = loadmat(MAT_FILE, squeeze_me=True, struct_as_record=False)
        sel = data.get("selections", np.array([]))

        if isinstance(sel, np.ndarray):
            all_sel = [str(x) for x in sel.tolist()]
        elif sel == []:
            all_sel = []
        else:
            all_sel = [str(sel)]

        if last_index_mat >= len(all_sel):
            return []

        nuevas = all_sel[last_index_mat:]
        last_index_mat = len(all_sel)
        return nuevas

    except Exception as e:
        print(f"[MAT ERROR] No se pudo leer {MAT_FILE}: {e}")
        return []

def send_command_to_robot(command):
    """Crea una nueva conexión, envía el comando, recibe la respuesta y la cierra inmediatamente."""
    
    # Crea un nuevo socket en cada llamada
    temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Aumentar el timeout a 3 segundos para mayor robustez
    temp_socket.settimeout(5.0) 

    robot_response = "NO RESPONSE"
    
    try:
        # 1. Conectar al robot
        temp_socket.connect((ROBOT_IP, ROBOT_PORT))
        
        # 2. Enviar comando (RAPID espera el \n)
        full_command = str(command).strip() + "\n"
        print(f"[TCP] Enviando comando: {command}")
        temp_socket.sendall(full_command.encode('ascii'))
        
        # 3. Recibir respuesta
        robot_response = temp_socket.recv(1024).decode("ascii", errors="ignore").strip()
        print(f"[TCP] Robot respondió: {robot_response}")

    except socket.timeout:
        print("[TCP ERROR] Falló envío/recepción: timed out")
        robot_response = "TIMEOUT"
    except ConnectionRefusedError:
        print("[TCP ERROR] Conexión rechazada. ¿El programa RAPID está en RUN?")
        robot_response = "REFUSED"
    except Exception as e:
        # Aquí caerían errores como 'Connection reset by peer'
        print(f"[TCP ERROR] Falló envío/recepción: {e}")
        robot_response = "ERROR: " + str(e)
    finally:
        # 4. CERRAR SIEMPRE EL SOCKET
        temp_socket.close() 
        
    return robot_response # Devuelve la respuesta si es necesario

def generate_unique_song_id():
    """Genera un ID único para las composiciones del usuario que no choque con comandos de modo."""
    global COMPOSITION_COUNTER
    COMPOSITION_COUNTER += 1
    
    # Usar letras para IDs de composiciones (no números que son comandos de modo)
    # Formato: A, B, C, D, E... AA, AB, AC...
    def num_to_letters(n):
        result = ""
        while n > 0:
            n -= 1
            result = chr(65 + (n % 26)) + result
            n //= 26
        return result if result else "A"
    
    return num_to_letters(COMPOSITION_COUNTER)

def process_selection(selection):
    """Procesa una selección del .mat según el modo actual"""
    global DATA_STATE, CURRENT_COMPOSITION, COMPOSITIONS, running, COMPOSITION_NAME, WAITING_FOR_NAME

    sel = str(selection).strip().upper()
    
    print(f"[PROCESS] Selección: {sel}, Modo actual: {DATA_STATE['mode']}, Esperando nombre: {WAITING_FOR_NAME}")

    # Si estamos esperando un nombre para la composición
    if WAITING_FOR_NAME:
        if sel == "N":
            # Guardar la composición con el nombre acumulado
            if CURRENT_COMPOSITION:
                song_id = generate_unique_song_id()  # Generar ID único (A, B, C, etc.)
                
                nueva_cancion = {
                    "title": COMPOSITION_NAME if COMPOSITION_NAME else f"Composición {song_id}",
                    "artist": "Usuario",
                    "notes": CURRENT_COMPOSITION.copy(),
                    "lyrics": f"Composición creada por el usuario.\nNotas: {' - '.join(CURRENT_COMPOSITION)}"
                }
                COMPOSITIONS.append(nueva_cancion)
                
                # Añadir al diccionario de canciones con ID único
                DATA_STATE["songs"][song_id] = nueva_cancion
                
                print(f"[COMPOSITOR] Composición guardada con ID '{song_id}': {nueva_cancion['title']}")
                UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                    "message": f"Composición '{nueva_cancion['title']}' guardada con ID [{song_id}]",
                    "composed_notes": []
                }})
                
                # Reset
                CURRENT_COMPOSITION = []
                COMPOSITION_NAME = ""
                WAITING_FOR_NAME = False
            return
        else:
            # Acumular caracteres para el nombre
            if sel.isalnum() or sel == " ":  # Permitir letras, números y espacios
                COMPOSITION_NAME += sel
                UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                    "message": f"Nombre actual: '{COMPOSITION_NAME}'. Presiona 'N' para guardar."
                }})
            return

    # Comandos de cambio de modo (funcionan en todos los modos)
    if sel == "1":
        DATA_STATE["mode"] = "NORMAL"
        DATA_STATE["message"] = "Modo NORMAL activado. Toca notas individuales."
        UI_QUEUE.put({"command":"UPDATE_MODE", "value":"NORMAL"})
        UI_QUEUE.put({"command":"UPDATE_DATA", "value":{"message": DATA_STATE["message"]}})
        print("[MODO] Cambiando a NORMAL")
        return
        
    elif sel == "2":
        DATA_STATE["mode"] = "COMPOSICION"
        DATA_STATE["message"] = "Modo COMPOSICIÓN activado. Crea tu secuencia."
        CURRENT_COMPOSITION = []
        DATA_STATE["composed_notes"] = []
        UI_QUEUE.put({"command":"UPDATE_MODE", "value":"COMPOSICION"})
        UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
            "message": DATA_STATE["message"],
            "composed_notes": []
        }})
        print("[MODO] Cambiando a COMPOSICION")
        return
        
    elif sel == "3":
        DATA_STATE["mode"] = "NEURIFY"
        DATA_STATE["message"] = "Modo NEURIFY activado. Selecciona una canción."
        UI_QUEUE.put({"command":"UPDATE_MODE", "value":"NEURIFY"})
        UI_QUEUE.put({"command":"UPDATE_DATA", "value":{"message": DATA_STATE["message"]}})
        print("[MODO] Cambiando a NEURIFY")
        return
        
    elif sel == "4":
        DATA_STATE["mode"] = "MENU"
        DATA_STATE["message"] = "Menú principal. Selecciona un modo."
        UI_QUEUE.put({"command":"UPDATE_MODE", "value":"MENU"})
        UI_QUEUE.put({"command":"UPDATE_DATA", "value":{"message": DATA_STATE["message"]}})
        print("[MODO] Cambiando a MENU")
        return

    # Procesamiento según el modo actual
    if DATA_STATE["mode"] == "NORMAL":
        # En modo NORMAL, tocar la nota inmediatamente
        nota = NOTA_MAP.get(sel, None)
        if nota:
            print(f"[NORMAL] Tocando nota: {nota}")
            UI_QUEUE.put({"command":"UPDATE_SELECTION", "value": nota})
            UI_QUEUE.put({"command":"UPDATE_DATA", "value":{"message": f"Tocando: {nota}"}})
            send_command_to_robot(nota)
        else:
            print(f"[NORMAL] Selección no reconocida: {sel}")
            
    elif DATA_STATE["mode"] == "COMPOSICION":
        if sel == "0":
            # Finalizar composición y pedir nombre
            if CURRENT_COMPOSITION:
                WAITING_FOR_NAME = True
                COMPOSITION_NAME = ""
                UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                    "message": "Introduce el nombre de la composición letra por letra. Presiona 'N' cuando termines."
                }})
                print("[COMPOSITOR] Esperando nombre de composición...")
            else:
                UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                    "message": "No hay notas para guardar. Añade notas primero."
                }})
        else:
            # Añadir nota a la composición
            nota = NOTA_MAP.get(sel, None)
            if nota:
                CURRENT_COMPOSITION.append(nota)
                DATA_STATE["composed_notes"].append(nota)
                print(f"[COMPOSITOR] Nota añadida: {nota}. Total: {len(CURRENT_COMPOSITION)}")
                UI_QUEUE.put({"command":"UPDATE_SELECTION", "value": nota})
                UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                    "composed_notes": DATA_STATE["composed_notes"],
                    "message": f"Notas: {len(CURRENT_COMPOSITION)}. Presiona '0' para finalizar."
                }})
            else:
                print(f"[COMPOSITOR] Selección no reconocida: {sel}")
                
    elif DATA_STATE["mode"] == "NEURIFY":
        # Reproducir canción predefinida (C, N, V)
        if sel in PREDEFINED_SONGS:
            song = PREDEFINED_SONGS[sel]
            print(f"[NEURIFY] Reproduciendo canción predefinida: {song['title']}")
            UI_QUEUE.put({"command":"PLAY_SONG", "value": sel})
            UI_QUEUE.put({"command":"UPDATE_SELECTION", "value": song['title']})
            UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                "message": f"Reproduciendo: {song['title']}",
                "current_song_id": sel
            }})
            for nota in song.get('notes', []):
                send_command_to_robot(nota)
                time.sleep(0.2)  # Pausa entre notas (ajusta si es necesario)
        
        
        # Reproducir composición guardada (usando IDs tipo A, B, C, etc.)
        elif sel in DATA_STATE["songs"]:
            song = DATA_STATE["songs"][sel]
            print(f"[NEURIFY] Reproduciendo composición: {song['title']}")
            UI_QUEUE.put({"command":"PLAY_SONG", "value": sel})
            UI_QUEUE.put({"command":"UPDATE_SELECTION", "value": song['title']})
            UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                "message": f"Reproduciendo: {song['title']}",
                "current_song_id": sel
            }})
            # Aquí podrías reproducir las notas en el robot
            for nota in song.get('notes', []):
                send_command_to_robot(nota)
                time.sleep(0.5)  # Pausa entre notas
        else:
            print(f"[NEURIFY] Canción no encontrada: {sel}")
            UI_QUEUE.put({"command":"UPDATE_DATA", "value":{
                "message": f"Canción '{sel}' no encontrada. Selecciona C, N, V o el ID de tu composición."
            }})

def main_loop():
    """Bucle principal que lee .mat y procesa selecciones"""
    global running
    print(f"Iniciando bucle BCI leyendo '{MAT_FILE}'...")
    while running:
        try:
            nuevas = read_new_mat_values()
            for sel in nuevas:
                print(f"[MAT DETECT] {sel}")
                process_selection(sel)
            time.sleep(0.1)
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            print(f"[ERROR] {e}")
    if socket_robot:
        socket_robot.close()
    print("BCI terminado.")

# =================================================================
# III. PUNTO DE ENTRADA
# =================================================================
if __name__ == "__main__":
    # Inicializar canciones predefinidas en DATA_STATE
    DATA_STATE["predefined_songs"] = PREDEFINED_SONGS
    
    root = ctk.CTk()

    # Hilo principal BCI
    bci_thread = threading.Thread(target=main_loop, daemon=True)
    bci_thread.start()

    # Lanzar GUI
    app = ui_app.NeuroPianistApp(root)
    root.mainloop()

    running = False
    sys.exit(0)