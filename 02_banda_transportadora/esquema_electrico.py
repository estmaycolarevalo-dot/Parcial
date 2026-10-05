"""
============================================================
ESQUEMA ELECTRICO - BANDA TRANSPORTADORA DE MONEDAS
============================================================
Genera dos laminas:

  1. POTENCIA      fuente, proteccion, regulacion, driver y motor.
                   Es donde estan las decisiones que se justifican
                   con la memoria de calculo (calculos_banda.py).

  2. SENALES       conexionado ESP32 con el driver, el encoder, el
                   sensor de paso y el bus I2C.

Se separan a proposito: mezclar 12 V de potencia con senales logicas
de 3,3 V en una sola lamina es lo que hace ilegible un esquema, y
ademas oculta el punto mas importante del diseno, que es DONDE se unen
las dos tierras.

Uso:
    pip install schemdraw
    python esquema_electrico.py
"""
import os

import schemdraw
import schemdraw.elements as elm

SALIDA = "esquemas"
os.makedirs(SALIDA, exist_ok=True)


def lamina_potencia():
    """Cadena de potencia: 12 V -> fusible -> buck 5 V -> driver -> motor."""
    with schemdraw.Drawing(file=os.path.join(SALIDA, "01_potencia.svg"),
                           show=False) as d:
        d.config(unit=2.4, fontsize=11)

        # --- entrada de 12 V ---
        V = d.add(elm.SourceV().up().label("Fuente\n12 V / 2 A", loc="left"))
        d.add(elm.Fuse().right().label("F1\n2 A"))
        d.add(elm.Line().right().length(1))
        nodo12 = d.add(elm.Dot(open=True).label("+12 V", loc="top"))

        # --- desacoplo de entrada ---
        d.push()
        d.add(elm.Line().down().length(1.4))
        d.add(elm.Capacitor(polar=True).down().label("C1\n1000 uF\n25 V",
                                                     loc="right"))
        d.add(elm.Line().down().length(0.4))
        gnd_pot = d.add(elm.Dot())
        d.add(elm.Ground())
        d.pop()

        # --- rama al regulador de 5 V ---
        d.add(elm.Line().right().length(1.6))
        buck = d.add(elm.RBox(w=2.6, h=1.8).right()
                     .label("Buck\nMP1584 / LM2596\n12 V -> 5 V"))
        d.add(elm.Line().right().length(0.8))
        d.add(elm.Dot(open=True).label("+5 V", loc="top"))
        d.add(elm.Line().down().length(1.4))
        d.add(elm.Capacitor(polar=True).down().label("C2\n470 uF", loc="right"))
        d.add(elm.Line().down().length(0.4))
        d.add(elm.Ground())

        d.save(os.path.join(SALIDA, "01_potencia.svg"))
    return "01_potencia.svg"


def lamina_driver():
    """Driver TB6612FNG y motor, con el desacoplo local."""
    with schemdraw.Drawing(file=os.path.join(SALIDA, "02_driver.svg"),
                           show=False) as d:
        d.config(unit=2.4, fontsize=11)

        drv = d.add(elm.Ic(
            pins=[
                elm.IcPin(name="VM", side="left", slot="1/4"),
                elm.IcPin(name="VCC", side="left", slot="2/4"),
                elm.IcPin(name="GND", side="left", slot="3/4"),
                elm.IcPin(name="STBY", side="left", slot="4/4"),
                elm.IcPin(name="AIN1", side="bottom", slot="1/3"),
                elm.IcPin(name="AIN2", side="bottom", slot="2/3"),
                elm.IcPin(name="PWMA", side="bottom", slot="3/3"),
                elm.IcPin(name="AO1", side="right", slot="1/2"),
                elm.IcPin(name="AO2", side="right", slot="2/2"),
            ],
            w=3.4, h=3.6, label="TB6612FNG\n1,2 A cont. / 3,2 A pico"))

        d.add(elm.Line().left().at(drv.VM).length(1.2)
              .label("+12 V", loc="left"))
        d.add(elm.Line().left().at(drv.VCC).length(1.2)
              .label("+5 V", loc="left"))
        d.add(elm.Line().left().at(drv.GND).length(1.2))
        d.add(elm.Ground())
        d.add(elm.Line().left().at(drv.STBY).length(1.2)
              .label("GPIO 13", loc="left"))

        d.add(elm.Line().right().at(drv.AO1).length(1.4))
        m = d.add(elm.Motor().right().label("M\nJGA25-371\n12 V  100 rpm"))
        d.add(elm.Line().down().at(drv.AO2).length(0.6))
        d.add(elm.Line().right().length(1.4))

        d.add(elm.Line().down().at(drv.AIN1).length(0.8)
              .label("GPIO 25", loc="bottom"))
        d.add(elm.Line().down().at(drv.AIN2).length(0.8)
              .label("GPIO 26", loc="bottom"))
        d.add(elm.Line().down().at(drv.PWMA).length(0.8)
              .label("GPIO 27\nPWM 20 kHz", loc="bottom"))

        d.save(os.path.join(SALIDA, "02_driver.svg"))
    return "02_driver.svg"


def lamina_senales():
    """Bus I2C con sus pull-ups, y el sensor de paso."""
    with schemdraw.Drawing(file=os.path.join(SALIDA, "03_senales.svg"),
                           show=False) as d:
        d.config(unit=2.2, fontsize=11)

        # --- pull-ups del bus I2C ---
        d.add(elm.Dot(open=True).label("+3,3 V", loc="top"))
        d.push()
        d.add(elm.Resistor().down().label("Rp1\n4,7 k"))
        sda = d.add(elm.Dot().label("SDA\nGPIO 21", loc="bottom"))
        d.pop()
        d.add(elm.Line().right().length(1.4))
        d.add(elm.Resistor().down().label("Rp2\n4,7 k"))
        scl = d.add(elm.Dot().label("SCL\nGPIO 22", loc="bottom"))

        d.save(os.path.join(SALIDA, "03_senales.svg"))
    return "03_senales.svg"


if __name__ == "__main__":
    print("\n  Generando laminas del esquema electrico\n")
    for fn in (lamina_potencia, lamina_driver, lamina_senales):
        try:
            nombre = fn()
            print(f"    OK   {nombre}")
        except Exception as e:
            print(f"    FALLA {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n  -> carpeta {SALIDA}/")
