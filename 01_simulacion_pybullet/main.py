# ============================================================
# SIMULACIÓN COMPLETA - Sistema de Logística de Monedas Inteligentes
# ============================================================
# Une los dos módulos que ya probamos por separado:
#   1) Banda + estación de visión (YOLO placeholder) que clasifica
#      monedas en 3 bandejas (Colombia / Extranjera / Botón).
#   2) Dron que recoge un vaso y lo lleva por una pista con 3
#      obstáculos hasta la meta.
#
# Cómo se conectan:
#   Cada vez que se han clasificado MONEDAS_POR_VASO monedas
#   (y el dron no está ocupado), se arma un vaso en el punto de
#   recolección (junto a las bandejas) y el dron despega con él.
#   Mientras el dron vuela, la banda sigue clasificando monedas
#   normalmente (son procesos independientes, igual que en el
#   sistema real).
#
# Próxima etapa: reemplazar clasificar_moneda_YOLO() por la
# inferencia real + I2C, y el "armado del vaso" por el brazo
# robótico (joint_1/joint_2 del URDF base) tapándolo de verdad.
# ============================================================

import pybullet as p
import pybullet_data
import time
import math
import random

# ============================================================
# CONEXIÓN Y ESCENA BASE
# ============================================================
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
p.resetDebugVisualizerCamera(cameraDistance=7.5, cameraYaw=40, cameraPitch=-45,
                              cameraTargetPosition=[3.5, 1.0, 0.5])

# Piso gris sólido
piso_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[20, 20, 0.05])
piso_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[20, 20, 0.05],
                                rgbaColor=[0.75, 0.75, 0.78, 1])
p.createMultiBody(baseMass=0, baseCollisionShapeIndex=piso_col,
                   baseVisualShapeIndex=piso_vis, basePosition=[3.5, 1.0, -0.05])

robot_id = p.loadURDF("maqueta.urdf", [0, 0, 0], useFixedBase=True)

# --- Mapear nombres de links a índices (igual que en simulacion_clasificador.py) ---
link_index = {}
for i in range(p.getNumJoints(robot_id)):
    info = p.getJointInfo(robot_id, i)
    link_index[info[12].decode("utf-8")] = i

LED_COLOMBIA = link_index["led_colombia"]
LED_EXTRANJERA = link_index["led_extranjera"]
LED_BOTON = link_index["led_boton"]

COLOR_APAGADO = [0.2, 0.2, 0.2, 1]
COLOR_COLOMBIA = [0.05, 0.85, 0.25, 1]
COLOR_EXTRANJERA = [0.15, 0.4, 0.95, 1]
COLOR_BOTON = [0.6, 0.6, 0.6, 1]

# ============================================================
# MÓDULO 1: BANDA + CLASIFICADOR (igual que simulacion_clasificador.py)
# ============================================================
STATION_X = 0.3
BELT_Y = 0.0
BELT_Z = 0.66
BELT_SPEED = 0.01
DIVERT_SPEED = 0.015
SPAWN_EVERY_STEPS = 150

BINS = {
    "colombia":   {"y": 0.6,  "color": COLOR_COLOMBIA,   "led": LED_COLOMBIA},
    "extranjera": {"y": 0.95, "color": COLOR_EXTRANJERA, "led": LED_EXTRANJERA},
    "boton":      {"y": 1.3,  "color": COLOR_BOTON,      "led": LED_BOTON},
}

contador = {"colombia": 0, "extranjera": 0, "boton": 0}
monedas = []


def crear_moneda():
    col_shape = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.05, height=0.02)
    vis_shape = p.createVisualShape(p.GEOM_CYLINDER, radius=0.05, length=0.02,
                                     rgbaColor=[0.85, 0.75, 0.2, 1])
    body_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col_shape,
                                 baseVisualShapeIndex=vis_shape,
                                 basePosition=[-0.9, BELT_Y, BELT_Z])
    return {"id": body_id, "x": -0.9, "y": BELT_Y, "estado": "avanzando",
            "clase": None, "target_y": None}


