"""
============================================================
DIAGRAMA ELECTRICO DE ARQUITECTURA - dibujado a mano en SVG
============================================================
Se abandono schemdraw para esta lamina: amontona las etiquetas cuando
un integrado tiene mas de cuatro o cinco pines, y el resultado era
ilegible. Schemdraw sirve para circuitos discretos (resistencias,
condensadores, fuentes); para conexionado de modulos con muchos pines
un SVG dibujado a proposito es mas claro y no cuesta mas.

La lamina separa visualmente lo que NO hay que mezclar:

    linea gruesa continua  -> potencia 12 V
    linea media continua   -> alimentacion 5 V
    linea fina continua    -> alimentacion 3,3 V
    linea punteada         -> senal logica
    linea a trazos         -> tierra

El punto que mas errores causa en un montaje real es el de tierras: la
tierra de potencia y la de senal deben unirse en UN SOLO punto, junto a
la fuente. Si se unen en varios, la corriente del motor circula por la
tierra de senal y mete ruido en la celda de carga y en el bus I2C. Por
eso aparece marcado explicitamente.
"""
import os

SALIDA = "esquemas"
os.makedirs(SALIDA, exist_ok=True)

W, H = 1180, 720


def bloque(x, y, w, h, titulo, sub="", relleno="#ffffff", borde="#333"):
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" '
         f'fill="{relleno}" stroke="{borde}" stroke-width="1.4"/>\n')
    if sub:
        s += (f'<text x="{x+w/2}" y="{y+h/2-6}" text-anchor="middle" '
              f'font-family="DejaVu Sans, Arial" font-size="14" '
              f'font-weight="600" fill="#111">{titulo}</text>\n')
        s += (f'<text x="{x+w/2}" y="{y+h/2+12}" text-anchor="middle" '
              f'font-family="DejaVu Sans, Arial" font-size="11.5" '
              f'fill="#555">{sub}</text>\n')
    else:
        s += (f'<text x="{x+w/2}" y="{y+h/2+5}" text-anchor="middle" '
              f'font-family="DejaVu Sans, Arial" font-size="14" '
              f'font-weight="600" fill="#111">{titulo}</text>\n')
    return s


def linea(x1, y1, x2, y2, tipo="senal", color=None):
    estilos = {
        "pot12": ("#c0392b", 3.4, ""),
        "pot5":  ("#d68910", 2.4, ""),
        "v33":   ("#1e8449", 1.6, ""),
        "senal": ("#1f4e79", 1.3, "4 3"),
        "gnd":   ("#555555", 1.8, "7 4"),
    }
    c, w, dash = estilos[tipo]
    if color:
        c = color
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{c}" '
            f'stroke-width="{w}"{da} stroke-linecap="round"/>\n')


def poli(pts, tipo="senal"):
    estilos = {"pot12": ("#c0392b", 3.4, ""), "pot5": ("#d68910", 2.4, ""),
               "v33": ("#1e8449", 1.6, ""), "senal": ("#1f4e79", 1.3, "4 3"),
               "gnd": ("#555555", 1.8, "7 4")}
    c, w, dash = estilos[tipo]
    da = f' stroke-dasharray="{dash}"' if dash else ""
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{w}"'
            f'{da} stroke-linejoin="round" stroke-linecap="round"/>\n')


def texto(x, y, t, size=11, anchor="start", color="#333", peso="400"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="DejaVu Sans, Arial" font-size="{size}" '
            f'font-weight="{peso}" fill="{color}">{t}</text>\n')


