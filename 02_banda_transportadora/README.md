# Banda transportadora de monedas — módulo de transporte

Diseño, simulación, CAD y electrónica del módulo de transporte del
sistema logístico de monedas inteligentes (ESP32).

Todo aquí es **paramétrico y verificable**: cambias un número en un
archivo, vuelves a correrlo, y el CAD, los cálculos y la selección de
componentes se recalculan solos.

---

## Empieza por aquí

```bash
python calculos_banda.py --md     # memoria de cálculo + presupuesto
python cad_banda.py               # modelo CAD → cad_salida/
python diagrama_electrico.py      # planos eléctricos → esquemas/
python prueba_banda.py --gui      # simulación física de la banda
```

Requisitos: `pip install pybullet cadquery numpy` (para la simulación y
el CAD). Los cálculos y los planos no necesitan nada más que Python.

---

## La decisión de fondo, antes de construir nada

La banda necesita **46,5 mW** de potencia mecánica. Eso es prácticamente
nada, y es la señal de que un motor es una solución sobrada para el
problema.

Un **riel inclinado por gravedad** hace el mismo trabajo con cero
actuadores, cero driver, cero encoder y cero banda que se desalinee. En
la simulación del alimentador, a 22° con escalón de 2,25–2,30 mm el
100 % de las monedas llega a la estación.

**Recomendación honesta:** si el presupuesto aprieta, usa el riel para
mover las monedas y construye la banda solo si la necesitas por lo
demostrativo en la sustentación.

---

## Presupuesto

| Concepto | Referencia | Económico | Alternativa |
|---|---:|---:|---|
| ADC de peso | 25 000 | 8 000 | HX711 en vez de NAU7802 |
| Driver de motor | 15 000 | 3 000 | MOSFET IRLZ44N + diodo |
| Sensor de paso | 20 000 | 4 000 | TCRT5000 |
| Motor | 55 000 | 0 | de impresora, reciclado |
| Rodillos | 30 000 | 3 000 | tubo PVC ¾" |
| Bastidor | 50 000 | 8 000 | MDF cortado a mano |
| Cinta | 20 000 | 5 000 | lona o banda de tela |
| Celda de carga 1 kg | 13 090 | 13 090 | *precio verificado* |
| ESP32 DevKit | 30 000 | 30 000 | imprescindible |
| Fuente 12 V 2 A | 25 000 | 0 | cargador reciclado |
| Rodamientos 608ZZ | 10 000 | 5 000 | 2 en vez de 4 |
| **TOTAL (COP)** | **293 090** | **79 090** | **ahorro 73 %** |

