"""
============================================================
BANDA TRANSPORTADORA CON FISICA REAL  (modulo M-transporte)
============================================================
Reemplaza el transporte por teletransporte de main.py por una banda
donde las monedas SE APOYAN, CHOCAN, SE ACUMULAN y pueden ATASCARSE.

POR QUE CAMBIAR
---------------
El main.py actual mueve las monedas con resetBasePositionAndOrientation()
y las crea con baseMass=0. En PyBullet, masa 0 significa cuerpo ESTATICO:
no cae, no choca, no lo empuja nada. O sea, la banda actual es una
ANIMACION, no una simulacion, y p.stepSimulation() no esta simulando
nada. Eso esta bien como primer avance visual, pero tiene un limite:
una celda de carga virtual no puede pesar monedas que flotan, y una
camara virtual no puede ver oclusiones que nunca ocurren. Justo esas
dos cosas son lo diferencial del proyecto.

COMO SE MODELA UNA BANDA EN PYBULLET
------------------------------------
PyBullet no tiene primitiva de cinta transportadora. Aqui se usa:

   superficie estatica
   + friccion ANISOTROPICA (baja en el sentido de avance, alta de lado)
   + fuerza tangencial aplicada a los cuerpos en contacto, saturada
     en mu*m*g

La friccion anisotropica es la parte no obvia y es la que hace que
funcione. Una superficie quieta con friccion normal frena a la moneda
tanto como la empuja el modelo, y no avanza nada. Pero una banda REAL
se mueve JUNTO con la moneda: no hay friccion que resista el avance, y
sin embargo si hay agarre lateral que impide que la moneda se deslice
de lado. Eso es exactamente friccion anisotropica.

El tope mu*m*g es lo que la hace realista: si pones mas monedas de las
que la friccion puede mover, la banda PATINA, igual que una de verdad.
Sin ese tope la banda seria infinitamente fuerte y nunca te avisaria
de que tu diseno esta sobrecargado.

ESCALA (importante para el informe)
-----------------------------------
La maqueta usa monedas de 100 mm de diametro y 20 mm de espesor; una
moneda COP real mide entre 17,00 y 26,70 mm, con 1,17 a 2,70 mm de
espesor. O sea la maqueta esta a ~3,75x en diametro pero a ~9x en
espesor: el disco simulado es 2,4 veces mas grueso de lo proporcional.
Se mantiene esa escala a proposito (cambiarla obligaria a mover toda
la maqueta), pero entonces LA MASA DE SIMULACION NO ES LA MASA REAL.
Por eso hay dos numeros separados y nunca se mezclan:

    masa_sim  -> la que usa el motor de fisica (coherente con el tamano
                 del disco de la maqueta)
    masa_g    -> la del catalogo del Banco de la Republica, la que se
                 acumula en las metricas y se muestra en el dashboard

El main.py ya hace esta separacion sin decirlo: toma el peso de
DENOMINACIONES_COP y no de la geometria. Aqui queda explicita.
"""
import math
import random

import pybullet as p

G = 9.81

# ---------------------------------------------------------------
#  Catalogo: masa REAL para metricas, familia 2012 del emisor.
#  La tabla de main.py mezcla familias: 100->5.31 y 200->7.08 son
#  valores de la familia ANTIGUA, no de la nueva. Con $200 = 7,08 g
#  y $500 = 7,14 g quedan separadas por 0,06 g, que es justo el par
#  que ninguna balanza de bajo costo puede distinguir. Conviene
#  declarar de que familia es cada fila en vez de mezclarlas.
# ---------------------------------------------------------------
CATALOGO_COP = [
    {"valor": 50,   "masa_g": 2.00, "diam_mm": 17.00, "familia": "2012"},
    {"valor": 100,  "masa_g": 3.34, "diam_mm": 20.30, "familia": "2012"},
    {"valor": 200,  "masa_g": 4.61, "diam_mm": 22.40, "familia": "2012"},
    {"valor": 500,  "masa_g": 7.14, "diam_mm": 23.70, "familia": "2012"},
    {"valor": 1000, "masa_g": 9.95, "diam_mm": 26.70, "familia": "2012"},
    {"valor": 200,  "masa_g": 7.08, "diam_mm": 24.40, "familia": "antigua"},
]
MASA_EXTRANJERA_G = 5.00
# Un boton NO tiene una masa unica: va de 0,35 g (plastico fino) a
# 2,08 g (metalico). Se sortea del rango en vez de usar un valor fijo,
# porque el rango completo de masas del sistema es de 45x y esa
# dispersion es justo lo que pone a prueba la auditoria de peso.
MASA_BOTON_MIN_G = 0.35
MASA_BOTON_MAX_G = 2.08
MASA_BOTON_G = 1.20                  # media, para compatibilidad


