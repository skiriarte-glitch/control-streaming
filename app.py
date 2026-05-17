import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Sistema Control Streaming", page_icon="🎬", layout="wide")

st.title("🎬 Sistema Control Streaming")

# Dirección directa de tu hoja de Google Sheets (Soluciona el ValueError)
URL_SHEET = "https://docs.google.com/spreadsheets/d/185i9CPA-e3uTvmEBKG8asklwhoPtsFf0fQsShtGiFfE/edit?gid=0#gid=0"

# Inicializar la conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# Leer los datos en tiempo real (ttl=0 para evitar datos antiguos almacenados)
try:
    df = conn.read(spreadsheet=URL_SHEET, ttl=0)
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

# Convertir los encabezados a minúsculas para evitar errores si cambiaste mayúsculas en la hoja
df.columns = [c.lower().strip() for c in df.columns]

# Asegurar que las columnas principales existan en el DataFrame
columnas_obligatorias = ['id', 'cliente', 'telefono', 'clave', 'fecha_vencimiento', 'estado']
for col in columnas_obligatorias:
    if col not in df.columns:
        df[col] = ""

# Convertir la columna de fechas a un formato de fecha nativo de Python para poder comparar
df['fecha_vencimiento'] = pd.to_datetime(df['fecha_vencimiento'], errors='coerce').dt.date

# Obtener la fecha de hoy
hoy = datetime.date.today()

# --- REGLAS DE FILTRADO CORREGIDAS ---
# 1. Avisos de Cobro: Vencen hoy o ya vencieron Y el estado NO es "PAGADO"
df_aviso_cobro = df[(df['fecha_vencimiento'] <= hoy) & (df['estado'].str.upper() != 'PAGADO')]

# 2. Por Renovar / Enviar Datos: Vencen hoy o ya vencieron Y el estado SÍ es "PAGADO"
df_enviar_accesos = df[(df['fecha_vencimiento'] <= hoy) & (df['estado'].str.upper() == 'PAGADO')]


# --- PANEL DE VISUALIZACIÓN ---
# Indicadores rápidos en la parte superior
col1, col2, col3 = st.columns(3)
col1.metric("📢 Avisos de Cobro Pendientes", len(df_aviso_cobro))
col2.metric("🔑 Accesos por Enviar (Ya Pagados)", len(df_enviar_accesos))
col3.metric("👥 Total de Registros", len(df))

# Pestañas de organización de trabajo
tab1, tab2, tab3 = st.tabs(["📝 Editor General", "📢 Alertas de Cobro", "🔑 Accesos por Enviar"])

with tab1:
    st.subheader("Base de Datos Completa")
    st.caption("Nota: Las columnas 'clave' y 'telefono' están completamente desbloqueadas para su edición.")
    
    # st.data_editor permite modificar las celdas directamente. 
    # Únicamente la columna 'id' queda bloqueada para mantener el orden correlativo automático.
    df_editado = st.data_editor(
        df,
        num_rows="dynamic",
        disabled=["id"], 
        use_container_width=True,
        key="editor_principal"
    )
    
    # Botón de guardado definitivo
    if st.button("Guardar Cambios en Google Sheets 💾"):
        try:
            conn.update(spreadsheet=URL_SHEET, data=df_editado)
            st.success("¡Cambios sincronizados correctamente en tu Google Sheets! 🚀")
            st.cache_data.clear()  # Limpia la memoria interna de Streamlit
            st.rerun()             # Recarga la aplicación para ver los datos limpios
        except Exception as e:
            st.error(f"Ocurrió un error al intentar guardar los cambios: {e}")

with tab2:
    st.subheader("Clientes que vencen hoy o están vencidos (Pendientes de Pago)")
    if not df_aviso_cobro.empty:
        st.dataframe(df_aviso_cobro, use_container_width=True)
        st.info("👉 Cambia su estado a 'PAGADO' en la pestaña 'Editor General' cuando realicen el pago.")
    else:
        st.success("🎉 ¡Excelente! No hay clientes con cobros pendientes para el día de hoy.")

with tab3:
    st.subheader("Clientes que ya pagaron hoy (Pendientes de Renovación y Nuevos Accesos)")
    if not df_enviar_accesos.empty:
        st.dataframe(df_enviar_accesos, use_container_width=True)
        st.warning("⚠️ Recuerda: Después de enviarles las nuevas credenciales en su chat, ve al 'Editor General', actualiza su 'fecha_vencimiento' al siguiente mes y limpia el estado.")
    else:
        st.info("No tienes datos de acceso pendientes por entregar en este momento.")
