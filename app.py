import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# Configuración del nombre en la pestaña del navegador
st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🎬 Control Streaming")

# --- CONTRASEÑA ---
CLAVE_MAESTRA = "Z2599393F" 

# Conexión a la base de datos
conn = st.connection("gsheets", type=GSheetsConnection)

# ttl="1m" mantiene la conexión estable y evita bloqueos de Google
df = conn.read(ttl="1m")

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

    # CREACIÓN DE PESTAÑAS
    tab1, tab2 = st.tabs(["🗃️ Panel de Gestión", "📊 Reporte Financiero"])

    with tab1:
        # =========================================================================
        # 1. 🚦 PERFILES DISPONIBLES
        # =========================================================================
        st.markdown("### 🚦 Perfiles Disponibles")
        condicion_libre = pd.Series(False, index=df.index)
        if 'estatus' in df.columns:
            condicion_libre = (df['estatus'].str.lower().str.contains('libre|vacante|disponible', na=False)) | \
                              (df['nombre'].str.lower().str.contains('disponible|libre|vacante', na=False)) | \
                              (df['nombre'].isna()) | (df['nombre'].str.strip() == "")
            disponibles = df[condicion_libre]
            
            if not disponibles.empty:
                for idx, row in disponibles.iterrows():
                    st.success(f"✨ **{row.get('servicio', 'Servicio')}** disponible en cuenta: `{row.get('id_cuenta', 'S/D')}`")
            else:
                st.write("No tienes cupos libres por ahora.")

        # Listas para organizar los siguientes grupos
        clientes_activos = df[~condicion_libre].copy()
        lista_prepagados = []
        lista_pendiente_renovar_pagados = []
        lista_pagos_pendientes = []
        lista_proximos_vencer = []
        lista_activos = []
        lista_inactivos = [] 

        for index, row in clientes_activos.iterrows():
            raw_nombre = row.get('nombre', '')
            nombre_completo = "Cliente" if pd.isna(raw_nombre) or str(raw_nombre).strip() == "" else str(raw_nombre).strip()
            primer_nombre = nombre_completo.split()[0] if nombre_completo != "Cliente" else "Cliente"
            estatus = str(row.get('estatus', '')).strip().lower()
            
            if 'inactivo' in estatus or 'cancelado' in estatus:
                lista_inactivos.append((row, nombre_completo, primer_nombre))
                continue
                
            vence_dt = row.get('vencimiento', pd.NaT)
            if pd.isna(vence_dt): continue
            fecha_vence = datetime(vence_dt.year, vence_dt.month, vence_dt.day)
            
            raw_meses = row.get('meses_adelanto', 0)
            try:
                meses_adelanto = 0 if pd.isna(raw_meses) or str(raw_meses).strip() == "" else int(float(raw_meses))
            except:
                meses_adelanto = 0

            # Distribución de grupos
            if meses_adelanto > 0:
                lista_prepagados.append((row, nombre_completo, primer_nombre))
            elif estatus == 'pagado':
                lista_pendiente_renovar_pagados.append((row, nombre_completo, primer_nombre))
            elif estatus == 'pendiente' or (fecha_vence < fecha_hoy and estatus != 'pagado'):
                lista_pagos_pendientes.append((row, nombre_completo, primer_nombre))
            elif estatus != 'pagado' and (fecha_hoy <= fecha_vence <= fecha_limite_cobro):
                lista_proximos_vencer.append((row, nombre_completo, primer_nombre))
            else:
                lista_activos.append((row, nombre_completo, primer_nombre, fecha_vence))

        # =========================================================================
        # 2. ✅ PREPAGADOS POR ACTUALIZAR
        # =========================================================================
        if len(lista_prepagados) > 0:
            st.divider()
            st.markdown("### ✅ Prepagado")
            
            for item in lista_prepagados:
                row, nombre_completo, primer_nombre = item
                servicio = str(row.get('servicio', 'Servicio')).strip()
                id_u = row.get('id_cuenta', 'S/D')
                clave = row.get('clave', 'S/D')
                precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
                vence_dt = row['vencimiento']
                fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
                meses_restantes = int(float(row.get('meses_adelanto', 0)))

                with st.expander(f"✅ PREPAGADO ({meses_restantes} meses a favor): {nombre_completo} - Cuenta: {id_u} - Vence: {fecha_vence_str}"):
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
                        msg_prepagado += f"🛜Host/URL: http://jumangis.cloud:2082n"
                    
                    msg_prepagado += f"👤 Usuario: {id_u}\n🔐 Contraseña: {clave}\n"
                    
                    if "flujotv" in servicio.lower():
                        msg_prepagado += f"🚯 PIN contenido adulto: 1234\n"
                    
                    msg_prepagado += f"\n¡Disfruta de tus contenidos favoritos! 📩"
                    
                    # AJUSTE WHATSAPP
                    num = str(row.get('telefono', '')).split('.')[0].strip()
                    num = ''.join(filter(str.isdigit, num)) 
                    if num != "":
                        if num.startswith("0"): num = num[1:] 
                        if len(num) == 10: num = f"58{num}"   
                    
                    texto_url = urllib.parse.quote(msg_prepagado)
                    link_prepagado = f"https://api.whatsapp.com/send?phone={num}&text={texto_url}"
                    
                    st.markdown(f'<a href="{link_prepagado}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#007BFF; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Claves (Sin Cobrar)</button></a>', unsafe_allow_html=True)

        # =========================================================================
        # 3. ⏳ PENDIENTES POR RENOVAR
        # =========================================================================
        if len(lista_pendiente_renovar_pagados) > 0:
            st.divider()
            st.markdown("### ⏳ Renovar")
            for item in lista_pendiente_renovar_pagados:
                row, nombre_completo, primer_nombre = item
                servicio = str(row.get('servicio', 'Servicio')).strip()
                id_u = row.get('id_cuenta', 'S/D')
                clave = row.get('clave', 'S/D')
                precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
                vence_dt = row['vencimiento']
                fecha_vence_str = vence_dt.strftime('%d-%m-%Y %H:%M:%S')

                with st.expander(f"⏳ RENOVAR: {nombre_completo} - Cuenta: {id_u}"):
                    conexiones = "1"
                    if "flujotv" in servicio.lower():
                        if precio == 6: conexiones = "2"
                        elif precio >= 9: conexiones = "3"
                    elif "jumangistv" in servicio.lower():
                        conexiones = "3"

                    msg_entrega_pendiente = (
                        f"Hola {primer_nombre} 🫂\n\n"
                        f"¡Gracias por tu pago! Tu servicio ha sido renovado. ✨\n"
                        f"Aquí tienes los datos correspondientes para tu ingreso:\n\n"
                        f"⚡️Conexiones: {conexiones}\n"
                        f"👤 Usuario: {id_u}\n🔐 Contraseña: {clave}\n"
                    )
                    
                    if "jumangistv" in servicio.lower():
                        msg_entrega_pendiente += f"🛜Host/URL: http://jumangis.cloud:2082n"
                    if "flujotv" in servicio.lower():
                        msg_entrega_pendiente += f"🚯 PIN contenido adulto: 1234\n"
                        
                    msg_entrega_pendiente += f"\n¡Gracias por tu fidelidad! Quedo a la orden. 📩"
                    
                    # AJUSTE WHATSAPP
                    num = str(row.get('telefono', '')).split('.')[0].strip()
                    num = ''.join(filter(str.isdigit, num))
                    if num != "":
                        if num.startswith("0"): num = num[1:]
                        if len(num) == 10: num = f"58{num}"
                    
                    texto_url = urllib.parse.quote(msg_entrega_pendiente)
                    link_entrega = f"https://api.whatsapp.com/send?phone={num}&text={texto_url}"
                    
                    st.markdown(f'<a href="{link_entrega}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Nuevos Datos</button></a>', unsafe_allow_html=True)

        # =========================================================================
        # 4. ⚠️ PRÓXIMOS A VENCER (HOY + 2 DÍAS)
        # =========================================================================
        if len(lista_proximos_vencer) > 0:
            st.divider()
            st.markdown("### ⚠️ Próximos a Vencer")
            for item in lista_proximos_vencer:
                row, nombre_completo, primer_nombre = item
                servicio = str(row.get('servicio', 'Servicio')).strip()
                id_u = row.get('id_cuenta', 'S/D')
                precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
                vence_dt = row['vencimiento']
                fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
                monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
                
                with st.expander(f"⚠️ PRÓXIMO A VENCER: {nombre_completo} - Cuenta: {id_u} - Vence: {fecha_vence_str}"):
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
                    
                    # AJUSTE WHATSAPP
                    num = str(row.get('telefono', '')).split('.')[0].strip()
                    num = ''.join(filter(str.isdigit, num))
                    if num != "":
                        if num.startswith("0"): num = num[1:]
                        if len(num) == 10: num = f"58{num}"
                    
                    texto_url = urllib.parse.quote(msg_preventivo)
                    link_cobro = f"https://api.whatsapp.com/send?phone={num}&text={texto_url}"
                    
                    st.markdown(f'<a href="{link_cobro}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FFC107; color:black; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Recordatorio Standard</button></a>', unsafe_allow_html=True)

        # =========================================================================
        # 5. 🚨 PAGOS PENDIENTES
        # =========================================================================
        if len(lista_pagos_pendientes) > 0:
            st.divider()
            st.markdown("### 🚨 Pagos Pendientes")
            for item in lista_pagos_pendientes:
                row, nombre_completo, primer_nombre = item
                servicio = str(row.get('servicio', 'Servicio')).strip()
                id_u = row.get('id_cuenta', 'S/D')
                precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
                vence_dt = row['vencimiento']
                fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
                monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
                
                with st.expander(f"🚨 PENDIENTE: {nombre_completo} - Cuenta: {id_u} - Venció: {fecha_vence_str}"):
                    msg_deudor = (
                        f"Hola {primer_nombre} 🚨\n"
                        f"Te escribo para recordarte que tenemos pendiente el pago de la renovación de tu servicio vencido el {fecha_vence_str}.\n\n"
                        f"Te dejo por aquí los datos para que puedas ponerte al día.\n"
                        f"Banco: Bancamiga\n"
                        f"13024234\n"
                        f"04246379018\n"
                        f"*{monto_bs} Bs.*\n\n"
                        f"Concepto en *BLANCO* o *PAGO*\n"
                        f"Solicita el correo si deseas pagar por Binance o Zelle 💵\n\n"
                        f"Quedo atenta ante cualquier duda. ¡Gracias! ✨"
                    )
                    
                    # AJUSTE WHATSAPP
                    num = str(row.get('telefono', '')).split('.')[0].strip()
                    num = ''.join(filter(str.isdigit, num))
                    if num != "":
                        if num.startswith("0"): num = num[1:]
                        if len(num) == 10: num = f"58{num}"
                    
                    texto_url = urllib.parse.quote(msg_deudor)
                    link_cobro = f"https://api.whatsapp.com/send?phone={num}&text={texto_url}"
                    
                    st.markdown(f'<a href="{link_cobro}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#DC3545; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🛑 Enviar Aviso de Deuda/Corte</button></a>', unsafe_allow_html=True)
        
        # =========================================================================
        # 6. 🟢 ACTIVOS
        # =========================================================================
        if len(lista_activos) > 0:
            st.divider()
            st.markdown("### 🟢 Activos")
            lista_activos.sort(key=lambda x: x[3])
            for item in lista_activos:
                row, nombre_completo, primer_nombre, _ = item
                servicio = str(row.get('servicio', 'Servicio')).strip()
                id_u = row.get('id_cuenta', 'S/D')
                clave = row.get('clave', 'S/D')
                precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
                vence_dt = row['vencimiento']
                fecha_vence_str = vence_dt.strftime('%d-%m-%Y')
                
                with st.expander(f"🟢 ACTIVO: {nombre_completo} ({id_u}) - Vence: {fecha_vence_str}"):
                    st.write("Cliente al día.")
                    
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
                        msg_entrega += f"🛜Host/URL: http://jumangis.cloud:2082n"
                    
                    msg_entrega += f"👤 Usuario: {id_u}\n🔐 Contraseña: {clave}\n"
                    
                    if "flujotv" in servicio.lower():
                        msg_entrega += f"🚯 PIN contenido adulto: 1234\n"
                    
                    msg_entrega += f"\n¡Disfruta de tus contenidos favoritos! Si necesitas ayuda, no dudes en contactarme. 📩"
                    
                    # AJUSTE WHATSAPP
                    num = str(row.get('telefono', '')).split('.')[0].strip()
                    num = ''.join(filter(str.isdigit, num))
                    if num != "":
                        if num.startswith("0"): num = num[1:]
                        if len(num) == 10: num = f"58{num}"
                    
                    texto_url = urllib.parse.quote(msg_entrega)
                    link_entrega = f"https://api.whatsapp.com/send?phone={num}&text={texto_url}"
                    
                    st.markdown(f'<a href="{link_entrega}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Re-Enviar Datos de Acceso</button></a>', unsafe_allow_html=True)

        # =========================================================================
        # 7. 📝 BASE DE DATOS
        # =========================================================================
        st.divider()
        st.subheader("📝 Base de Datos")
        df_editor = df.copy()
        if 'estatus' in df_editor.columns:
            df_editor['es_inactivo'] = df_editor['estatus'].str.lower().str.contains('inactivo|cancelado', na=False)
            df_editor = df_editor.sort_values(by=['es_inactivo', 'vencimiento'], ascending=[True, True]).reset_index(drop=True).drop(columns=['es_inactivo'])
        
        columnas_texto = ["clave", "telefono", "nombre", "id_cuenta", "estatus", "servicio"]
        for col in columnas_texto: 
            if col in df_editor.columns: df_editor[col] = df_editor[col].fillna('').astype(str).replace('nan', '')
        if 'vencimiento' in df_editor.columns: df_editor['vencimiento'] = df_editor['vencimiento'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')
        
        df_editado = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar Cambios en Google Sheets"):
            try:
                if 'vencimiento' in df_editado.columns:
                    fechas_c = pd.to_datetime(df_editado['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
                    df_editado['vencimiento'] = [x.strftime('%d/%m/%Y %H:%M:%S') if pd.notna(x) else '' for x in fechas_c]
                st.cache_data.clear()
                conn.update(data=df_editado)
                st.success("¡Datos guardados!")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

        # =========================================================================
        # 8. ❌ CLIENTES INACTIVOS
        # =========================================================================
        if len(lista_inactivos) > 0:
            st.divider()
            st.markdown("### ❌ Clientes Inactivos")
            for item in lista_inactivos:
                row, nombre_completo, _ = item
                with st.expander(f"❌ INACTIVO: {nombre_completo}"):
                    st.write(f"Usuario: {row.get('id_cuenta', 'S/D')}")

    # =========================================================================
    # 📊 PESTAÑA 2: REPORTE FINANCIERO (CON GRÁFICO VISUAL)
    # =========================================================================
    with tab2:
        st.subheader("📊 Reportes")
        
        flujo_cuentas_dict = {}
        juman_cuentas_dict = {}

        # Solo tomamos dinero de los que ya pagaron (Prepagados, Pendientes renovar y Activos)
        # Excluimos pagos pendientes (morosos) por instrucción contable
        clientes_reporte = lista_prepagados + lista_pendiente_renovar_pagados + lista_proximos_vencer + lista_activos

        for item in clientes_reporte:
            row = item[0]
            servicio = str(row.get('servicio', '')).strip().lower()
            id_u = str(row.get('id_cuenta', '')).strip().lower()
            precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0

            if id_u == "" or id_u == "s/d" or id_u == "nan": id_u = f"sin_id_{row.name}"

            if "flujo" in servicio:
                if id_u not in flujo_cuentas_dict: flujo_cuentas_dict[id_u] = {'tipo': 'pantalla', 'ingreso': 0.0}
                flujo_cuentas_dict[id_u]['ingreso'] += precio
                if precio >= 9: flujo_cuentas_dict[id_u]['tipo'] = 'completa'
            elif "jumangis" in servicio:
                if id_u not in juman_cuentas_dict: juman_cuentas_dict[id_u] = {'ingreso': 0.0}
                juman_cuentas_dict[id_u]['ingreso'] += precio

        # Totales Flujo
        flujo_completas = sum(1 for d in flujo_cuentas_dict.values() if d['tipo'] == 'completa')
        flujo_pantallas_acc = sum(1 for d in flujo_cuentas_dict.values() if d['tipo'] == 'pantalla')
        flujo_ingreso = sum(d['ingreso'] for d in flujo_cuentas_dict.values())
        flujo_costo = (flujo_completas + flujo_pantallas_acc) * 3.0

        # Totales Jumangis
        juman_cuentas = len(juman_cuentas_dict)
        juman_ingreso = sum(d['ingreso'] for d in juman_cuentas_dict.values())
        juman_costo = juman_cuentas * 1.5

        ingreso_total = flujo_ingreso + juman_ingreso
        costo_total = flujo_costo + juman_costo
        ganancia_total = ingreso_total - costo_total

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Ingreso Pagado", f"${ingreso_total:,.2f} USD")
        m2.metric("📉 Costos Proveedores", f"${costo_total:,.2f} USD")
        m3.metric("✨ Ganancia Neta", f"${ganancia_total:,.2f} USD")

        st.divider()

        # --- SECCIÓN VISUAL (NUEVA) ---
        st.markdown("### 📈 Comparativa de Rentabilidad")
        
        # Preparamos los datos para el gráfico
        data_grafico = pd.DataFrame({
            "Monto ($)": [flujo_ingreso, flujo_costo, juman_ingreso, juman_costo],
            "Categoría": ["Ingreso", "Costo", "Ingreso", "Costo"],
            "Servicio": ["FlujoTV", "FlujoTV", "JumangisTV", "JumangisTV"]
        })
        
        # Mostramos el gráfico de barras comparativo
        st.bar_chart(data=data_grafico, x="Servicio", y="Monto ($)", color="Categoría", stack=False)

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**🎬 FlujoTV**\n\n* Cuentas: {flujo_completas + flujo_pantallas_acc}\n* Ingreso: ${flujo_ingreso:.2f}\n* Ganancia: ${flujo_ingreso - flujo_costo:.2f}")
        with col_b:
            st.markdown(f"**🎥 JumangisTV**\n\n* Cuentas: {juman_cuentas}\n* Ingreso: ${juman_ingreso:.2f}\n* Ganancia: ${juman_ingreso - juman_costo:.2f}")

        st.divider()
        st.info(f"**Flujo Bruto en Bolívares:** {ingreso_total * tasa_dia:,.2f} Bs.")
        st.success(f"**Utilidad Real en Bolívares:** {ganancia_total * tasa_dia:,.2f} Bs.")

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