class BandaFisica:
    """Banda con arrastre real sobre la geometria que ya tiene la maqueta.

    Se coloca encima de cinta_seg1 sin tocar el URDF: la superficie de
    arrastre es una placa propia, delgada, apoyada sobre la goma de la
    banda del URDF (que es solo visual y no tiene <collision>).
    """

    def __init__(self, x_ini=-0.9, x_fin=3.0, ancho=0.30, z_sup=0.605,
                 velocidad=0.35, mu=0.28, k_arrastre=25.0,
                 alto_guia=0.06):
        self.x_ini, self.x_fin = x_ini, x_fin
        self.ancho = ancho
        self.z_sup = z_sup
        self.velocidad = velocidad
        self.mu = mu
        self.k = k_arrastre
        self.cuerpos = []

        largo = x_fin - x_ini
        cx = (x_ini + x_fin) / 2.0
        e = 0.01

        # --- superficie de arrastre ---
        # El URDF define la banda SOLO con <visual>, sin <collision>:
        # para PyBullet ese link no existe fisicamente y las monedas lo
        # atraviesan. Esta placa es la que realmente las sostiene.
        col = p.createCollisionShape(p.GEOM_BOX,
                                     halfExtents=[largo / 2, ancho / 2, e / 2])
        vis = p.createVisualShape(p.GEOM_BOX,
                                  halfExtents=[largo / 2, ancho / 2, e / 2],
                                  rgbaColor=[0.08, 0.08, 0.09, 1])
        self.superficie = p.createMultiBody(0, col, vis, [cx, 0.0, z_sup - e / 2])
        p.changeDynamics(self.superficie, -1, lateralFriction=0.6,
                         restitution=0.05,
                         anisotropicFriction=[0.03, 1.0, 1.0])
        self.cuerpos.append(self.superficie)

        # --- guias laterales: sin ellas las monedas se caen de lado ---
        for signo in (+1, -1):
            gcol = p.createCollisionShape(
                p.GEOM_BOX, halfExtents=[largo / 2, e / 2, alto_guia / 2])
            gvis = p.createVisualShape(
                p.GEOM_BOX, halfExtents=[largo / 2, e / 2, alto_guia / 2],
                rgbaColor=[0.45, 0.48, 0.52, 0.45])
            self.cuerpos.append(p.createMultiBody(
                0, gcol, gvis,
                [cx, signo * (ancho / 2 + e / 2), z_sup + alto_guia / 2]))

    # ------------------------------------------------------------------
    def paso(self, uids):
        """Aplica el arrastre. Llamar UNA vez por stepSimulation().

        Devuelve el set de monedas que esta arrastrando: si ese numero
        crece y las monedas no avanzan, la banda patina por sobrecarga.

        RENDIMIENTO: una sola llamada a getContactPoints(bodyB=superficie)
        devuelve TODOS los contactos de golpe. Preguntar moneda por
        moneda (getContactPoints(bodyA=u, bodyB=sup) dentro del for) hace
        N llamadas por paso y a 240 Hz eso solo vuelve la simulacion
        varias veces mas lenta que la version por teletransporte, que es
        justo el argumento que usaria alguien para no pasar a fisica.
        """
        encima = {c[1] for c in p.getContactPoints(bodyB=self.superficie)}
        encima &= set(uids)
        for u in encima:
            m = p.getDynamicsInfo(u, -1)[0]
            (vx, _, _), _ = p.getBaseVelocity(u)
            f = self.k * m * (self.velocidad - vx)
            tope = self.mu * m * G          # la banda no puede dar mas
            f = max(-tope, min(tope, f))
            pos, _ = p.getBasePositionAndOrientation(u)
            p.applyExternalForce(u, -1, [f, 0, 0], pos, p.WORLD_FRAME)
        return encima

    def fuera(self, uid):
        (x, _, z), _ = p.getBasePositionAndOrientation(uid)
        return x > self.x_fin or z < self.z_sup - 0.25


# ---------------------------------------------------------------
#  Monedas CON MASA (la diferencia de fondo con el main.py actual)
# ---------------------------------------------------------------
def crear_moneda_fisica(x, y, z, radio=0.05, espesor=0.02,
                        densidad=2700.0, color=(0.85, 0.75, 0.2, 1)):
    """Crea una moneda como cuerpo DINAMICO.

    baseMass tiene que ser > 0. Con baseMass=0 PyBullet la trata como
    cuerpo estatico y nada de esto funciona: no cae, no la arrastra la
    banda, no choca con sus vecinas.

    La masa sale de la densidad por el volumen del disco de la maqueta,
    no del catalogo: a esta escala un disco de 100x20 mm con la masa
    real de 9,95 g tendria densidad de corcho y flotaria de forma rara.
    Densidad 2700 (aluminio) da un disco de ~424 g, que se comporta de
    forma creible. La masa REAL sigue yendo a las metricas, aparte.
    """
    vol = math.pi * radio ** 2 * espesor
    masa_sim = densidad * vol

    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=radio, height=espesor)
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radio, length=espesor,
                              rgbaColor=list(color))
    uid = p.createMultiBody(
        baseMass=masa_sim,
        baseCollisionShapeIndex=col,
        baseVisualShapeIndex=vis,
        basePosition=[x, y, z],
        baseOrientation=p.getQuaternionFromEuler([0, 0, random.uniform(0, 6.28)]))
    p.changeDynamics(uid, -1, lateralFriction=0.25, rollingFriction=1e-4,
                     spinningFriction=1e-4, restitution=0.2,
                     linearDamping=0.04, angularDamping=0.04)
    return uid, masa_sim


def metricas_de_clase(clase):
    """Masa REAL y valor de una moneda recien clasificada.

    Separado de la geometria a proposito: la maqueta esta a escala, el
    catalogo no. Mezclarlos es lo que hace que un dashboard reporte
    kilos donde deberia reportar gramos.
    """
    if clase == "colombia":
        d = random.choice(CATALOGO_COP)
        return d["masa_g"], d["valor"]
    if clase == "extranjera":
        return MASA_EXTRANJERA_G, 0
    return random.uniform(MASA_BOTON_MIN_G, MASA_BOTON_MAX_G), 0
