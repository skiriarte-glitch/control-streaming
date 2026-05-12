import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# Configuración de página
st.set_page_config(page_title="Control Streaming", layout="wide")

st.title("🚀 Mi Control de Streaming")
password = st.sidebar.text_input("Contraseña de acceso", type="password")

# Aquí pones tu clave secreta
if password == "Admin123":  
    
    # Conexión con tu Google Sheet
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()

    # --- TASA DEL DÍA ---
    st.sidebar.header("📊 Finanzas")
    tasa_dia = st.sidebar.number_input("Tasa del Día (Bs/$)", min_value=1.0, value=40.0, step=0.1)

    # --- ALERTAS DE COBRO ---
    st.subheader("📅 Próximos Vencimientos")
    hoy = datetime.now().date()
    
    # Asegurarnos de que las fechas se lean bien
    df['Vencimiento'] = pd.to_datetime(df['Vencimiento']).dt.date
    
    for index, row in df.iterrows():
        dias_restantes = (row['Vencimiento'] - hoy).days
        
        if dias_restantes <= 3:
            monto_bs = round(row["Precio_USD"] * tasa_dia, 2)
            color = "🔴" if dias_restantes < 0 else "🟡"
            
            # Mensaje automático para WhatsApp
            # Incluimos ID_Cuenta (Expo) y Perfil para que el cliente sepa qué paga
            texto = (f"¡Hola {row['Nombre']}! Te recuerdo el vencimiento de tu perfil {row['Perfil']} "
                     f"de {row['Servicio']} ({row['ID_Cuenta']}). "
                     f"Vence {'hoy' if dias_restantes == 0 else f'en {dias_restantes} días'}. "
                     f"Total a pagar: {row['Precio_USD']}$ (Bs. {monto_bs}). "
                     f"¡Quedo atento a tu comprobante!")
            
            # Formatear el teléfono
            num = str(row['Telefono']).strip().replace(".0", "")
            if not num.startswith("58") and not num.startswith("+58"): 
                num = f"58{num}"
                
            link_wa = f"https://wa.me/{num}?text={urllib.parse.quote(texto)}"
            
            col1, col2 = st.columns([3, 1])
            col1.write(f"{color} **{row['Nombre']}** | {row['Servicio']} - {row['ID_Cuenta']} (Perfil {row['Perfil']})")
            col2.markdown(f"[📲 Cobrar Bs. {monto_bs}]({link_wa})")

    st.divider()
    st.subheader("👥 Lista Completa")
    st.dataframe(df, use_container_width=True)

else:
    st.info("Introduce tu contraseña en la barra lateral.")
