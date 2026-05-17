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

df = conn.read()
# Limpieza de nombres de columnas
df.columns = [str(c).strip().lower().replace('é', 'e').replace('ó', 'o') for c in df.columns]

password = st.sidebar.text_input("Contraseña", type="password")

if password == CLAVE_MAESTRA:
    tasa_dia = st.sidebar.number_input("Tasa del día (Bs/$)", min_value=1.0, value=660.0, step=1.0)
    
    ahora = datetime.now()
    fecha_hoy = datetime(ahora.year, agora.month, ahora.day, ahora.hour, ahora.minute, ahora.second) if 'ahora' in locals() else ahora
    
    # Preparar el DataFrame convirtiendo fechas con formato mixto (conservando horas)
    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(df['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
        df = df.sort_values(by='vencimiento')

    # =========================================================================
    # 1. 💟 PERFILES DISPONIBLES
    # =========================================================================
    st.markdown("### 💟 Perfiles Disponibles")
    
    # Un perfil está disponible si el estatus dice libre/vacante/disponible O si el nombre está completamente vacío
    condicion_libre = pd.Series(False, index=df.index)
    if 'nombre' in df.columns:
        condicion_libre = (df['nombre'].isna()) | (df['nombre'].str.strip() == "")
    if 'estatus' in df.columns:
        condicion_libre = condicion_libre | (df['estatus'].str.lower().str.contains('libre|vacante|disponible', na=False))
        
    disponibles = df[condicion_libre]
    
    if not disponibles.empty:
        for idx, row in disponibles.iterrows():
            st.success(f"✨ **{row.get('servicio', 'Servicio')}** disponible en cuenta: `{row.get('id_cuenta', 'S/D')}`")
    else:
        st.write("No tienes cupos libres por ahora.")

    # Listas para organizar los siguientes grupos
    clientes_activos = df[~condicion_libre].copy()
    lista_prepagados_standby = []
    lista_pagos_pendientes = []
    lista_proximos_vencer = []
    lista_activos = []

    # Fecha límite para alertas de cobro (48 horas en el futuro)
    fecha_limite_cobro = ahora + timedelta(days=2)

    for index, row in clientes_activos.iterrows():
        # Extracción del nombre completo y del primer nombre
        raw_nombre = row.get('nombre', '')
        nombre_completo = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
        primer_nombre = nombre_completo.split()[0] if nombre_completo != "Cliente" else "Cliente"
        
        estatus = str(row.get('estatus', '')).strip().lower()
        vence_dt = row.get('vencimiento', pd.NaT)
        
        if pd.isna(vence_dt): 
            continue

        # Lectura segura de los Meses Adelantados
        raw_meses = row.get('meses_adelanto', 0)
        try:
            meses_adelanto = 0 if pd.isna(raw_meses) or str(raw_meses).strip() == "" else int(float(raw_meses))
        except:
            meses_adelanto = 0

        # === DISTRIBUCIÓN DE GRUPOS ESTRICTA MODIFICADA ===
        # Si ya pagó (estatus == pagado) o tiene meses a favor, va directo a Standby/Prepagados para no cobrarle de más
        if estatus == 'pagado' or meses_adelanto > 0:
            lista_prepagados_standby.append((row, nombre_completo, primer_nombre))
            
        elif estatus == 'pendiente' or (vence_dt < ahora and estatus != 'pagado'):
            lista_pagos_pendientes.append((row, nombre_completo, primer_nombre))
            
        elif estatus != 'pagado' and (ahora <= vence_dt <= fecha_limite_cobro):
            lista_proximos_vencer.append((row, nombre_completo, primer_nombre))
            
        else:
            lista_activos.append((row, nombre_completo, primer_nombre))

    # =========================================================================
    # 2. ♻️ PREPAGADOS / PENDIENTES POR RENOVAR (STANDBY)
    # =========================================================================
    if len(lista_prepagados_standby) > 0:
        st.divider()
        st.markdown("### ♻️ Prepagados / Pendientes por Renovar")
        st.write("Clientes que ya pagaron (o tienen meses a favor) pero su cuenta está en espera de renovación física o actualización de datos.")
        
        for item in lista_prepagados_standby:
            row, nombre_completo, primer_nombre = item
            servicio = str(row.get('servicio', 'Servicio')).strip()
            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
            vence_dt = row['vencimiento']
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y %H:%M:%S')
            meses_restantes = int(float(row.get('meses_adelanto', 0))) if not pd.isna(row.get('meses_adelanto', 0)) and str(row.get('meses_adelanto', '')).strip() != "" else 0

            etiqueta = f"⏳ EN ESPERA (YA PAGÓ):" if str(row.get('estatus', '')).lower() == 'pagado' else f"♻️ PREPAGADO ({meses_restantes} m a favor):"

            with st.expander(f"{etiqueta} {nombre_completo} ({servicio}) - Fecha actual en tabla: {fecha_vence_str}"):
                conexiones = "1"
                if "flujotv" in servicio.lower():
                    if precio == 6: conexiones = "2"
                    elif precio >= 9: conexiones = "3"
                elif "jumangistv" in servicio.lower():
                    connections = "3"

                msg_prepagado = (
                    f"Hola {primer_nombre} 🫂\n\n"
                    f"Tu recarga ha sido procesada exitosamente. ✨\n"
                    f"Aquí tienes los datos de acceso para que sigas disfrutando de tu servicio.\n\n"
                    f"⚡️Conexiones: {conexiones}\n"
                    f"📆 Próximo corte: {vence_dt.strftime('%d-%m-%Y')}\n\n"
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
                
                st.markdown(f'<a href="{link_prepagado}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#007BFF; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Claves Nuevas</button></a>', unsafe_allow_html=True)

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
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y %H:%M:%S')
            monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
            
            with st.expander(f"🔴 SERVICIO RENOVADO / DEBE PAGO: {nombre_completo} ({servicio}) - Venció: {fecha_vence_str}"):
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
                
                st.markdown(f'<a href="{link_cobro}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FF4B4B; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Recordatorio de Deuda</button></a>', unsafe_allow_html=True)
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
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y %H:%M:%S')
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
                    f"*{monto_bs} Bs.*\n\n"
                    f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                    f"Quedo atenta ante cualquier duda ✨"
                )
                num = str(row.get('telefono', '58')).split('.')[0].strip()
                if not num.startswith("58") and num != "": num = f"58{num}"
                
                texto_url = urllib.parse.quote(msg_preventivo)
                link_cobro = f"https://web.whatsapp.com/send?phone={num}&text={texto_url}"
                
                st.markdown(f'<a href="{link_cobro}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FFAA00; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Mensaje de Cobro Standard</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay vencimientos para las próximas 48 horas.")

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
            fecha_vence_str = vence_dt.strftime('%d-%m-%Y %H:%M:%S')
            
            with st.expander(f"🟢 ACTIVO: {nombre_completo} ({servicio}) - Vence: {fecha_vence_str}"):
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
                    f"📆 Próxima renovación: {vence_dt.strftime('%d-%m-%Y')}\n\n"
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
                
                st.markdown(f'<a href="{link_entrega}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Datos de Acceso</button></a>', unsafe_allow_html=True)
    else:
        st.write("No hay membresías activas registradas.")

    # =========================================================================
    # 6. 📝 BASE DE DATOS EDITABLE (CONFIGURADA PARA PREVENIR BLOQUEOS)
    # =========================================================================
    st.divider()
    st.subheader("📝 Base de Datos Editable")
    st.write("Modifica los datos directamente. Las celdas de claves y teléfonos están optimizadas para que puedas agregar líneas de prueba.")
    
    df_editor = df.copy()
    if 'vencimiento' in df_editor.columns:
        df_editor['vencimiento'] = df_editor['vencimiento'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')
    
    # Forzamos que las columnas clave y telefono se configuren estrictamente como Texto (Evita que Streamlit las bloquee)
    df_editado = st.data_editor(
        df_editor, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "clave": st.column_config.TextColumn("clave"),
            "telefono": st.column_config.TextColumn("telefono"),
            "id_cuenta": st.column_config.TextColumn("id_cuenta"),
            "nombre": st.column_config.TextColumn("nombre"),
            "estatus": st.column_config.TextColumn("estatus")
        }
    )
    
    if st.button("💾 Guardar Cambios en Google Sheets"):
        try:
            if 'vencimiento' in df_editado.columns:
                fechas_convertidas = pd.to_datetime(df_editado['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
                df_editado['vencimiento'] = [x.strftime('%d/%m/%Y %H:%M:%S') if pd.notna(x) else '' for x in fechas_convertidas]
            
            conn.update(data=df_editado)
            st.success("¡Datos guardados con éxito! 🚀 El sistema se actualizará automáticamente...")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Hubo un error al guardar: {e}")

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
