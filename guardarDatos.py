import socket
import datetime
from scipy.io import savemat
import numpy as np
import time 

UDP_IP = "127.0.0.1"
UDP_PORT = 8888     #cuando se cambie de ordenador, mirar el network output y cambiar el puerto
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(0.5)   # suficiente para permitir Ctrl+C

# =================================================================
# Variables para almacenar los datos
# =================================================================
timestamps = []
selections = []

def buscar_seleccion_en_paquete(data_bytes):
    """
    Intenta encontrar el caracter de la selección buscando un patrón fijo.
    Se asume que la selección está 6 bytes después del patrón \x06\x06\x00\x00\x00\x01.
    """
    patron = b'\x06\x06\x00\x00\x00\x01'
    
    try:
        patron_start_index = data_bytes.find(patron)
        
        if patron_start_index != -1:
            # El byte del carácter está 6 bytes después del inicio del patrón
            char_index = patron_start_index + 6
            selection_byte = data_bytes[char_index:char_index + 1]
            selection = selection_byte.decode('ascii')
            return selection.strip(), char_index
            
    except Exception as e:
        f"Error en búsqueda: {e}", 1500
        return "ERROR", -1
        
    "NO ENCONTRADA", 1500
    return "NO_ENCONTRADA_O_ERROR", -1
        

def guardar_datos_mat(filename="speller_selections.mat"):
    """Guarda las listas de datos en un archivo .mat"""
    
    # Convertir las listas a arrays de numpy para compatibilidad con .mat
    data_to_save = {
        'timestamps': np.array(timestamps),
        'selections': np.array(selections, dtype=object), 
    }
    
    # Guardar el diccionario en el archivo .mat
    try:
        savemat(filename, data_to_save)
        print(f"Datos guardados → Total: {len(selections)} selecciones")
    except Exception as e:
       print(f"ERROR al guardar: {e}")

# =================================================================
# Bucle principal de recepción
# =================================================================
print("Guardado DINÁMICO activado → ...")
print("Cada selección se guarda automáticamente en 'speller_selections.mat'.")
print("Esperando selecciones del Unicorn Speller...")
print("-" * 70)

try:
    while True:
        
        try:
            data, _ = sock.recvfrom(65535)
        except socket.timeout:
            continue  # no llegó nada, pero no rompas el programa
        
        selection, index = buscar_seleccion_en_paquete(data)
        
        timestamp = datetime.datetime.now().isoformat()
        
        if selection == "NO_ENCONTRADA_O_ERROR":
            # Ignorar paquetes que no contienen una selección válida
            pass  # Silencioso para no saturar la consola
        else:
            print(f"\n{timestamp}")
            print(f"SELECCIÓN: '{selection}'")
            
            # Almacenar los datos en las listas
            timestamps.append(timestamp)
            selections.append(selection)
            
            # *** GUARDADO DINÁMICO: Guardar inmediatamente después de cada selección ***
            guardar_datos_mat()
             
             
except KeyboardInterrupt:
    print("\n" + "=" * 70)
    print("Script detenido por el usuario (Ctrl+C).")
    print(f"Total de selecciones capturadas: {len(selections)}")
    
finally:
    sock.close()
    print("Conexión UDP cerrada.")