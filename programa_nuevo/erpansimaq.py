import streamlit as st
import pandas as pd
import plotly.express as px
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
    df = pd.read_sql("SELECT * FROM contrato", engine)
    return df

def cargar_cobros():
    df = pd.read_sql("SELECT * FROM cobros", engine)
    return df

def cargar_historial_contrato():
    df = pd.read_sql("SELECT * FROM historial_contrato", engine)
    return df



menu = st.sidebar.radio("Menú", [
    "Inicio",
    "Equipos",
    "Contratos",
    "Historial de Contratos",
    "Historial de Cobros"
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

        if busqueda:
            df_equipos = df_equipos[
                df_equipos["nombre_modelo"].str.contains(busqueda, case=False, na=False) |
                df_equipos["numero_vigente"].str.contains(busqueda, case=False, na=False)
            ]
        if estado_sel is not None:
            df_equipos = df_equipos[df_equipos["estado"].isin(estado_sel)]

        st.dataframe(df_equipos)
    
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




