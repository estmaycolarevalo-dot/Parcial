# Lista de materiales — banda transportadora

Generada desde el CAD paramétrico. Si cambias un parámetro en
`cad_banda.py`, vuelve a correrlo y esta tabla se actualiza sola.

## Dimensiones derivadas

| Magnitud | Valor |
|---|---|
| Distancia entre centros | 300 mm |
| Largo de corte de la cinta | 683.3 mm |
| Ancho de cinta | 70 mm |
| Paso de guías (entrada → salida) | 64 → 30 mm |
| Diámetro de rodillo | 25 mm (corona +0.8 mm) |
| Recorrido por vuelta de rodillo | 78.5 mm |
| Rpm para 0,10 m/s | 76 rpm |

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
| Eje Ø8 mm | 2 | Acero, largo 116 mm |
| Cinta PVC lisa 1.5 mm | 0.68 m | Empalme en bisel, no a tope |
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
- La ranura de tensado deja 14 mm de carrera: la cinta de PVC
  se estira con el uso y sin ella empieza a patinar.
