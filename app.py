import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# Configuración del nombre en la pestaña del navegador
st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🎬 Sistema de Control Streaming")

# --- CONTRASEÑA ---
CLAVE_MAESTRA = "Prueba123" 

# Conexión a la base de datos
conn = st.connection("gsheets", type=GSheetsConnection)

# --- BOTÓN DE ACTUALIZACIÓN MANUAL ---
if st.sidebar.button("🔄 Actualizar Datos Ahora"):
    st.cache_data.clear()
    st.rerun()

df = conn.read()
# Limpieza de nombres de columnas
df.columns = [str(c).strip().lower().replace('é', 'e').replace('ó', 'o') for c in df.columns]

password = st.sidebar.text_input("Contraseña", type="password")

if password == CLAVE_MAESTRA:
    tasa_dia = st.sidebar.number_input("Tasa del día (Bs/$)", min_value=1.0, value=660.0, step=1.0)
    
    # 1. CONSEGUIR FECHA DE HOY LIMPIA (Sin horas, minutos ni segundos)
    ahora = datetime.now()
    fecha_hoy = datetime(ahora.year, ahora.month, ahora.day)
    
    # 2. LÍMITE MÁXIMO DE COBRO (Exactamente hoy + 2 días, a las 00:00:00)
    fecha_limite_cobro = fecha_hoy + timedelta(days=2)

    # Preparar el DataFrame convirtiendo fechas
    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(df['vencimiento'], errors='coerce')
        df = df.sort_values(by='vencimiento')

    # =========================================================================
    # 1. 💜 PERFILES DISPONIBLES
    # =========================================================================
    st.markdown("### 💜 Perfiles Disponibles")
    condicion_libre = pd.Series(False, index=df.index)
    if 'estatus' in df.columns:
        condicion_libre = (df['estatus'].str.lower().str.contains('libre|vacante', na=False)) | \
                          (df['nombre'].str.lower().str.contains('disponible|libre|vacante', na=False))
        disponibles = df[condicion_libre]
        
        if not disponibles.empty:
            for idx, row in disponibles.iterrows():
                st.success(f"✨ **{row.get('servicio', 'Servicio')}** disponible en cuenta: `{row.get('id_cuenta', 'S/D')}`")
        else:
            st.write("No tienes cupos libres por ahora.")

    # Listas para organizar los siguientes grupos
    clientes_activos = df[~condicion_libre].copy()
    lista_pagos_pendientes = []
    lista_proximos_vencer = []
    lista_activos = []

    for index, row in clientes_activos.iterrows():
        raw_nombre = row.get('nombre', '')
        nombre = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
        
        estatus = str(row.get('estatus', '')).strip().lower()
        vence_dt = row.get('vencimiento', pd.NaT)
        
        if pd.isna(vence_dt): 
            continue
            
        # 3. EXTRAER SOLO EL AÑO-MES-DÍA DEL CLIENTE (Elimina interferencia de horas)
        fecha_vence = datetime(vence_dt.year, vence_dt.month, vence_dt.day)

        # APLICACIÓN DE TUS REGLAS SIN INTERFERENCIAS:
        if estatus == 'pendiente' or fecha_vence < fecha_hoy:
            # Si el estatus manual es 'pendiente' o el día de vencimiento ya pasó (es menor a hoy)
            lista_pagos_pendientes.append(row)
            
        elif fecha_hoy <= fecha_vence <= fecha_limite_cobro:
            # Si vence HOY, MAÑANA o PASADO MAÑANA
            lista_proximos_vencer.append(row)
            
        else:
            # Si vence dentro de 3 días o más
            lista_activos.append(row)

    # =========================================================================
    # 2. 🔍 PAGOS PENDIENTES
    # =========================================================================
    st.divider()
    st.markdown("### 🔍 Pagos pendientes")
    
    if len(lista_pagos_pendientes) > 0:
        for row in lista_pagos_pendientes:
            raw_nombre = row.get('nombre', '')
            nombre = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
            servicio = str(row.get('servicio', 'Servicio')).strip()
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
            
            with st.expander(f"🔴 SERVICIO RENOVADO / DEBE PAGO: {nombre} ({servicio}) - Vence: {fecha_vence_str}"):
                msg_deudor = (
                    f"Hola “{nombre}” 🫂\n"
                    f"Te escribo para recordarte que ya se realizó la renovación de tu suscripción de {servicio}, pero aún tenemos pendiente el pago.\n\n"
                    f"Te dejo por aquí los datos para que puedas ponerte al día.\n"
                    f"Pago móvil 💳\n"
                    f"Banco: Bancamiga\n"
                    f"Documento: 13024234\n"
                    f"Teléfono: 04246379018\n"
                    f"Concepto: *PAGO*\n"
                    f"Monto: *{monto_bs} Bs.*\n\n"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda. ¡Gracias! ✨"
                )
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_deudor)
                link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_cobro}" target="_self" style="text-decoration:none;"><button style="background-color:#FF4B4B; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Recordatorio de Deuda</button></a>', unsafe_allow_html=True)
    else:
        st.write("✅ Todo al día. Ningún deudor ni vencido.")

    # =========================================================================
    # 3. ⏰ PRÓXIMOS A VENCER
    # =========================================================================
    st.divider()
    st.markdown("### ⏰ Próximos a Vencer")
    
    if len(lista_proximos_vencer) > 0:
        for row in lista_proximos_vencer:
            raw_nombre = row.get('nombre', '')
            nombre = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
            servicio = str(row.get('servicio', 'Servicio')).strip()
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
            
            with st.expander(f"🟡 AVISAR RENOVAR: {nombre} ({servicio}) - Vence: {fecha_vence_str}"):
                msg_preventivo = (
                    f"Hola “{nombre}” 🫂\n\n"
                    f"Ya está disponible la renovación de tu suscripción de {servicio}.\n\n"
                    f"Si deseas renovar, te dejo los datos de pago.\n\n"
                    f"Pago móvil 💳\n"
                    f"Banco: Bancamiga\n"
                    f"Documento: 13024234\n"
                    f"Teléfono: 04246379018\n"
                    f"Concepto: *PAGO*\n"
                    f"Monto: *{monto_bs} Bs.*%0A%0A"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda ✨"
                )
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_preventivo)
                link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_cobro}" target="_self" style="text-decoration:none;"><button style="background-color:#FFAA00; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Mensaje de Cobro Standard</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay vencimientos en el rango de aviso (hoy o próximas 48 horas).")

    # =========================================================================
    # 4. 🟢 ACTIVOS
    # =========================================================================
    st.divider()
    st.markdown("### 🟢 Activos")
    
    if len(lista_activos) > 0:
        for row in lista_activos:
            raw_nombre = row.get('nombre', '')
            nombre = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
            servicio = str(row.get('servicio', 'Servicio')).strip()
            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            
            badge_estado = " (Esperando Grupo)" if str(row.get('estatus', '')).lower() == 'pagado' else ""

            with st.expander(f"🟢 ACTIVO{badge_estado}: {nombre} ({servicio}) - Vence: {fecha_vence_str}"):
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
                    msg_entrega += f"🛜Host/URL: http://jumangis.cloud:2082\n"
                
                msg_entrega += f"👤 Usuario: {id_u}\n🔐 Contraseña: {clave}\n"
                
                if "flujotv" in servicio.lower():
                    msg_entrega += f"🚯 PIN contenido adulto: 1234\n"
                
                msg_entrega += f"\n¡Disfruta de tus contenidos favoritos! Si necesitas ayuda, no dudes en contactarme. 📩"
                
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_entrega)
                link_entrega = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_entrega}" target="_self" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Datos de Acceso</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay membresías activas a largo plazo registradas.")

    st.divider()
    st.subheader("👥 Base de Datos General")
    st.dataframe(df)
else:
    st.info("Introduce la contraseña para gestionar el sistema.")