def clasificar_moneda_YOLO():
    """Placeholder de la inferencia real (ver simulacion_clasificador.py)."""
    return random.choices(["colombia", "extranjera", "boton"], weights=[0.6, 0.3, 0.1], k=1)[0]


def actualizar_leds(clase_activa):
    for nombre, datos in BINS.items():
        color = datos["color"] if nombre == clase_activa else COLOR_APAGADO
        p.changeVisualShape(robot_id, datos["led"], rgbaColor=color)


def actualizar_banda():
    """Avanza el estado de todas las monedas activas un paso. Devuelve la
    clase ('colombia'/'extranjera'/'boton') si se clasificó una moneda nueva
    en este paso, o None si no."""
    clase_clasificada = None
    for moneda in monedas:
        if moneda["estado"] == "avanzando":
            moneda["x"] += BELT_SPEED
            if moneda["x"] >= STATION_X:
                moneda["x"] = STATION_X
                clase = clasificar_moneda_YOLO()
                moneda["clase"] = clase
                moneda["target_y"] = BINS[clase]["y"]
                contador[clase] += 1
                clase_clasificada = clase

                actualizar_leds(clase)
                p.changeVisualShape(moneda["id"], -1, rgbaColor=BINS[clase]["color"])
                moneda["estado"] = "desviando"

        elif moneda["estado"] == "desviando":
            if moneda["y"] < moneda["target_y"]:
                moneda["y"] = min(moneda["y"] + DIVERT_SPEED, moneda["target_y"])
            else:
                moneda["estado"] = "listo"

        p.resetBasePositionAndOrientation(moneda["id"], [moneda["x"], moneda["y"], BELT_Z], [0, 0, 0, 1])

    return clase_clasificada


# ============================================================
# MÓDULO 2: DRON + PISTA CON OBSTÁCULOS
# ============================================================
# El punto de recolección queda justo después de la última bandeja (caja_boton,
# en y=1.3), para que visualmente el dron "recoja" el vaso ahí mismo.
PUNTO_RECOLECCION = (0.3, 1.7)

WAYPOINTS = [PUNTO_RECOLECCION, (2.8, 2.9), (5.2, 1.3), (7.6, 2.9), (10.0, 1.6)]
ALTURA_VUELO = 1.0
ALTURA_OBSTACULO = 1.7
DISTANCIA_ESQUIVE = 1.0
OBSTACULOS_X = [1.6, 5.2, 8.6]


def interpolar_y_en_x(x_obj):
    for i in range(len(WAYPOINTS) - 1):
        x1, y1 = WAYPOINTS[i]
        x2, y2 = WAYPOINTS[i + 1]
        if x1 <= x_obj <= x2:
            t = (x_obj - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return WAYPOINTS[-1][1]


def dibujar_pista():
    for i in range(len(WAYPOINTS) - 1):
        x1, y1 = WAYPOINTS[i]
        x2, y2 = WAYPOINTS[i + 1]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        largo = math.hypot(x2 - x1, y2 - y1)
        angulo = math.atan2(y2 - y1, x2 - x1)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[largo / 2, 0.5, 0.02])
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[largo / 2, 0.5, 0.02],
                                   rgbaColor=[0.15, 0.15, 0.17, 1])
        orn = p.getQuaternionFromEuler([0, 0, angulo])
        p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                           basePosition=[cx, cy, 0.01], baseOrientation=orn)


def crear_obstaculo(x):
    y = interpolar_y_en_x(x)
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.08, 0.4, 0.3])
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.4, 0.3], rgbaColor=[0.6, 0.25, 0.15, 1])
    p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                       basePosition=[x, y, 0.3])


def crear_meta():
    x, y = WAYPOINTS[-1]
    asta_col = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.02, height=1.2)
    asta_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.02, length=1.2, rgbaColor=[0.3, 0.3, 0.3, 1])
    p.createMultiBody(baseMass=0, baseCollisionShapeIndex=asta_col, baseVisualShapeIndex=asta_vis,
                       basePosition=[x, y, 0.6])
    bandera_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.001, 0.25, 0.18], rgbaColor=[0.1, 0.75, 0.2, 1])
    p.createMultiBody(baseMass=0, baseVisualShapeIndex=bandera_vis, basePosition=[x, y + 0.25, 1.05])


