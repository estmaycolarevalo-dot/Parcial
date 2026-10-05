# ============================================================
# DASHBOARD EN TIEMPO REAL - Sistema de Logística de Monedas Inteligentes
# ============================================================
# Lee "estado_sistema.json" (escrito por main.py cada 30 pasos de
# simulación) y lo muestra en una página web con Streamlit.
#
# IMPORTANTE: este dashboard NO se conecta a la ESP32 todavía. Lee
# los datos de un archivo que la simulación de PyBullet va
# actualizando. Cuando llegue la etapa de conectar la ESP32 real, lo
# único que cambia es DE DÓNDE vienen los datos (de un GET/MQTT del
# microcontrolador en vez del archivo JSON) — el resto del dashboard
# (las métricas, las gráficas, el layout) se queda igual.
#
# Cómo correrlo (en una terminal aparte, mientras main.py corre en otra):
#   pip install streamlit
#   streamlit run streamlit_dashboard.py
# ============================================================

import streamlit as st
import json
import os
import time

ARCHIVO_ESTADO = "estado_sistema.json"

st.set_page_config(
    page_title="Sistema de Logística de Monedas Inteligentes",
    page_icon="🪙",
    layout="wide",
)

st.title("🪙 Dashboard en Tiempo Real")
st.caption("Sistema de Logística de Monedas Inteligentes — datos leídos de la simulación PyBullet")

if not os.path.exists(ARCHIVO_ESTADO):
    st.warning(
        f"Todavía no existe **{ARCHIVO_ESTADO}**. Deja corriendo `main.py` "
        "en otra terminal (en la misma carpeta) y esta página se actualizará sola."
    )
    time.sleep(2)
    st.rerun()

try:
    with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
        estado = json.load(f)
except (json.JSONDecodeError, OSError):
    # el archivo se estaba escribiendo justo en este instante: solo esperamos al próximo refresco
    st.info("Leyendo datos, un momento...")
    time.sleep(2)
    st.rerun()

contador = estado.get("contador", {"colombia": 0, "extranjera": 0, "boton": 0})
total_monedas = sum(contador.values())

st.caption(f"Última actualización: {estado.get('actualizado', '—')}  |  "
           f"Estado del dron: **{estado.get('dron_estado', '—')}**")

# --- Métricas principales ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Monedas procesadas", total_monedas)
col2.metric("Valor total", f"${estado.get('valor_total_cop', 0):,} COP")
col3.metric("Peso total", f"{estado.get('peso_total_g', 0):.1f} g")
col4.metric("Vasos entregados", estado.get("vasos_entregados", 0))

st.divider()

# --- Desglose por clase ---
st.subheader("Clasificación por tipo de moneda")
c1, c2, c3 = st.columns(3)
c1.metric("🟢 Colombia", contador.get("colombia", 0))
c2.metric("🔵 Extranjera", contador.get("extranjera", 0))
c3.metric("⚪ Botón", contador.get("boton", 0))

st.bar_chart(contador)

st.divider()
st.caption(
    "Este dashboard se actualiza solo cada 2 segundos (sin recargar la página) "
    "leyendo el archivo que escribe main.py — todavía no depende de la ESP32."
)

# --- Auto-actualización SIN recargar el navegador ---
# st.rerun() vuelve a ejecutar este script por la misma conexión (WebSocket)
# de Streamlit y solo repinta los datos que cambiaron, en vez de que el
# NAVEGADOR recargue la página completa (que es lo que hacía el <meta refresh>
# de antes, y por eso volvía a aparecer el aviso de "Install"/"Deploy").
time.sleep(2)
st.rerun()