Precios de orden de magnitud; solo la celda está confirmada
([Sigma Electrónica](https://www.sigmaelectronica.net/producto/celda-1k/)).

Tres sustituciones que valen la pena entender:

**El driver.** La banda gira **siempre en el mismo sentido**, así que el
puente H completo está de más. Un MOSFET de canal N en low-side con PWM
y un diodo volante hace el trabajo con tres componentes.

**Los rodillos.** El tubo de PVC de ¾" tiene 26,67 mm de diámetro
exterior, casi los 25 mm del diseño. Y la corona — que es obligatoria —
se consigue enrollando dos vueltas de cinta aislante en el centro.

**El ADC.** Recomendé el NAU7802 "porque unifica el bus I²C". No vale el
triple de precio. El HX711 usa dos GPIO propios y está en todas partes.

---

## El hallazgo que cambia el diseño

Al verificar el rango completo de objetos —incluidos los botones, que
son una clase de rechazo del clasificador— apareció esto:

El escalón separador debe cumplir dos condiciones a la vez:

```
luz > espesor del objeto más grueso      → deja pasar uno
luz < suma de los dos más finos apilados → no deja pasar dos
```

| | Mínimo | Máximo | Ventana |
|---|---:|---:|---:|
| Solo monedas | 2,20 mm | 2,34 mm | **+0,14 mm** |
| Con botones | 2,20 mm | 1,97 mm | **−0,23 mm** |

**La ventana es negativa.** No existe ningún valor de escalón que deje
pasar la moneda de $1000 sola y a la vez impida que se cuelen un botón
fino y una moneda de $50 juntos (1,97 mm contra los 2,30 mm de luz).

La singularización **por altura** no funciona cuando el rango incluye
objetos más finos que las monedas. Dos salidas:

1. **Separar en el tiempo**: compuerta que cierra a ras de la banda y
   libera de a uno, en vez de un escalón de altura fija.
2. **Aceptarlo y resolverlo con visión**: el botón es clase de rechazo,
   así que confundir dos botones no cuesta dinero. **La tolerancia puede
   ser asimétrica** — exigente entre denominaciones, relajada en la
   clase que vas a descartar de todos modos.

---

## Memoria de cálculo

| Magnitud | Valor | De dónde sale |
|---|---:|---|
| Carga (peor caso) | 243,1 g | 20 × $1000 + tramo de cinta |
| Carga (mezcla real) | 112,9 g | media de 5,65 g por moneda |
| Fuerza de arrastre | 0,465 N | μ = 0,15 (UHMW) × N × 1,30 |
| **Par requerido** | **0,059 kgf·cm** | T = F·r |
| **Velocidad** | **76,4 rpm** | ω = v/r para 0,10 m/s |
| Corriente del motor | 75 mA | usa el 1,32 % de su par nominal |
| Corriente de pico | 1 477 mA | arranque + WiFi |
| PWM | 20 kHz, 11 bits | máx = log₂(80 MHz / 20 kHz) |
| Resolución lineal | 0,052 mm/pulso | π·D / 1496 |

Dimensionar con "todas de $1000" sobrestima la carga un 76 % frente a
la mezcla real. Es conservador, y está bien para elegir motor.

**Forrar la placa de apoyo con cinta UHMW ahorra el 62 % del esfuerzo**
frente al acrílico desnudo. Es la mejora más barata del diseño.

### El motor con más par que no sirve

| Motor | Par | rpm | Margen | |
|---|---:|---:|---:|---|
| N20 6 V 100 rpm | 0,35 | 100 | 2,0× | **el mínimo viable** |
| N20 12 V 60 rpm | 0,60 | 60 | 3,4× | rpm insuficientes |
| JGA25-371 | 4,50 | 100 | 25,3× | con holgura |

El N20 de 60 rpm tiene casi el doble de par y aun así no sirve: no
alcanza las 76 rpm que exige la velocidad. Más par no compensa una
velocidad que no llega.

---

## Los errores de montaje que más cuestan

**Tierra en varios puntos.** Las tierras de potencia y señal se unen en
**un solo punto**, junto a la fuente. Si se unen en varios, la corriente
del motor circula por la tierra de señal y tendrás lecturas de peso que
bailan sin causa aparente.

**Alimentar el motor desde el pin de 5 V del ESP32.** El regulador de la
placa da unos 500 mA; el pico del motor es de 1,2 A. Resultado:
reinicios en cada arranque.

**GPIO 34 y 35 no tienen pull-up interna** en el ESP32 (son
solo-entrada). Si el encoder es de colector abierto, necesitas pull-ups
externas de 10 kΩ.

**PWM en la banda audible.** A 1 kHz el motor chilla. 20 kHz está fuera
del rango audible y sigue permitiendo 11 bits de resolución.

---

## Archivos

| Archivo | Qué hace |
|---|---|
| `calculos_banda.py` | memoria de cálculo completa + presupuesto |
| `cad_banda.py` | modelo CAD paramétrico → STEP, STL, SVG |
| `diagrama_electrico.py` | planos eléctricos, versión referencia y económica |
| `banda_fisica.py` | banda con física real para PyBullet |
| `prueba_banda.py` | simulación sobre `maqueta.urdf` |
| `esquema_electrico.py` | láminas con schemdraw (ver nota) |

Salidas: `cad_salida/` (STEP, STL, vistas), `esquemas/` (planos SVG),
`CALCULOS.md` y `COMPONENTES.md`.

---

## Notas técnicas de lo que costó hacerlo

**PyBullet y la banda.** No tiene primitiva de cinta transportadora. Se
modela como superficie estática con **fricción anisotrópica** (baja en
el sentido de avance, alta en transversal) más fuerza tangencial
saturada en μ·N. Una superficie quieta con fricción normal frena tanto
como el modelo empuja: 0 de 8 monedas avanzan. Con anisotropía, 6 de 8.

**No bajes el paso de integración para acelerar.** A 1/120 s la física
se rompe: 5 monedas atascadas y 0 clasificadas, contra 20/20 a 1/240 s.
Se acelera reduciendo llamadas a la API, no el paso.

**CadQuery y el `revolve`.** Falla con `StdFail_NotDone`, un error de
OpenCascade que no dice nada de la causa. De cinco combinaciones de
perfil y eje probadas, solo funciona dibujando el perfil con la
coordenada axial en horizontal y revolucionando alrededor de X.

**Schemdraw** amontona las etiquetas cuando un integrado pasa de cuatro
o cinco pines. Sirve para circuitos discretos, no para conexionado de
módulos. El plano de arquitectura está dibujado a mano en SVG.

**La compuerta batiente no cabe en un canal estrecho.** Girando sobre el
eje Z quedaba tendida sobre el canal al abrirse y lo partía en dos.
Levadiza: de 6/10 a 9/10 monedas que pasan.

**La barrera IR no sirve como contador.** Con seis monedas pasando
registró tres flancos: las que viajan pegadas cortan el haz de forma
continua. Sirve como disparador para saber cuándo leer la celda; el
conteo autoritativo es el de visión.
