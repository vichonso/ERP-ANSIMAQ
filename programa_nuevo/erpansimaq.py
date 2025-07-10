import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página


from sqlalchemy import text
from sqlalchemy import create_engine

# Configuración del tema de Streamlit


# Conexión a la base de datos PostgreSQL
engine = create_engine('postgresql+psycopg2://postgres:pc-database@localhost:5432/ansimaq_bdd')


# Funciones para cargar datos de las tablas principales
def cargar_equipos():
    df = pd.read_sql("SELECT * FROM equipos", engine)
    return df

def cargar_clientes():
    df = pd.read_sql("SELECT * FROM clientes", engine)
    return df

def cargar_contratos():
    query = """
        SELECT contrato.*, clientes.nombre_empresa, clientes.nombre_representante, clientes.rut_representante, clientes.obra, clientes.correo, clientes.telefono
        FROM contrato
        JOIN clientes ON contrato.rut_empresa = clientes.rut_empresa
    """
    df = pd.read_sql(query, engine)
    return df

def cargar_cobros():
    query = """
        SELECT cobros.*, contrato.folio, contrato.rut_empresa, clientes.nombre_empresa
        FROM cobros
        JOIN contrato ON cobros.folio = contrato.folio
        JOIN clientes ON contrato.rut_empresa = clientes.rut_empresa
    """
    df = pd.read_sql(query, engine)
    return df

def cargar_historial_contrato():
    query = """
        SELECT historial_contrato.*, contrato.folio, contrato.rut_empresa, clientes.nombre_empresa
        FROM historial_contrato
        JOIN contrato ON historial_contrato.folio = contrato.folio
        JOIN clientes ON contrato.rut_empresa = clientes.rut_empresa
    """
    df = pd.read_sql(query, engine)
    return df

def obtener_historial_inicial(folio_seleccionado):
    query = """
        SELECT id_historial, numero_vigente, tipo_servicio, fecha_servicio, horometro
        FROM historial_contrato
        WHERE folio = :folio
          AND tipo_servicio = 'Entrega en obra'
        LIMIT 1;
    """
    df = pd.read_sql(text(query), engine, params={"folio": folio_seleccionado})
    return df



menu = st.sidebar.radio("Menú", [
    "Inicio",
    "Equipos",
    "Clientes",
    "Contratos",
    "Historial de Contratos",
    "Cobros",
])

if menu == "Inicio":
    st.title("💼 Bienvenido a Ansimaq")
    st.markdown("## 🛠️ Resumen general")

    # --- Cargar datos
    df_equipos = cargar_equipos()
    df_cobros = cargar_cobros()

    # --- Generadores disponibles
    generadores_disponibles = df_equipos[df_equipos["estado"] == 1]  # Estado 1 = disponible
    total_generadores = len(generadores_disponibles)

    # --- Pagos pendientes (ajusta según tu tabla)
    if "pagado" in df_cobros.columns:
        pagos_pendientes = df_cobros[df_cobros["pagado"] == False]
    else:
        pagos_pendientes = df_cobros  # Si no hay campo, muestra todos

    total_pagos = len(pagos_pendientes)
    monto_total = pagos_pendientes["monto"].sum() if "monto" in pagos_pendientes.columns else 0

    # --- Mostrar métricas principales
    col1, col2 = st.columns(2)
    col1.metric("🔋 Generadores disponibles", total_generadores)
    col2.metric("💰 Pagos pendientes", f"{total_pagos} pagos - ${monto_total:,.0f}")

    st.markdown("---")
    st.subheader("🔋 Detalle de generadores disponibles")
    if total_generadores > 0:
        st.dataframe(
            generadores_disponibles[["numero_vigente", "nombre_modelo", "estado"]],
            use_container_width=True
        )
    else:
        st.info("No hay generadores disponibles en este momento.")

    st.markdown("---")
    st.subheader("📄 Detalle de pagos pendientes")
    if total_pagos > 0:
        st.dataframe(
            pagos_pendientes[["cliente", "monto", "fecha_limite"]],
            use_container_width=True
        )
    else:
        st.success("No hay pagos pendientes. ¡Todo está al día!")


