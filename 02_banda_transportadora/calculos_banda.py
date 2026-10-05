"""
============================================================
MEMORIA DE CALCULO - BANDA TRANSPORTADORA DE MONEDAS
Sistema logistico de monedas inteligentes (objetivo 2)
============================================================
Calcula, en este orden, lo que hace falta para seleccionar cada
componente con justificacion numerica:

  A. MECANICA      carga, friccion, par, rpm, potencia
  B. TRANSMISION   tension de banda (Euler-Eytelwein), no deslizamiento
  C. RODAMIENTOS   carga radial y vida util
  D. MOTOR         seleccion con factor de seguridad
  E. ELECTRICA     corrientes, fuente, condensadores, cableado
  F. SENSORES      pull-ups I2C, niveles logicos, resolucion de encoder
  G. CONTROL       PWM, frecuencia de encoder, periodo de muestreo

Todo sale de los parametros del CAD (cad_banda.py). Si cambias el
diametro del rodillo alli, vuelves a correr esto y la seleccion de
motor se recalcula sola. Esa trazabilidad es lo que distingue una
memoria de calculo de una lista de valores copiados.

Uso:
    python calculos_banda.py            # imprime en pantalla
    python calculos_banda.py --md       # ademas escribe CALCULOS.md
"""
import argparse
import math

# ============================================================
#  PARAMETROS DE ENTRADA  (coherentes con cad_banda.py)
# ============================================================
# --- geometria (mm, luego pasado a SI) ---
D_RODILLO = 25.0e-3          # m
ENTRE_CENTROS = 300.0e-3     # m
ANCHO_BANDA = 70.0e-3        # m
ESP_BANDA = 1.5e-3           # m
LARGO_CINTA = 683.3e-3       # m  (calculado por el CAD)

# --- operacion ---
V_OBJETIVO = 0.10            # m/s
N_MONEDAS_MAX = 20           # objetos sobre la banda
MASA_MONEDA_MAX = 9.95e-3    # kg, la de $1000 (peor caso para el motor)
# Mezcla REAL: la banda no transporta solo monedas de $1000. Media de
# las siete denominaciones en circulacion (familia 2012 + antigua).
MASA_MONEDA_MEDIA = 5.65e-3  # kg
# Catalogo completo de lo que puede entrar, INCLUIDOS los rechazos.
# masa (g), diametro (mm), espesor (mm)
OBJETOS = {
    "$50":        (2.00, 17.00, 1.17),
    "$100":       (3.34, 20.30, 1.35),
    "$200":       (4.61, 22.40, 1.39),
    "$500":       (7.14, 23.70, 2.10),
    "$1000":      (9.95, 26.70, 2.20),
    "$200 ant":   (7.08, 24.40, 1.70),
    "$100 ant":   (5.40, 23.00, 1.70),
    "boton fino": (0.35, 12.00, 0.80),
    "boton medio":(2.08, 15.00, 1.50),
    "boton grueso":(0.49, 15.00, 2.00),
}

# --- materiales ---
RHO_PVC = 1400.0             # kg/m3
MU_BANDA_APOYO_UHMW = 0.15   # PVC sobre cinta UHMW
MU_BANDA_APOYO_ACRIL = 0.40  # PVC sobre acrilico desnudo
MU_BANDA_RODILLO = 0.30      # PVC sobre PLA
K_RESISTENCIAS = 1.30        # +30% por rodadura, flexion y rodamientos

