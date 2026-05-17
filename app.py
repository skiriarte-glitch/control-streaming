import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# Configuración inicial de la página
st.set_page_config(page_title="Sistema Control Streaming", page_icon="🎬", layout="wide")
st.title("🎬 Sistema Control Streaming")

# Dirección directa de tu hoja de Google Sheets (modo público)
URL_SHEET = "https://docs.google.com/spreadsheets/d/185i9CPA-e3uTvmEBKG8asklwhoPtsFf0fQsShtGiFfE/edit?gid=0#gid=0"

# Inicializar conexión limpia sin depender de Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Al pasarle la URL aquí, lee la hoja directamente sin pedir llaves ni credenciales
    df = conn.read(spreadsheet=URL_SHEET, ttl=0)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# Asegurar que todas las columnas estén en minúsculas para evitar errores
df.columns = [str(c).lower().strip() for c in df.columns]

# Crear las columnas principales si la hoja está vacía
columnas_obligatorias = ['id', 'cliente', 'telefono', 'clave', 'fecha_vencimiento', 'estado']
for col in columnas_obligatorias:
    if col not in df.columns:
        df[col] = ""

# --- FILTROS SEGUROS DE FECHAS Y ESTADOS ---
df['fecha_segura'] = pd.to_datetime(df['fecha_vencimiento'], format='%d/%m/%Y', errors='coerce').fillna(pd.to_datetime(df['fecha_vencimiento'], errors='coerce'))
hoy = pd.to_datetime(date.today())
estado_limpio = df['estado'].astype(str).str.strip().str.upper()

# 1. Avisos de Cobro: Vencen hoy (o ya vencieron) Y estado NO es PAGADO
df_aviso_cobro = df[(df['fecha_segura'] <= hoy) & (estado_limpio != 'PAGADO')]

# 2. Accesos por enviar: Vencen hoy (o ya vencieron) Y estado SÍ es PAGADO
df_enviar_accesos = df[(df['fecha_segura'] <= hoy) & (estado_limpio == 'PAGADO')]

# Borrar columna temporal antes de mostrar las tablas
df = df.drop(columns=['fecha_segura'], errors='ignore')
df_aviso_cobro = df_aviso_cobro.drop(columns=['fecha_segura'], errors='ignore')
df_enviar_accesos = df_enviar_accesos.drop(columns=['fecha_segura'], errors='ignore')

# --- PANELES VISUALES ---
col1, col2, col3 = st.columns(3)
col1.metric("📢 Avisos de Cobro Pendientes", len(df_aviso_cobro))
col2.metric("🔑 Accesos por Enviar (Ya Pagados)", len(df_enviar_accesos))
col3.metric("👥 Total de Registros", len(df))

tab1, tab2, tab3 = st.tabs(["📝 Base de Datos", "📢 Alertas de Cobro", "🔑 Accesos por Enviar"])

with tab1:
    st.subheader("Base de Datos Completa (Modo Estable)")
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("Pendientes de Pago (Avisos de Cobro)")
    st.dataframe(df_aviso_cobro, use_container_width=True)

with tab3:
    st.subheader("Ya Pagaron (Pendientes de enviar clave o renovar mes)")
    st.dataframe(df_enviar_accesos, use_container_width=True)
