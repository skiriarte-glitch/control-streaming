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
    
    ahora = datetime.now()
    fecha_hoy = datetime(ahora.year, ahora.month, ahora.day)
    fecha_limite_cobro = fecha_hoy + timedelta(days=2)

    # Preparar el DataFrame convirtiendo fechas con formato mixto
    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(df['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
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
    lista_prepagados = []
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
            
        fecha_vence = datetime(vence_dt.year, vence_dt.month, vence_dt.day)
        
        # Lectura segura de los Meses Adelantados
        raw_meses = row.get('meses_adelanto', 0)
        try:
            meses_adelanto = 0 if pd.isna(raw_meses) or str(raw_meses).strip() == "" else int(float(raw_meses))
        except:
            meses_adelanto = 0

        # === DISTRIBUCIÓN DE GRUPOS ESTRICTA ===
        # 1. Si tiene meses adelantados, SIEMPRE va a prepagados (sin importar la fecha)
        if meses_adelanto > 0:
            lista_prepagados.append(row)
            
        # 2. Si es deudor manual o si su fecha ya pasó y NO está pagado
        elif estatus == 'pendiente' or (fecha_vence < fecha_hoy and estatus != 'pagado'):
            lista_pagos_pendientes.append(row)
            
        # 3. Si vence en los próximos 2 días (y no está pagado)
        elif estatus != 'pagado' and (fecha_hoy <= fecha_vence <= fecha_limite_cobro):
            lista_proximos_vencer.append(row)
            
        # 4. Activos normales o Pagados esperando grupo
        else:
            lista_activos.append(row)

    # =========================================================================
    # 2. 🔵 PREPAGADOS POR ACTUALIZAR (DISEÑO SOMBREADO)
    # =========================================================================
    if len(lista_prepagados) > 0:
        st.divider()
        st.markdown("### 🔵 Prepagados por Actualizar")
        st.write("Clientes que pagaron por adelantado. Pásales sus claves nuevas, cambia su fecha y bájales 1 mes de adelanto en la tabla cuando corresponda.")
        
        for row in lista_prepagados:
            raw_nombre = row.get('nombre', '')
            nombre = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
            servicio = str(row.get('servicio', 'Servicio')).strip()
            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            meses_restantes = int(float(row.get('meses_adelanto', 0)))

            conexiones = "1"
            if "flujotv" in servicio.lower():
                if precio == 6: conexiones = "2"
                elif precio >= 9: conexiones = "3"
            elif "jumangistv" in servicio.lower():
                conexiones = "3"

            msg_prepagado = (
                f"Hola “{nombre}” 🫂%0A%0A"
                f"Tu mes ha sido renovado exitosamente como parte de tu pago adelantado. ✨%0A"
                f"Aquí tienes tus datos de acceso para que sigas disfrutando de {servicio}.%0A%0A"
                f"⚡️Conexiones: {conexiones}%0A"
                f"📆 Próximo corte: {fecha_vence_str}%0A%0A"
            )
            
            if "jumangistv" in servicio.lower():
                msg_prepagado += f"🛜Host/URL: http://jumangis.cloud:2082%0A"
            
            msg_prepagado += f"👤 Usuario: {id_u}%0A🔐 Contraseña: {clave}%0A"
            
            if "flujotv" in servicio.lower():
                msg_prepagado += f"🚯 PIN contenido adulto: 1234%0A"
            
            msg_prepagado += f"%0A¡Disfruta de tus contenidos favoritos! 📩"
            
            num = str(row.get('telefono', '58')).split('.')[0].strip()
            if not num.startswith("58") and num != "": num = f"58{num}"
            
            texto_url = urllib.parse.quote(msg_prepagado)
            link_prepagado = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
            
            # Bloque visual sombreado azul
            st.info(f"🔵 **PREPAGADO ({meses_restantes} meses a favor):** {nombre} ({servicio}) - Vence: {fecha_vence_str}")
            # CORREGIDO: cambiado target a "whatsapp" para reutilizar pestaña activa
            st.markdown(f'<div style="margin-top: -10px; margin-bottom: 20px;"><a href="{link_prepagado}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#007BFF; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Claves (Sin Cobrar)</button></a></div>', unsafe_allow_html=True)

    # =========================================================================
    # 3. 🔍 PAGOS PENDIENTES (DISEÑO SOMBREADO)
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
            
            msg_deudor = (
                f"Hola “{nombre}” 🫂%0A"
                f"Te escribo para recordarte que ya se realizó la renovación de tu suscripción de {servicio}, pero aún tenemos pendiente el pago.%0A%0A"
                f"Te dejo por aquí los datos para que puedas ponerte al día.%0A"
                f"Pago móvil 💳%0A"
                f"Banco: Bancamiga%0A"
                f"Documento: 13024234%0A"
                f"Teléfono: 04246379018%0A"
                f"Concepto: *PAGO*%0A"
                f"Monto: *{monto_bs} Bs.*%0A%0A"
                f"Solicita el correo si deseas pagar por Binance o Zelle 💵%0A%0A"
                f"Quedo atenta ante cualquier duda. ¡Gracias! ✨"
            )
            num = str(row.get('telefono', '58')).split('.')[0].strip()
            if not num.startswith("58") and num != "": num = f"58{num}"
            
            texto_url = urllib.parse.quote(msg_deudor)
            link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
            
            # Bloque visual sombreado rojo
            st.error(f"🔴 **SERVICIO RENOVADO / DEBE PAGO:** {nombre} ({servicio}) - Vence: {fecha_vence_str}")
            # CORREGIDO: cambiado target a "whatsapp"
            st.markdown(f'<div style="margin-top: -10px; margin-bottom: 20px;"><a href="{link_cobro}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FF4B4B; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Recordatorio de Deuda</button></a></div>', unsafe_allow_html=True)
    else:
        st.write("✅ Todo al día. Ningún cliente moroso.")

    # =========================================================================
    # 4. ⏰ PRÓXIMOS A VENCER
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
                    f"Monto: *{monto_bs} Bs.*\n\n"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda ✨"
                )
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_preventivo)
                link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                # CORREGIDO: cambiado target a "whatsapp"
                st.markdown(f'<a href="{link_cobro}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FFAA00; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Mensaje de Cobro Standard</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay vencimientos para hoy o las próximas 48 horas.")

    # =========================================================================
    # 5. 🟢 ACTIVOS
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
                
                # CORREGIDO: cambiado target a "whatsapp"
                st.markdown(f'<a href="{link_entrega}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Datos de Acceso</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay membresías activas registradas.")

    # =========================================================================
    # 6. 📝 BASE DE DATOS EDITABLE
    # =========================================================================
    st.divider()
    st.subheader("📝 Base de Datos Editable")
    st.write("Modifica el estatus, actualiza fechas o administra adelantos directamente.")
    
    df_editado = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Guardar Cambios en Google Sheets"):
        try:
            if 'vencimiento' in df_editado.columns:
                df_editado['vencimiento'] = df_editado['vencimiento'].dt.strftime('%d/%m/%Y')
            
            conn.update(data=df_editado)
            st.success("¡Datos guardados con éxito! 🚀 La pantalla se actualizará en breve...")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hubo un error al guardar: {e}")

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
