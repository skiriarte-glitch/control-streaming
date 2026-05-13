import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# Configuración de la pestaña
st.set_page_config(page_title="Control Skarleth", layout="wide")

# TÍTULO ACTUALIZADO
st.title("🎬 Sistema de Control Streaming")

# --- CONTRASEÑA ---
CLAVE_MAESTRA = "Skarleth2026" 

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# Limpieza y unificación de columnas
df.columns = [str(c).strip().lower().replace('é', 'e').replace('ó', 'o').replace('status', 'estatus') for c in df.columns]

password = st.sidebar.text_input("Contraseña", type="password")

if password == CLAVE_MAESTRA:
    # TASA INICIAL CONFIGURADA EN 660 (Tasa Binance)
    tasa_dia = st.sidebar.number_input("Tasa del día (Bs/$)", min_value=1.0, value=660.0, step=1.0)
    
    # 1. SECCIÓN DE INVENTARIO
    st.markdown("### 💜 Perfiles Disponibles (Inventario)")
    if 'nombre' in df.columns:
        mask_nombre = df['nombre'].str.contains('DISPONIBLE|VACANTE|LIBRE', case=False, na=False)
        mask_estatus = pd.Series([False] * len(df))
        if 'estatus' in df.columns:
            mask_estatus = df['estatus'].str.contains('libre', case=False, na=False)
            
        disponibles = df[mask_nombre | mask_estatus]
        
        if not disponibles.empty:
            for idx, row in disponibles.iterrows():
                st.success(f"✨ **{row.get('servicio', 'Servicio')}** disponible en cuenta: `{row.get('id_cuenta', 'S/D')}`")
        else:
            st.write("No tienes cupos libres por ahora.")

    st.divider()

    # 2. GESTIÓN DE CLIENTES
    st.subheader("📅 Gestión de Clientes")
    ahora = datetime.now()

    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(df['vencimiento'], errors='coerce')
        df = df.sort_values(by='vencimiento')

        for index, row in df.iterrows():
            nombre = str(row.get('nombre', ''))
            if any(x in nombre.lower() for x in ['disponible', 'vacante', 'libre']): continue
            
            servicio = str(row.get('servicio', 'Servicio')).strip()
            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')
            precio = float(row.get('precio_usd', 0) if row.get('precio_usd') else 0)
            vence_dt = row['vencimiento']
            
            if pd.isna(vence_dt): continue
            
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            # El cálculo ahora usará los 660 por defecto
            monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
            
            estatus = str(row.get('estatus', '')).lower()
            color = "🔴" if vence_dt < ahora else "🟡"
            
            # --- COBRO ---
            if estatus != 'pagado' and vence_dt <= ahora + timedelta(days=3):
                with st.expander(f"{color} COBRAR A: {nombre} ({servicio})"):
                    msg_cobro = (
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
                    link_cobro = f"https://wa.me/{num}?text={urllib.parse.quote(msg_cobro.encode('utf-8'))}"
                    st.markdown(f"[📲 Enviar Mensaje de Cobro]({link_cobro})")

            # --- ENTREGA DE CLAVES ---
            with st.expander(f"🔑 ENTREGAR CLAVES A: {nombre} ({servicio})"):
                conexiones = "1"
                if "flujotv" in servicio.lower():
                    if precio == 6: conexiones = "2"
                    elif precio >= 9: conexiones = "3"
                elif "jumangistv" in servicio.lower():
                    conexiones = "3"

                msg_entrega = (
                    f"✨ Aquí están tus datos personales de acceso. No los compartas con nadie. "
                    f"Asegúrate de que no se exceda tu número máximo de conexiones permitidas.\n\n"
                    f"⚡️Conexiones: {conexiones}\n"
                    f"📆 Próxima renovación: {fecha_vence_str}\n\n"
                )
                if "jumangistv" in servicio.lower():
                    msg_entrega += f"🛜Host/URL: http://jumangis.cloud:2082n"
                
                msg_entrega += f"👤 Usuario: {id_u}\n🔐 Contraseña: {clave}\n"
                if "flujotv" in servicio.lower():
                    msg_entrega += f"🚯 PIN contenido adulto: 1234\n"
                
                msg_entrega += f"\n¡Disfruta de tus contenidos favoritos! Si necesitas ayuda, no dudes en contactarme. 📩"
                
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58"): num = f"58{num}"
                link_entrega = f"https://wa.me/{num}?text={urllib.parse.quote(msg_entrega.encode('utf-8'))}"
                st.markdown(f"[🚀 Enviar Datos de Acceso]({link_entrega})")

    st.divider()
    st.subheader("👥 Base de Datos General")
    st.dataframe(df)

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
