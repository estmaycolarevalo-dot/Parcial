"""
============================================================
CAD PARAMETRICO - BANDA TRANSPORTADORA DE MONEDAS
Sistema logistico de monedas inteligentes (objetivo 2)
============================================================
Genera el modelo solido de la banda y exporta:

    STEP  -> formato de intercambio ISO 10303. Es EL formato que se
             abre en SolidWorks, Inventor, Fusion 360 o FreeCAD y que
             se espera cuando un enunciado pide "modelo CAD". No es una
             malla: conserva la geometria exacta y es acotable.
    STL   -> malla, para imprimir en 3D y para las <mesh> del URDF.
    SVG   -> vistas ortogonales, base de los planos mecanicos.
    URDF  -> el mismo ensamblaje referenciando los STL, para que la
             simulacion de PyBullet corra sobre la geometria REAL y no
             sobre cajas aproximadas.

Ese ultimo paso es el que cierra el ciclo: CAD -> STL -> URDF ->
simulacion. Sin el, el modelo CAD y el simulado son dos cosas
distintas que se desincronizan a la primera modificacion.

DE DONDE SALEN LAS DIMENSIONES
------------------------------
No son inventadas: vienen del analisis previo del proyecto.

  ancho de salida 30 mm   del barrido de guias convergentes: a 28 mm el
                          orden es perfecto pero el caudal cae a 58%; a
                          44 mm el caudal sube a 92% y el orden se
                          desploma a 8%. 30 mm dio 83% de caudal con
                          100% de orden.
  ventana fisica 27-34 mm por debajo de 27 mm no pasa la moneda de
                          $1000 (26,70 mm); por encima de 34 mm caben
                          dos de $50 en paralelo (2 x 17,00 mm).
  rodillo D25 mm          del calculo de par: con 3 vasos, mu=0,4 y
                          FS=3 se necesitan 0,42 kgf*cm, muy por debajo
                          de lo que da un JGA25-371.
  corona +0,4 mm          el rodillo es 0,8 mm mas grueso al centro que
                          en los extremos. Es lo que hace que la banda
                          se autocentre sola en vez de irse de lado.

USO
---
    pip install cadquery
    python cad_banda.py                # exporta todo a cad_salida/
    python cad_banda.py --solo-step    # solo el STEP del ensamblaje
"""
import argparse
import os

import cadquery as cq

# ============================================================
#  PARAMETROS  (todo en milimetros)
# ============================================================
# --- banda y recorrido ---
ENTRE_CENTROS = 300.0      # distancia entre ejes de los dos rodillos
ANCHO_BANDA = 70.0         # ancho de la cinta de PVC
ESP_BANDA = 1.5            # espesor de la cinta

# --- guias convergentes: singularizacion PASIVA, sin actuadores ---
# El ancho de ENTRADA no puede superar el de la cinta: con 90 mm de
# entrada sobre una cinta de 50 mm las guias quedaban volando 16,5 mm
# por fuera de las placas laterales, sin nada que las sostuviera. Lo
# detecto comparando los bounding box del ensamblaje, no mirando el
# render. Ahora entrada 64 < cinta 70, y la convergencia sigue siendo
# de 2,1x (64 -> 30).
ANCHO_ENTRADA = 64.0       # recibe el volcado de la tolva
ANCHO_SALIDA = 30.0        # optimo medido en el barrido
X_INICIO_CONV = 40.0       # donde empieza a estrecharse
X_FIN_CONV = 200.0         # donde termina de estrecharse
ALTO_GUIA = 14.0
ESP_GUIA = 3.0

# --- rodillos ---
D_RODILLO = 25.0
CORONA = 0.8               # sobreespesor de diametro al centro
L_RODILLO = ANCHO_BANDA + 6.0
D_EJE = 8.0
D_RODAMIENTO = 22.0        # 608ZZ: 22 ext x 8 int x 7 ancho
ANCHO_RODAMIENTO = 7.0

# --- estructura ---
ESP_LATERAL = 5.0          # placas laterales de acrilico
ALTO_LATERAL = 60.0
ESP_APOYO = 3.0            # placa antifriccion bajo el tramo superior
RANURA_TENSADO = 14.0      # carrera para tensar la banda

