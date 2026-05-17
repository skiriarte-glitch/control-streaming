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
        # 1. 💟 PERFILES DISPONIBLES
        # =========================================================================
        st.markdown("### 💟 Perfiles Disponibles")
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

        # --- SECCIONES DE GESTIÓN ---
        if len(lista_prepagados) > 0:
            st.divider()
            st.markdown("### ♻️ Prepagados por Actualizar")
            for item in lista_prepagados:
                row, nombre_completo, primer_nombre = item
                id_u = row.get('id_cuenta', 'S/D')
                vence_dt = row['vencimiento']
                with st.expander(f"♻️ PREPAGADO: {nombre_completo} - Cuenta: {id_u} - Vence: {vence_dt.strftime('%d-%m-%Y')}"):
                    # Lógica de WhatsApp (Igual que antes)
                    msg = f"Hola {primer_nombre} 🫂\nRecarga procesada exitosamente..."
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', ''))))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#007BFF; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Claves (Sin Cobrar)</button></a>', unsafe_allow_html=True)

        if len(lista_pendiente_renovar_pagados) > 0:
            st.divider()
            st.markdown("### ⏳ Pendientes por Renovar (Ya Pagaron)")
            for item in lista_pendiente_renovar_pagados:
                row, nombre_completo, primer_nombre = item
                id_u = row.get('id_cuenta', 'S/D')
                vence_dt = row['vencimiento']
                with st.expander(f"⏳ PAGADO / POR RENOVAR: {nombre_completo} - Cuenta: {id_u}"):
                    msg = f"Hola {primer_nombre} 🫂\n¡Gracias por tu pago! Tu servicio ha sido renovado..."
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', ''))))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#28A745; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🚀 Enviar Nuevos Datos</button></a>', unsafe_allow_html=True)

        # --- SECCIÓN DE PRÓXIMOS A VENCER (HOY + 2 DÍAS) ---
        if len(lista_proximos_vencer) > 0:
            st.divider()
            st.markdown("### ⚠️ Próximos a Vencer (Cobrar en 2 días)")
            for item in lista_proximos_vencer:
                row, nombre_completo, primer_nombre = item
                id_u = row.get('id_cuenta', 'S/D')
                vence_dt = row['vencimiento']
                with st.expander(f"⚠️ PRÓXIMO A VENCER: {nombre_completo} - Cuenta: {id_u} - Vence: {vence_dt.strftime('%d-%m-%Y')}"):
                    msg = f"Hola {primer_nombre} 🫂\nTe recordamos que tu servicio vence el {vence_dt.strftime('%d-%m-%Y')}. Puedes ir realizando tu pago para evitar interrupciones."
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', ''))))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#FFC107; color:black; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">📲 Enviar Recordatorio</button></a>', unsafe_allow_html=True)

        # --- SECCIÓN DE PAGOS PENDIENTES / VENCIDOS ---
        if len(lista_pagos_pendientes) > 0:
            st.divider()
            st.markdown("### 🚨 Pagos Pendientes o Vencidos")
            for item in lista_pagos_pendientes:
                row, nombre_completo, primer_nombre = item
                id_u = row.get('id_cuenta', 'S/D')
                vence_dt = row['vencimiento']
                with st.expander(f"🚨 MOROSO/PENDIENTE: {nombre_completo} - Cuenta: {id_u} - Venció: {vence_dt.strftime('%d-%m-%Y')}"):
                    msg = f"Hola {primer_nombre} 🚨\nTu servicio se encuentra vencido desde el {vence_dt.strftime('%d-%m-%Y')}. Por favor realiza el pago para mantener tu servicio activo."
                    num = ''.join(filter(str.isdigit, str(row.get('telefono', ''))))
                    if len(num) == 10: num = f"58{num}"
                    st.markdown(f'<a href="https://api.whatsapp.com/send?phone={num}&text={urllib.parse.quote(msg)}" target="whatsapp" style="text-decoration:none;"><button style="background-color:#DC3545; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer;">🛑 Enviar Aviso de Corte</button></a>', unsafe_allow_html=True)
        
        # (Secciones de Pagos Pendientes y Próximos a Vencer omitidas por brevedad pero se mantienen idénticas en tu archivo real)
        # Sección Activos (Ordenada)
        if len(lista_activos) > 0:
            st.divider()
            st.markdown("### ✅ Activos")
            lista_activos.sort(key=lambda x: x[3])
            for item in lista_activos:
                row, nombre_completo, primer_nombre, _ = item
                id_u = row.get('id_cuenta', 'S/D')
                vence_dt = row['vencimiento']
                with st.expander(f"🟢 ACTIVO: {nombre_completo} ({id_u}) - Vence: {vence_dt.strftime('%d-%m-%Y')}"):
                    st.write("Cliente al día.")

        # --- EDITOR ---
        st.divider()
        st.subheader("📝 Base de Datos Editable")
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

        # --- INACTIVOS AL FINAL ---
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
        st.subheader("📊 Reporte Financiero de Volumen Pagado")
        
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
            st.markdown(f"**🎬 Canal FlujoTV**\n\n* Cuentas: {flujo_completas + flujo_pantallas_acc}\n* Ingreso: ${flujo_ingreso:.2f}\n* Ganancia: ${flujo_ingreso - flujo_costo:.2f}")
        with col_b:
            st.markdown(f"**🛜 Canal JumangisTV**\n\n* Cuentas: {juman_cuentas}\n* Ingreso: ${juman_ingreso:.2f}\n* Ganancia: ${juman_ingreso - juman_costo:.2f}")

        st.divider()
        st.info(f"**Flujo Bruto en Bolívares:** {ingreso_total * tasa_dia:,.2f} Bs.")
        st.success(f"**Utilidad Real en Bolívares:** {ganancia_total * tasa_dia:,.2f} Bs.")

else:
    st.info("Introduce la contraseña para gestionar el sistema.")
