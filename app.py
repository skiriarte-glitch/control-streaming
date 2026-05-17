import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# Configuración inicial de la página
st.set_page_config(page_title="Sistema Control Streaming", page_icon="🎬", layout="wide")
st.title("🎬 Sistema Control Streaming")

# 1. Conexión segura (tal cual te estaba funcionando)
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leemos la hoja (ttl=0 para que siempre traiga datos frescos)
    df = conn.read(ttl=0)
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# Asegurar que todas las columnas estén en minúsculas para evitar errores
df.columns = [str(c).lower().strip() for c in df.columns]

# Crear las columnas si la hoja está vacía
columnas_obligatorias = ['id', 'cliente', 'telefono', 'clave', 'fecha_vencimiento', 'estado']
for col in columnas_obligatorias:
    if col not in df.columns:
        df[col] = ""

# --- ESCUDO CONTRA ERRORES DE FECHAS ---
# Creamos una columna temporal segura para comparar fechas sin que el sistema explote por celdas vacías
df['fecha_segura'] = pd.to_datetime(df['fecha_vencimiento'], format='%d/%m/%Y', errors='coerce').fillna(pd.to_datetime(df['fecha_vencimiento'], errors='coerce'))
hoy = pd.to_datetime(date.today())

# Limpiamos el texto de la columna estado (quitamos espacios extra y pasamos a mayúsculas)
estado_limpio = df['estado'].astype(str).str.strip().str.upper()


# --- TUS DOS CORRECCIONES DE FILTRADO ---

# 1. Avisos de Cobro: Vencen hoy (o ya vencieron) Y estado NO es PAGADO
df_aviso_cobro = df[(df['fecha_segura'] <= hoy) & (estado_limpio != 'PAGADO')]

# 2. Accesos por enviar: Vencen hoy (o ya vencieron) Y estado SÍ es PAGADO
df_enviar_accesos = df[(df['fecha_segura'] <= hoy) & (estado_limpio == 'PAGADO')]

# Borramos la columna de fecha temporal para que no se muestre en tu tabla
df = df.drop(columns=['fecha_segura'])
df_aviso_cobro = df_aviso_cobro.drop(columns=['fecha_segura'], errors='ignore')
df_enviar_accesos = df_enviar_accesos.drop(columns=['fecha_segura'], errors='ignore')


# --- PANELES VISUALES ---
col1, col2, col3 = st.columns(3)
col1.metric("📢 Avisos de Cobro Pendientes", len(df_aviso_cobro))
col2.metric("🔑 Accesos por Enviar (Ya Pagados)", len(df_enviar_accesos))
col3.metric("👥 Total de Registros", len(df))

tab1, tab2, tab3 = st.tabs(["📝 Editor General", "📢 Alertas de Cobro", "🔑 Accesos por Enviar"])

with tab1:
    st.subheader("Base de Datos Completa")
    st.caption("Escribe directamente en la tabla para modificar.")
    
    # --- TU CORRECCIÓN DE DESBLOQUEO ---
    # Al dejar solo "id", las columnas "clave" y "telefono" quedan 100% libres para escribir
    df_editado = st.data_editor(
        df,
        num_rows="dynamic",
        disabled=["id"], 
        use_container_width=True
    )
    
    if st.button("Guardar Cambios en Google Sheets 💾"):
        try:
            conn.update(data=df_editado)
            st.success("¡Datos guardados con éxito!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

with tab2:
    st.subheader("Pendientes de Pago (Avisos de Cobro)")
    st.dataframe(df_aviso_cobro, use_container_width=True)

with tab3:
    st.subheader("Ya Pagaron (Pendientes de enviar clave o renovar mes)")
    st.dataframe(df_enviar_accesos, use_container_width=True)