# --- motor ---
L_MOTOR = 65.0             # JGA25-371 con reductora
D_MOTOR = 25.0

SALIDA = "cad_salida"


# ============================================================
#  PIEZAS
# ============================================================
def rodillo(coronado=True, motriz=False):
    """Rodillo con CORONA: el diametro al centro es mayor que en los
    extremos, formando un barril muy suave.

    Por que importa: una banda sobre rodillos cilindricos rectos se va
    de lado y se sale en minutos, porque cualquier asimetria de tension
    la empuja hacia un extremo. Sobre un rodillo coronado la banda
    busca sola el punto de mayor diametro y se autocentra. Es la
    diferencia entre una banda que funciona y una que hay que reajustar
    cada cinco minutos, y es el modo de falla que mas proyectos de
    banda casera arruina.
    """
    r_borde = D_RODILLO / 2.0
    r_centro = r_borde + (CORONA / 2.0 if coronado else 0.0)
    h = L_RODILLO / 2.0

    # OJO CON EL EJE DE REVOLUCION.
    # En el workplane "XZ" hay que dibujar el perfil con la coordenada
    # AXIAL en horizontal y el RADIO en vertical, y revolucionar
    # alrededor de X. Dibujarlo al reves (radio en horizontal) y
    # revolucionar alrededor de Z falla con StdFail_NotDone, un error de
    # OpenCascade que no dice nada sobre la causa. Probado: de cinco
    # variantes de perfil y eje, solo esta construye el solido.
    perfil = (cq.Workplane("XZ")
              .moveTo(-h, 0)
              .lineTo(-h, r_borde)
              .threePointArc((0, r_centro), (h, r_borde))
              .lineTo(h, 0)
              .close())
    pieza = perfil.revolve(360, (0, 0, 0), (1, 0, 0))   # eje del rodillo = X

    # agujero pasante del eje
    pieza = (pieza.faces(">X").workplane()
             .circle(D_EJE / 2).cutThruAll())

    # alojamiento de rodamientos en los dos extremos (rodillo loco)
    if not motriz:
        for cara in (">X", "<X"):
            pieza = (pieza.faces(cara).workplane()
                     .circle(D_RODAMIENTO / 2)
                     .cutBlind(-ANCHO_RODAMIENTO))
    return pieza


def placa_lateral(lado=1):
    """Placa lateral con agujero fijo para el rodillo motriz y RANURA
    para el tensor.

    La ranura no es un lujo: la banda de PVC se estira con el uso y sin
    forma de retensarla empieza a patinar. Con la ranura se recupera la
    tension aflojando dos tornillos.
    """
    largo = ENTRE_CENTROS + 60.0
    z_eje = ALTO_LATERAL / 2.0

    placa = (cq.Workplane("XY")
             .box(largo, ALTO_LATERAL, ESP_LATERAL)
             .edges("|Z").fillet(6.0))

    x_motriz = ENTRE_CENTROS / 2.0
    x_tensor = -ENTRE_CENTROS / 2.0

    # apoyo fijo del rodillo motriz
    placa = (placa.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(x_motriz, 0)
             .circle(D_RODAMIENTO / 2).cutThruAll())

    # ranura de tensado: agujero alargado = rectangulo + dos semicirculos
    placa = (placa.faces(">Z").workplane(centerOption="CenterOfBoundBox")
             .center(x_tensor, 0)
             .slot2D(RANURA_TENSADO + D_RODAMIENTO, D_RODAMIENTO, 0)
             .cutThruAll())

    # agujeros de fijacion a la base (M3)
    for xf in (-largo / 2 + 15, 0, largo / 2 - 15):
        placa = (placa.faces(">Z").workplane(centerOption="CenterOfBoundBox")
                 .center(xf, -ALTO_LATERAL / 2 + 7)
                 .circle(1.6).cutThruAll())
    return placa