elif menu == "Equipos": 
    st.title("Equipos")
    opcion = st.radio("Seleccione una opción", ["Ver Equipos", "Agregar Equipo", "Editar o Eliminar Equipo"])

    if opcion == "Ver Equipos":
        st.subheader("Lista de Equipos")
        df_equipos = cargar_equipos()

        # Mapear estado numérico a texto
        estados_dict = {1: "Disponible", 2: "En arriendo", 3: "Mantenimiento", 4: "Averiado"}
        if "estado" in df_equipos.columns:
            df_equipos["estado"] = df_equipos["estado"].map(estados_dict).fillna(df_equipos["estado"])

        # Barra de búsqueda y filtro en la misma fila
        col1, col2 = st.columns([2, 1])
        with col1:
            busqueda = st.text_input("Buscar por modelo o número de serie")
        with col2:
            if "estado" in df_equipos.columns:
                estados = df_equipos["estado"].unique()
                estado_sel = st.multiselect("Filtrar por estado", estados, default=list(estados))
            else:
                estado_sel = None

        df_filtrado = df_equipos.copy()
        if busqueda:
            df_filtrado = df_filtrado[
                df_filtrado["nombre_modelo"].str.contains(busqueda, case=False, na=False) |
                df_filtrado["numero_vigente"].str.contains(busqueda, case=False, na=False)
            ]
        if estado_sel is not None:
            df_filtrado = df_filtrado[df_filtrado["estado"].isin(estado_sel)]

        # Resetear el índice para evitar errores de pandas al filtrar
        df_filtrado = df_filtrado.reset_index(drop=True)
        st.dataframe(df_filtrado)
    
    elif opcion == "Agregar Equipo":
        st.subheader("Agregar Nuevo Equipo")
        df_equipos = cargar_equipos()
        with st.form("form_agregar_equipo"):
            numero_vigente = st.text_input("Número Vigente")
            nombre_modelo = st.text_input("Nombre del Modelo")
            estado = 1 # Estado disponible por defecto
            
            submit_button = st.form_submit_button("Agregar Equipo")

            if submit_button:
                if not numero_vigente:
                    st.error("El número vigente es obligatorio.")
                elif numero_vigente in df_equipos["numero_vigente"].values:
                    st.error("El número vigente ya existe. Por favor, ingrese uno diferente.")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO equipos (nombre_modelo, numero_vigente, estado)
                            VALUES (:nombre_modelo, :numero_vigente, :estado)
                        """), {
                            "nombre_modelo": nombre_modelo,
                            "numero_vigente": numero_vigente,
                            "estado": estado,
                        })
                    st.success("✅ Equipo agregado exitosamente.")

    elif opcion == "Editar o Eliminar Equipo":
        st.subheader("Editar o Eliminar Equipo")
        df_equipos = cargar_equipos()
        numero_vigente = st.selectbox("Seleccione el número vigente del equipo a modificar", df_equipos["numero_vigente"].unique())
        g = df_equipos[df_equipos["numero_vigente"] == numero_vigente].iloc[0]
        equipo_seleccionado = g["numero_vigente"]

        with st.form("form_editar_equipo"):
            nuevo_nvigente = st.text_input("Número Vigente", value=g["numero_vigente"]) 
            nombre_modelo = st.text_input("Nombre del Modelo", value=g["nombre_modelo"])
            # Estado como selectbox
            estados_dict = {1: "Disponible", 2: "En arriendo", 3: "Mantenimiento", 4: "Averiado"}
            estados_opciones = list(estados_dict.values())
            estado_actual_texto = estados_dict.get(g["estado"], "Disponible")
            estado_index = estados_opciones.index(estado_actual_texto)
            estado_texto = st.selectbox("Estado", estados_opciones, index=estado_index)
            estado = [k for k, v in estados_dict.items() if v == estado_texto][0]

            editar_button = st.form_submit_button("Guardar Cambios")
            if editar_button:
                if not nuevo_nvigente:
                    st.error("El número vigente es obligatorio.")
                elif nuevo_nvigente != equipo_seleccionado and nuevo_nvigente in df_equipos["numero_vigente"].values:
                    st.error("El número vigente ya existe. Por favor, ingrese uno diferente.")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE equipos
                            SET numero_vigente = :nuevo_nvigente, nombre_modelo = :nombre_modelo, estado = :estado
                            WHERE numero_vigente = :equipo_seleccionado
                        """), {
                            "nuevo_nvigente": nuevo_nvigente,
                            "nombre_modelo": nombre_modelo,
                            "estado": estado,
                            "equipo_seleccionado": equipo_seleccionado
                        })
                    st.success("✅ Equipo actualizado exitosamente.")
            eliminar_button = st.form_submit_button("Eliminar Equipo")
            if eliminar_button:
                confirmacion = st.checkbox("CONFIRMAR ELIMINACIÓN")
                if confirmacion:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            DELETE FROM equipos WHERE numero_vigente = :equipo_seleccionado
                        """), {
                            "equipo_seleccionado": equipo_seleccionado
                        })
                    st.warning("✅ Equipo eliminado exitosamente.")
                elif not confirmacion:
                    st.error("¿Estas seguro de que deseas eliminar este equipo?")


elif menu == "Clientes":
    st.title("Clientes")
    opcion = st.radio("Seleccione una opción", ["Ver Clientes", "Agregar Cliente", "Editar o Eliminar Cliente"])

    if opcion == "Ver Clientes":
        st.subheader("Lista de Clientes")
        df_clientes = cargar_clientes()
        
        busqueda = st.text_input("Buscar por RUT o Nombre")
        
        if busqueda:
            df_clientes = df_clientes[
                df_clientes["rut"].str.contains(busqueda, case=False, na=False) |
                df_clientes["nombre"].str.contains(busqueda, case=False, na=False)
            ]
        
        st.dataframe(df_clientes)
    
    elif opcion == "Agregar Cliente":
        st.subheader("Agregar Nuevo Cliente")
        df_clientes = cargar_clientes()
        with st.form("form_agregar_cliente"):
            rut = st.text_input("RUT de la empresa", placeholder="Sin puntos Ej: 123456789-K")
            nombre = st.text_input("Nombre de la empresa")
            obra = st.text_input("Obra")
            nombre_representante = st.text_input("Nombre del Representante")
            rut_representante = st.text_input("RUT del Representante", placeholder="Sin puntos Ej: 123456789-K")
            email = st.text_input("Email del Cliente", placeholder="correo@email.com")
            telefono = st.text_input("Teléfono del Cliente", placeholder="sin espacios ni caracteres Ej: 912345678")
            
            submit_button = st.form_submit_button("Agregar Cliente")

            if submit_button:
                if not rut or not nombre:
                    st.error("El RUT y el nombre son obligatorios.")
                elif rut in df_clientes["rut_empresa"].values:
                    st.error("El RUT ya existe. Por favor, ingrese uno diferente.")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO clientes (rut_empresa, nombre_empresa, obra, nombre_representante, rut_representante, correo, telefono)
                            VALUES (:rut_empresa, :nombre_empresa, :obra, :nombre_representante, :rut_representante, :correo, :telefono)
                        """), {
                            "rut_empresa": rut,
                            "nombre_empresa": nombre,
                            "obra": obra,
                            "nombre_representante": nombre_representante,
                            "rut_representante": rut_representante,
                            "correo": email,
                            "telefono": telefono if telefono else None,
                        })
                    st.success("✅ Cliente agregado exitosamente.")
    
    elif opcion == "Editar o Eliminar Cliente":
        st.subheader("Editar o Eliminar Cliente")
        df_clientes = cargar_clientes()
        rut_seleccionado = st.selectbox("Seleccione el RUT del cliente a modificar", df_clientes["rut_empresa"].unique())
        g = df_clientes[df_clientes["rut_empresa"] == rut_seleccionado].iloc[0]
        
        with st.form("form_editar_cliente"):
            nuevo_rut = st.text_input("RUT de la empresa", value=g["rut_empresa"], placeholder="Sin puntos Ej: 123456789-K")
            nombre = st.text_input("Nombre de la empresa", value=g["nombre_empresa"])
            obra = st.text_input("Obra", value=g["obra"])
            nombre_representante = st.text_input("Nombre del Representante", value=g["nombre_representante"])
            rut_representante = st.text_input("RUT del Representante", value=g["rut_representante"], placeholder="Sin puntos Ej: 123456789-K")
            email = st.text_input("Email del Cliente", value=g["correo"], placeholder="correo@email.com")
            telefono = st.text_input("Teléfono del Cliente", value=g["telefono"], placeholder="sin espacios ni caracteres Ej: 912345678")
            editar_button = st.form_submit_button("Guardar Cambios")
            if editar_button:
                if not nuevo_rut or not nombre:
                    st.error("El RUT y el nombre son obligatorios.")
                elif nuevo_rut != rut_seleccionado and nuevo_rut in df_clientes["rut_empresa"].values:
                    st.error("El RUT ya existe. Por favor, ingrese uno diferente.")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE clientes
                            SET rut_empresa = :nuevo_rut, nombre_empresa = :nombre, obra = :obra, 
                                nombre_representante = :nombre_representante, rut_representante = :rut_representante, 
                                correo = :correo, telefono = :telefono
                            WHERE rut_empresa = :rut_seleccionado
                        """), {
                            "nuevo_rut": nuevo_rut,
                            "nombre": nombre,
                            "obra": obra,
                            "nombre_representante": nombre_representante,
                            "rut_representante": rut_representante,
                            "correo": email,
                            "telefono": telefono if telefono else None,
                            "rut_seleccionado": rut_seleccionado
                        })
                    st.success("✅ Cliente actualizado exitosamente.")
            eliminar_button = st.form_submit_button("Eliminar Cliente")
            if eliminar_button:
                confirmacion = st.checkbox("CONFIRMAR ELIMINACIÓN")
                if confirmacion:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            DELETE FROM clientes WHERE rut_empresa = :rut_seleccionado
                        """), {
                            "rut_seleccionado": rut_seleccionado
                        })
                    st.warning("✅ Cliente eliminado exitosamente.")
                elif not confirmacion:
                    st.error("¿Estas seguro de que deseas eliminar este cliente?")


