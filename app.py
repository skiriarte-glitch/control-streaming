import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🍿 Mi Control de Streaming")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# --- MAGIA PARA EVITAR ERRORES DE NOMBRES ---
# Esto pone todos los títulos en minúsculas y quita espacios
df.columns = df.columns.str.strip().str.lower()

password = st.sidebar.text_input("Contraseña", type="password")

if password == "Admin123":  
    tasa_dia = st.sidebar.number_input("Tasa (Bs/$)", min_value=1.0, value=40.0, step=0.1)
    
    st.subheader("📅 Próximos Vencimientos")
    hoy = datetime.now().date()
    
    # Buscamos la columna de vencimiento sin importar cómo la escribiste
    col_vence = 'vencimiento' 
    df[col_vence] = pd.to_datetime(df[col_vence], errors='coerce').dt.date
    df = df.dropna(subset=[col_vence])

    for index, row in df.iterrows():
        dias_restantes = (row[col_vence] - hoy).days
        
        if dias_restantes <= 3:
            # Usamos nombres en minúsculas porque el código los transformó así
            monto_bs = round(float(row["precio_usd"]) * tasa_dia, 2)
            color = "🔴" if dias_restantes < 0 else "🟡"
            
            texto = (f"¡Hola {row['nombre']}! Vence tu perfil {row['perfil']} "
                     f"de {row['servicio']}. Total: {row['precio_usd']}$ (Bs. {monto_bs}).")
            
            num = str(row['telefono']).split('.')[0].strip()
            if not num.startswith("58"): num = f"58{num}"
            link_wa = f"https://wa.me/{num}?text={urllib.parse.quote(texto)}"
            
            col1, col2 = st.columns([3, 1])
            col1.write(f"{color} **{row['nombre']}** | {row[col_vence]}")
            col2.markdown(f"[📲 Cobrar]({link_wa})")

    st.divider()
    st.subheader("👥 Lista Completa")
    st.dataframe(df)
else:
    st.info("Pon la clave en el menú lateral (>).")