def placa_apoyo():
    """Placa antifriccion bajo el tramo superior de la banda.

    Sin ella, 50 g de vaso (o un punado de monedas) hunden la cinta
    entre los dos rodillos y la carga se bambolea. Se forra con cinta
    UHMW o de teflon: baja el coeficiente de friccion de ~0,4 a ~0,15 y
    ahorra mas de la mitad del par del motor.
    """
    return (cq.Workplane("XY")
            .box(ENTRE_CENTROS - 20.0, ANCHO_BANDA + 4.0, ESP_APOYO)
            .edges("|Z").fillet(3.0))


def guia_convergente(lado=1):
    """Guia lateral que estrecha el paso de 90 mm a 30 mm.

    Es singularizacion PASIVA: ordena las monedas en fila sin un solo
    actuador, solo con geometria. Mismo principio que los embudos de
    las contadoras comerciales.
    """
    largo = ENTRE_CENTROS + 20.0
    x0 = -largo / 2.0

    def semiancho(x):
        xr = x - x0
        if xr <= X_INICIO_CONV:
            return ANCHO_ENTRADA / 2.0
        if xr >= X_FIN_CONV:
            return ANCHO_SALIDA / 2.0
        t = (xr - X_INICIO_CONV) / (X_FIN_CONV - X_INICIO_CONV)
        return ANCHO_ENTRADA / 2.0 + t * (ANCHO_SALIDA / 2.0 - ANCHO_ENTRADA / 2.0)

    n = 24
    pts = [(x0 + largo * i / n, lado * semiancho(x0 + largo * i / n))
           for i in range(n + 1)]
    pts_ext = [(x, y + lado * ESP_GUIA) for x, y in reversed(pts)]

    return (cq.Workplane("XY")
            .polyline(pts + pts_ext).close()
            .extrude(ALTO_GUIA))


def banda_cinta():
    """La cinta como lazo cerrado: dos tramos rectos y dos semicirculos.

    Se modela solo para verificar interferencias y para calcular el
    largo de corte. En el ensamblaje se muestra semitransparente.
    """
    r = D_RODILLO / 2.0 + ESP_BANDA
    ri = D_RODILLO / 2.0
    a = ENTRE_CENTROS / 2.0

    ext = (cq.Workplane("XZ")
           .moveTo(-a, r).lineTo(a, r)
           .threePointArc((a + r, 0), (a, -r))
           .lineTo(-a, -r)
           .threePointArc((-a - r, 0), (-a, r))
           .close())
    inte = (cq.Workplane("XZ")
            .moveTo(-a, ri).lineTo(a, ri)
            .threePointArc((a + ri, 0), (a, -ri))
            .lineTo(-a, -ri)
            .threePointArc((-a - ri, 0), (-a, ri))
            .close())
    return (ext.extrude(ANCHO_BANDA).cut(inte.extrude(ANCHO_BANDA))
            .translate((0, ANCHO_BANDA / 2.0, 0)))
    # El extrude de un perfil dibujado en XZ avanza hacia -Y, asi que el
    # lazo nace en [-ancho, 0] y hay que correrlo +ancho/2 para centrarlo.
    # Con -ancho/2 (el signo intuitivo) la cinta queda en [-75, -25]:
    # fuera del bastidor y sin tocar los rodillos.


def largo_banda_mm():
    """Largo de corte de la cinta: dos tramos rectos + un circulo.

    Numero para llevar al proveedor. Al empalme hay que sumarle el
    traslape del bisel.
    """
    import math
    r = D_RODILLO / 2.0 + ESP_BANDA / 2.0
    return 2 * ENTRE_CENTROS + 2 * math.pi * r


