"""
============================================================
PRUEBA DE LA BANDA FISICA SOBRE LA MAQUETA DEL PROYECTO
============================================================
Carga maqueta.urdf tal cual, le monta la banda con arrastre real y
mide tres cosas que la version por teletransporte no puede medir:

  1. CAUDAL     cuantas monedas llegan de verdad a la estacion
  2. ACUMULACION si se amontonan (una moneda tapada es invisible
                 para la camara y rompe la auditoria de masa)
  3. PATINAJE   si la banda se sobrecarga y deja de arrastrar

Uso:
    python prueba_banda.py            # sin ventana, imprime numeros
    python prueba_banda.py --gui      # con ventana de PyBullet
    python prueba_banda.py --barrido  # barre velocidad y cadencia
"""
import argparse
import math
import os
import random
import sys

import pybullet as p
import pybullet_data

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banda_fisica import BandaFisica, crear_moneda_fisica, metricas_de_clase

STATION_X = 0.3        # misma x que la estacion de vision del URDF
BELT_Z_SUP = 0.605     # tope de la goma de cinta_seg1, medido del URDF


def clasificar_YOLO():
    return random.choices(["colombia", "extranjera", "boton"],
                          weights=[0.6, 0.3, 0.1], k=1)[0]


def corrida(velocidad=0.35, cada_pasos=60, n_monedas=20, gui=False,
            segundos=22.0, semilla=7):
    cli = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8)
    p.setPhysicsEngineParameter(fixedTimeStep=1 / 240.0,
                                numSolverIterations=80)
    if gui:
        p.resetDebugVisualizerCamera(2.6, 50, -35, [0.6, 0.2, 0.6])

    piso_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[20, 20, 0.05])
    p.createMultiBody(0, piso_col, basePosition=[3.5, 1.0, -0.05])
    p.loadURDF("maqueta.urdf", [0, 0, 0], useFixedBase=True)

    banda = BandaFisica(x_ini=-0.9, x_fin=3.0, ancho=0.30,
                        z_sup=BELT_Z_SUP, velocidad=velocidad)

    rng = random.Random(semilla)
    dt = 1 / 240.0
    uids, verdad = [], {}
    clasificadas, pendientes = set(), n_monedas
    contador = {"colombia": 0, "extranjera": 0, "boton": 0}
    metricas = {"valor_cop": 0, "peso_g": 0.0}
    max_arrastradas, pasos_patinando = 0, 0
    t_llegada = {}

    pasos = int(segundos / dt)
    for k in range(pasos):
        if pendientes > 0 and k % cada_pasos == 0:
            uid, _ = crear_moneda_fisica(
                -0.85, rng.uniform(-0.07, 0.07), BELT_Z_SUP + 0.03)
            uids.append(uid)
            verdad[uid] = None
            pendientes -= 1

        encima = banda.paso(uids)
        max_arrastradas = max(max_arrastradas, len(encima))
        p.stepSimulation()

        # --- estacion de vision: clasifica al cruzar STATION_X ---
        for u in list(uids):
            if u in clasificadas:
                continue
            (x, _, _), _ = p.getBasePositionAndOrientation(u)
            if x >= STATION_X:
                clase = clasificar_YOLO()
                clasificadas.add(u)
                contador[clase] += 1
                masa, valor = metricas_de_clase(clase)
                metricas["peso_g"] += masa
                metricas["valor_cop"] += valor
                t_llegada[u] = k * dt

        # --- patinaje: hay monedas encima pero ninguna avanza ---
        if len(encima) >= 3 and k % 8 == 0:
            vels = [p.getBaseVelocity(u)[0][0] for u in encima]
            if vels and max(vels) < 0.02:
                pasos_patinando += 8

    # --- acumulacion: monedas que terminaron encima de otra ---
    pos = {u: p.getBasePositionAndOrientation(u)[0] for u in uids}
    apiladas = 0
    for u in uids:
        xu, yu, zu = pos[u]
        for v in uids:
            if u == v:
                continue
            xv, yv, zv = pos[v]
            if math.hypot(xu - xv, yu - yv) < 0.045 and zu > zv + 0.012:
                apiladas += 1
                break

    atascadas = sum(1 for u in uids if u not in clasificadas
                    and pos[u][2] > BELT_Z_SUP - 0.1)
    p.disconnect()

    tiempos = sorted(t_llegada.values())
    intervalos = [b - a for a, b in zip(tiempos[:-1], tiempos[1:])]
    med = sum(intervalos) / len(intervalos) if intervalos else 0.0

    return {
        "velocidad": velocidad,
        "cadencia_pasos": cada_pasos,
        "lanzadas": len(uids),
        "clasificadas": len(clasificadas),
        "apiladas": apiladas,
        "atascadas": atascadas,
        "max_en_banda": max_arrastradas,
        "patinando_s": round(pasos_patinando * dt, 2),
        "monedas_min": round(60.0 / med, 1) if med > 0 else 0.0,
        "contador": contador,
        "valor_cop": metricas["valor_cop"],
        "peso_g": round(metricas["peso_g"], 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--barrido", action="store_true")
    ap.add_argument("--monedas", type=int, default=20)
    args = ap.parse_args()

    if args.barrido:
        print("  Barrido: velocidad de banda vs cadencia de entrada\n")
        print(f"  {'v (m/s)':>8}{'cada':>7}{'llegan':>8}{'apilad':>8}"
              f"{'atasc':>7}{'patina':>8}{'mon/min':>9}")
        print("  " + "-" * 56)
        for v in (0.15, 0.25, 0.35, 0.50):
            for cada in (40, 80):
                r = corrida(velocidad=v, cada_pasos=cada,
                            n_monedas=args.monedas)
                print(f"  {r['velocidad']:>8.2f}{r['cadencia_pasos']:>7}"
                      f"{r['clasificadas']:>8}{r['apiladas']:>8}"
                      f"{r['atascadas']:>7}{r['patinando_s']:>7.1f}s"
                      f"{r['monedas_min']:>9.0f}")
        return

    r = corrida(n_monedas=args.monedas, gui=args.gui,
                segundos=40.0 if args.gui else 22.0)
    print("\n  Resultado de la banda con fisica real\n")
    for k in ("lanzadas", "clasificadas", "apiladas", "atascadas",
              "max_en_banda", "patinando_s", "monedas_min"):
        print(f"    {k:<16} {r[k]}")
    print(f"    contador         {r['contador']}")
    print(f"    valor            ${r['valor_cop']:,} COP")
    print(f"    peso real        {r['peso_g']} g")


if __name__ == "__main__":
    main()
