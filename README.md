<div align="center">

<br/>

```
███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗ ██████╗ ██╗ █████╗ ███╗   ██╗██╗███████╗████████╗
████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗██╔══██╗██║██╔══██╗████╗  ██║██║██╔════╝╚══██╔══╝
██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║██████╔╝██║███████║██╔██╗ ██║██║███████╗   ██║   
██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔═══╝ ██║██╔══██║██║╚██╗██║██║╚════██║   ██║   
██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝██║     ██║██║  ██║██║ ╚████║██║███████║   ██║   
╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚══════╝   ╚═╝   
```

### _Tocar música con el cerebro. Sin manos._

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![ABB Robot](https://img.shields.io/badge/ABB_Robot-RAPID-FF6F00?style=for-the-badge&logo=robot-framework&logoColor=white)](https://new.abb.com/products/robotics)
[![EEG](https://img.shields.io/badge/EEG-Unicorn_Hybrid_Black-8A2BE2?style=for-the-badge)](https://www.unicorn-bi.com/)
[![BCI](https://img.shields.io/badge/Interface-Brain--Computer-00CED1?style=for-the-badge)](https://en.wikipedia.org/wiki/Brain%E2%80%93computer_interface)
[![RobotStudio](https://img.shields.io/badge/Simulation-RobotStudio-FF6F00?style=for-the-badge)](https://new.abb.com/products/robotics/robotstudio)

<br/>

> **Proyecto Académico** · Robótica de Servicios · Ingeniería Robótica · Curso 2025/26

</div>

---

## ⚡ ¿Qué es NeuroPianist?

**NeuroPianist** conecta la actividad cerebral humana con un robot industrial para hacer algo que hasta hace poco parecía ciencia ficción: **tocar un piano usando únicamente la atención visual.**

El usuario lleva puesto un casco EEG (**Unicorn Hybrid Black**). Mira fijamente una letra en pantalla. El sistema decodifica esa intención cerebral y la transforma en una orden que viaja, en tiempo real, a un **brazo robótico ABB** que pulsa la tecla correspondiente del piano.

Sin manos. Sin voz. Solo pensamiento → música.

---

## 🧠 Arquitectura del Sistema

```
┌─────────────────┐     UDP      ┌──────────────────┐     TCP/IP    ┌─────────────────┐
│  CASCO EEG      │ ──────────▶  │   PYTHON BACKEND │ ────────────▶ │  ROBOT ABB      │
│  Unicorn Hybrid │             │                  │               │  (RAPID)        │
│  Black          │             │  guardarDatos.py │               │                 │
│                 │             │  leerDatos.py    │               │  Pulsa teclas   │
│  Señales EEG    │             │  interfaz_pau.py │               │  del piano      │
│  → Unicorn      │             │                  │               │                 │
│    Speller      │             │  .mat ──▶ notas  │               │  ♪ ♫ ♪ ♫       │
└─────────────────┘             └──────────────────┘               └─────────────────┘
         │                               │
         │                               ▼
         │                    ┌──────────────────┐
         │                    │  INTERFAZ GUI    │
         └───────────────────▶│  (customtkinter) │
           Selección visual   │                  │
                              │  • Modo Normal   │
                              │  • Compositor    │
                              │  • Neurify       │
                              └──────────────────┘
```

---

## 🎯 Modos de Operación

### 🎹 Modo Normal — _Tiempo Real_
El usuario selecciona una letra con la mirada → el robot pulsa esa nota al instante.

| Comando BCI | Nota |
|:-----------:|:----:|
| `D` | Do |
| `R` | Re |
| `M` | Mi |
| `F` | Fa |
| `S` | Sol |
| `L` | La |
| `I` | Si |
| `O` | Do⁺ |

---

### ✏️ Modo Compositor — _Crea tu partitura_
Selecciona notas una a una para construir una secuencia. Cuando terminas, le das un nombre letra por letra y la guardas. El robot la ejecutará íntegra cuando quieras.

```
Seleccionar nota → [D][R][M][F]... → [0] Finalizar → Escribir nombre → [N] Guardar
```

---

### 🎧 Modo Neurify — _Tu playlist BCI_
Reproduce canciones predefinidas o tus propias composiciones guardadas. El robot las interpreta en el piano de principio a fin.

```
[C] → Cumpleaños Feliz
[N] → Noche de Paz
[V] → Feliz Navidad
[A], [B]... → Tus composiciones
```

---

## 🔧 Cómo funciona por dentro

### 1. Captura de señal EEG → `guardarDatos.py`

El **Unicorn Speller** emite los datos por UDP. El problema: la aplicación serializa los datos en formato `BinaryFormatter.NET`, sin opción de exportación directa.

**Solución ingeniosa:** analizamos los paquetes UDP en hexadecimal, identificamos el patrón fijo `\x06\x06\x00\x00\x00\x01` y leemos el byte de selección exactamente 6 posiciones después. Cada selección válida se guarda automáticamente en `speller_selections.mat`.

```python
patron = b'\x06\x06\x00\x00\x00\x01'
patron_start_index = data_bytes.find(patron)
char_index = patron_start_index + 6
selection = data_bytes[char_index:char_index + 1].decode('ascii')
```

### 2. Procesamiento y envío al robot → `leerDatos.py`

Un hilo BCI monitoriza continuamente el `.mat`. Cuando detecta una nueva selección, la interpreta según el modo activo y envía el comando al robot ABB vía **socket TCP/IP**.

```python
# Arquitectura multihilo para no bloquear la GUI
bci_thread = threading.Thread(target=main_loop, daemon=True)
bci_thread.start()
root.mainloop()  # GUI en hilo principal
```

### 3. Robot ABB — `simulacion_final.rspag`

Programado en **RAPID** con tres puntos por tecla (Home → Approach → Pulse) y offsets de 30mm entre teclas. Tool personalizada diseñada e impresa en 3D para un contacto preciso con las teclas.

---

## 🚀 Instalación y Uso

### Requisitos
```bash
pip install customtkinter scipy numpy Pillow
```

### Orden de ejecución

```bash
# 1. Iniciar captura BCI (conectar Unicorn Speller primero)
python guardarDatos.py

# 2. Iniciar simulación en RobotStudio (o encender robot real)
#    → Dale play al programa RAPID

# 3. Lanzar interfaz principal
python leerDatos.py
```

> ⚠️ Para usar con robot real, cambiar `ROBOT_IP = "127.0.0.1"` por la IP del controlador ABB en `leerDatos.py`.

---

## 🗂️ Estructura del Proyecto

```
NeuroPianist/
├── guardarDatos.py          # Servidor UDP → captura selecciones EEG → .mat
├── leerDatos.py             # Backend BCI + lógica de modos + envío TCP al robot
├── interfaz_pau.py          # GUI (customtkinter) con los 3 modos
├── simulacion_final.rspag   # Escenario RobotStudio (simulación + robot real)
├── speller_selections.mat   # Generado en tiempo real (selecciones BCI)
└── VÍDEO FINAL.mp4          # Demo del sistema completo
```

---

## ⚔️ Retos Técnicos Superados

| Reto | Solución |
|------|----------|
| Unicorn Speller no permite exportar datos directamente | Ingeniería inversa del paquete UDP para localizar el byte de selección |
| GUI bloqueada esperando señales BCI | Arquitectura multihilo con `threading` + `queue` |
| Posiciones virtuales ≠ posiciones físicas del piano | Recalibración de puntos RAPID en el entorno real |
| Tecla no suena: ni muy fuerte ni muy débil | Ajuste fino de velocidades, zonas de aproximación y herramienta 3D |
| Conexión Bluetooth intermitente en pruebas finales | Cambio de portátil y reconfiguración del driver |

---

## 👥 Equipo

| Nombre |
|--------|
| Paula Arredondo Escamilla |
| Ruth Cremades Martínez |
| Marta Andrada Moñino |
| Nicolás Fernández Blánquez |
| Klaudia Martínez Bautista |
| Raquel Mollá Bañón |

---

## 📚 Contexto Académico

**Asignatura:** Robótica de Servicios  
**Titulación:** Ingeniería Robótica  
**Curso:** 2025/26  

---

<div align="center">

**Hardware utilizado:**  
Unicorn Hybrid Black (EEG) · Robot ABB · Piano físico · Herramienta impresa en 3D

**Stack tecnológico:**  
Python · customtkinter · scipy · socket TCP/UDP · ABB RAPID · RobotStudio · MATLAB .mat

<br/>

_"Transformar la intención mental en música a través de un robot no solo evidencia el potencial de las BCI como herramientas intuitivas de control, sino que también abre un espacio para explorar aplicaciones artísticas, educativas y experimentales donde el cerebro se convierte en un instrumento más."_

<br/>

⭐ Si te parece interesante, dale una estrella al repo

</div>
