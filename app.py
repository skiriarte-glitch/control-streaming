import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

# CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🎬 Mi Control de Streaming")

# --- AQUÍ CAMBIAS TU CONTRASEÑA ---
CLAVE_MAESTRA = "Z2599393F" 

# Conexión
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()
df.columns = [str(c).strip().lower().replace('é', 'e') for c in df.columns]

password = st.sidebar.text_input("Contraseña de acceso", type="password")

if password == CLAVE_MAESTRA:  
    tasa_dia = st.sidebar.number_input("Tasa del día (Bs/$)", min_value=1.0, value=40.0, step=0.1)
    
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
                precio_usd = float(row.get('precio_usd', 0))
                
                # CÁLCULO DEL MONTO EN BS
                monto_bs = "{:,.2f}".format(precio_usd * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
                
                color = "🔴" if dias_restantes < 0 else "🟡"
                
                # TU MENSAJE PERSONALIZADO
                texto = (
                    f"Hola “{nombre}” 🫂\n\n"
                    f"Ya está disponible la renovación de tu suscripción de {servicio}.\n\n"
                    f"Si deseas renovar, te dejo los datos de pago.\n\n"
                    f"*Pago móvil* 💳\n"
                    f"Banco: Bancamiga\n"
                    f"Documento: 13024234\n"
                    f"Teléfono: 04246379018\n"
                    f"Concepto: *PAGO*\n"
                    f"Monto: *{monto_bs} Bs.*\n\n"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda ✨"
                )
                
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58"): num = f"58{num}"
                link_wa = f"https://wa.me/{num}?text={urllib.parse.quote(texto)}"
                
                col1, col2 = st.columns([3, 1])
                col1.write(f"{color} **{nombre}** | {servicio} | Vence: {row['vencimiento']}")
                col2.markdown(f"[📲 Enviar Cobro]({link_wa})")
    
    st.divider()
    st.subheader("👥 Lista Completa de Clientes")
    st.dataframe(df)
else:
    st.info("Introduce tu nueva contraseña en la barra lateral (>).")
