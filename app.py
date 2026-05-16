import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# Configuración del nombre en la pestaña del navegador
st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🎬 Sistema Control Streaming")

# --- CONTRASEÑA ---
CLAVE_MAESTRA = "Prueba123" 

# Conexión a la base de datos
conn = st.connection("gsheets", type=GSheetsConnection)

# --- BOTÓN DE ACTUALIZACIÓN MANUAL ---
if st.sidebar.button("🔄 Actualizar"):
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
    # 1. 💟 PERFILES DISPONIBLES
    # =========================================================================
    st.markdown("### 💟 Perfiles Disponibles")
    condicion_libre = pd.Series(False, index=df.index)
    if 'estatus' in df.columns:
        condicion_libre = (df['estatus'].str.lower().str.contains('libre|vacante', na=False)) | \
                          (df['nombre'].str.lower().str.contains('disponible|libre|vacante', na=False))
        disponibles = df[condicion_libre]
        
        if not disponibles.empty:
            for idx, row in disponibles.iterrows():
                st.success(f"🟣 **{row.get('servicio', 'Servicio')}** disponible en cuenta: `{row.get('id_cuenta', 'S/D')}`")
        else:
            st.write("No tienes cupos libres por ahora.")

    # Listas para organizar los siguientes grupos
    clientes_activos = df[~condicion_libre].copy()
    lista_prepagados = []
    lista_pagos_pendientes = []
    lista_proximos_vencer = []
    lista_activos = []

    for index, row in clientes_activos.iterrows():
        # Extracción del nombre completo y del primer nombre
        raw_nombre = row.get('nombre', '')
        nombre_completo = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
        primer_nombre = nombre_completo.split()[0] if nombre_completo != "Cliente" else "Cliente"
        
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
        if meses_adelanto > 0:
            lista_prepagados.append((row, nombre_completo, primer_nombre))
            
        elif estatus == 'pendiente' or (fecha_vence < fecha_hoy and estatus != 'pagado'):
            lista_pagos_pendientes.append((row, nombre_completo, primer_nombre))
            
        elif estatus != 'pagado' and (fecha_hoy <= fecha_vence <= fecha_limite_cobro):
            lista_proximos_vencer.append((row, nombre_completo, primer_nombre))
            
        else:
            lista_activos.append((row, nombre_completo, primer_nombre))

    # =========================================================================
    # 2. ♻️ PREPAGADOS POR ACTUALIZAR
    # =========================================================================
    if len(lista_prepagados) > 0:
        st.divider()
        st.markdown("### ♻️ Prepagados por Actualizar")
        st.write("Clientes que pagaron por adelantado. Pásales sus claves nuevas, cambia su fecha y bájales 1 mes de adelanto en la tabla cuando corresponda.")
        
        for item in lista_prepagados:
            row, nombre_completo, primer_nombre = item
            servicio = str(row.get('servicio', 'Servicio')).strip()
            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            meses_restantes = int(float(row.get('meses_adelanto', 0)))

            # USO DE EXPANDER PARA MANTENER EL BOTÓN OCULTO
            with st.expander(f"♻️ PREPAGADO ({meses_restantes} meses a favor): {nombre_completo} ({servicio}) - Vence: {fecha_vence_str}"):
                conexiones = "1"
                if "flujotv" in servicio.lower():
                    if precio == 6: conexiones = "2"
                    elif precio >= 9: conexiones = "3"
                elif "jumangistv" in servicio.lower():
                    conexiones = "3"

                msg_prepagado = (
                    f"Hola {primer_nombre} 🫂\n\n"
                    f"Tu recarga ha sido procesada exitosamente. ✨\n"
                    f"Aquí tienes los datos de acceso para que sigas disfrutando de tu servicio.\n\n"
                    f"⚡️Conexiones: {conexiones}\n"
                    f"📆 Próximo corte: {fecha_vence_str}\n\n"
                )
                
                if "jumangistv" in servicio.lower():
                    msg_prepagado += f"🛜Host/URL: http://jumangis.cloud:2082\n"
                
                msg_prepagado += f"👤 Usuario: {id_u}\n🔐 Contraseña: {clave}\n"
                
                if "flujotv" in servicio.lower():
                    msg_prepagado += f"🚯 PIN contenido adulto: 1234\n"
                
                msg_prepagado += f"\n¡Disfruta de tus contenidos favoritos! 📩"
                
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_prepagado)
                link_prepagado = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_prepagado}" target="ventana_wa" style="text-decoration:none;"><button style="background-color:#007BFF; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Claves (Sin Cobrar)</button></a>', unsafe_allow_html=True)

    # =========================================================================
    # 3. 🚩 PAGOS PENDIENTES
    # =========================================================================
    st.divider()
    st.markdown("### 🚩 Pagos pendientes")
    
    if len(lista_pagos_pendientes) > 0:
        for item in lista_pagos_pendientes:
            row, nombre_completo, primer_nombre = item
            servicio = str(row.get('servicio', 'Servicio')).strip()
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
            
            # USO DE EXPANDER PARA MANTENER EL BOTÓN OCULTO
            with st.expander(f"🔴 SERVICIO RENOVADO / DEBE PAGO: {nombre_completo} ({servicio}) - Vence: {fecha_vence_str}"):
                msg_deudor = (
                    f"Hola {primer_nombre} 🫂\n"
                    f"Te escribo para recordarte que tenemos pendiente el pago de la renovación.\n\n"
                    f"Te dejo por aquí los datos para que puedas ponerte al día.\n"
                    f"Banco: Bancamiga\n"
                    f"13024234\n"
                    f"04246379018\n"
                    f"*{monto_bs} Bs.*\n\n"
                    f"Concepto en *BLANCO* o *PAGO*\n"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda. ¡Gracias! ✨"
                )
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_deudor)
                link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_cobro}" target="ventana_wa" style="text-decoration:none;"><button style="background-color:#FF4B4B; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Recordatorio de Deuda</button></a>', unsafe_allow_html=True)
    else:
        st.write("✅ Todo al día. Ningún cliente moroso.")

    # =========================================================================
    # 4. ⏰ PRÓXIMOS A VENCER
    # =========================================================================
    st.divider()
    st.markdown("### ⏰ Próximos a Vencer")
    
    if len(lista_proximos_vencer) > 0:
        for item in lista_proximos_vencer:
            row, nombre_completo, primer_nombre = item
            servicio = str(row.get('servicio', 'Servicio')).strip()
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
            
            with st.expander(f"🟡 AVISAR RENOVAR: {nombre_completo} ({servicio}) - Vence: {fecha_vence_str}"):
                msg_preventivo = (
                    f"Hola {primer_nombre} 🫂\n\n"
                    f"Ya está disponible la renovación de tu suscripción.\n\n"
                    f"Si deseas renovar, te dejo los datos de pago.\n\n"
                    f"Bancamiga\n"
                    f"13024234\n"
                    f"04246379018\n"
                    f"Concepto en *BLANCO* o *PAGO*\n"
                    f"{monto_bs} Bs.\n\n"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda ✨"
                )
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_preventivo)
                link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_cobro}" target="ventana_wa" style="text-decoration:none;"><button style="background-color:#FFAA00; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Mensaje de Cobro Standard</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay vencimientos para hoy o las próximas 48 horas.")

    # =========================================================================
    # 5. ✅ ACTIVOS
    # =========================================================================
    st.divider()
    st.markdown("### ✅ Activos")
    
    if len(lista_activos) > 0:
        for item in lista_activos:
            row, nombre_completo, primer_nombre = item
            servicio = str(row.get('servicio', 'Servicio')).strip()
            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
            
            badge_estado = " (Esperando Grupo)" if str(row.get('estatus', '')).lower() == 'pagado' else ""

            with st.expander(f"🟢 ACTIVO{badge_estado}: {nombre_completo} ({servicio}) - Vence: {fecha_vence_str}"):
                conexiones = "1"
                if "flujotv" in servicio.lower():
                    if precio == 6: conexiones = "2"
                    elif precio >= 9: conexiones = "3"
                elif "jumangistv" in servicio.lower():
                    conexiones = "3"

                msg_entrega = (
                    f"✨ Aquí están tus datos de acceso. No los compartas con nadie. "
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
                
                st.markdown(f'<a href="{link_entrega}" target="ventana_wa" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Datos de Acceso</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay membresías activas a largo plazo registradas.")

    # =========================================================================
    # 6. 📝 BASE DE DATOS EDITABLE (MODIFICADO PARA PERMITIR ESCRITURA LIBRE)
    # =========================================================================
    st.divider()
    st.subheader("📝 Base de Datos Editable")
    st.write("Modifica el estatus, actualiza fechas o administra adelantos directamente.")
    
    # Truco de estabilidad: Pasamos la columna de fecha a texto limpio en el editor 
    # para que Streamlit te permita escribir libremente y pulsar Enter sin borrar nada.
    df_editor = df.copy()
    if 'vencimiento' in df_editor.columns:
        df_editor['vencimiento'] = df_editor['vencimiento'].dt.strftime('%d/%m/%Y').fillna('')
    
    df_editado = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Guardar Cambios en Google Sheets"):
        try:
            if 'vencimiento' in df_editado.columns:
                # Convertimos de forma segura a objetos temporales lo que sea que hayas escrito
                fechas_convertidas = pd.to_datetime(df_editado['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
                # Formateamos fila por fila a texto para que Google Sheets lo procese sin error.
                df_editado['vencimiento'] = [x.strftime('%d/%m/%Y') if pd.notna(x) else '' for x in fechas_convertidas]
            
            conn.update(data=df_editado)
            st.success("¡Datos guardados con éxito! 🚀 La pantalla se actualizará en breve...")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hubo un error al guardar: {e}")

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
