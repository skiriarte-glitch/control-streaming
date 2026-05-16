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
df.columns = [
    str(c).strip().lower()
    .replace('é', 'e')
    .replace('ó', 'o')
    for c in df.columns
]

password = st.sidebar.text_input("Contraseña", type="password")

if password == CLAVE_MAESTRA:

    tasa_dia = st.sidebar.number_input(
        "Tasa del día (Bs/$)",
        min_value=1.0,
        value=660.0,
        step=1.0
    )

    ahora = datetime.now()

    # Convertir fechas
    if 'vencimiento' in df.columns:
        df['vencimiento'] = pd.to_datetime(
            df['vencimiento'],
            errors='coerce'
        )

        df = df.sort_values(by='vencimiento')

    # =========================================================================
    # 1. 💜 PERFILES DISPONIBLES
    # =========================================================================
    st.markdown("### 💜 Perfiles Disponibles")

    condicion_libre = pd.Series(False, index=df.index)

    if 'estatus' in df.columns:

        condicion_libre = (
            df['estatus'].str.lower().str.contains(
                'libre|vacante',
                na=False
            )
        ) | (
            df['nombre'].str.lower().str.contains(
                'disponible|libre|vacante',
                na=False
            )
        )

        disponibles = df[condicion_libre]

        if not disponibles.empty:

            for idx, row in disponibles.iterrows():

                st.success(
                    f"✨ **{row.get('servicio', 'Servicio')}** "
                    f"disponible en cuenta: "
                    f"`{row.get('id_cuenta', 'S/D')}`"
                )

        else:
            st.write("No tienes cupos libres por ahora.")

    # =========================================================================
    # LISTAS
    # =========================================================================
    clientes_activos = df[~condicion_libre].copy()

    lista_pagos_pendientes = []
    lista_proximos_vencer = []
    lista_activos = []

    for index, row in clientes_activos.iterrows():

        raw_nombre = row.get('nombre', '')

        nombre = (
            "Cliente"
            if pd.isna(raw_nombre) or str(raw_nombre).strip() == ""
            else str(raw_nombre).strip()
        )

        estatus = str(row.get('estatus', '')).strip().lower()

        vence_dt = row.get('vencimiento', pd.NaT)

        if pd.isna(vence_dt):
            continue

        if estatus == 'pendiente':
            lista_pagos_pendientes.append(row)

        elif estatus != 'pagado' and vence_dt <= ahora + timedelta(days=2):
            lista_proximos_vencer.append(row)

        else:
            lista_activos.append(row)

    # =========================================================================
    # 2. 🔍 PAGOS PENDIENTES
    # =========================================================================
    st.divider()
    st.markdown("### 🔍 Pagos pendientes")

    if len(lista_pagos_pendientes) > 0:

        for row in lista_pagos_pendientes:

            raw_nombre = row.get('nombre', '')

            nombre = (
                "Cliente"
                if pd.isna(raw_nombre) or str(raw_nombre).strip() == ""
                else str(raw_nombre).strip()
            )

            servicio = str(row.get('servicio', 'Servicio')).strip()

            precio = (
                float(row.get('precio_usd', 0))
                if not pd.isna(row.get('precio_usd', 0))
                else 0.0
            )

            vence_dt = row['vencimiento']

            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')

            monto_bs = "{:,.2f}".format(
                precio * tasa_dia
            ).replace(",", "X").replace(".", ",").replace("X", ".")

            with st.expander(
                f"🔴 SERVICIO RENOVADO / DEBE PAGO: "
                f"{nombre} ({servicio}) - "
                f"Vence: {fecha_vence_str}"
            ):

                msg_deudor = (
                    f'Hola "{nombre}" 🫂\n\n'
                    f'Te escribo para recordarte que ya se realizó '
                    f'la renovación de tu suscripción de {servicio}, '
                    f'pero aún tenemos pendiente el pago.\n\n'

                    f'Te dejo por aquí los datos para que puedas '
                    f'ponerte al día.\n\n'

                    f'Pago móvil 💳\n'
                    f'Banco: Bancamiga\n'
                    f'Documento: 13024234\n'
                    f'Teléfono: 04246379018\n'
                    f'Concepto: PAGO\n'
                    f'Monto: {monto_bs} Bs.\n\n'

                    f'Solicita el correo si deseas pagar '
                    f'por Binance o Zelle 💵\n\n'

                    f'Quedo atenta ante cualquier duda. '
                    f'¡Gracias! ✨'
                )

                num = str(
                    row.get('telefono', '58')
                ).split('.')[0].strip()

                if not num.startswith("58") and num != "":
                    num = f"58{num}"

                # IMPORTANTE:
                # usamos quote en vez de quote_plus
                texto_url = urllib.parse.quote(msg_deudor)

                link_cobro = (
                    f"https://wa.me/{num}?text={texto_url}"
                )

                st.markdown(
                    f"[📲 Enviar Recordatorio de Deuda]"
                    f"({link_cobro})"
                )

    else:
        st.write(
            "✅ Todo al día. "
            "Ningún cliente bajo el estatus 'Pendiente'."
        )

    # =========================================================================
    # 3. ⏰ PRÓXIMOS A VENCER
    # =========================================================================
    st.divider()
    st.markdown("### ⏰ Próximos a Vencer")

    if len(lista_proximos_vencer) > 0:

        for row in lista_proximos_vencer:

            raw_nombre = row.get('nombre', '')

            nombre = (
                "Cliente"
                if pd.isna(raw_nombre) or str(raw_nombre).strip() == ""
                else str(raw_nombre).strip()
            )

            servicio = str(row.get('servicio', 'Servicio')).strip()

            precio = (
                float(row.get('precio_usd', 0))
                if not pd.isna(row.get('precio_usd', 0))
                else 0.0
            )

            vence_dt = row['vencimiento']

            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')

            monto_bs = "{:,.2f}".format(
                precio * tasa_dia
            ).replace(",", "X").replace(".", ",").replace("X", ".")

            with st.expander(
                f"🟡 AVISAR RENOVAR: "
                f"{nombre} ({servicio}) - "
                f"Vence: {fecha_vence_str}"
            ):

                msg_preventivo = (
                    f'Hola "{nombre}" 🫂\n\n'

                    f'Ya está disponible la renovación '
                    f'de tu suscripción de {servicio}.\n\n'

                    f'Si deseas renovar, te dejo los datos de pago.\n\n'

                    f'Pago móvil 💳\n'
                    f'Banco: Bancamiga\n'
                    f'Documento: 13024234\n'
                    f'Teléfono: 04246379018\n'
                    f'Concepto: PAGO\n'
                    f'Monto: {monto_bs} Bs.\n\n'

                    f'Solicita el correo si deseas pagar '
                    f'por Binance o Zelle 💵\n\n'

                    f'Quedo atenta ante cualquier duda ✨'
                )

                num = str(
                    row.get('telefono', '58')
                ).split('.')[0].strip()

                if not num.startswith("58") and num != "":
                    num = f"58{num}"

                texto_url = urllib.parse.quote(msg_preventivo)

                link_cobro = (
                    f"https://wa.me/{num}?text={texto_url}"
                )

                st.markdown(
                    f"[📲 Enviar Mensaje de Cobro Standard]"
                    f"({link_cobro})"
                )

    else:
        st.write("No hay vencimientos en el rango de aviso.")

    # =========================================================================
    # 4. 🟢 ACTIVOS
    # =========================================================================
    st.divider()
    st.markdown("### 🟢 Activos")

    if len(lista_activos) > 0:

        for row in lista_activos:

            raw_nombre = row.get('nombre', '')

            nombre = (
                "Cliente"
                if pd.isna(raw_nombre) or str(raw_nombre).strip() == ""
                else str(raw_nombre).strip()
            )

            servicio = str(row.get('servicio', 'Servicio')).strip()

            id_u = row.get('id_cuenta', 'S/D')
            clave = row.get('clave', 'S/D')

            precio = (
                float(row.get('precio_usd', 0))
                if not pd.isna(row.get('precio_usd', 0))
                else 0.0
            )

            vence_dt = row['vencimiento']

            fecha_vence_str = vence_dt.strftime('%d-%m-%Y')

            badge_estado = (
                " (Esperando Grupo)"
                if str(row.get('estatus', '')).lower() == 'pagado'
                else ""
            )

            with st.expander(
                f"🟢 ACTIVO{badge_estado}: "
                f"{nombre} ({servicio}) - "
                f"Vence: {fecha_vence_str}"
            ):

                conexiones = "1"

                if "flujotv" in servicio.lower():

                    if precio == 6:
                        conexiones = "2"

                    elif precio >= 9:
                        conexiones = "3"

                elif "jumangistv" in servicio.lower():
                    conexiones = "3"

                msg_entrega = (
                    f'✨ Aquí están tus datos personales de acceso.\n'
                    f'No los compartas con nadie.\n\n'

                    f'⚡️ Conexiones: {conexiones}\n'
                    f'📆 Próxima renovación: {fecha_vence_str}\n\n'
                )

                if "jumangistv" in servicio.lower():

                    msg_entrega += (
                        f'🛜 Host/URL: '
                        f'http://jumangis.cloud:2082\n'
                    )

                msg_entrega += (
                    f'👤 Usuario: {id_u}\n'
                    f'🔐 Contraseña: {clave}\n'
                )

                if "flujotv" in servicio.lower():

                    msg_entrega += (
                        f'🚯 PIN contenido adulto: 1234\n'
                    )

                msg_entrega += (
                    f'\n¡Disfruta de tus contenidos favoritos! '
                    f'Si necesitas ayuda, no dudes en contactarme. 📩'
                )

                num = str(
                    row.get('telefono', '58')
                ).split('.')[0].strip()

                if not num.startswith("58") and num != "":
                    num = f"58{num}"

                texto_url = urllib.parse.quote(msg_entrega)

                link_entrega = (
                    f"https://wa.me/{num}?text={texto_url}"
                )

                st.markdown(
                    f"[🚀 Enviar Datos de Acceso]"
                    f"({link_entrega})"
                )

    else:
        st.write("No hay membresías activas registradas.")

    st.divider()
    st.subheader("👥 Base de Datos General")
    st.dataframe(df)

else:
    st.info(
        "Introduce la contraseña para gestionar el sistema."
    )