# --- electrico ---
V_FUENTE = 12.0              # V
# La banda gira SIEMPRE en el mismo sentido: no hace falta puente H.
# Un MOSFET de canal N en low-side con PWM y diodo volante hace el
# trabajo con tres componentes y a la quinta parte del costo.
I_MOTOR_VACIO = 0.06         # A   (JGA25-371 12V, hoja tipica)
I_MOTOR_STALL = 1.20         # A
PAR_MOTOR_NOM = 4.5          # kgf*cm a 100 rpm
RPM_MOTOR_NOM = 100.0
I_ESP32_PICO = 0.24          # A   (transmision WiFi)
I_ESP32_MEDIA = 0.08         # A
I_E18 = 0.025                # A
I_NAU7802 = 0.002            # A
I_ENCODER = 0.010            # A
F_PWM = 20000.0              # Hz  (fuera del rango audible)
F_CPU_LEDC = 80e6            # Hz  (reloj base del periferico LEDC)
ENCODER_PPR = 11             # pulsos por vuelta del EJE DEL MOTOR
REDUCCION = 34               # relacion de la reductora
CABLE_AWG22_MM2 = 0.33e-6    # m2
RHO_CU = 1.68e-8             # ohm*m
LARGO_CABLE = 1.0            # m (ida; se cuenta ida y vuelta)

G = 9.81
R = D_RODILLO / 2.0


# ============================================================
def seccion_A_mecanica():
    """Carga, friccion y par. El punto de partida de todo lo demas."""
    m_monedas = N_MONEDAS_MAX * MASA_MONEDA_MAX
    # solo el TRAMO SUPERIOR de la banda apoya sobre la placa
    vol_tramo = ENTRE_CENTROS * ANCHO_BANDA * ESP_BANDA
    m_tramo = RHO_PVC * vol_tramo
    m_total = m_monedas + m_tramo
    N = m_total * G

    F_uhmw = MU_BANDA_APOYO_UHMW * N * K_RESISTENCIAS
    F_acril = MU_BANDA_APOYO_ACRIL * N * K_RESISTENCIAS

    par_uhmw = F_uhmw * R
    par_acril = F_acril * R
    omega = V_OBJETIVO / R
    rpm = omega * 60.0 / (2 * math.pi)
    pot = F_uhmw * V_OBJETIVO

    return dict(m_monedas=m_monedas, m_tramo=m_tramo, m_total=m_total, N=N,
                F_uhmw=F_uhmw, F_acril=F_acril, par_uhmw=par_uhmw,
                par_acril=par_acril, omega=omega, rpm=rpm, pot=pot)


def seccion_B_transmision(F_efectiva):
    """Tension de la banda por Euler-Eytelwein.

    T1/T2 <= e^(mu*theta) es la condicion de NO DESLIZAMIENTO entre la
    banda y el rodillo motriz. Si la relacion de tensiones la supera, la
    banda patina sobre el rodillo por mucho par que tenga el motor. Con
    abrazamiento de 180 grados (theta = pi) y mu = 0,30 el limite es
    e^(0,30*pi) = 2,57.
    """
    theta = math.pi                       # 180 grados de abrazamiento
    razon_max = math.exp(MU_BANDA_RODILLO * theta)
    # T1 - T2 = Fe  y  T1 = razon * T2  ->  T2 = Fe/(razon-1)
    T2 = F_efectiva / (razon_max - 1.0)
    T1 = T2 + F_efectiva
    T_total = T1 + T2

    # pretension practica: se monta con mas tension que el minimo
    # teorico para que la banda no se descuelgue entre rodillos
    T_montaje = max(3.0 * T2, 8.0)        # N, minimo practico

    return dict(theta_deg=180.0, razon_max=razon_max, T1=T1, T2=T2,
                T_total=T_total, T_montaje=T_montaje)


def seccion_C_rodamientos(T_montaje, m_rodillo=0.032):
    """Carga radial en cada rodamiento 608ZZ y vida util L10.

    L10 = (C/P)^3 millones de revoluciones, para rodamientos de bolas.
    """
    C_dinamica = 3350.0                   # N, catalogo 608ZZ
    P = (T_montaje + m_rodillo * G) / 2.0  # repartida entre 2 rodamientos
    L10_Mrev = (C_dinamica / P) ** 3
    rpm = V_OBJETIVO / R * 60 / (2 * math.pi)
    L10_horas = L10_Mrev * 1e6 / (rpm * 60.0)
    return dict(C=C_dinamica, P=P, L10_Mrev=L10_Mrev,
                L10_horas=L10_horas, L10_anios=L10_horas / (8 * 250))


