# Memoria de cálculo — banda transportadora

```

==============================================================
  A. MECANICA
==============================================================
  Monedas sobre la banda (20 de $1000, peor caso)        199.0 g
  Tramo superior de la cinta                          44.1 g
  Masa total sobre la placa de apoyo                 243.1 g
  Fuerza normal N = m*g                               2.38 N

  Fuerza de arrastre con cinta UHMW (mu=0.15)       0.465 N
  Fuerza de arrastre sin ella (acrilico, mu=0.4)    1.240 N
  -> forrar la placa AHORRA 62% del esfuerzo

  Par en el rodillo  T = F*r                         5.813 mN*m
                                                     0.059 kgf*cm
  Velocidad angular  w = v/r                          8.00 rad/s
  Velocidad de giro                                   76.4 rpm
  Potencia mecanica  P = F*v                         46.50 mW

==============================================================
  B. TENSION DE LA BANDA  (Euler-Eytelwein)
==============================================================
  Angulo de abrazamiento                               180 grados
  Relacion maxima T1/T2 = e^(mu*theta)                2.57
  Tension del lado tenso    T1                        0.76 N
  Tension del lado flojo    T2                        0.30 N
  Carga total sobre el eje  T1+T2                     1.06 N
  Pretension de montaje recomendada                    8.0 N
  La condicion de no deslizamiento se cumple por diseno: la
  fuerza que hay que transmitir es minima frente al limite.

==============================================================
  C. RODAMIENTOS 608ZZ
==============================================================
  Capacidad dinamica de catalogo  C                   3350 N
  Carga radial por rodamiento     P                   4.16 N
  Vida util L10 = (C/P)^3                         5.23e+08 Mrev
  Equivalente en horas                            1.14e+11 h
  Sobredimensionados por varios ordenes de magnitud: se eligen
  por disponibilidad y por el eje de 8 mm, no por capacidad.

==============================================================
  D. SELECCION DE MOTOR
==============================================================
  Par requerido                                      0.059 kgf*cm
  Factor de seguridad                                  3.0
  Par de diseno                                      0.178 kgf*cm
  Velocidad requerida                                 76.4 rpm

  motor                    par    rpm   margen  veredicto
  --------------------------------------------------------
  N20 6V 100rpm          0.35    100     2.0x  sirve
  N20 12V 60rpm          0.60     60     3.4x  rpm baja
  JGA25-371 12V          4.50    100    25.3x  sirve
  JGB37-520 12V         15.00     90    84.4x  sirve

  Recomendado: N20 6V 100rpm es el minimo que cumple par Y
  velocidad (2,0x de margen). El N20 de 60 rpm tiene mas par
  pero NO alcanza las 76 rpm que pide la velocidad de 0,10 m/s:
  mas par no compensa una velocidad que no llega.
  Si quieres holgura para subir carga o anadir un segundo tramo,
  el JGA25-371 (25x) cuesta poco mas y evita rediseniar.

==============================================================
  E. ELECTRICA
==============================================================
  Fraccion del par nominal que se usa                 1.32 %
  Corriente del motor en regimen                        75 mA
  Corriente total media del sistema                    192 mA
  Corriente total de pico (arranque + WiFi)           1477 mA
  Potencia media consumida                            2.30 W

  Fuente recomendada    12 V /                            2.22 A
  Fusible                                              2.0 A

  Condensador: medio ciclo de PWM a 20 kHz        25.0 us
  C minimo = I*dt/dV  (dV = 0,10 V)                    300 uF
  Valor adoptado (comercial, con margen)              1000 uF

  Resistencia del cable AWG22, 1 m ida y vuelta     0.102 ohm
  Caida de tension en regimen                          7.6 mV
  Caida de tension en el pico                        122.2 mV

==============================================================
  F. SENSORES E INTERFACES
==============================================================
  --- pull-ups de I2C: es un RANGO, no un valor magico ---
  Rp minima (la fija IOL = 3 mA del pin)              0.97 kohm
  Rp maxima a 100 kHz (tiempo de subida)             11.80 kohm
  Rp maxima a 400 kHz                                 3.54 kohm
  -> 4,7 kohm sirve a 100 kHz;  a 400 kHz hay que bajar a 2,2 k

  --- encoder en cuadratura ---
  Pulsos por vuelta del eje de salida (x1)             374
  En cuadratura (x4)                                  1496
  Resolucion angular                                 0.241 grados
  Resolucion lineal sobre la banda                   0.052 mm/pulso
  Frecuencia de pulsos a 76 rpm                      1905 Hz

  --- divisor si un sensor entrega 5 V a un pin de 3,3 V ---
  R1 = 10 k  ->  R2 teorica               19.41 kohm
  R2 comercial 20 k  ->  tension en el pin            3.33 V

==============================================================
  G. CONTROL
==============================================================
  Resolucion maxima de PWM a 20 kHz (LEDC, 80 MHz)        11 bits
  Pasos de ciclo util                                 2048
  Frecuencia del lazo de velocidad                      50 Hz
  Pulsos de encoder por periodo de muestreo           38.1
  Suficientes pulsos por periodo para medir velocidad por
  conteo simple, sin recurrir a medida de periodo.

==============================================================
  H. SINGULARIZACION CON TODO EL RANGO DE OBJETOS
==============================================================
  Rango de masas    (boton fino a $1000)                28 x
  Rango de diametros                                   2.2 x

  El escalon separador debe cumplir DOS cosas a la vez:
     luz > espesor del mas grueso      -> deja pasar uno
     luz < suma de los dos mas finos   -> no deja pasar dos

  SOLO MONEDAS      minimo 2.20 mm  maximo 2.52 mm  ventana +0.32 mm
  CON BOTONES       minimo 2.20 mm  maximo 1.97 mm  ventana -0.23 mm

  LA VENTANA ES NEGATIVA: no existe ningun valor de escalon
  que deje pasar la moneda de $1000 sola y a la vez impida
  que se cuelen un boton fino y una moneda juntos.

  Con la luz de 2.30 mm (calculada solo para monedas)
  se colarian apilados estos pares:
      $50           + boton fino    = 1.97 mm
      $100          + boton fino    = 2.15 mm
      $200          + boton fino    = 2.19 mm
      boton fino    + boton medio   = 2.30 mm

  CONSECUENCIA DE DISENO: la singularizacion por ALTURA no
  sirve cuando el rango incluye objetos mas finos que las
  monedas. Hay dos salidas:
    1. Separar en el TIEMPO (compuerta que cierra a ras y
       libera de a uno), no en altura.
    2. Aceptar que pasen apilados y resolverlo con vision:
       el boton es clase de RECHAZO, asi que confundir dos
       botones no cuesta dinero. La tolerancia puede ser
       asimetrica: exigente entre denominaciones, relajada
       en la clase que vas a descartar de todos modos.

==============================================================
  I. PRESUPUESTO
==============================================================
  concepto                   ideal    barato  alternativa
  ----------------------------------------------------------------------
  ADC de peso               25,000     8,000  HX711
  Driver de motor           15,000     3,000  MOSFET IRLZ44N + diodo
  Sensor de paso            20,000     4,000  TCRT5000
  Motor                     55,000         0  motor de impresora
  Rodillos                  30,000     3,000  tubo PVC 3/4"
  Bastidor                  50,000     8,000  MDF a mano
  Cinta                     20,000     5,000  lona o banda de tela
  Celda de carga 1 kg       13,090    13,090  Sigma Electronica
  ESP32 DevKit              30,000    30,000  -
  Fuente 12 V 2 A           25,000         0  cargador reciclado
  Rodamientos 608ZZ x4      10,000     5,000  x2 + eje pasante
  ----------------------------------------------------------------------
  TOTAL                    293,090    79,090  COP
  Ahorro: 214,000 COP (73%)

  Precios de orden de magnitud, verificalos antes de comprar.
  Solo la celda de carga esta confirmada (Sigma Electronica).

  La banda necesita 46.5 mW de potencia mecanica.
  Un riel inclinado por gravedad hace el mismo trabajo con CERO
  actuadores. Si el presupuesto aprieta, esa es la via.
```
