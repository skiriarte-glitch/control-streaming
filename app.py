import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🚀 Mi Control de Streaming")

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()
df.columns = [str(c).strip().lower().replace('é', 'e') for c in df.columns]

password = st.sidebar.text_input("Contraseña", type="password")

if password == "Admin123":  
    tasa_dia = st.sidebar.number_input("Tasa (Bs/$)", min_value=1.0, value=40.0, step=0.1)
    
    st.subheader("📅 Próximos Vencimientos")
    hoy = datetime.now().date()
    
    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(df['vencimiento'], errors='coerce').dt.date
        df_vence = df.dropna(subset=['vencimiento'])

        for index, row in df_vence.iterrows():
            dias_restantes = (row['vencimiento'] - hoy).days
            if dias_restantes <= 3:
                nombre = row.get('nombre', 'Cliente')
                servicio = row.get('servicio', 'Servicio')
                precio = row.get('precio_usd', 0)
                id_c = row.get('id_cuenta', 'S/D')
                
                monto_bs = round(float(precio) * tasa_dia, 2)
                color = "🔴" if dias_restantes < 0 else "🟡"
                
                # Mensaje usando ID_Cuenta en lugar de Perfil
                texto = f"¡Hola {nombre}! Vence tu servicio de {servicio} ({id_c}). Total: {precio}$ (Bs. {monto_bs})."
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58"): num = f"58{num}"
                link_wa = f"https://wa.me/{num}?text={urllib.parse.quote(texto)}"
                
                col1, col2 = st.columns([3, 1])
                col1.write(f"{color} **{nombre}** | {servicio} | Vence: {row['vencimiento']}")
                col2.markdown(f"[📲 Cobrar]({link_wa})")
    
    st.divider()
    st.subheader("👥 Lista de Clientes")
    st.dataframe(df)
else:
    st.info("Introduce tu contraseña en la barra lateral (>).")