def seccion_D_motor(par_requerido_Nm, rpm_requerida):
    """Seleccion de motor con factor de seguridad."""
    par_kgfcm = par_requerido_Nm * 100.0 / G * 10.0 / 10.0  # N*m -> kgf*cm
    par_kgfcm = par_requerido_Nm / (G * 0.01)               # exacto
    FS = 3.0
    par_diseno = par_kgfcm * FS

    candidatos = [
        ("N20 6V 100rpm",    0.35, 100, 0.12),
        ("N20 12V 60rpm",    0.60,  60, 0.10),
        ("JGA25-371 12V",    4.50, 100, 1.20),
        ("JGB37-520 12V",   15.00,  90, 2.00),
    ]
    evaluados = []
    for nombre, par_nom, rpm_nom, i_stall in candidatos:
        margen = par_nom / par_diseno if par_diseno > 0 else float("inf")
        ok_rpm = rpm_nom >= rpm_requerida * 0.9
        evaluados.append((nombre, par_nom, rpm_nom, i_stall, margen, ok_rpm))
    return dict(par_kgfcm=par_kgfcm, FS=FS, par_diseno=par_diseno,
                candidatos=evaluados)


def seccion_E_electrica(par_requerido_Nm):
    """Corrientes, fuente, condensador y cableado."""
    # el motor solo entrega una fraccion de su par nominal, asi que su
    # corriente esta cerca de la de vacio
    par_nom_Nm = PAR_MOTOR_NOM * G * 0.01
    frac_par = par_requerido_Nm / par_nom_Nm
    # modelo lineal del motor DC: I = I_vacio + (I_stall - I_vacio)*frac
    I_motor = I_MOTOR_VACIO + (I_MOTOR_STALL - I_MOTOR_VACIO) * frac_par

    I_total_media = I_motor + I_ESP32_MEDIA + I_E18 + I_NAU7802 + I_ENCODER
    I_total_pico = I_MOTOR_STALL + I_ESP32_PICO + I_E18 + I_NAU7802 + I_ENCODER
    P_media = V_FUENTE * I_total_media

    # fuente con 50% de margen sobre el pico
    I_fuente = I_total_pico * 1.5

    # --- condensador de desacoplo ---
    # El electrolitico local NO sostiene todo el arranque: filtra el
    # rizado de conmutacion del PWM. Se dimensiona para el medio ciclo:
    dt_pwm = 1.0 / (2 * F_PWM)
    dV_admisible = 0.10                   # V
    C_min = I_MOTOR_STALL * dt_pwm / dV_admisible
    # valor comercial inmediatamente superior, con margen
    C_elegido = 1000e-6

    # --- cableado ---
    R_cable = RHO_CU * (2 * LARGO_CABLE) / CABLE_AWG22_MM2   # ida y vuelta
    dV_media = I_motor * R_cable
    dV_pico = I_MOTOR_STALL * R_cable

    # --- fusible ---
    I_fusible = math.ceil(I_total_pico * 1.3 * 2) / 2.0      # a 0,5 A

    return dict(frac_par=frac_par, I_motor=I_motor,
                I_total_media=I_total_media, I_total_pico=I_total_pico,
                P_media=P_media, I_fuente=I_fuente,
                dt_pwm=dt_pwm, C_min=C_min, C_elegido=C_elegido,
                R_cable=R_cable, dV_media=dV_media, dV_pico=dV_pico,
                I_fusible=I_fusible)