def crear_dron():
    cuerpo_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.12, 0.12, 0.03])
    cuerpo_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.12, 0.12, 0.03], rgbaColor=[0.2, 0.2, 0.25, 1])
    cuerpo_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=cuerpo_col, baseVisualShapeIndex=cuerpo_vis,
                                   basePosition=[PUNTO_RECOLECCION[0], PUNTO_RECOLECCION[1], ALTURA_VUELO])
    helices = []
    for ox, oy in [(0.15, 0.15), (-0.15, 0.15), (0.15, -0.15), (-0.15, -0.15)]:
        h_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.06, length=0.01, rgbaColor=[0.05, 0.05, 0.05, 0.85])
        h_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=h_vis,
                                  basePosition=[PUNTO_RECOLECCION[0] + ox, PUNTO_RECOLECCION[1] + oy, ALTURA_VUELO + 0.02])
        helices.append((h_id, ox, oy))
    return cuerpo_id, helices


dibujar_pista()
for ox in OBSTACULOS_X:
    crear_obstaculo(ox)
crear_meta()
dron_id, helices = crear_dron()
vaso_id = None  # solo existe mientras el dron va cargando uno

segmentos = []
dist_total = 0.0
for i in range(len(WAYPOINTS) - 1):
    x1, y1 = WAYPOINTS[i]
    x2, y2 = WAYPOINTS[i + 1]
    d = math.hypot(x2 - x1, y2 - y1)
    segmentos.append((x1, y1, x2, y2, d))
    dist_total += d


def posicion_en_avance(avance_m):
    restante = avance_m
    for (x1, y1, x2, y2, d) in segmentos:
        if restante <= d:
            t = restante / d if d > 0 else 0
            return x1 + t * (x2 - x1), y1 + t * (y2 - y1)
        restante -= d
    return WAYPOINTS[-1]


def altura_en_x(x_actual):
    for ox in OBSTACULOS_X:
        if abs(x_actual - ox) < DISTANCIA_ESQUIVE:
            factor = 1 - (abs(x_actual - ox) / DISTANCIA_ESQUIVE)
            return ALTURA_VUELO + factor * (ALTURA_OBSTACULO - ALTURA_VUELO)
    return ALTURA_VUELO


# ============================================================
# LÓGICA DE INTEGRACIÓN: banda -> vaso -> dron
# ============================================================
MONEDAS_POR_VASO = 8      # cada cuántas monedas clasificadas se arma un vaso
VELOCIDAD_DRON = 0.02

monedas_desde_ultimo_vaso = 0
composicion_vaso = {"colombia": 0, "extranjera": 0, "boton": 0}  # monedas que van en el vaso actual
etiqueta_vaso_id = None  # texto que viaja pegado al dron con el desglose
entregas = 0
dron_estado = "en_base"   # en_base -> volando -> entregado -> regresando
avance = 0.0
angulo_helice = 0.0


def color_por_composicion(comp):
    """Color del vaso según la clase mayoritaria que contiene."""
    clase_mayoritaria = max(comp, key=comp.get)
    return BINS[clase_mayoritaria]["color"]


def texto_composicion(comp):
    return f"COL:{comp['colombia']}  EXT:{comp['extranjera']}  BOT:{comp['boton']}"

contador_text_id = p.addUserDebugText("", [0.3, 0.9, 1.2], textSize=1.3)

print("\n" + "=" * 60)
print("SIMULACIÓN COMPLETA - Sistema de Logística de Monedas Inteligentes")
print(f"Se arma un vaso cada {MONEDAS_POR_VASO} monedas clasificadas")
print("Presiona ESC en la ventana de PyBullet para salir")
print("=" * 60 + "\n")

paso = 0

