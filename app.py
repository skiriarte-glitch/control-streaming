import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

st.set_page_config(page_title="Control Streaming", layout="wide")
st.title("🎬 Control Streaming")

CLAVE_MAESTRA = "Z2599393F" 
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONEXIÓN A LAS 3 HOJAS ---
try:
    df = conn.read(worksheet="Clientes", ttl="1m")
    df.columns = [str(c).strip().lower().replace('é', 'e').replace('ó', 'o') for c in df.columns]
    
    df_compras = conn.read(worksheet="Compras_Proveedor", ttl="1m")
    df_compras.columns = [str(c).strip().lower() for c in df_compras.columns]
    
    df_historial = conn.read(worksheet="Historial_Mensual", ttl="1m")
    df_historial.columns = [str(c).strip().lower() for c in df_historial.columns]
except Exception as e:
    st.error("⚠️ Error leyendo Google Sheets. Verifica que las pestañas se llamen: Clientes, Compras_Proveedor y Historial_Mensual.")
    st.stop()

password = st.sidebar.text_input("Contraseña", type="password")

if password == CLAVE_MAESTRA:
    tasa_dia = st.sidebar.number_input("Tasa del día (Bs/$)", min_value=1.0, value=660.0, step=1.0)
    
    ahora = datetime.now()
    fecha_hoy = datetime(ahora.year, ahora.month, ahora.day)
    fecha_limite_cobro = fecha_hoy + timedelta(days=2)

    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(df['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
        df = df.sort_values(by='vencimiento')

    # CREACIÓN DE 3 PESTAÑAS
    tab1, tab3, tab2 = st.tabs(["🗃️ Panel de Gestión", "📦 Proveedores", "📊 Reporte Financiero"])

    # =========================================================================
    # PESTAÑA 1: GESTIÓN DE CLIENTES
    # =========================================================================
    with tab1:
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

        clientes_activos = df[~condicion_libre].copy()
        lista_prepagados, lista_pendiente_renovar_pagados, lista_pagos_pendientes, lista_proximos_vencer, lista_activos, lista_inactivos = [], [], [], [], [], []

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
            
            try: meses_adelanto = 0 if pd.isna(row.get('meses_adelanto', 0)) or str(row.get('meses_adelanto', 0)).strip() == "" else int(float(row.get('meses_adelanto', 0)))
            except: meses_adelanto = 0

            if meses_adelanto > 0: lista_prepagados.append((row, nombre_completo, primer_nombre))
            elif estatus == 'pagado': lista_pendiente_renovar_pagados.append((row, nombre_completo, primer_nombre))
            elif estatus == 'pendiente' or (fecha_vence < fecha_hoy and estatus != 'pagado'): lista_pagos_pendientes.append((row, nombre_completo, primer_nombre))
            elif estatus != 'pagado' and (fecha_hoy <= fecha_vence <= fecha_limite_cobro): lista_proximos_vencer.append((row, nombre_completo, primer_nombre))
            else: lista_activos.append((row, nombre_completo, primer_nombre, fecha_vence))

        # --- SECCIONES WHATSAPP (Mantenidas idénticas por brevedad visual, funcionan igual) ---
        if len(lista_prepagados) > 0:
            st.divider()
            st.markdown("### ✅ Prepagado")
            for item in lista_prepagados:
                row, nombre_completo, primer_nombre = item
                id_u, clave, servicio = row.get('id_cuenta', 'S/D'), row.get('clave', 'S/D'), str(row.get('servicio', 'Servicio')).strip()
                vence_dt = row['vencimiento']
                meses_restantes = int(float(row.get('meses_adelanto', 0)))
                with st.expander(f"✅ PREPAGADO ({meses_restantes} meses a favor): {nombre_completo} - Vence: {vence_dt.strftime('%d-%m-%Y')}"):
                    msg = f"Hola {primer_nombre} 🫂\nTu recarga ha sido procesada.\nUsuario: {id_u}\nClave: {clave}"
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', '')).split('.')[0]))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#007BFF; color:white; border:none; padding:8px 16px; border-radius:4px;">🚀 Enviar Claves</button></a>', unsafe_allow_html=True)

        if len(lista_pendiente_renovar_pagados) > 0:
            st.divider()
            st.markdown("### ⏳ Renovar")
            for item in lista_pendiente_renovar_pagados:
                row, nombre_completo, primer_nombre = item
                id_u, clave = row.get('id_cuenta', 'S/D'), row.get('clave', 'S/D')
                with st.expander(f"⏳ RENOVAR: {nombre_completo} - Cuenta: {id_u}"):
                    msg = f"Hola {primer_nombre} 🫂\n¡Gracias por tu pago! Tu servicio ha sido renovado.\nUsuario: {id_u}\nClave: {clave}"
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', '')).split('.')[0]))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px;">🚀 Enviar Nuevos Datos</button></a>', unsafe_allow_html=True)

        if len(lista_proximos_vencer) > 0:
            st.divider()
            st.markdown("### ⚠️ Próximos a Vencer")
            for item in lista_proximos_vencer:
                row, nombre_completo, primer_nombre = item
                precio = float(row.get('precio_usd', 0)) if not pd.isna(row.get('precio_usd', 0)) else 0.0
                vence_dt = row['vencimiento']
                monto_bs = "{:,.2f}".format(precio * tasa_dia).replace(",", "X").replace(".", ",").replace("X", ".")
                with st.expander(f"⚠️ PRÓXIMO A VENCER: {nombre_completo} - Vence: {vence_dt.strftime('%d-%m-%Y')}"):
                    msg = f"Hola {primer_nombre} 🫂\nTe recordamos que tu servicio vence el {vence_dt.strftime('%d-%m-%Y')}. Monto: {monto_bs} Bs."
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', '')).split('.')[0]))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FFC107; color:black; border:none; padding:8px 16px; border-radius:4px;">📲 Enviar Recordatorio</button></a>', unsafe_allow_html=True)

        if len(lista_pagos_pendientes) > 0:
            st.divider()
            st.markdown("### 🚨 Pagos Pendientes")
            for item in lista_pagos_pendientes:
                row, nombre_completo, primer_nombre = item
                vence_dt = row['vencimiento']
                with st.expander(f"🚨 PENDIENTE: {nombre_completo} - Venció: {vence_dt.strftime('%d-%m-%Y')}"):
                    msg = f"Hola {primer_nombre} 🚨\nTu servicio se encuentra vencido desde el {vence_dt.strftime('%d-%m-%Y')}."
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', '')).split('.')[0]))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#DC3545; color:white; border:none; padding:8px 16px; border-radius:4px;">🛑 Enviar Aviso</button></a>', unsafe_allow_html=True)
        
        if len(lista_activos) > 0:
            st.divider()
            st.markdown("### 🟢 Activos")
            for item in lista_activos:
                row, nombre_completo, primer_nombre, _ = item
                with st.expander(f"🟢 ACTIVO: {nombre_completo} - Vence: {row['vencimiento'].strftime('%d-%m-%Y')}"):
                    st.write("Cliente al día.")

        # --- EDITOR ---
        st.divider()
        st.subheader("📝 Base de Datos")
        df_editor = df.copy()
        if 'estatus' in df_editor.columns:
            df_editor['es_inactivo'] = df_editor['estatus'].str.lower().str.contains('inactivo|cancelado', na=False)
            df_editor = df_editor.sort_values(by=['es_inactivo', 'vencimiento'], ascending=[True, True]).reset_index(drop=True).drop(columns=['es_inactivo'])
        
        for col in ["clave", "telefono", "nombre", "id_cuenta", "estatus", "servicio"]: 
            if col in df_editor.columns: df_editor[col] = df_editor[col].fillna('').astype(str).replace('nan', '')
        if 'vencimiento' in df_editor.columns: df_editor['vencimiento'] = df_editor['vencimiento'].dt.strftime('%d/%m/%Y %H:%M:%S').fillna('')
        
        df_editado = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Guardar Cambios en Clientes"):
            if 'vencimiento' in df_editado.columns:
                fechas_c = pd.to_datetime(df_editado['vencimiento'], dayfirst=True, format='mixed', errors='coerce')
                df_editado['vencimiento'] = [x.strftime('%d/%m/%Y %H:%M:%S') if pd.notna(x) else '' for x in fechas_c]
            st.cache_data.clear()
            conn.update(worksheet="Clientes", data=df_editado)
            st.success("¡Datos guardados!")
            st.rerun()

    # =========================================================================
    # PESTAÑA 2: PROVEEDORES (NUEVA)
    # =========================================================================
    with tab3:
        st.subheader("🛒 Registro de Compras al Proveedor")
        st.write("Registra aquí cada vez que le pagues al proveedor por nuevos créditos.")
        
        with st.form("registro_compras"):
            col1, col2 = st.columns(2)
            fecha_c = col1.date_input("Fecha de compra", value=ahora)
            prov_c = col2.selectbox("Plataforma", ["FlujoTV", "JumangisTV", "Otro"])
            creditos_c = col1.number_input("Créditos comprados", min_value=1, step=1)
            monto_c = col2.number_input("Monto pagado ($ USD)", min_value=0.1, step=0.5)
            
            if st.form_submit_button("💳 Registrar Compra"):
                nueva_fila = pd.DataFrame([{
                    "fecha": fecha_c.strftime("%d/%m/%Y"),
                    "proveedor": prov_c,
                    "creditos": creditos_c,
                    "monto_usd": monto_c
                }])
                df_compras_actualizado = pd.concat([df_compras, nueva_fila], ignore_index=True)
                st.cache_data.clear()
                conn.update(worksheet="Compras_Proveedor", data=df_compras_actualizado)
                st.success("¡Compra registrada en el libro diario con éxito!")
                st.rerun()
                
        st.divider()
        st.markdown("### 📋 Libro Diario de Compras")
        if not df_compras.empty:
            st.dataframe(df_compras, use_container_width=True)
        else:
            st.info("Aún no has registrado compras.")

    # =========================================================================
    # PESTAÑA 3: REPORTE FINANCIERO Y CIERRE
    # =========================================================================
    with tab2:
        st.subheader("📊 Reportes en Vivo")
        
        # --- Cálculo de Ingresos (Los que están al día) ---
        ingreso_total = 0.0
        clientes_reporte = lista_prepagados + lista_pendiente_renovar_pagados + lista_proximos_vencer + lista_activos
        for item in clientes_reporte:
            precio = float(item[0].get('precio_usd', 0)) if not pd.isna(item[0].get('precio_usd', 0)) else 0.0
            ingreso_total += precio

        # --- Cálculo de Gastos Reales (De la hoja de compras) ---
        gasto_real = pd.to_numeric(df_compras['monto_usd'], errors='coerce').sum() if not df_compras.empty else 0.0
        creditos_totales = pd.to_numeric(df_compras['creditos'], errors='coerce').sum() if not df_compras.empty else 0
        ganancia_neta = ingreso_total - gasto_real

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Ingreso Asegurado", f"${ingreso_total:,.2f} USD")
        m2.metric("📉 Gastos Proveedor", f"${gasto_real:,.2f} USD")
        m3.metric("✨ Ganancia Neta Actual", f"${ganancia_neta:,.2f} USD")

        st.divider()
        
        # --- EL BOTÓN DE CIERRE ---
        st.markdown("### 💾 Guardar Cierre de Mes")
        mes_actual_str = ahora.strftime("%m/%Y")
        st.info(f"Haz clic aquí a final de mes para guardar estos números en tu historial anual.")
        
        if st.button(f"Registrar Cierre de {mes_actual_str}"):
            nueva_fila_hist = pd.DataFrame([{
                "mes": mes_actual_str,
                "ingresos": ingreso_total,
                "gastos": gasto_real,
                "ganancia": ganancia_neta,
                "creditos": creditos_totales
            }])
            df_hist_actualizado = pd.concat([df_historial, nueva_fila_hist], ignore_index=True)
            st.cache_data.clear()
            conn.update(worksheet="Historial_Mensual", data=df_hist_actualizado)
            st.success(f"¡Cierre de {mes_actual_str} guardado exitosamente!")
            st.rerun()

        # --- HISTORIAL ANUAL ---
        st.divider()
        st.markdown("### 📈 Historial Anual (Estado de Resultados)")
        if not df_historial.empty:
            st.dataframe(df_historial, use_container_width=True)
            # Gráfico comparativo de meses
            if 'ingresos' in df_historial.columns and 'ganancia' in df_historial.columns:
                try:
                    df_grafico = df_historial.set_index("mes")[["ingresos", "gastos", "ganancia"]]
                    st.bar_chart(df_grafico)
                except:
                    pass
        else:
            st.write("Aún no tienes cierres de mes registrados.")

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