elif menu == "Contratos":
    st.title("Contratos")
    opcion = st.radio("Seleccione una opción", ["Ver Contratos", "Agregar Contrato", "Editar o Eliminar Contrato"])
    if opcion == "Ver Contratos":
        st.subheader("Lista de Contratos")
        df_contratos = cargar_contratos()
        
        busqueda = st.text_input(label="Nombre de empresa o RUT, Nombre del representante")
        if busqueda:
            df_contratos = df_contratos[
                df_contratos["rut_empresa"].str.contains(busqueda, case=False, na=False) |
                df_contratos["nombre_representante"].str.contains(busqueda, case=False, na=False) |
                df_contratos["nombre_empresa"].str.contains(busqueda, case=False, na=False) |
                df_contratos["rut_representante"].str.contains(busqueda, case=False, na=False)
            ]
        st.dataframe(df_contratos)

    elif opcion == "Agregar Contrato":
        st.subheader("Agregar Nuevo Contrato")
        df_contratos = cargar_contratos()
        df_clientes = cargar_clientes()
        df_equipos = cargar_equipos()

        # Solo equipos disponibles (estado == 1)
        equipos_disponibles = df_equipos[df_equipos["estado"] == 1]["numero_vigente"].tolist()

        with st.form("form_agregar_contrato"):
            rut_empresa = st.selectbox("Seleccione el RUT de la empresa", df_clientes["rut_empresa"].unique())
            cliente_seleccionado = df_clientes[df_clientes["rut_empresa"] == rut_empresa].iloc[0]
            st.write(f"Nombre de la empresa: {cliente_seleccionado['nombre_empresa']}")
            st.write(f"Rut del representante: {cliente_seleccionado['rut_representante']}")
            st.write(f"Nombre del representante: {cliente_seleccionado['nombre_representante']}")

            fecha_inicio = st.date_input("Fecha de inicio del contrato")
            indefinido = st.checkbox("Contrato a plazo indefinido")
            if indefinido:
                fecha_termino = pd.to_datetime("2099-12-31")
                st.info("Fecha de término establecida como 31/12/2099. Puede ser modificada al termino del contrato.")
            else:
                fecha_termino = st.date_input("Fecha de término del contrato")
            # Selección de equipo inicial SOLO de los disponibles
            equipo_inicial = st.selectbox("Seleccione el equipo con el que inicia el contrato", equipos_disponibles)
            horometro = st.number_input("Horómetro inicial (horas)", min_value=0, step=1)
            horas_contratadas = st.number_input("Horas contratadas", min_value=0, step=1)
            precio_mensual = st.number_input("Precio mensual", min_value=0, step=1000)
            precio_envio = st.number_input("Precio de envío", min_value=0, step=1000)

            # Generar folio automático: AAAA00000
            from datetime import date
            hoy = date.today()
            anio = hoy.year
            folio_prefijo = f"{anio}"
            # Buscar el último folio del año actual
            df_folios = df_contratos[df_contratos['folio'].astype(str).str.startswith(folio_prefijo)] if 'folio' in df_contratos.columns else pd.DataFrame()
            if not df_folios.empty:
                ultimos = df_folios['folio'].astype(str).str[-5:].astype(int)
                siguiente = ultimos.max() + 1
            else:
                siguiente = 0
            folio_generado = f"{folio_prefijo}{siguiente:05d}"
            st.info(f"Folio generado automáticamente: {folio_generado}")

            submit_button = st.form_submit_button("Agregar Contrato")

            if submit_button:
                # ...validaciones y lógica de inserción aquí...
                with engine.begin() as conn:
                    # Insertar contrato con egreso_arriendo inicializado en 0
                    conn.execute(text("""
                        INSERT INTO contrato (folio, rut_empresa, precio_mensual, horas_contrtadas, fecha_inicio_contrato, fecha_termino_contrato, egreso_arriendo, precio_envio)
                        VALUES (:folio, :rut_empresa, :precio_mensual, :horas_contrtadas, :fecha_inicio_contrato, :fecha_termino_contrato, :egreso_arriendo, :precio_envio)
                    """), {
                        "folio": int(folio_generado),
                        "rut_empresa": rut_empresa,
                        "precio_mensual": precio_mensual,
                        "horas_contrtadas": horas_contratadas,
                        "fecha_inicio_contrato": fecha_inicio,
                        "fecha_termino_contrato": fecha_termino,
                        "egreso_arriendo": 0,
                        "precio_envio": precio_envio
                    })
                    # Insertar historial_contrato inicial
                    conn.execute(text("""
                        INSERT INTO historial_contrato (folio, numero_vigente, tipo_servicio, fecha_servicio, horometro)
                        VALUES (:folio, :numero_vigente, :tipo_servicio, :fecha_servicio, :horometro)
                    """), {
                        "folio": int(folio_generado),
                        "numero_vigente": equipo_inicial,
                        "tipo_servicio": "Entrega en obra",
                        "fecha_servicio": fecha_inicio,
                        "horometro": horometro
                    })
                    # Actualizar el estado del equipo a "En arriendo" (estado 2)
                    conn.execute(text("""UPDATE equipos
                        SET estado = 2
                        WHERE numero_vigente = :numero_vigente
                    """), {
                        "numero_vigente": equipo_inicial
                    })
                st.success(f"✅ Contrato agregado exitosamente con folio {folio_generado} y registro inicial en historial de contrato.")

    elif opcion == "Editar o Eliminar Contrato":
        st.subheader("Editar o Eliminar Contrato")
        df_contratos = cargar_contratos()
        df_clientes = cargar_clientes()
        df_equipos = cargar_equipos()
        df_historial = cargar_historial_contrato()

        folio_seleccionado = st.selectbox("Seleccione el folio del contrato a modificar", df_contratos["folio"].unique())
        contrato_seleccionado = df_contratos[df_contratos["folio"] == folio_seleccionado].iloc[0]
        historial_inicial = obtener_historial_inicial(folio_seleccionado)


        with st.form("form_editar_contrato"):
            folio = st.text_input("Folio del contrato", value=str(contrato_seleccionado["folio"]))
            if folio != str(contrato_seleccionado["folio"]) and folio in df_contratos["folio"].astype(str).values:
                st.error("El folio ya existe.")

            rut_empresa = st.selectbox("Seleccione el RUT de la empresa", df_clientes["rut_empresa"].unique(), index=df_clientes["rut_empresa"].tolist().index(contrato_seleccionado["rut_empresa"]))
            cliente_seleccionado = df_clientes[df_clientes["rut_empresa"] == rut_empresa].iloc[0]
            st.write(f"Nombre de la empresa: {cliente_seleccionado['nombre_empresa']}")
            st.write(f"Rut del representante: {cliente_seleccionado['rut_representante']}")
            st.write(f"Nombre del representante: {cliente_seleccionado['nombre_representante']}")
            st.write(f"Obra: {cliente_seleccionado['obra']}")
            precio_nuevo = st.number_input("Precio mensual", value=contrato_seleccionado["precio_mensual"], min_value=0, step=1000)
            horas_contratadas = st.number_input("Horas contratadas", value=contrato_seleccionado["horas_contrtadas"], min_value=0, step=1)
            precio_envio = st.number_input("Precio de envío", value=contrato_seleccionado["precio_envio"], min_value=0, step=1000)
            fecha_inicio = st.date_input("Fecha de inicio del contrato", value=contrato_seleccionado["fecha_inicio_contrato"])
            indefinido = st.checkbox("Contrato a plazo indefinido", value=contrato_seleccionado["fecha_termino_contrato"] == pd.to_datetime("2099-12-31"))
            if indefinido:
                fecha_termino = pd.to_datetime("2099-12-31")
            else:
                fecha_termino = st.date_input("Fecha de término del contrato", value=contrato_seleccionado["fecha_termino_contrato"])
            egreso_arriendo = st.number_input("Egreso de arriendo acumulado", value=contrato_seleccionado["egreso_arriendo"], min_value=0, step=1000)
            
            # Equipos disponibles para edición: los disponibles o el que ya tiene el contrato
            equipo_actual = historial_inicial["numero_vigente"].iloc[0] if not historial_inicial.empty else None
            # Solo mostrar equipos disponibles o el actual (si existe)
            equipos_disponibles = df_equipos[df_equipos["estado"] == 1]["numero_vigente"].tolist()
            disponibles= equipos_disponibles + [equipo_actual] if equipo_actual else equipos_disponibles
            equipo_inicial = st.selectbox("Seleccione el equipo con el que inicia el contrato",
                                           options=disponibles,
                                           index=disponibles.index(equipo_actual) if equipo_actual in disponibles else 0)
            horometro = st.number_input("Horómetro inicial (horas)", value=historial_inicial["horometro"].iloc[0] if not historial_inicial.empty else 0, min_value=0, step=1)

            submit_button = st.form_submit_button("Guardar Cambios")
            eliminar_button = st.form_submit_button("Eliminar Contrato")
            confirmacion = st.checkbox("CONFIRMAR ELIMINACIÓN")
            if submit_button:
                if not folio or not rut_empresa:
                    st.error("El folio y el RUT de la empresa son obligatorios.")
                elif folio != str(contrato_seleccionado["folio"]) and folio in df_contratos["folio"].astype(str).values:
                    st.error("El folio ya existe. Por favor, ingrese uno diferente.")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE contrato
                            SET folio = :folio, rut_empresa = :rut_empresa, precio_mensual = :precio_mensual, 
                                horas_contrtadas = :horas_contratadas, fecha_inicio_contrato = :fecha_inicio_contrato, 
                                fecha_termino_contrato = :fecha_termino_contrato, egreso_arriendo = :egreso_arriendo, 
                                precio_envio = :precio_envio
                            WHERE folio = :folio_seleccionado
                        """), {
                            "folio": int(folio),
                            "rut_empresa": rut_empresa,
                            "precio_mensual": precio_nuevo,
                            "horas_contratadas": horas_contratadas,
                            "fecha_inicio_contrato": fecha_inicio,
                            "fecha_termino_contrato": fecha_termino,
                            "egreso_arriendo": egreso_arriendo,
                            "precio_envio": precio_envio,
                            "folio_seleccionado": folio_seleccionado
                        })
                        # Actualizar historial inicial (no crear uno nuevo)
                        if not historial_inicial.empty:
                            id_historial = int(historial_inicial["id_historial"].iloc[0])
                            conn.execute(text("""
                                UPDATE historial_contrato
                                SET folio = :folio, numero_vigente = :numero_vigente, fecha_servicio = :fecha_servicio, horometro = :horometro
                                WHERE id_historial = :id_historial
                            """), {
                                "folio": int(folio),
                                "numero_vigente": equipo_inicial,
                                "fecha_servicio": fecha_inicio,
                                "horometro": horometro,
                                "id_historial": id_historial
                            })
                        #actualizar el estado del equipo a "En arriendo" (estado 2)
                        conn.execute(text("""update equipos
                            set estado = 2
                            where numero_vigente = :numero_vigente
                        """), {
                            "numero_vigente": equipo_inicial
                        })
                        #actualizar equipo anterior a "Disponible" (estado 1)
                        if equipo_actual and equipo_actual != equipo_inicial:
                            conn.execute(text("""
                                UPDATE equipos
                                SET estado = 1
                                WHERE numero_vigente = :numero_vigente
                            """), {
                                "numero_vigente": equipo_actual
                            })
                    st.success("✅ Contrato actualizado exitosamente.")
            if eliminar_button:
                if confirmacion:
                    with engine.begin() as conn:
                        # Eliminar el contrato y su historial
                        conn.execute(text("""
                            DELETE FROM contrato WHERE folio = :folio_seleccionado
                        """), {
                            "folio_seleccionado": folio_seleccionado
                        })
                        conn.execute(text("""
                            DELETE FROM historial_contrato WHERE folio = :folio_seleccionado
                        """), {
                            "folio_seleccionado": folio_seleccionado
                        })
                        # Actualizar el estado del equipo a "Disponible" (estado 1)
                        conn.execute(text("""
                            UPDATE equipos SET estado = 1 WHERE numero_vigente = :numero_vigente
                        """), {
                            "numero_vigente": equipo_inicial
                        })
                    st.warning("✅ Contrato eliminado exitosamente.")
                else:
                    st.error("Para eliminar el contrato, debe confirmar la eliminación marcando la casilla.")


elif menu == "Historial de Contratos":
    st.title("Historial de Contratos")
    df_historial = cargar_historial_contrato()
    
    