def seccion_F_sensores():
    """Pull-ups de I2C, niveles logicos y resolucion de encoder."""
    # --- I2C: la pull-up tiene un rango, no un valor magico ---
    # Rp_min la fija la corriente que el pin puede hundir en nivel bajo
    VDD, VOL, IOL = 3.3, 0.4, 3e-3
    Rp_min = (VDD - VOL) / IOL
    # Rp_max la fija el tiempo de subida: t_r = 0.8473 * Rp * Cb
    Cb = 100e-12                          # bus corto, pocos dispositivos
    tr_100k, tr_400k = 1000e-9, 300e-9
    Rp_max_100k = tr_100k / (0.8473 * Cb)
    Rp_max_400k = tr_400k / (0.8473 * Cb)

    # --- encoder en cuadratura ---
    ppr_salida_x1 = ENCODER_PPR * REDUCCION
    ppr_salida_x4 = ppr_salida_x1 * 4
    res_angular = 360.0 / ppr_salida_x4
    res_lineal = math.pi * D_RODILLO / ppr_salida_x4
    rpm = V_OBJETIVO / R * 60 / (2 * math.pi)
    f_pulsos = rpm / 60.0 * ppr_salida_x4

    # --- divisor si el sensor entrega 5 V a un pin de 3,3 V ---
    # Vout = Vin * R2/(R1+R2) -> con R1 = 10k, R2 para 3,3 V
    R1 = 10e3
    R2 = R1 * 3.3 / (5.0 - 3.3)
    R2_com = 20e3
    V_div = 5.0 * R2_com / (R1 + R2_com)

    return dict(Rp_min=Rp_min, Rp_max_100k=Rp_max_100k,
                Rp_max_400k=Rp_max_400k, Cb=Cb,
                ppr_x1=ppr_salida_x1, ppr_x4=ppr_salida_x4,
                res_angular=res_angular, res_lineal=res_lineal,
                f_pulsos=f_pulsos, R1=R1, R2_teor=R2, R2_com=R2_com,
                V_div=V_div)


def seccion_G_control(f_pulsos):
    """PWM y periodo de muestreo del lazo de velocidad."""
    # LEDC del ESP32: resolucion maxima = log2(f_clk / f_pwm)
    bits_max = math.floor(math.log2(F_CPU_LEDC / F_PWM))
    pasos = 2 ** bits_max

    # el lazo debe muestrear bastante mas lento que el encoder para
    # contar un numero util de pulsos por periodo
    f_lazo = 50.0                         # Hz
    pulsos_por_periodo = f_pulsos / f_lazo
    return dict(bits_max=bits_max, pasos=pasos, f_lazo=f_lazo,
                pulsos_por_periodo=pulsos_por_periodo)


def seccion_H_singularizacion():
    """Viabilidad del escalon separador con TODO el rango de objetos.

    El escalon debe cumplir dos cosas a la vez:
        luz > espesor del objeto mas grueso        -> deja pasar uno
        luz < suma de los dos objetos mas finos    -> no deja pasar dos
    Si el maximo es menor que el minimo, NO EXISTE valor que sirva.
    """
    esp = {k: v[2] for k, v in OBJETOS.items()}
    solo_mon = {k: v for k, v in esp.items() if k.startswith("$")}

    def ventana(d):
        vals = sorted(d.values())
        lo = vals[-1]                       # el mas grueso
        hi = vals[0] + vals[1]              # los dos mas finos apilados
        return lo, hi, hi - lo

    lo_m, hi_m, v_m = ventana(solo_mon)
    lo_t, hi_t, v_t = ventana(esp)

    # pares que se colarian juntos con la luz calculada para monedas
    luz = lo_m + 0.10
    ks = list(esp)
    pares = []
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            su = esp[ks[i]] + esp[ks[j]]
            if su < luz:
                pares.append((ks[i], ks[j], su))
    return dict(lo_m=lo_m, hi_m=hi_m, v_m=v_m, lo_t=lo_t, hi_t=hi_t,
                v_t=v_t, luz=luz, pares=pares,
                rango_masa=max(v[0] for v in OBJETOS.values()) /
                min(v[0] for v in OBJETOS.values()),
                rango_diam=max(v[1] for v in OBJETOS.values()) /
                min(v[1] for v in OBJETOS.values()))