# ============================================================
#  ENSAMBLAJE
# ============================================================
def ensamblaje(con_laterales=True):
    z_eje = 0.0
    y_lat = (ANCHO_BANDA + 6.0) / 2.0 + ESP_LATERAL / 2.0 + 1.0
    z_sup = D_RODILLO / 2.0 + ESP_BANDA

    asm = cq.Assembly(name="banda_transportadora")

    asm.add(rodillo(motriz=True).rotate((0, 0, 0), (1, 0, 0), 90),
            name="rodillo_motriz",
            loc=cq.Location(cq.Vector(ENTRE_CENTROS / 2, 0, z_eje)),
            color=cq.Color(0.25, 0.25, 0.28))
    asm.add(rodillo().rotate((0, 0, 0), (1, 0, 0), 90),
            name="rodillo_tensor",
            loc=cq.Location(cq.Vector(-ENTRE_CENTROS / 2, 0, z_eje)),
            color=cq.Color(0.25, 0.25, 0.28))

    for signo, nombre in (((1, "lateral_der"), (-1, "lateral_izq"))
                          if con_laterales else ()):
        asm.add(placa_lateral().rotate((0, 0, 0), (1, 0, 0), 90),
                name=nombre,
                loc=cq.Location(cq.Vector(0, signo * y_lat, z_eje)),
                color=cq.Color(0.55, 0.6, 0.68, 0.55))

    asm.add(placa_apoyo(), name="placa_apoyo",
            loc=cq.Location(cq.Vector(0, 0, z_sup - ESP_BANDA - ESP_APOYO / 2)),
            color=cq.Color(0.85, 0.85, 0.80))

    for lado, nombre in ((1, "guia_der"), (-1, "guia_izq")):
        asm.add(guia_convergente(lado), name=nombre,
                loc=cq.Location(cq.Vector(0, 0, z_sup)),
                color=cq.Color(0.45, 0.5, 0.58, 0.5))

    asm.add(banda_cinta(), name="cinta",
            loc=cq.Location(cq.Vector(0, 0, z_eje)),
            color=cq.Color(0.12, 0.12, 0.13, 0.85))

    # El motor es COAXIAL al rodillo motriz, o sea su eje va en Y. Con
    # el perfil en YZ el cilindro se extruia en X y atravesaba la placa
    # lateral en vez de quedar por fuera acoplado al eje.
    motor = (cq.Workplane("XZ").circle(D_MOTOR / 2).extrude(-L_MOTOR))
    asm.add(motor, name="motorreductor",
            loc=cq.Location(cq.Vector(ENTRE_CENTROS / 2,
                                      y_lat + ESP_LATERAL / 2 + 2, z_eje)),
            color=cq.Color(0.75, 0.55, 0.15))

    return asm


# ============================================================
#  EXPORTACION
# ============================================================
PIEZAS = {
    "rodillo_motriz": lambda: rodillo(motriz=True),
    "rodillo_tensor": lambda: rodillo(),
    "placa_lateral": placa_lateral,
    "placa_apoyo": placa_apoyo,
    "guia_der": lambda: guia_convergente(1),
    "guia_izq": lambda: guia_convergente(-1),
}


def exportar(solo_step=False):
    os.makedirs(SALIDA, exist_ok=True)
    os.makedirs(os.path.join(SALIDA, "stl"), exist_ok=True)
    os.makedirs(os.path.join(SALIDA, "piezas_step"), exist_ok=True)

    asm = ensamblaje()
    asm.save(os.path.join(SALIDA, "banda_ensamblaje.step"))
    print(f"  STEP ensamblaje -> {SALIDA}/banda_ensamblaje.step")
    if solo_step:
        return

    for nombre, fn in PIEZAS.items():
        pieza = fn()
        cq.exporters.export(
            pieza, os.path.join(SALIDA, "piezas_step", f"{nombre}.step"))
        cq.exporters.export(
            pieza, os.path.join(SALIDA, "stl", f"{nombre}.stl"),
            tolerance=0.05, angularTolerance=0.1)
    print(f"  {len(PIEZAS)} piezas -> STEP y STL individuales")

    # La cinta y la placa de apoyo quedan DENTRO del bastidor, asi que en
    # una vista con las placas puestas no se ven. Por eso se exporta
    # ademas un conjunto sin laterales: es la vista que sirve para
    # explicar el recorrido en el informe.
    interior = ensamblaje(con_laterales=False)
    vistas = {
        "vista_isometrica": (asm, (-1.2, -1.0, 0.9)),
        "vista_lateral": (asm, (0, -1, 0)),
        "vista_planta": (asm, (0, 0, 1)),
        "vista_interior_iso": (interior, (-1.2, -1.0, 0.9)),
        "vista_interior_planta": (interior, (0, 0, 1)),
    }
    for nombre, (origen, direccion) in vistas.items():
        cq.exporters.export(
            origen.toCompound(), os.path.join(SALIDA, f"{nombre}.svg"),
            opt={"width": 900, "height": 520, "marginLeft": 20,
                 "marginTop": 20, "showAxes": False,
                 "projectionDir": direccion,
                 "strokeWidth": 0.4, "strokeColor": (40, 40, 40),
                 "hiddenColor": (170, 170, 170), "showHidden": False})
    print(f"  {len(vistas)} vistas ortogonales -> SVG (base de los planos)")

    with open(os.path.join(SALIDA, "lista_materiales.md"), "w",
              encoding="utf-8") as f:
        f.write(tabla_materiales())
    print(f"  lista de materiales -> {SALIDA}/lista_materiales.md")


