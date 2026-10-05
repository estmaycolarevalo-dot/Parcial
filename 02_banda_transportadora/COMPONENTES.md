# Lista de componentes y pinout — banda transportadora

Todo lo de aquí sale de `calculos_banda.py`. Si cambias un parámetro
(diámetro de rodillo, velocidad, carga), vuelves a correrlo y la
selección se recalcula.

## Resumen de los cálculos

| Magnitud | Valor | De dónde sale |
|---|---|---|
| Carga sobre la placa | 243,1 g | 20 monedas de $1000 + tramo superior de cinta |
| Fuerza normal | 2,38 N | N = m·g |
| Fuerza de arrastre | 0,465 N | μ=0,15 (UHMW) × N × 1,30 |
| **Par requerido** | **0,059 kgf·cm** | T = F·r, r = 12,5 mm |
| Par de diseño (FS=3) | 0,178 kgf·cm | |
| **Velocidad de giro** | **76,4 rpm** | ω = v/r para 0,10 m/s |
| Potencia mecánica | 46,5 mW | P = F·v |
| Corriente del motor | 75 mA | usa el 1,32 % de su par nominal |
| Corriente de pico | 1 477 mA | arranque + WiFi transmitiendo |

Forrar la placa de apoyo con cinta UHMW **ahorra el 62 % del esfuerzo**
frente al acrílico desnudo (0,465 N contra 1,240 N). Es la mejora más
barata de todo el diseño.

## Selección de motor

| Motor | Par | rpm | Margen | Veredicto |
|---|---|---|---|---|
| N20 6 V 100 rpm | 0,35 kgf·cm | 100 | 2,0× | **sirve — el mínimo viable** |
| N20 12 V 60 rpm | 0,60 kgf·cm | 60 | 3,4× | rpm insuficientes |
| JGA25-371 12 V | 4,50 kgf·cm | 100 | 25,3× | sirve, con holgura |
| JGB37-520 12 V | 15,0 kgf·cm | 90 | 84,4× | sobredimensionado |

El N20 de 60 rpm tiene más par pero **no alcanza las 76 rpm** que exige
la velocidad de 0,10 m/s: más par no compensa una velocidad que no
llega. Si quieres margen para subir carga o añadir un segundo tramo, el
JGA25-371 cuesta poco más y evita rediseñar.

## Componentes

### Potencia

| Componente | Especificación | Justificación |
|---|---|---|
| Fuente | 12 V / 2 A conmutada | pico calculado 1,48 A + 50 % |
| Fusible F1 | 2 A | 1,48 A × 1,3, redondeado |
| C1 | 1000 µF / 25 V | mínimo calculado 300 µF |
| Buck | MP1584 o LM2596, 12→5 V, 3 A | ESP32 y sensores |
| C2 | 470 µF | salida del buck |
| Driver | TB6612FNG | 1,2 A cont. sobre 75 mA de uso |

El condensador se dimensiona para el medio ciclo de PWM a 20 kHz
(25 µs), no para sostener el arranque: C = I·Δt/ΔV = 1,2 × 25 µs / 0,1 V
= 300 µF. Se adopta 1000 µF por ser el comercial inmediato con margen.

**El TB6612FNG y no el L298N**: el L298N es un puente en darlington con
caída de 2–3 V y disipación alta; a 12 V perderías una cuarta parte de
la tensión en el propio driver. El TB6612 es MOSFET, con caída ~0,5 V.

### Sensores

| Componente | Función | Interfaz |
|---|---|---|
| Encoder Hall | velocidad y posición | 2 GPIO en cuadratura |
| E18-D80NK | paso de moneda | 1 GPIO, NPN colector abierto |
| NAU7802 + celda 1 kg | pesaje | I²C |
| SSD1306 | estado local | I²C |

**El E18-D80NK y no el TCRT5000**: el reflectivo simple cambia de
umbral con el color y el brillo de lo que pasa; el E18 trae umbral
ajustable por potenciómetro. Su salida es NPN en colector abierto, así
que se conecta directo a un GPIO con pull-up interno — **no necesita
divisor de tensión**.

### Pasivos

| Componente | Valor | Cálculo |
|---|---|---|
| Rp1, Rp2 (I²C) | 4,7 kΩ | rango válido 0,97 – 11,8 kΩ a 100 kHz |
| R1, R2 (divisor) | 10 kΩ / 20 kΩ | solo si algún sensor entrega 5 V |
| Cable | AWG22 | caída de 122 mV en el pico |

Las pull-ups de I²C son un **rango, no un valor mágico**: el mínimo lo
fija la corriente que el pin puede hundir (IOL = 3 mA → 0,97 kΩ) y el
máximo el tiempo de subida (11,8 kΩ a 100 kHz). 4,7 kΩ cae en medio. Si
subes el bus a 400 kHz el máximo baja a 3,54 kΩ y **tendrías que
cambiar a 2,2 kΩ**.

## Pinout del ESP32

| GPIO | Dirección | Conexión | Nota |
|---|---|---|---|
| 27 | salida | PWMA del TB6612 | PWM 20 kHz, 11 bits |
| 25 | salida | AIN1 | sentido de giro |
| 26 | salida | AIN2 | sentido de giro |
| 13 | salida | STBY | habilitación del driver |
| 34 | entrada | Encoder A | solo entrada, sin pull-up interno |
| 35 | entrada | Encoder B | solo entrada, sin pull-up interno |
| 32 | entrada | E18-D80NK | pull-up interna activada |
| 21 | bidireccional | SDA | pull-up externa 4,7 kΩ |
| 22 | bidireccional | SCL | pull-up externa 4,7 kΩ |

**GPIO 34 y 35 no tienen pull-up interna** (son solo-entrada en el
ESP32). Si el encoder es de colector abierto, necesitas pull-ups
externas de 10 kΩ. Si es push-pull, van directo.

## Control

| Parámetro | Valor | Cálculo |
|---|---|---|
| PWM | 20 kHz, 11 bits (2048 pasos) | máx = log₂(80 MHz / 20 kHz) |
| Resolución del encoder | 1496 pulsos/vuelta (×4) | 11 PPR × 34 de reducción |
| Resolución lineal | 0,052 mm por pulso | π·D / 1496 |
| Frecuencia de pulsos | 1905 Hz a 76 rpm | |
| Lazo de velocidad | 50 Hz | 38 pulsos por periodo |

38 pulsos por periodo de muestreo son suficientes para medir velocidad
por **conteo simple**. Por debajo de ~10 pulsos habría que medir el
periodo entre flancos, que es bastante más complicado de programar.

## Los tres errores de montaje que más cuestan

**1. Tierra en varios puntos.** La tierra de potencia y la de señal se
unen en **un solo punto**, junto a la fuente. Si se unen en varios, la
corriente del motor circula por la tierra de señal y mete ruido en la
celda de carga y en el bus I²C. Es el error que produce lecturas de
peso que "bailan" sin causa aparente.

**2. Alimentar el motor desde el pin de 5 V del ESP32.** El regulador
de la placa da unos 500 mA; el pico del motor es de 1,2 A. El resultado
son reinicios cada vez que arranca la banda. El motor va del buck, no
del ESP32.

**3. PWM en la banda audible.** A 1 kHz el motor chilla. 20 kHz está
fuera del rango audible y sigue permitiendo 11 bits de resolución.