def generar(economico=False):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">\n<rect width="{W}" height="{H}" '
         f'fill="#ffffff"/>\n']

    s.append(texto(30, 34, "Arquitectura eléctrica — banda transportadora "
                   "de monedas", 17, peso="700", color="#111"))
    sub = ("versión económica · presupuesto de estudiante"
           if economico else "versión de referencia")
    s.append(texto(30, 54, "Sistema logístico de monedas inteligentes · "
                   f"ESP32 · 12 V · {sub}", 12, color="#666"))

    # ---------- columna 1: alimentación ----------
    s.append(bloque(30, 90, 170, 58, "Fuente 12 V / 2 A",
                    "conmutada", "#fdf2f2"))
    s.append(bloque(30, 178, 170, 50, "Fusible F1  2 A", "", "#fdf2f2"))
    s.append(bloque(30, 258, 170, 58, "C1  1000 µF / 25 V",
                    "desacoplo de entrada", "#fdf2f2"))
    s.append(bloque(30, 346, 170, 66, "Buck 12 V → 5 V",
                    "MP1584 · 3 A", "#fef9e7"))
    s.append(bloque(30, 442, 170, 50, "C2  470 µF", "", "#fef9e7"))

    s.append(poli([(115, 148), (115, 178)], "pot12"))
    s.append(poli([(115, 228), (115, 258)], "pot12"))
    s.append(poli([(115, 316), (115, 346)], "pot12"))
    s.append(poli([(115, 412), (115, 442)], "pot5"))

    # ---------- columna 2: driver y motor ----------
    if economico:
        # La banda gira SIEMPRE en el mismo sentido, asi que el puente H
        # completo esta de mas: un MOSFET de canal N en low-side con PWM
        # y un diodo volante hacen el trabajo por la quinta parte.
        s.append(bloque(300, 120, 200, 96, "IRLZ44N + 1N5819",
                        "MOSFET low-side + diodo", "#fdf2f2"))
    else:
        s.append(bloque(300, 120, 200, 96, "TB6612FNG",
                        "1,2 A cont. · 3,2 A pico", "#fdf2f2"))
    s.append(bloque(580, 120, 190, 96, "Motorreductor",
                    ("de impresora, reciclado" if economico
                     else "JGA25-371 12 V · 100 rpm"), "#f4f6f7"))
    s.append(bloque(580, 250, 190, 70, "Encoder Hall",
                    "11 PPR × 34 = 374", "#eaf2f8"))

    # 12 V al driver
    s.append(poli([(200, 119), (250, 119), (250, 142), (300, 142)], "pot12"))
    s.append(texto(206, 112, ("+12 V → motor" if economico else "+12 V → VM"), 10.5, color="#c0392b"))
    # 5 V al driver
    s.append(poli([(200, 467), (250, 467), (250, 166), (300, 166)], "pot5"))
    s.append(texto(256, 186, ("" if economico else "+5 V → VCC"), 10.5, color="#d68910"))

    # driver -> motor
    s.append(poli([(500, 152), (580, 152)], "pot12"))
    s.append(texto(512, 145, ("drain → M" if economico else "AO1 / AO2"), 10.5, color="#c0392b"))

    # ---------- columna 3: ESP32 ----------
    # El bloque generico centra el titulo, y con seis lineas de texto
    # dentro eso lo dejaba encima de "GPIO 25/26". Se dibuja a mano con
    # el titulo arriba.
    s.append('<rect x="300" y="300" width="200" height="150" rx="6" '
             'fill="#eaf2f8" stroke="#333" stroke-width="1.4"/>\n')
    s.append(texto(400, 324, "ESP32", 14, "middle", "#111", "600"))
    s.append(texto(400, 342, "DevKit v1", 11.5, "middle", "#555"))
    if economico:
        s.append(texto(316, 368, "GPIO 27  →  PWM del MOSFET", 10.5))
        s.append(texto(316, 386, "GPIO 34/35  ←  encoder A/B", 10.5))
        s.append(texto(316, 404, "GPIO 18/19  ↔  HX711 (DT/SCK)", 10.5))
        s.append(texto(316, 422, "GPIO 32  ←  TCRT5000", 10.5))
        s.append(texto(316, 440, "GPIO 21/22  ↔  I²C (solo OLED)", 10.5))
    else:
        s.append(texto(316, 368, "GPIO 27  →  PWMA (20 kHz)", 10.5))
        s.append(texto(316, 386, "GPIO 25/26  →  AIN1/AIN2", 10.5))
        s.append(texto(316, 404, "GPIO 13  →  STBY", 10.5))
        s.append(texto(316, 422, "GPIO 34/35  ←  encoder A/B", 10.5))
        s.append(texto(316, 440, "GPIO 21/22  ↔  I²C", 10.5))

    # 5 V al ESP32
    s.append(poli([(200, 467), (250, 467), (250, 430), (300, 430)], "pot5"))
    s.append(texto(206, 462, "+5 V → VIN", 10.5, color="#d68910"))

    # señales ESP32 -> driver
    s.append(poli([(400, 300), (400, 216)], "senal"))
    s.append(texto(406, 262, ("PWM" if economico else "PWM + DIR"), 10.5, color="#1f4e79"))

    # encoder -> ESP32
    s.append(poli([(580, 285), (540, 285), (540, 340), (500, 340)], "senal"))
    s.append(texto(506, 300, "A / B", 10.5, color="#1f4e79"))
    s.append(poli([(675, 216), (675, 250)], "senal"))

    # ---------- columna 4: sensores I2C ----------
    s.append(bloque(830, 300, 200, 58,
                    ("HX711" if economico else "NAU7802"),
                    ("celda de carga · 2 GPIO" if economico
                     else "celda de carga · I²C"), "#eaf2f8"))
    s.append(bloque(830, 378, 200, 58, "SSD1306", "OLED de estado · I²C",
                    "#eaf2f8"))
    s.append(bloque(830, 456, 200, 58,
                    ("TCRT5000" if economico else "E18-D80NK"),
                    "sensor de paso", "#eaf2f8"))

    # bus I2C
    s.append(poli([(500, 434), (790, 434), (790, 211)], "senal"))
    if economico:
        # El HX711 NO es I2C: usa dos GPIO con protocolo propio, asi que
        # su linea no puede colgar del bus. Sale directo del ESP32.
        s.append(poli([(500, 390), (700, 390), (700, 329), (830, 329)],
                      "senal"))
    else:
        s.append(poli([(790, 329), (830, 329)], "senal"))
    s.append(poli([(790, 407), (830, 407)], "senal"))
    s.append(texto(796, 452, "bus I²C 100 kHz", 10.5, color="#1f4e79"))

    # pull-ups
    # Reubicadas: en (700,180) se solapaban con el motorreductor
    # (x 580-770, y 120-216) y su etiqueta caia sobre el encoder.
    s.append(bloque(850, 180, 160, 62, "Rp1 · Rp2", "4,7 kΩ a 3,3 V",
                    "#eafaf1"))
    s.append(poli([(850, 211), (790, 211)], "v33"))
    s.append(texto(796, 202, "pull-ups", 10.5, "start", "#1e8449"))

    # sensor de paso -> ESP32
    s.append(poli([(830, 485), (660, 485), (660, 450), (500, 450)], "senal"))
    s.append(texto(666, 478, "salida NPN, colector abierto", 10.5,
                   color="#1f4e79"))

    # ---------- tierra común ----------
    s.append(bloque(300, 556, 480, 54, "TIERRA COMÚN — un solo punto de unión",
                    "", "#f2f3f4"))
    for x0 in (115, 400, 675, 930):
        s.append(poli([(x0, 540), (x0, 556)], "gnd"))
    s.append(poli([(115, 540), (930, 540)], "gnd"))
    s.append(texto(300, 534, "GND potencia + GND señal se unen aquí y solo "
                   "aquí", 10.5, color="#555"))

    # ---------- leyenda ----------
    ly = 648
    s.append(texto(30, ly - 10, "Leyenda", 12, peso="700", color="#111"))
    items = [("pot12", "12 V potencia"), ("pot5", "5 V"),
             ("v33", "3,3 V"), ("senal", "señal lógica"),
             ("gnd", "tierra")]
    x = 30
    for tipo, etq in items:
        s.append(poli([(x, ly + 8), (x + 34, ly + 8)], tipo))
        s.append(texto(x + 42, ly + 12, etq, 11))
        x += 150

    s.append(texto(30, ly + 44,
                   "Nota: el motor y el ESP32 comparten tierra pero NO "
                   "comparten el regulador. Alimentar el motor desde el "
                   "pin 5 V del ESP32 provoca reinicios por caída de "
                   "tensión.", 10.5, color="#777"))

    s.append("</svg>\n")
    return "".join(s)


if __name__ == "__main__":
    for eco, nombre in ((False, "arquitectura_electrica.svg"),
                        (True, "arquitectura_electrica_economica.svg")):
        ruta = os.path.join(SALIDA, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(generar(economico=eco))
        print(f"  -> {ruta}")