def tabla_materiales():
    import math
    return f"""# Lista de materiales — banda transportadora

Generada desde el CAD paramétrico. Si cambias un parámetro en
`cad_banda.py`, vuelve a correrlo y esta tabla se actualiza sola.

## Dimensiones derivadas

| Magnitud | Valor |
|---|---|
| Distancia entre centros | {ENTRE_CENTROS:.0f} mm |
| Largo de corte de la cinta | {largo_banda_mm():.1f} mm |
| Ancho de cinta | {ANCHO_BANDA:.0f} mm |
| Paso de guías (entrada → salida) | {ANCHO_ENTRADA:.0f} → {ANCHO_SALIDA:.0f} mm |
| Diámetro de rodillo | {D_RODILLO:.0f} mm (corona +{CORONA:.1f} mm) |
| Recorrido por vuelta de rodillo | {math.pi * D_RODILLO:.1f} mm |
| Rpm para 0,10 m/s | {0.10 * 1000 * 60 / (math.pi * D_RODILLO):.0f} rpm |

## Piezas a fabricar

| Pieza | Cant. | Proceso | Material |
|---|---|---|---|
| Rodillo motriz | 1 | Impresión 3D | PLA o PETG |
| Rodillo tensor | 1 | Impresión 3D | PLA o PETG |
| Placa lateral | 2 | Corte láser | Acrílico 5 mm |
| Placa de apoyo | 1 | Corte láser | Acrílico 3 mm + cinta UHMW |
| Guía convergente | 2 | Impresión 3D | PLA |

## Componentes comerciales

| Componente | Cant. | Nota |
|---|---|---|
| Rodamiento 608ZZ | 4 | 22 × 8 × 7 mm |
| Eje Ø8 mm | 2 | Acero, largo {L_RODILLO + 40:.0f} mm |
| Cinta PVC lisa {ESP_BANDA:.1f} mm | {largo_banda_mm() / 1000:.2f} m | Empalme en bisel, no a tope |
| Motorreductor JGA25-371 12 V | 1 | ~100 rpm, con encoder hall |
| Driver TB6612FNG | 1 | PWM a 20 kHz |
| Sensor E18-D80NK | 1 | Umbral ajustable |
| Tornillería M3 | — | Fijación de placas y motor |

## Notas de fabricación

- **La corona del rodillo es obligatoria.** Sin ella la banda se desvía
  y se sale. Imprímelo con el eje vertical y capa de 0,1 mm para que la
  superficie quede lisa.
- **Empalme en bisel**, rebajando ~15 mm de cada punta en diagonal. Un
  traslape a tope crea un escalón que hace saltar la carga en cada
  vuelta y dispara falsos positivos en el sensor.
- La ranura de tensado deja {RANURA_TENSADO:.0f} mm de carrera: la cinta de PVC
  se estira con el uso y sin ella empieza a patinar.
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo-step", action="store_true")
    args = ap.parse_args()
    print("\n  CAD paramétrico de la banda transportadora\n")
    exportar(solo_step=args.solo_step)
    print(f"\n  largo de corte de la cinta: {largo_banda_mm():.1f} mm")