def seccion_I_presupuesto():
    """Dos listas de materiales: la tecnicamente ideal y la viable con
    presupuesto de estudiante. Precios en COP, orden de magnitud —
    verificalos antes de comprar. Solo la celda esta confirmada.
    """
    filas = [
        # (concepto, ideal, costo_ideal, barato, costo_barato, nota)
        ("ADC de peso", "NAU7802", 25000, "HX711", 8000,
         "el I2C unificado no vale el triple de precio"),
        ("Driver de motor", "TB6612FNG", 15000, "MOSFET IRLZ44N + diodo", 3000,
         "la banda gira en un solo sentido: sobra el puente H"),
        ("Sensor de paso", "E18-D80NK", 20000, "TCRT5000", 4000,
         "el umbral ajustable es comodo, no imprescindible"),
        ("Motor", "JGA25-371 c/encoder", 55000, "motor de impresora", 0,
         "se necesitan 0,059 kgf*cm: casi cualquiera sobra"),
        ("Rodillos", "impresion 3D", 30000, "tubo PVC 3/4\"", 3000,
         "26,67 mm de diametro exterior"),
        ("Bastidor", "acrilico corte laser", 50000, "MDF a mano", 8000, ""),
        ("Cinta", "PVC 1,5 mm por metro", 20000, "lona o banda de tela", 5000,
         ""),
        ("Celda de carga 1 kg", "Sigma Electronica", 13090,
         "Sigma Electronica", 13090, "precio verificado"),
        ("ESP32 DevKit", "-", 30000, "-", 30000, "imprescindible"),
        ("Fuente 12 V 2 A", "-", 25000, "cargador reciclado", 0, ""),
        ("Rodamientos 608ZZ x4", "-", 10000, "x2 + eje pasante", 5000, ""),
    ]
    tot_i = sum(r[2] for r in filas)
    tot_b = sum(r[4] for r in filas)
    return dict(filas=filas, total_ideal=tot_i, total_barato=tot_b)


# ============================================================
def informe():
    A = seccion_A_mecanica()
    B = seccion_B_transmision(A["F_uhmw"])
    C = seccion_C_rodamientos(B["T_montaje"])
    D = seccion_D_motor(A["par_uhmw"], A["rpm"])
    E = seccion_E_electrica(A["par_uhmw"])
    F = seccion_F_sensores()
    Gc = seccion_G_control(F["f_pulsos"])
    return A, B, C, D, E, F, Gc