try:
    while True:
        if not p.isConnected():
            print("\nVentana de PyBullet cerrada. Terminando simulación...")
            break
        paso += 1

        # --- Módulo banda: generar y avanzar monedas ---
        if paso % SPAWN_EVERY_STEPS == 0:
            monedas.append(crear_moneda())
        clase_nueva = actualizar_banda()
        if clase_nueva is not None:
            monedas_desde_ultimo_vaso += 1
            composicion_vaso[clase_nueva] += 1

        # --- Disparar un nuevo vaso si ya hay suficientes monedas y el dron está libre ---
        if dron_estado == "en_base" and monedas_desde_ultimo_vaso >= MONEDAS_POR_VASO:
            monedas_desde_ultimo_vaso = 0
            color_vaso = color_por_composicion(composicion_vaso)
            vaso_id = p.createMultiBody(
                baseMass=0,
                baseVisualShapeIndex=p.createVisualShape(
                    p.GEOM_CYLINDER, radius=0.08, length=0.22, rgbaColor=color_vaso),
                basePosition=[PUNTO_RECOLECCION[0], PUNTO_RECOLECCION[1], ALTURA_VUELO - 0.15])
            # Etiqueta pegada al vaso (parentObjectUniqueId lo hace seguirlo automáticamente)
            etiqueta_vaso_id = p.addUserDebugText(
                texto_composicion(composicion_vaso), [0, 0, 0.2], textSize=1.2,
                textColorRGB=[1, 1, 1], parentObjectUniqueId=vaso_id)
            print(f"[SISTEMA] Vaso armado ({texto_composicion(composicion_vaso)}) -> el dron despega")
            composicion_vaso = {"colombia": 0, "extranjera": 0, "boton": 0}
            avance = 0.0
            dron_estado = "volando"

        # --- Módulo dron ---
        if dron_estado == "volando":
            avance += VELOCIDAD_DRON
            if avance >= dist_total:
                avance = dist_total
                dron_estado = "entregado"
                entregas += 1
                print(f"[DRON] ¡Meta alcanzada! Vaso entregado #{entregas}")

            x, y = posicion_en_avance(avance)
            z = altura_en_x(x)
            p.resetBasePositionAndOrientation(dron_id, [x, y, z], [0, 0, 0, 1])
            if vaso_id is not None:
                p.resetBasePositionAndOrientation(vaso_id, [x, y, z - 0.18], [0, 0, 0, 1])

            angulo_helice += 0.6
            for h_id, ox, oy in helices:
                p.resetBasePositionAndOrientation(h_id, [x + ox, y + oy, z + 0.02],
                                                    p.getQuaternionFromEuler([0, 0, angulo_helice]))

        elif dron_estado == "entregado":
            if vaso_id is not None:
                p.removeBody(vaso_id)
                vaso_id = None
            if etiqueta_vaso_id is not None:
                p.removeUserDebugItem(etiqueta_vaso_id)
                etiqueta_vaso_id = None
            dron_estado = "regresando"
            avance = dist_total  # el regreso lo hacemos por la misma ruta, en reversa

        elif dron_estado == "regresando":
            avance -= VELOCIDAD_DRON
            if avance <= 0:
                avance = 0
                dron_estado = "en_base"
                print("[DRON] De vuelta en la base, listo para el próximo vaso")

            x, y = posicion_en_avance(avance)
            z = altura_en_x(x)
            p.resetBasePositionAndOrientation(dron_id, [x, y, z], [0, 0, 0, 1])
            angulo_helice += 0.6
            for h_id, ox, oy in helices:
                p.resetBasePositionAndOrientation(h_id, [x + ox, y + oy, z + 0.02],
                                                    p.getQuaternionFromEuler([0, 0, angulo_helice]))

        # --- Texto de estado en pantalla ---
        if paso % 30 == 0:
            p.removeUserDebugItem(contador_text_id)
            texto = (f"Colombia: {contador['colombia']}   Extranjera: {contador['extranjera']}   "
                     f"Boton: {contador['boton']}   |   Vasos entregados: {entregas}")
            contador_text_id = p.addUserDebugText(texto, [0.3, 0.9, 1.4], textSize=1.3,
                                                    textColorRGB=[1, 1, 1])

        p.stepSimulation()
        time.sleep(1 / 240)

except KeyboardInterrupt:
    print("\nSimulación detenida por el usuario")
finally:
    if p.isConnected():
        p.disconnect()
    print("Contador final de monedas:", contador)
    print("Vasos entregados:", entregas)