def imprimir():
    A, B, C, D, E, F, Gc = informe()
    Hs = seccion_H_singularizacion()
    I = seccion_I_presupuesto()
    L = []
    p = L.append

    p("\n" + "=" * 62)
    p("  A. MECANICA")
    p("=" * 62)
    p(f"  Monedas sobre la banda ({N_MONEDAS_MAX} de $1000, peor caso)"
      f"     {A['m_monedas']*1000:8.1f} g")
    p(f"  Tramo superior de la cinta                      "
      f"{A['m_tramo']*1000:8.1f} g")
    p(f"  Masa total sobre la placa de apoyo              "
      f"{A['m_total']*1000:8.1f} g")
    p(f"  Fuerza normal N = m*g                           "
      f"{A['N']:8.2f} N")
    p("")
    p(f"  Fuerza de arrastre con cinta UHMW (mu={MU_BANDA_APOYO_UHMW})    "
      f"{A['F_uhmw']:8.3f} N")
    p(f"  Fuerza de arrastre sin ella (acrilico, mu={MU_BANDA_APOYO_ACRIL}) "
      f"{A['F_acril']:8.3f} N")
    p(f"  -> forrar la placa AHORRA "
      f"{100*(1-A['F_uhmw']/A['F_acril']):.0f}% del esfuerzo")
    p("")
    p(f"  Par en el rodillo  T = F*r                      "
      f"{A['par_uhmw']*1000:8.3f} mN*m")
    p(f"                                                  "
      f"{A['par_uhmw']/(G*0.01):8.3f} kgf*cm")
    p(f"  Velocidad angular  w = v/r                      "
      f"{A['omega']:8.2f} rad/s")
    p(f"  Velocidad de giro                               "
      f"{A['rpm']:8.1f} rpm")
    p(f"  Potencia mecanica  P = F*v                      "
      f"{A['pot']*1000:8.2f} mW")

    p("\n" + "=" * 62)
    p("  B. TENSION DE LA BANDA  (Euler-Eytelwein)")
    p("=" * 62)
    p(f"  Angulo de abrazamiento                          "
      f"{B['theta_deg']:8.0f} grados")
    p(f"  Relacion maxima T1/T2 = e^(mu*theta)            "
      f"{B['razon_max']:8.2f}")
    p(f"  Tension del lado tenso    T1                    "
      f"{B['T1']:8.2f} N")
    p(f"  Tension del lado flojo    T2                    "
      f"{B['T2']:8.2f} N")
    p(f"  Carga total sobre el eje  T1+T2                 "
      f"{B['T_total']:8.2f} N")
    p(f"  Pretension de montaje recomendada               "
      f"{B['T_montaje']:8.1f} N")
    p("  La condicion de no deslizamiento se cumple por diseno: la")
    p("  fuerza que hay que transmitir es minima frente al limite.")

    p("\n" + "=" * 62)
    p("  C. RODAMIENTOS 608ZZ")
    p("=" * 62)
    p(f"  Capacidad dinamica de catalogo  C               "
      f"{C['C']:8.0f} N")
    p(f"  Carga radial por rodamiento     P               "
      f"{C['P']:8.2f} N")
    p(f"  Vida util L10 = (C/P)^3                         "
      f"{C['L10_Mrev']:8.3g} Mrev")
    p(f"  Equivalente en horas                            "
      f"{C['L10_horas']:8.3g} h")
    p("  Sobredimensionados por varios ordenes de magnitud: se eligen")
    p("  por disponibilidad y por el eje de 8 mm, no por capacidad.")

    p("\n" + "=" * 62)
    p("  D. SELECCION DE MOTOR")
    p("=" * 62)
    p(f"  Par requerido                                   "
      f"{D['par_kgfcm']:8.3f} kgf*cm")
    p(f"  Factor de seguridad                             "
      f"{D['FS']:8.1f}")
    p(f"  Par de diseno                                   "
      f"{D['par_diseno']:8.3f} kgf*cm")
    p(f"  Velocidad requerida                             "
      f"{A['rpm']:8.1f} rpm")
    p("")
    p(f"  {'motor':<20}{'par':>8}{'rpm':>7}{'margen':>9}  veredicto")
    p("  " + "-" * 56)
    for nombre, par, rpm_n, i_st, margen, ok in D["candidatos"]:
        ver = "sirve" if (margen >= 1 and ok) else (
            "rpm baja" if margen >= 1 else "par insuficiente")
        p(f"  {nombre:<20}{par:>7.2f} {rpm_n:>6.0f}{margen:>8.1f}x  {ver}")
    p("")
    p("  Recomendado: N20 6V 100rpm es el minimo que cumple par Y")
    p("  velocidad (2,0x de margen). El N20 de 60 rpm tiene mas par")
    p("  pero NO alcanza las 76 rpm que pide la velocidad de 0,10 m/s:")
    p("  mas par no compensa una velocidad que no llega.")
    p("  Si quieres holgura para subir carga o anadir un segundo tramo,")
    p("  el JGA25-371 (25x) cuesta poco mas y evita rediseniar.")

    p("\n" + "=" * 62)
    p("  E. ELECTRICA")
    p("=" * 62)
    p(f"  Fraccion del par nominal que se usa             "
      f"{E['frac_par']*100:8.2f} %")
    p(f"  Corriente del motor en regimen                  "
      f"{E['I_motor']*1000:8.0f} mA")
    p(f"  Corriente total media del sistema               "
      f"{E['I_total_media']*1000:8.0f} mA")
    p(f"  Corriente total de pico (arranque + WiFi)       "
      f"{E['I_total_pico']*1000:8.0f} mA")
    p(f"  Potencia media consumida                        "
      f"{E['P_media']:8.2f} W")
    p("")
    p(f"  Fuente recomendada    {V_FUENTE:.0f} V /                        "
      f"{E['I_fuente']:8.2f} A")
    p(f"  Fusible                                         "
      f"{E['I_fusible']:8.1f} A")
    p("")
    p(f"  Condensador: medio ciclo de PWM a {F_PWM/1000:.0f} kHz    "
      f"{E['dt_pwm']*1e6:8.1f} us")
    p(f"  C minimo = I*dt/dV  (dV = 0,10 V)               "
      f"{E['C_min']*1e6:8.0f} uF")
    p(f"  Valor adoptado (comercial, con margen)          "
      f"{E['C_elegido']*1e6:8.0f} uF")
    p("")
    p(f"  Resistencia del cable AWG22, {LARGO_CABLE:.0f} m ida y vuelta  "
      f"{E['R_cable']:8.3f} ohm")
    p(f"  Caida de tension en regimen                     "
      f"{E['dV_media']*1000:8.1f} mV")
    p(f"  Caida de tension en el pico                     "
      f"{E['dV_pico']*1000:8.1f} mV")

    p("\n" + "=" * 62)
    p("  F. SENSORES E INTERFACES")
    p("=" * 62)
    p("  --- pull-ups de I2C: es un RANGO, no un valor magico ---")
    p(f"  Rp minima (la fija IOL = 3 mA del pin)          "
      f"{F['Rp_min']/1000:8.2f} kohm")
    p(f"  Rp maxima a 100 kHz (tiempo de subida)          "
      f"{F['Rp_max_100k']/1000:8.2f} kohm")
    p(f"  Rp maxima a 400 kHz                             "
      f"{F['Rp_max_400k']/1000:8.2f} kohm")
    p("  -> 4,7 kohm sirve a 100 kHz;  a 400 kHz hay que bajar a 2,2 k")
    p("")
    p("  --- encoder en cuadratura ---")
    p(f"  Pulsos por vuelta del eje de salida (x1)        "
      f"{F['ppr_x1']:8.0f}")
    p(f"  En cuadratura (x4)                              "
      f"{F['ppr_x4']:8.0f}")
    p(f"  Resolucion angular                              "
      f"{F['res_angular']:8.3f} grados")
    p(f"  Resolucion lineal sobre la banda                "
      f"{F['res_lineal']*1000:8.3f} mm/pulso")
    p(f"  Frecuencia de pulsos a {A['rpm']:.0f} rpm                  "
      f"{F['f_pulsos']:8.0f} Hz")
    p("")
    p("  --- divisor si un sensor entrega 5 V a un pin de 3,3 V ---")
    p(f"  R1 = {F['R1']/1000:.0f} k  ->  R2 teorica            "
      f"{F['R2_teor']/1000:8.2f} kohm")
    p(f"  R2 comercial 20 k  ->  tension en el pin        "
      f"{F['V_div']:8.2f} V")

    p("\n" + "=" * 62)
    p("  G. CONTROL")
    p("=" * 62)
    p(f"  Resolucion maxima de PWM a {F_PWM/1000:.0f} kHz "
      f"(LEDC, {F_CPU_LEDC/1e6:.0f} MHz)  {Gc['bits_max']:8.0f} bits")
    p(f"  Pasos de ciclo util                             "
      f"{Gc['pasos']:8.0f}")
    p(f"  Frecuencia del lazo de velocidad                "
      f"{Gc['f_lazo']:8.0f} Hz")
    p(f"  Pulsos de encoder por periodo de muestreo       "
      f"{Gc['pulsos_por_periodo']:8.1f}")
    if Gc["pulsos_por_periodo"] < 10:
        p("  AVISO: pocos pulsos por periodo -> la medida de velocidad")
        p("  sera ruidosa. Baja la frecuencia del lazo o mide por")
        p("  periodo entre flancos en vez de por conteo.")
    else:
        p("  Suficientes pulsos por periodo para medir velocidad por")
        p("  conteo simple, sin recurrir a medida de periodo.")

    p("\n" + "=" * 62)
    p("  H. SINGULARIZACION CON TODO EL RANGO DE OBJETOS")
    p("=" * 62)
    p(f"  Rango de masas    (boton fino a $1000)          "
      f"{Hs['rango_masa']:8.0f} x")
    p(f"  Rango de diametros                              "
      f"{Hs['rango_diam']:8.1f} x")
    p("")
    p("  El escalon separador debe cumplir DOS cosas a la vez:")
    p("     luz > espesor del mas grueso      -> deja pasar uno")
    p("     luz < suma de los dos mas finos   -> no deja pasar dos")
    p("")
    p(f"  SOLO MONEDAS      minimo {Hs['lo_m']:.2f} mm  maximo "
      f"{Hs['hi_m']:.2f} mm  ventana {Hs['v_m']:+.2f} mm")
    p(f"  CON BOTONES       minimo {Hs['lo_t']:.2f} mm  maximo "
      f"{Hs['hi_t']:.2f} mm  ventana {Hs['v_t']:+.2f} mm")
    p("")
    if Hs["v_t"] <= 0:
        p("  LA VENTANA ES NEGATIVA: no existe ningun valor de escalon")
        p("  que deje pasar la moneda de $1000 sola y a la vez impida")
        p("  que se cuelen un boton fino y una moneda juntos.")
        p("")
        p(f"  Con la luz de {Hs['luz']:.2f} mm (calculada solo para monedas)")
        p("  se colarian apilados estos pares:")
        for a, b, su in Hs["pares"]:
            p(f"      {a:<13} + {b:<13} = {su:.2f} mm")
        p("")
        p("  CONSECUENCIA DE DISENO: la singularizacion por ALTURA no")
        p("  sirve cuando el rango incluye objetos mas finos que las")
        p("  monedas. Hay dos salidas:")
        p("    1. Separar en el TIEMPO (compuerta que cierra a ras y")
        p("       libera de a uno), no en altura.")
        p("    2. Aceptar que pasen apilados y resolverlo con vision:")
        p("       el boton es clase de RECHAZO, asi que confundir dos")
        p("       botones no cuesta dinero. La tolerancia puede ser")
        p("       asimetrica: exigente entre denominaciones, relajada")
        p("       en la clase que vas a descartar de todos modos.")

    p("\n" + "=" * 62)
    p("  I. PRESUPUESTO")
    p("=" * 62)
    p(f"  {'concepto':<22}{'ideal':>10}{'barato':>10}  alternativa")
    p("  " + "-" * 70)
    for con, idl, ci, bar, cb, nota in I["filas"]:
        p(f"  {con:<22}{ci:>10,}{cb:>10,}  {bar}")
    p("  " + "-" * 70)
    p(f"  {'TOTAL':<22}{I['total_ideal']:>10,}{I['total_barato']:>10,}  COP")
    p(f"  Ahorro: {I['total_ideal']-I['total_barato']:,} COP "
      f"({100*(1-I['total_barato']/I['total_ideal']):.0f}%)")
    p("")
    p("  Precios de orden de magnitud, verificalos antes de comprar.")
    p("  Solo la celda de carga esta confirmada (Sigma Electronica).")
    p("")
    p(f"  La banda necesita {A['pot']*1000:.1f} mW de potencia mecanica.")
    p("  Un riel inclinado por gravedad hace el mismo trabajo con CERO")
    p("  actuadores. Si el presupuesto aprieta, esa es la via.")

    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()
    A = seccion_A_mecanica()
    texto = imprimir()
    print(texto)
    if args.md:
        with open("CALCULOS.md", "w", encoding="utf-8") as f:
            f.write("# Memoria de cálculo — banda transportadora\n\n")
            f.write("```\n" + texto + "\n```\n")
        print("\n  -> CALCULOS.md escrito")
