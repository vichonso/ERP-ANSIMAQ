import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from sqlalchemy import create_engine


# =============================
# Configuración del tema de Streamlit
# =============================
st.set_page_config(
    page_title="ERP Ansimaq",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown(
    """
    <style>
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(120deg, #046205 0%, #4cbd49 100%);
        color: #fff !important;
    }
    section[data-testid="stSidebar"] * {
        color: #fff !important;
    }
    /* Botones */
    button, .stButton>button {
        background: linear-gradient(90deg, #046205 0%, #1976d2 100%);
        color: #fff;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        padding: 0.5em 1.2em;
        transition: background 0.2s;
    }
    button:hover, .stButton>button:hover {
        background: linear-gradient(90deg, #046205 0%, #3949ab 100%);
        color: #fff;
    }
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        background: #e3e6f0;
    }
    ::-webkit-scrollbar-thumb {
        background: #b0bec5;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --- CSS mínimo solo para adaptar al ancho de pantalla ---
st.markdown("""
<style>
.stApp {
    width: 100vw !important;
    min-width: 100vw !important;
    max-width: 100vw !important;
    box-sizing: border-box;
}
</style>
""", unsafe_allow_html=True)


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
        SELECT cobros.id_cobros, cobros.id_historial, cobros.numero_vigente, cobros.folio, cobros.fecha_pago, cobros.horas_extra, cobros.costo_hora_extra, cobros.estado, cobros.cobro, cobros.egreso_equipo, cobros.mes, cobros.anio, contrato.rut_empresa, clientes.nombre_empresa
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
    st.title("💼 Dashboard Ansimaq")
    st.markdown("## 🛠️ Resumen general")

    # --- Cargar datos
    df_equipos = cargar_equipos()
    df_cobros = cargar_cobros()
    df_contratos = cargar_contratos()
    df_clientes = cargar_clientes() if 'cargar_clientes' in globals() else None

    # --- Métricas principales
    generadores_disponibles = df_equipos[df_equipos["estado"] == 1]
    total_generadores = len(generadores_disponibles)
    pagos_pendientes = df_cobros[df_cobros["estado"] == 1] if "estado" in df_cobros.columns else df_cobros
    total_pagos = len(pagos_pendientes)
    monto_total = pagos_pendientes["cobro"].sum() if "cobro" in pagos_pendientes.columns else 0
    ingresos_totales = df_cobros["cobro"].sum() if "cobro" in df_cobros.columns else 0
    egresos_totales = df_cobros["egreso_equipo"].sum() if "egreso_equipo" in df_cobros.columns else 0
    utilidad_total = ingresos_totales - egresos_totales

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔋 Equipos disponibles", total_generadores)
    col2.metric("💰 Pagos pendientes", f"{total_pagos} pagos - ${monto_total:,.0f}")
    col3.metric("📈 Ingresos totales", f"${ingresos_totales:,.0f}")
    col4.metric("📉 Utilidad neta", f"${utilidad_total:,.0f}")

    st.markdown("---")
    st.subheader("🔋 Detalle de equipos disponibles")
    if total_generadores > 0:
        df_disp = generadores_disponibles.copy()
        df_disp["estado"] = "Disponible"
        df_disp = df_disp.rename(columns={
            "numero_vigente": "Numero vigente",
            "nombre_modelo": "Nombre del modelo",
            "estado": "Estado"
        })
        st.dataframe(
            df_disp[["Numero vigente", "Nombre del modelo", "Estado"]],
            use_container_width=True
        )
    else:
        st.info("No hay generadores disponibles en este momento.")

    st.markdown("---")
    st.subheader("📄 Detalle de pagos pendientes")
    if total_pagos > 0 and all(col in pagos_pendientes.columns for col in ["folio", "cobro", "fecha_pago", "mes", "anio"]):
        df_pagos = pagos_pendientes.copy()
        # Calcular fecha de facturación (día 25 de cada mes/año)
        df_pagos["fecha_facturacion"] = pd.to_datetime({
            "year": df_pagos["anio"],
            "month": df_pagos["mes"],
            "day": 25
        }, errors="coerce")
        # Renombrar columnas para mostrar nombres amigables
        df_pagos = df_pagos.rename(columns={
            "folio": "Folio",
            "cobro": "Monto del cobro",
            "fecha_facturacion": "Fecha de facturacion",
            "fecha_pago": "Fecha en la que se pagará"
        })
        st.dataframe(
            df_pagos[["Folio", "Monto del cobro", "Fecha de facturacion", "Fecha en la que se pagará"]],
            use_container_width=True
        )
    else:
        st.success("No hay pagos pendientes. ¡Todo está al día!")

    st.markdown("---")
    st.subheader("🏆 Top Equipos por Utilidad")
    if "numero_vigente" in df_cobros.columns and "cobro" in df_cobros.columns:
        utilidad_por_equipo = df_cobros.groupby("numero_vigente").agg(
            ingreso=("cobro", "sum"),
            egreso=("egreso_equipo", "sum") if "egreso_equipo" in df_cobros.columns else (lambda x: 0),
        )
        utilidad_por_equipo["utilidad"] = utilidad_por_equipo["ingreso"] - utilidad_por_equipo["egreso"]
        # Renombrar columnas para visualización
        utilidad_por_equipo = utilidad_por_equipo.rename(columns={
            "ingreso": "Ingreso",
            "egreso": "Egreso",
            "utilidad": "Utilidad"
        })
        utilidad_por_equipo.index.name = "Numero vigente"
        utilidad_por_equipo = utilidad_por_equipo.reset_index()
        top_equipos = utilidad_por_equipo.sort_values("Utilidad", ascending=False).head(5)
        low_equipos = utilidad_por_equipo.sort_values("Utilidad", ascending=True).head(5)
        st.write("### 🔝 Equipos con mayor utilidad")
        st.dataframe(top_equipos[["Numero vigente", "Ingreso", "Egreso", "Utilidad"]])
        st.write("### 🔻 Equipos con menor utilidad")
        st.dataframe(low_equipos[["Numero vigente", "Ingreso", "Egreso", "Utilidad"]])
        st.bar_chart(utilidad_por_equipo.set_index("Numero vigente")["Utilidad"])
    else:
        st.info("No hay datos suficientes para mostrar ranking de utilidad.")

    st.markdown("---")
    st.subheader("🔍 Análisis por Equipo")
    equipos_lista = df_equipos["numero_vigente"].unique().tolist()
    equipo_sel = st.selectbox("Seleccione un equipo", equipos_lista)
    df_cobros_equipo = df_cobros[df_cobros["numero_vigente"] == equipo_sel]
    if not df_cobros_equipo.empty:
        # Asegurar que la columna 'egreso_equipo' exista
        if "egreso_equipo" not in df_cobros_equipo.columns:
            df_cobros_equipo["egreso_equipo"] = 0
        resumen_equipo = df_cobros_equipo.groupby(["anio", "mes"]).agg(
            ingreso=("cobro", "sum"),
            egreso=("egreso_equipo", "sum"),
        )
        resumen_equipo["utilidad"] = resumen_equipo["ingreso"] - resumen_equipo["egreso"]
        resumen_equipo = resumen_equipo.reset_index()
        # Renombrar columnas
        resumen_equipo = resumen_equipo.rename(columns={
            "anio": "Año",
            "mes": "Mes",
            "ingreso": "Ingreso",
            "egreso": "Egreso",
            "utilidad": "Utilidad"
        })
        st.write("#### Resumen mensual")
        st.dataframe(resumen_equipo[["Año", "Mes", "Ingreso", "Egreso", "Utilidad"]])
        # Crear columna para eje X: 'Año-Mes'
        resumen_equipo["Año-Mes"] = resumen_equipo["Año"].astype(str) + "-" + resumen_equipo["Mes"].astype(str).str.zfill(2)
        resumen_equipo = resumen_equipo.set_index("Año-Mes")
        st.line_chart(resumen_equipo[["Ingreso", "Egreso", "Utilidad"]])
        st.write(f"**Total Ingreso:** ${resumen_equipo['Ingreso'].sum():,.0f}")
        st.write(f"**Total Egreso:** ${resumen_equipo['Egreso'].sum():,.0f}")
        st.write(f"**Utilidad Total:** ${resumen_equipo['Utilidad'].sum():,.0f}")
    else:
        st.info("No hay cobros registrados para este equipo.")

    st.markdown("---")
    st.subheader("📑 Análisis por Contrato")
    # Filtro de vigencia antes de seleccionar folio
    hoy = pd.Timestamp.today().date()
    # Convertir columnas a tipo fecha si no lo son y comparar como date
    if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_inicio_contrato"]):
        df_contratos["fecha_inicio_contrato"] = pd.to_datetime(df_contratos["fecha_inicio_contrato"], errors="coerce")
    if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_termino_contrato"]):
        df_contratos["fecha_termino_contrato"] = pd.to_datetime(df_contratos["fecha_termino_contrato"], errors="coerce")
    df_contratos["vigente"] = (
        df_contratos["fecha_inicio_contrato"].dt.date <= hoy
    ) & (
        df_contratos["fecha_termino_contrato"].dt.date >= hoy
    )
    filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes"], horizontal=True)
    if filtro_vigencia == "Vigentes":
        folios_filtrados = df_contratos[df_contratos["vigente"]]["folio"].tolist()
    else:
        folios_filtrados = df_contratos[~df_contratos["vigente"]]["folio"].tolist()
    if folios_filtrados:
        contrato_sel = st.selectbox("Seleccione un contrato", folios_filtrados)
        df_cobros_contrato = df_cobros[df_cobros["folio"] == contrato_sel]
        if not df_cobros_contrato.empty:
            # Asegurar que la columna 'egreso_equipo' exista
            if "egreso_equipo" not in df_cobros_contrato.columns:
                df_cobros_contrato["egreso_equipo"] = 0
            resumen_contrato = df_cobros_contrato.groupby(["anio", "mes"]).agg(
                ingreso=("cobro", "sum"),
                egreso=("egreso_equipo", "sum"),
            )
            resumen_contrato["utilidad"] = resumen_contrato["ingreso"] - resumen_contrato["egreso"]
            resumen_contrato = resumen_contrato.reset_index()
            # Renombrar columnas
            resumen_contrato = resumen_contrato.rename(columns={
                "anio": "Año",
                "mes": "Mes",
                "ingreso": "Ingreso",
                "egreso": "Egreso",
                "utilidad": "Utilidad"
            })
            st.write("#### Resumen mensual")
            st.dataframe(resumen_contrato[["Año", "Mes", "Ingreso", "Egreso", "Utilidad"]])
            # Crear columna para eje X: 'Año-Mes'
            resumen_contrato["Año-Mes"] = resumen_contrato["Año"].astype(str) + "-" + resumen_contrato["Mes"].astype(str).str.zfill(2)
            resumen_contrato = resumen_contrato.set_index("Año-Mes")
            st.line_chart(resumen_contrato[["Ingreso", "Egreso", "Utilidad"]])
            st.write(f"**Total Ingreso:** ${resumen_contrato['Ingreso'].sum():,.0f}")
            st.write(f"**Total Egreso:** ${resumen_contrato['Egreso'].sum():,.0f}")
            st.write(f"**Utilidad Total:** ${resumen_contrato['Utilidad'].sum():,.0f}")
        else:
            st.info("No hay cobros registrados para este contrato.")
    else:
        st.info("No hay contratos para el filtro seleccionado.")

    st.markdown("---")
    st.subheader("📊 Tendencia global de ingresos y egresos")
    if "anio" in df_cobros.columns and "mes" in df_cobros.columns:
        # Asegurar que la columna 'egreso_equipo' exista
        if "egreso_equipo" not in df_cobros.columns:
            df_cobros["egreso_equipo"] = 0
        tendencia = df_cobros.groupby(["anio", "mes"]).agg(
            ingreso=("cobro", "sum"),
            egreso=("egreso_equipo", "sum"),
        )
        tendencia["utilidad"] = tendencia["ingreso"] - tendencia["egreso"]
        tendencia = tendencia.reset_index()
        # Renombrar columnas
        tendencia = tendencia.rename(columns={
            "anio": "Año",
            "mes": "Mes",
            "ingreso": "Ingreso",
            "egreso": "Egreso",
            "utilidad": "Utilidad"
        })
        # Crear columna para eje X: 'Año-Mes'
        tendencia["Año-Mes"] = tendencia["Año"].astype(str) + "-" + tendencia["Mes"].astype(str).str.zfill(2)
        tendencia = tendencia.set_index("Año-Mes")
        st.line_chart(tendencia[["Ingreso", "Egreso", "Utilidad"]])
    else:
        st.info("No hay datos de fechas para mostrar tendencia.")

    st.markdown("---")
    st.subheader("🚨 Alertas y sugerencias")
    equipos_sin_contrato = set(df_equipos["numero_vigente"]) - set(df_cobros["numero_vigente"])
    if equipos_sin_contrato:
        st.warning(f"Equipos sin contrato: {', '.join(map(str, equipos_sin_contrato))}")
    contratos_por_vencer = df_contratos[df_contratos["fecha_termino_contrato"] < pd.Timestamp.today() + pd.Timedelta(days=30)]
    if not contratos_por_vencer.empty:
        st.warning(f"Contratos por vencer en los próximos 30 días: {len(contratos_por_vencer)}")
    # Corregir comparación de fechas: asegurar que 'fecha_pago' sea datetime
    if "estado" in df_cobros.columns and "fecha_pago" in df_cobros.columns:
        df_cobros["fecha_pago"] = pd.to_datetime(df_cobros["fecha_pago"], errors="coerce")
        pagos_atrasados = df_cobros[(df_cobros["estado"] == 1) & (df_cobros["fecha_pago"] < pd.Timestamp.today())]
    else:
        pagos_atrasados = None
    if pagos_atrasados is not None and not pagos_atrasados.empty:
        st.error(f"Pagos atrasados: {len(pagos_atrasados)}")

    # Ranking de clientes por ingresos generados
    st.markdown("---")
    st.subheader("👥 Ranking de clientes por ingresos generados")
    if (
        df_clientes is not None and
        "folio" in df_cobros.columns and
        "folio" in df_contratos.columns and
        "rut_empresa" in df_contratos.columns and
        "nombre_empresa" in df_clientes.columns and
        "cobro" in df_cobros.columns
    ):
        # Sumar ingresos y egresos por folio (contrato)
        resumen_folio = df_cobros.groupby("folio").agg(
            ingresos=("cobro", "sum"),
            egresos=("egreso_equipo", "sum") if "egreso_equipo" in df_cobros.columns else (lambda x: 0),
        ).reset_index()
        # Unir con contratos para obtener rut_empresa y egreso_arriendo
        contratos_info = df_contratos[["folio", "rut_empresa", "egreso_arriendo"]].copy()
        resumen_folio = resumen_folio.merge(contratos_info, on="folio", how="left")
        # Sumar egreso_arriendo al egreso total de cada folio
        resumen_folio["egresos_totales"] = resumen_folio["egresos"] + resumen_folio["egreso_arriendo"].fillna(0)
        # Agrupar por cliente (rut_empresa)
        resumen_cliente = resumen_folio.groupby("rut_empresa").agg(
            ingreso_total=("ingresos", "sum"),
            egreso_total=("egresos_totales", "sum")
        ).reset_index()
        resumen_cliente["utilidad_total"] = resumen_cliente["ingreso_total"] - resumen_cliente["egreso_total"]
        # Unir con clientes para obtener nombre_empresa
        resumen_cliente = resumen_cliente.merge(df_clientes[["rut_empresa", "nombre_empresa"]], on="rut_empresa", how="left")
        resumen_cliente = resumen_cliente[["nombre_empresa", "ingreso_total", "egreso_total", "utilidad_total"]]
        resumen_cliente = resumen_cliente.rename(columns={
            "nombre_empresa": "Nombre de empresa",
            "ingreso_total": "Ingreso total",
            "egreso_total": "Egreso total",
            "utilidad_total": "Utilidad total"
        })
        resumen_cliente = resumen_cliente.sort_values("Ingreso total", ascending=False)
        st.dataframe(resumen_cliente)
        # Comentario sobre egreso_arriendo:
        st.caption("Nota: El campo 'egreso_arriendo' en la tabla contratos representa el egreso acumulado asociado a cada contrato y se suma al egreso total del cliente.")
    else:
        st.info("No hay datos suficientes para mostrar ranking de clientes.")

    # Puedes agregar más secciones según tus necesidades


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
        else:
            pass # Si no hay columna de estado, no hacer nada

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
        # Renombrar columnas para visualización
        df_filtrado = df_filtrado.rename(columns={
            "numero_vigente": "Numero vigente",
            "nombre_modelo": "Nombre del modelo",
            "estado": "Estado"
        })
        columnas_mostrar = [col for col in ["Numero vigente", "Nombre del modelo", "Estado"] if col in df_filtrado.columns]
        st.dataframe(df_filtrado[columnas_mostrar] if columnas_mostrar else df_filtrado)
    
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
        busqueda = st.text_input("Buscar por nombre o RUT de la empresa")
        df_filtrado = df_clientes.copy()
        if busqueda:
            df_filtrado = df_filtrado[
                df_filtrado["nombre_empresa"].str.contains(busqueda, case=False, na=False) |
                df_filtrado["rut_empresa"].str.contains(busqueda, case=False, na=False)
            ]
        # Resetear el índice para evitar errores de pandas al filtrar
        df_filtrado = df_filtrado.reset_index(drop=True)
        # Renombrar columnas para visualización
        df_filtrado = df_filtrado.rename(columns={
            "rut_empresa": "Rut de la empresa",
            "nombre_empresa": "Nombre de la empresa",
            "obra": "Obra",
            "nombre_representante": "Nombre del representante",
            "rut_representante": "Rut del representante",
            "correo": "Correo",
            "telefono": "Telefono"
        })
        columnas_mostrar = [
            "Rut de la empresa",
            "Nombre de la empresa",
            "Obra",
            "Nombre del representante",
            "Rut del representante",
            "Correo",
            "Telefono"
        ]
        columnas_mostrar = [col for col in columnas_mostrar if col in df_filtrado.columns]
        st.dataframe(df_filtrado[columnas_mostrar] if columnas_mostrar else df_filtrado)
    
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
        if not df_clientes.empty:
            rut_seleccionado = st.selectbox("Seleccione el RUT del cliente a modificar", df_clientes["rut_empresa"].unique())
            cliente_filtrado = df_clientes[df_clientes["rut_empresa"] == rut_seleccionado]
            if not cliente_filtrado.empty:
                g = cliente_filtrado.iloc[0]
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
            else:
                st.warning("No se encontró el cliente seleccionado.")
        else:
            st.info("No hay clientes registrados.")


elif menu == "Contratos":
    st.title("Contratos")
    opcion = st.radio("Seleccione una opción", ["Ver Contratos", "Agregar Contrato", "Editar o Eliminar Contrato"])

    if opcion == "Ver Contratos":
        st.subheader("Lista de Contratos")
        df_contratos = cargar_contratos()
        # Filtro de vigencia
        hoy = pd.Timestamp.today().date()
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_inicio_contrato"]):
            df_contratos["fecha_inicio_contrato"] = pd.to_datetime(df_contratos["fecha_inicio_contrato"], errors="coerce")
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_termino_contrato"]):
            df_contratos["fecha_termino_contrato"] = pd.to_datetime(df_contratos["fecha_termino_contrato"], errors="coerce")
        df_contratos["vigente"] = (
            df_contratos["fecha_inicio_contrato"].dt.date <= hoy
        ) & (
            df_contratos["fecha_termino_contrato"].dt.date >= hoy
        )
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes", "Todos"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            df_contratos_filtrados = df_contratos[df_contratos["vigente"]]
        elif filtro_vigencia == "No vigentes":
            df_contratos_filtrados = df_contratos[~df_contratos["vigente"]]
        else:
            df_contratos_filtrados = df_contratos
        busqueda = st.text_input(label="Nombre de empresa o RUT, Nombre del representante")
        if busqueda:
            df_contratos_filtrados = df_contratos_filtrados[
                df_contratos_filtrados["rut_empresa"].str.contains(busqueda, case=False, na=False) |
                df_contratos_filtrados["nombre_representante"].str.contains(busqueda, case=False, na=False) |
                df_contratos_filtrados["nombre_empresa"].str.contains(busqueda, case=False, na=False) |
                df_contratos_filtrados["rut_representante"].str.contains(busqueda, case=False, na=False)
            ]
        # Renombrar columnas para visualización
        df_contratos_filtrados = df_contratos_filtrados.rename(columns={
            "folio": "Folio",
            "rut_empresa": "Rut de la empresa",
            "precio_mensual": "Precio mensual",
            "horas_contrtadas": "Horas contratadas",
            "fecha_inicio_contrato": "Fecha de inicio",
            "fecha_termino_contrato": "Fecha de termino",
            "egreso_arriendo": "Egreso del arriendo",
            "precio_envio": "Precio de instalación",
            "nombre_empresa": "Nombre de la empresa",
            "nombre_representante": "Nombre del representante",
            "rut_representante": "Rut del representante",
            "obra": "Obra",
            "correo": "Correo",
            "telefono": "Telefono",
            "vigente": "Vigencia"
        })
        columnas_mostrar = [
            "Folio",
            "Rut de la empresa",
            "Precio mensual",
            "Horas contratadas",
            "Fecha de inicio",
            "Fecha de termino",
            "Egreso del arriendo",
            "Precio de instalación",
            "Nombre de la empresa",
            "Nombre del representante",
            "Rut del representante",
            "Obra",
            "Correo",
            "Telefono",
            "Vigencia"
        ]
        columnas_mostrar = [col for col in columnas_mostrar if col in df_contratos_filtrados.columns]
        st.dataframe(df_contratos_filtrados[columnas_mostrar] if columnas_mostrar else df_contratos_filtrados)

    elif opcion == "Agregar Contrato":
        st.subheader("Agregar Nuevo Contrato")
        df_contratos = cargar_contratos()
        df_clientes = cargar_clientes()
        df_equipos = cargar_equipos()

        # Solo equipos disponibles (estado == 1)
        equipos_disponibles = df_equipos[df_equipos["estado"] == 1]["numero_vigente"].tolist()
        rut_empresa = st.selectbox("Seleccione el RUT de la empresa", df_clientes["rut_empresa"].unique())
        cliente_seleccionado = df_clientes[df_clientes["rut_empresa"] == rut_empresa].iloc[0]
        st.write(f"Nombre de la empresa: {cliente_seleccionado['nombre_empresa']}")
        st.write(f"Rut del representante: {cliente_seleccionado['rut_representante']}")
        st.write(f"Nombre del representante: {cliente_seleccionado['nombre_representante']}")

        with st.form("form_agregar_contrato"):
            
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
        # Filtro de vigencia antes de seleccionar folio
        hoy = pd.Timestamp.today().date()
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_inicio_contrato"]):
            df_contratos["fecha_inicio_contrato"] = pd.to_datetime(df_contratos["fecha_inicio_contrato"], errors="coerce")
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_termino_contrato"]):
            df_contratos["fecha_termino_contrato"] = pd.to_datetime(df_contratos["fecha_termino_contrato"], errors="coerce")
        df_contratos["vigente"] = (
            df_contratos["fecha_inicio_contrato"].dt.date <= hoy
        ) & (
            df_contratos["fecha_termino_contrato"].dt.date >= hoy
        )
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes", "Todos"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            df_contratos_filtrados = df_contratos[df_contratos["vigente"]]
        elif filtro_vigencia == "No vigentes":
            df_contratos_filtrados = df_contratos[~df_contratos["vigente"]]
        else:
            df_contratos_filtrados = df_contratos
        folios_disponibles = df_contratos_filtrados["folio"].unique()
        if len(folios_disponibles) == 0:
            st.info("No hay contratos para el filtro seleccionado.")
        else:
            folio_seleccionado = st.selectbox("Seleccione el folio del contrato a modificar", folios_disponibles)
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
                            if int(folio) != int(folio_seleccionado):
                                # 1. Insertar nuevo contrato con el nuevo folio y datos actualizados
                                conn.execute(text("""
                                    INSERT INTO contrato (folio, rut_empresa, precio_mensual, horas_contrtadas, fecha_inicio_contrato, fecha_termino_contrato, egreso_arriendo, precio_envio)
                                    VALUES (:folio, :rut_empresa, :precio_mensual, :horas_contratadas, :fecha_inicio_contrato, :fecha_termino_contrato, :egreso_arriendo, :precio_envio)
                                """), {
                                    "folio": int(folio),
                                    "rut_empresa": rut_empresa,
                                    "precio_mensual": precio_nuevo,
                                    "horas_contratadas": horas_contratadas,
                                    "fecha_inicio_contrato": fecha_inicio,
                                    "fecha_termino_contrato": fecha_termino,
                                    "egreso_arriendo": egreso_arriendo,
                                    "precio_envio": precio_envio
                                })
                                # 2. Actualizar historial_contrato
                                conn.execute(text("""
                                    UPDATE historial_contrato
                                    SET folio = :nuevo_folio
                                    WHERE folio = :folio_seleccionado
                                """), {
                                    "nuevo_folio": int(folio),
                                    "folio_seleccionado": folio_seleccionado
                                })
                                # 3. Actualizar cobros si existe la columna folio
                                try:
                                    conn.execute(text("""
                                        UPDATE cobros
                                        SET folio = :nuevo_folio
                                        WHERE folio = :folio_seleccionado
                                    """), {
                                        "nuevo_folio": int(folio),
                                        "folio_seleccionado": folio_seleccionado
                                    })
                                except Exception:
                                    pass
                                # 4. Eliminar el contrato antiguo
                                conn.execute(text("""
                                    DELETE FROM contrato WHERE folio = :folio_seleccionado
                                """), {
                                    "folio_seleccionado": folio_seleccionado
                                })
                                folio_seleccionado = int(folio)
                            else:
                                # Solo actualizar los campos si el folio no cambia
                                conn.execute(text("""
                                    UPDATE contrato
                                    SET rut_empresa = :rut_empresa, precio_mensual = :precio_mensual, 
                                        horas_contrtadas = :horas_contratadas, fecha_inicio_contrato = :fecha_inicio_contrato, 
                                        fecha_termino_contrato = :fecha_termino_contrato, egreso_arriendo = :egreso_arriendo, 
                                        precio_envio = :precio_envio
                                    WHERE folio = :folio_seleccionado
                                """), {
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
    opcion = st.radio("Seleccione una opción", ["Ver Historial", "Agregar Registro al Historial", "Editar o Eliminar Registro del Historial"])

    if opcion == "Ver Historial":
        st.subheader("Historial de Contratos")
        df_historial = cargar_historial_contrato()
        df_contratos = cargar_contratos()
        df_clientes = cargar_clientes() if 'cargar_clientes' in globals() else None
        # Eliminar columnas duplicadas conservando la primera aparición
        df_historial = df_historial.loc[:, ~df_historial.columns.duplicated()]
        # Filtro de vigencia antes de seleccionar folio
        hoy = pd.Timestamp.today().date()
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_inicio_contrato"]):
            df_contratos["fecha_inicio_contrato"] = pd.to_datetime(df_contratos["fecha_inicio_contrato"], errors="coerce")
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_termino_contrato"]):
            df_contratos["fecha_termino_contrato"] = pd.to_datetime(df_contratos["fecha_termino_contrato"], errors="coerce")
        df_contratos["vigente"] = (
            df_contratos["fecha_inicio_contrato"].dt.date <= hoy
        ) & (
            df_contratos["fecha_termino_contrato"].dt.date >= hoy
        )
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes", "Todos"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            folios_filtrados = df_contratos[df_contratos["vigente"]]["folio"].tolist()
        elif filtro_vigencia == "No vigentes":
            folios_filtrados = df_contratos[~df_contratos["vigente"]]["folio"].tolist()
        else:
            folios_filtrados = df_contratos["folio"].tolist()
        # Obtener todos los folios únicos de contratos presentes en el historial y filtrados por vigencia
        if "folio" in df_historial.columns and not df_historial.empty:
            folio_col = df_historial["folio"]
            if isinstance(folio_col, pd.DataFrame):
                folio_col = folio_col.iloc[:, 0]
            folios_disponibles = [f for f in folio_col.drop_duplicates().tolist() if f in folios_filtrados]
        else:
            folios_disponibles = []
        if folios_disponibles:
            folio_seleccionado = st.selectbox("Seleccione el folio de contrato para ver sus servicios", folios_disponibles)
            # Filtrar todos los servicios asociados a ese folio
            servicios_folio = df_historial[df_historial["folio"] == folio_seleccionado].reset_index(drop=True)
            # Asegurar que 'rut_empresa' esté en servicios_folio
            if "rut_empresa" not in servicios_folio.columns:
                contratos_folio = df_contratos[df_contratos["folio"] == folio_seleccionado][["folio", "rut_empresa"]]
                servicios_folio = servicios_folio.merge(contratos_folio, on="folio", how="left")
            # Unir con clientes para obtener nombre_empresa
            if df_clientes is not None and "rut_empresa" in servicios_folio.columns:
                servicios_folio = servicios_folio.merge(df_clientes[["rut_empresa", "nombre_empresa"]], on="rut_empresa", how="left")
            # Asegurar que egreso_equipo esté presente, uniendo con cobros si es necesario
            if "egreso_equipo" not in servicios_folio.columns:
                try:
                    df_cobros = cargar_cobros()
                    servicios_folio = servicios_folio.merge(
                        df_cobros[["id_historial", "egreso_equipo"]],
                        left_on="id_historial", right_on="id_historial", how="left"
                    )
                except Exception:
                    servicios_folio["egreso_equipo"] = None
            rename_dict = {
                "id_historial": "ID del historial",
                "folio": "Folio",
                "numero_vigente": "Numero vigente",
                "tipo_servicio": "Tipo de servicio",
                "fecha_servicio": "Fecha del servicio",
                "horometro": "Horometro",
                "rut_empresa": "Rut de la empresa",
                "nombre_empresa": "Nombre de la empresa",
                "egreso_equipo": "Egreso del equipo"
            }
            servicios_folio = servicios_folio.rename(columns=rename_dict)
            columnas_mostrar = [
                "ID del historial",
                "Folio",
                "Numero vigente",
                "Tipo de servicio",
                "Fecha del servicio",
                "Horometro",
                "Egreso del equipo",
                "Rut de la empresa",
                "Nombre de la empresa"
            ]
            columnas_mostrar = [col for col in columnas_mostrar if col in servicios_folio.columns]
            if not servicios_folio.empty:
                st.dataframe(servicios_folio[columnas_mostrar], use_container_width=True)
            else:
                st.warning("No hay servicios registrados para este folio de contrato.")
        else:
            st.info("No hay historial de contratos registrado para el filtro seleccionado.")

    elif opcion == "Agregar Registro al Historial":
        st.subheader("Agregar Registro al Historial de Contrato")
        df_contratos = cargar_contratos()
        df_equipos = cargar_equipos()
        df_historial = cargar_historial_contrato()

        # Filtro de vigencia antes de seleccionar folio
        hoy = pd.Timestamp.today().date()
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_inicio_contrato"]):
            df_contratos["fecha_inicio_contrato"] = pd.to_datetime(df_contratos["fecha_inicio_contrato"], errors="coerce")
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_termino_contrato"]):
            df_contratos["fecha_termino_contrato"] = pd.to_datetime(df_contratos["fecha_termino_contrato"], errors="coerce")
        df_contratos["vigente"] = (
            df_contratos["fecha_inicio_contrato"].dt.date <= hoy
        ) & (
            df_contratos["fecha_termino_contrato"].dt.date >= hoy
        )
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes", "Todos"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            df_contratos_filtrados = df_contratos[df_contratos["vigente"]]
        elif filtro_vigencia == "No vigentes":
            df_contratos_filtrados = df_contratos[~df_contratos["vigente"]]
        else:
            df_contratos_filtrados = df_contratos
        if "folio" in df_contratos_filtrados.columns and not df_contratos_filtrados.empty:
            folios_disponibles = df_contratos_filtrados["folio"].astype(str).tolist()
        else:
            folios_disponibles = []
        if folios_disponibles:
            folio_seleccionado = st.selectbox("Seleccione el folio de contrato al que desea agregar un registro", folios_disponibles)
            contrato_seleccionado = df_contratos[df_contratos["folio"] == int(folio_seleccionado)].iloc[0]
            st.write(f"Contrato seleccionado: Folio {contrato_seleccionado['folio']}, Empresa: {contrato_seleccionado['rut_empresa']}")

            # Eliminar columnas duplicadas antes de filtrar para evitar errores de pandas
            df_historial = df_historial.loc[:, ~df_historial.columns.duplicated()]

            # Obtener el equipo actualmente asignado al contrato (último en historial para ese folio)
            historial_folio = df_historial[df_historial["folio"] == int(folio_seleccionado)]
            if not historial_folio.empty:
                equipo_actual = historial_folio.sort_values("id_historial").iloc[-1]["numero_vigente"]
            else:
                equipo_actual = None
            # Equipos disponibles (estado == 1)
            equipos_disponibles = df_equipos[df_equipos["estado"] == 1]["numero_vigente"].tolist()
            # Incluir el equipo actual si no está en la lista
            if equipo_actual and equipo_actual not in equipos_disponibles:
                equipos_disponibles.append(equipo_actual)

            with st.form("form_agregar_historial"):
                numero_vigente = st.selectbox("Seleccione el número vigente del equipo", equipos_disponibles, index=equipos_disponibles.index(equipo_actual) if equipo_actual in equipos_disponibles else 0)
                tipo_servicio = st.selectbox("Seleccione el tipo de servicio", ["Mantenimiento", "Reparación", "Inspección", "Cambio del equipo", "Entrega en obra", "Otro"])
                fecha_servicio = st.date_input("Fecha del servicio")
                horometro = st.number_input("Horómetro al momento del servicio", min_value=0, step=1, value=0)

                st.text("Si el tipo de servicio es Mantenimiento o Reparación, se agregará el costo del servicio.")
                egreso_equipo = st.number_input("Costo del servicio (egreso)", min_value=0, step=1000, value=0)

                submit_button = st.form_submit_button("Agregar Registro al Historial")

                if submit_button:
                    # Si el horómetro no se llena, se pone 0
                    if horometro is None:
                        horometro = 0
                    from datetime import datetime
                    with engine.begin() as conn:
                        # Insertar en historial_contrato
                        result = conn.execute(text("""
                            INSERT INTO historial_contrato (folio, numero_vigente, tipo_servicio, fecha_servicio, horometro)
                            VALUES (:folio, :numero_vigente, :tipo_servicio, :fecha_servicio, :horometro)
                            RETURNING id_historial
                        """), {
                            "folio": int(folio_seleccionado),
                            "numero_vigente": numero_vigente,
                            "tipo_servicio": tipo_servicio,
                            "fecha_servicio": fecha_servicio,
                            "horometro": horometro
                        })
                        id_historial = result.fetchone()[0]

                        # Si es mantención o reparación, crear cobro asociado y sumar egreso_equipo a egreso_arriendo
                        if tipo_servicio in ["Mantenimiento", "Reparación"]:
                            estado = 2  # Pagado
                            fecha_pago = fecha_servicio
                            mes = fecha_pago.month if hasattr(fecha_pago, 'month') else pd.to_datetime(fecha_pago).month
                            anio = fecha_pago.year if hasattr(fecha_pago, 'year') else pd.to_datetime(fecha_pago).year
                            # Sumar egreso_equipo a egreso_arriendo del contrato
                            conn.execute(text("""
                                UPDATE contrato SET egreso_arriendo = egreso_arriendo + :egreso_equipo WHERE folio = :folio
                            """), {
                                "egreso_equipo": egreso_equipo,
                                "folio": int(folio_seleccionado)
                            })
                            conn.execute(text("""
                                INSERT INTO cobros (id_historial, numero_vigente, folio, fecha_pago, egreso_equipo, estado, mes, anio)
                                VALUES (:id_historial, :numero_vigente, :folio, :fecha_pago, :egreso_equipo, :estado, :mes, :anio)
                            """), {
                                "id_historial": id_historial,
                                "numero_vigente": numero_vigente,
                                "folio": int(folio_seleccionado),
                                "fecha_pago": fecha_pago,
                                "egreso_equipo": egreso_equipo,
                                "estado": estado,
                                "mes": mes,
                                "anio": anio
                            })
                        # Actualizar el estado del equipo a "En arriendo" (estado 2)
                        conn.execute(text("""UPDATE equipos
                            SET estado = 2
                            WHERE numero_vigente = :numero_vigente
                        """), {
                            "numero_vigente": numero_vigente
                        })
                        #actualizar el estado del equipo anterior a "Disponible" (estado 1)
                        if equipo_actual and equipo_actual != numero_vigente:
                            conn.execute(text("""
                                UPDATE equipos
                                SET estado = 1
                                WHERE numero_vigente = :numero_vigente
                            """), {
                                "numero_vigente": equipo_actual
                            })
                    st.success("✅ Registro agregado al historial exitosamente.")
    
    elif opcion == "Editar o Eliminar Registro del Historial":
        st.subheader("Editar o Eliminar Registro del Historial de Contrato")
        df_historial = cargar_historial_contrato()
        df_contratos = cargar_contratos()
        df_equipos = cargar_equipos()

        # Filtro de vigencia antes de seleccionar folio
        hoy = pd.Timestamp.today().date()
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_inicio_contrato"]):
            df_contratos["fecha_inicio_contrato"] = pd.to_datetime(df_contratos["fecha_inicio_contrato"], errors="coerce")
        if not pd.api.types.is_datetime64_any_dtype(df_contratos["fecha_termino_contrato"]):
            df_contratos["fecha_termino_contrato"] = pd.to_datetime(df_contratos["fecha_termino_contrato"], errors="coerce")
        df_contratos["vigente"] = (
            df_contratos["fecha_inicio_contrato"].dt.date <= hoy
        ) & (
            df_contratos["fecha_termino_contrato"].dt.date >= hoy
        )
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes", "Todos"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            df_contratos_filtrados = df_contratos[df_contratos["vigente"]]
        elif filtro_vigencia == "No vigentes":
            df_contratos_filtrados = df_contratos[~df_contratos["vigente"]]
        else:
            df_contratos_filtrados = df_contratos

        # Eliminar columnas duplicadas antes de cualquier filtrado para evitar errores de pandas
        df_historial = df_historial.loc[:, ~df_historial.columns.duplicated()]

        # Obtener folios disponibles según filtro de vigencia
        if "folio" in df_historial.columns and not df_historial.empty:
            folio_col = df_historial["folio"]
            if isinstance(folio_col, pd.DataFrame):
                folio_col = folio_col.iloc[:, 0]
            # Solo folios que están en los contratos filtrados
            folios_filtrados = df_contratos_filtrados["folio"].astype(str).tolist()
            folios_disponibles = [str(f) for f in folio_col.drop_duplicates().astype(str).to_list() if str(f) in folios_filtrados]
        else:
            folios_disponibles = []

        if folios_disponibles:
            folio_seleccionado = st.selectbox("Seleccione el folio del contrato para editar un registro", folios_disponibles)
            # Eliminar columnas duplicadas nuevamente por robustez antes de filtrar por folio
            df_historial = df_historial.loc[:, ~df_historial.columns.duplicated()]
            historial_folio = df_historial[df_historial["folio"] == int(folio_seleccionado)]
            # --- Igualar visualización a 'Ver Historial' ---
            df_contratos = cargar_contratos()
            df_clientes = cargar_clientes() if 'cargar_clientes' in globals() else None
            # Asegurar que 'rut_empresa' esté en historial_folio
            if "rut_empresa" not in historial_folio.columns:
                contratos_folio = df_contratos[df_contratos["folio"] == int(folio_seleccionado)][["folio", "rut_empresa"]]
                historial_folio = historial_folio.merge(contratos_folio, on="folio", how="left")
            # Unir con clientes para obtener nombre_empresa
            if df_clientes is not None and "rut_empresa" in historial_folio.columns:
                historial_folio = historial_folio.merge(df_clientes[["rut_empresa", "nombre_empresa"]], on="rut_empresa", how="left")
            # Asegurar que egreso_equipo esté presente, uniendo con cobros si es necesario
            if "egreso_equipo" not in historial_folio.columns:
                try:
                    df_cobros = cargar_cobros()
                    historial_folio = historial_folio.merge(
                        df_cobros[["id_historial", "egreso_equipo"]],
                        left_on="id_historial", right_on="id_historial", how="left"
                    )
                except Exception:
                    historial_folio["egreso_equipo"] = None
            rename_dict = {
                "id_historial": "ID del historial",
                "folio": "Folio",
                "numero_vigente": "Numero vigente",
                "tipo_servicio": "Tipo de servicio",
                "fecha_servicio": "Fecha del servicio",
                "horometro": "Horometro",
                "rut_empresa": "Rut de la empresa",
                "nombre_empresa": "Nombre de la empresa",
                "egreso_equipo": "Egreso del equipo"
            }
            historial_folio = historial_folio.rename(columns=rename_dict)
            columnas_mostrar = [
                "ID del historial",
                "Folio",
                "Numero vigente",
                "Tipo de servicio",
                "Fecha del servicio",
                "Horometro",
                "Egreso del equipo",
                "Rut de la empresa",
                "Nombre de la empresa"
            ]
            columnas_mostrar = [col for col in columnas_mostrar if col in historial_folio.columns]
            if not historial_folio.empty:
                st.info("Registros del historial para este folio:")
                st.dataframe(historial_folio[columnas_mostrar], use_container_width=True)
                id_historial_seleccionado = st.selectbox("Seleccione el ID del registro a editar", historial_folio["ID del historial"].tolist())
                registro_seleccionado = historial_folio[historial_folio["ID del historial"] == id_historial_seleccionado].iloc[0]

                # Para el selectbox de equipos, mostrar disponibles y el actual
                # Usar el nombre de columna renombrado
                equipo_actual = registro_seleccionado["Numero vigente"] if "Numero vigente" in registro_seleccionado else None
                equipos_disponibles = df_equipos[df_equipos["estado"] == 1]["numero_vigente"].tolist()
                if equipo_actual and equipo_actual not in equipos_disponibles:
                    equipos_disponibles.append(equipo_actual)

                with st.form("form_editar_historial"):
                    numero_vigente = st.selectbox("Seleccione el número vigente del equipo", equipos_disponibles, index=equipos_disponibles.index(equipo_actual) if equipo_actual in equipos_disponibles else 0)
                    tipos_servicio = ["Mantenimiento", "Reparación", "Inspección", "Cambio del equipo", "Entrega en obra", "Otro"]
                    # Usar el nombre de columna renombrado
                    valor_tipo_servicio = registro_seleccionado["Tipo de servicio"] if "Tipo de servicio" in registro_seleccionado else None
                    tipo_servicio = st.selectbox(
                        "Seleccione el tipo de servicio",
                        tipos_servicio,
                        index=tipos_servicio.index(valor_tipo_servicio) if valor_tipo_servicio in tipos_servicio else 0
                    )
                    # Usar el nombre de columna renombrado
                    valor_fecha_servicio = registro_seleccionado["Fecha del servicio"] if "Fecha del servicio" in registro_seleccionado else None
                    fecha_servicio = st.date_input("Fecha del servicio", value=valor_fecha_servicio)
                    # Usar el nombre de columna renombrado
                    valor_horometro = registro_seleccionado["Horometro"] if "Horometro" in registro_seleccionado else 0
                    horometro = st.number_input("Horómetro al momento del servicio", min_value=0, step=1, value=valor_horometro)
                    # Mostrar el costo anterior si es mantenimiento o reparación
                    # Buscar el cobro asociado a este id_historial para mostrar el valor anterior
                    egreso_anterior = 0
                    try:
                        cobro_existente = pd.read_sql(
                            text("SELECT egreso_equipo FROM cobros WHERE id_historial = :id_historial"),
                            engine,
                            params={"id_historial": id_historial_seleccionado}
                        )
                        if not cobro_existente.empty and not pd.isnull(cobro_existente["egreso_equipo"].iloc[0]):
                            egreso_anterior = int(cobro_existente["egreso_equipo"].iloc[0])
                    except Exception:
                        egreso_anterior = int(registro_seleccionado.get("egreso_equipo", 0))
                    egreso_equipo = st.number_input(
                        "Costo del servicio (egreso)",
                        min_value=0,
                        step=1000,
                        value=egreso_anterior
                    )

                    submit_button = st.form_submit_button("Guardar Cambios")
                    eliminar_button = st.form_submit_button("Eliminar Registro")
                    confirmacion = st.checkbox("CONFIRMAR ELIMINACIÓN")

                if submit_button:
                    # Actualizar historial_contrato
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE historial_contrato
                            SET numero_vigente = :numero_vigente, tipo_servicio = :tipo_servicio, fecha_servicio = :fecha_servicio, horometro = :horometro
                            WHERE id_historial = :id_historial
                        """), {
                            "numero_vigente": numero_vigente,
                            "tipo_servicio": tipo_servicio,
                            "fecha_servicio": fecha_servicio,
                            "horometro": horometro,
                            "id_historial": id_historial_seleccionado
                        })
                        # Si se cambió el equipo, marcar el nuevo como en arriendo (2) y el anterior como disponible (1)
                        if numero_vigente != equipo_actual:
                            conn.execute(text("""
                                UPDATE equipos SET estado = 2 WHERE numero_vigente = :nuevo_equipo
                            """), {"nuevo_equipo": numero_vigente})
                            conn.execute(text("""
                                UPDATE equipos SET estado = 1 WHERE numero_vigente = :antiguo_equipo
                            """), {"antiguo_equipo": equipo_actual})
                        # Si es mantención o reparación, actualizar o crear cobro
                        if tipo_servicio in ["Mantenimiento", "Reparación"]:
                            # Buscar si ya existe cobro para este id_historial
                            cobro_existente = pd.read_sql(text("SELECT * FROM cobros WHERE id_historial = :id_historial"), engine, params={"id_historial": id_historial_seleccionado})
                            estado = 2
                            fecha_pago = fecha_servicio
                            mes = fecha_pago.month if hasattr(fecha_pago, 'month') else pd.to_datetime(fecha_pago).month
                            anio = fecha_pago.year if hasattr(fecha_pago, 'year') else pd.to_datetime(fecha_pago).year
                            # Sumar egreso_equipo a egreso_arriendo del contrato
                            conn.execute(text("""
                                UPDATE contrato SET egreso_arriendo = egreso_arriendo + :egreso_equipo WHERE folio = :folio
                            """), {
                                "egreso_equipo": egreso_equipo,
                                "folio": int(folio_seleccionado)
                            })
                            if not cobro_existente.empty:
                                conn.execute(text("""
                                    UPDATE cobros SET numero_vigente = :numero_vigente, folio = :folio, fecha_pago = :fecha_pago, egreso_equipo = :egreso_equipo, estado = :estado, mes = :mes, anio = :anio
                                    WHERE id_historial = :id_historial
                                """), {
                                    "numero_vigente": numero_vigente,
                                    "folio": int(folio_seleccionado),
                                    "fecha_pago": fecha_pago,
                                    "egreso_equipo": egreso_equipo,
                                    "estado": estado,
                                    "mes": mes,
                                    "anio": anio,
                                    "id_historial": id_historial_seleccionado
                                })
                            else:
                                conn.execute(text("""
                                    INSERT INTO cobros (id_historial, numero_vigente, folio, fecha_pago, egreso_equipo, estado, mes, anio)
                                    VALUES (:id_historial, :numero_vigente, :folio, :fecha_pago, :egreso_equipo, :estado, :mes, :anio)
                                """), {
                                    "id_historial": id_historial_seleccionado,
                                    "numero_vigente": numero_vigente,
                                    "folio": int(folio_seleccionado),
                                    "fecha_pago": fecha_pago,
                                    "egreso_equipo": egreso_equipo,
                                    "estado": estado,
                                    "mes": mes,
                                    "anio": anio
                                })
                        else:
                            # Si el tipo de servicio ya no es mantención ni reparación, eliminar cobro asociado si existe
                            conn.execute(text("DELETE FROM cobros WHERE id_historial = :id_historial"), {"id_historial": id_historial_seleccionado})
                    st.success("✅ Registro del historial actualizado exitosamente.")
                
                if eliminar_button:
                    if confirmacion:
                        # Acceso robusto a los campos para evitar KeyError si están renombrados
                        def get_col(registro, *nombres):
                            for n in nombres:
                                if n in registro:
                                    return registro[n]
                            return None
                        tipo_servicio_borrar = get_col(registro_seleccionado, "tipo_servicio", "Tipo de servicio")
                        equipo_borrar = get_col(registro_seleccionado, "numero_vigente", "Numero vigente")
                        folio_borrar = get_col(registro_seleccionado, "folio", "Folio")
                        # Buscar el nombre correcto de la columna id_historial
                        id_hist_col = None
                        for col in ["id_historial", "ID del historial"]:
                            if col in historial_folio.columns:
                                id_hist_col = col
                                break
                        equipo_anterior = None
                        with engine.begin() as conn:
                            if tipo_servicio_borrar == "Cambio del equipo":
                                if id_hist_col:
                                    prev_historial = historial_folio[historial_folio[id_hist_col] < id_historial_seleccionado]
                                    if not prev_historial.empty:
                                        # Buscar el nombre correcto de la columna numero_vigente
                                        num_vig_col = "numero_vigente" if "numero_vigente" in prev_historial.columns else "Numero vigente"
                                        equipo_anterior = prev_historial.sort_values(id_hist_col).iloc[-1][num_vig_col]
                            conn.execute(text("DELETE FROM historial_contrato WHERE id_historial = :id_historial"), {"id_historial": id_historial_seleccionado})
                            conn.execute(text("DELETE FROM cobros WHERE id_historial = :id_historial"), {"id_historial": id_historial_seleccionado})
                            if tipo_servicio_borrar == "Cambio del equipo" and equipo_anterior:
                                conn.execute(text("UPDATE equipos SET estado = 2 WHERE numero_vigente = :numero_vigente"), {"numero_vigente": equipo_anterior})
                                conn.execute(text("UPDATE equipos SET estado = 1 WHERE numero_vigente = :numero_vigente"), {"numero_vigente": equipo_borrar})
                            else:
                                conn.execute(text("UPDATE equipos SET estado = 1 WHERE numero_vigente = :numero_vigente"), {"numero_vigente": equipo_borrar})
                        st.warning("✅ Registro del historial eliminado exitosamente.")


elif menu == "Cobros":
    st.title("Cobros")
    opcion = st.radio("Seleccione una opción", ["Ver Cobros", "Agregar Cobro", "Editar o Eliminar Cobro"])

    if opcion == "Ver Cobros":
        st.subheader("Ver Cobros")
        df_cobros = cargar_cobros()
        df_contratos = cargar_contratos()
        df_clientes = cargar_clientes() if 'cargar_clientes' in globals() else None
        # Eliminar columnas duplicadas antes de mostrar
        df_cobros = df_cobros.loc[:, ~df_cobros.columns.duplicated()]
        # Filtrar para mostrar solo contratos donde egreso_equipo es nulo o cero (no mostrar contratos de mantenciones/reparaciones)
        if "egreso_equipo" in df_cobros.columns:
            df_cobros = df_cobros[(df_cobros["egreso_equipo"].isnull()) | (df_cobros["egreso_equipo"] == 0)]
        else:
            df_cobros = df_cobros[df_cobros["egreso_equipo"].isnull()]
        # Determinar contratos vigentes y no vigentes
        import datetime
        hoy = datetime.date.today()
        df_contratos["vigente"] = (df_contratos["fecha_inicio_contrato"] <= hoy) & (df_contratos["fecha_termino_contrato"] >= hoy)
        # Filtro de vigencia
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            folios_vigentes = df_contratos[df_contratos["vigente"]]["folio"].astype(str).tolist()
        else:
            folios_vigentes = df_contratos[~df_contratos["vigente"]]["folio"].astype(str).tolist()
        # Unir con contratos y clientes para obtener rut y nombre empresa
        if "folio" in df_cobros.columns and df_clientes is not None:
            df_cobros = df_cobros.merge(df_contratos[["folio", "rut_empresa"]], on="folio", how="left")
            if "rut_empresa" in df_cobros.columns:
                df_cobros = df_cobros.merge(df_clientes[["rut_empresa", "nombre_empresa"]], on="rut_empresa", how="left")
        # Filtrar para mostrar solo cobros reales (egreso_equipo nulo o cero)
        if "egreso_equipo" in df_cobros.columns:
            df_cobros = df_cobros[(df_cobros["egreso_equipo"].isnull()) | (df_cobros["egreso_equipo"] == 0)]
        else:
            df_cobros = df_cobros[df_cobros.get("egreso_equipo", pd.Series([None]*len(df_cobros))).isnull()]
        # Filtrar para mostrar solo cobros reales (egreso_equipo nulo o cero)
        if "egreso_equipo" in df_cobros.columns:
            df_cobros = df_cobros[(df_cobros["egreso_equipo"].isnull()) | (df_cobros["egreso_equipo"] == 0)]
        else:
            df_cobros = df_cobros[df_cobros.get("egreso_equipo", pd.Series([None]*len(df_cobros))).isnull()]
        # Renombrar columnas para visualización
        df_cobros = df_cobros.rename(columns={
            "id_cobros": "ID cobro",
            "id_historial": "ID historial",
            "numero_vigente": "Numero vigente",
            "folio": "Folio",
            "fecha_pago": "Fecha en la que se paga",
            "horas_extra": "Horas extra",
            "costo_hora_extra": "Costo de horas extra",
            "estado": "Estado",
            "cobro": "Cobro",
            "mes": "Mes de facturacion",
            "anio": "Año de facturacion",
            "rut_empresa": "Rut de la empresa",
            "nombre_empresa": "Nombre de la empresa"
        })
        columnas_mostrar = [
            "ID cobro",
            "ID historial",
            "Numero vigente",
            "Folio",
            "Fecha en la que se paga",
            "Horas extra",
            "Costo de horas extra",
            "Estado",
            "Cobro",
            "Mes de facturacion",
            "Año de facturacion",
            "Rut de la empresa",
            "Nombre de la empresa"
        ]
        # Selección de contrato (folio)
        folios_disponibles = [f for f in df_cobros["Folio"].drop_duplicates().astype(str).tolist() if f in folios_vigentes]
        if folios_disponibles:
            folio_seleccionado = st.selectbox("Seleccione el folio del contrato para ver sus cobros", folios_disponibles)
            cobros_folio = df_cobros[df_cobros["Folio"] == int(folio_seleccionado)]
            st.dataframe(cobros_folio[[col for col in columnas_mostrar if col in cobros_folio.columns]], use_container_width=True)
        else:
            st.info("No hay cobros registrados.")
        
    elif opcion == "Agregar Cobro":
        st.subheader("Agregar Cobro")
        df_contratos = cargar_contratos()
        df_historial = cargar_historial_contrato()
        # Determinar contratos vigentes y no vigentes
        import datetime
        hoy = datetime.date.today()
        df_contratos["vigente"] = (df_contratos["fecha_inicio_contrato"] <= hoy) & (df_contratos["fecha_termino_contrato"] >= hoy)
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            folios_vigentes = df_contratos[df_contratos["vigente"]]["folio"].astype(str).tolist()
        else:
            folios_vigentes = df_contratos[~df_contratos["vigente"]]["folio"].astype(str).tolist()
        folios_disponibles = folios_vigentes
        if folios_disponibles:
            # Eliminar columnas duplicadas antes de operar
            df_historial = df_historial.loc[:, ~df_historial.columns.duplicated()]
            # Asegurar tipos correctos
            df_historial["id_historial"] = df_historial["id_historial"].astype(int)
            df_historial["folio"] = df_historial["folio"].astype(int)
            # Obtener el id_historial más reciente de cada folio SOLO de los folios_disponibles (vigentes o no vigentes según filtro)
            historial_filtrado = df_historial[df_historial["folio"].astype(str).isin(folios_disponibles)]
            if not historial_filtrado.empty:
                idx = historial_filtrado.groupby("folio")["id_historial"].idxmax()
                historial_reciente = historial_filtrado.loc[idx].sort_values("folio")
                # Opciones para el selectbox: folio y equipo actual
                opciones = [
                    f"{row['folio']} - Equipo actual: {row['numero_vigente']} (id_historial: {row['id_historial']})"
                    for _, row in historial_reciente.iterrows()
                ]
                seleccion = st.selectbox("Seleccione el folio y equipo actual para el cobro", opciones)
                folio_seleccionado = int(seleccion.split(" - ")[0])
                id_historial_seleccionado = int(seleccion.split("id_historial: ")[1].replace(")", ""))
            else:
                st.info("No hay contratos disponibles para el filtro seleccionado.")
                st.stop()

            contrato_seleccionado = df_contratos[df_contratos["folio"] == folio_seleccionado].iloc[0]
            equipo_actual = historial_reciente[historial_reciente["folio"] == folio_seleccionado]["numero_vigente"].iloc[0]
            precio_mensual = contrato_seleccionado["precio_mensual"]
            precio_envio = contrato_seleccionado["precio_envio"]
            st.write(f"Contrato seleccionado: Folio {contrato_seleccionado['folio']}, Empresa: {contrato_seleccionado['rut_empresa']}, Nombre: {contrato_seleccionado['nombre_empresa']}")
            st.info(f"Monto pactado mensual: ${precio_mensual:,.0f}")
            st.write(f"Equipo actual: {equipo_actual}")

            # Determinar si es el primer mes de arriendo (primer cobro para este folio)
            df_cobros = cargar_cobros()
            # Eliminar columnas duplicadas antes de filtrar para evitar errores de pandas
            df_cobros = df_cobros.loc[:, ~df_cobros.columns.duplicated()]
            cobros_folio = df_cobros[df_cobros["folio"] == folio_seleccionado]
            es_primer_mes = cobros_folio.empty

            # Calcular fecha de facturación (día 25 del mes actual o siguiente si ya pasó)
            import datetime
            hoy = datetime.date.today()
            if hoy.day <= 25:
                fecha_facturacion = hoy.replace(day=25)
            else:
                # Si ya pasó el 25, siguiente mes
                if hoy.month == 12:
                    fecha_facturacion = hoy.replace(year=hoy.year+1, month=1, day=25)
                else:
                    fecha_facturacion = hoy.replace(month=hoy.month+1, day=25)
            st.info(f"Fecha de facturación proxima: {fecha_facturacion.strftime('%d/%m/%Y')}")

            with st.form("form_agregar_cobro"):
                fecha_facturacion_input = st.date_input("Fecha de facturación (emisión de la factura)", value=fecha_facturacion)
                fecha_pago = st.date_input("Fecha en la que se realiza el pago (cuando paga el cliente)", value=fecha_facturacion)
                horas_extra = st.number_input("Horas extra de uso", min_value=0, step=1, value=0)
                costo_hora_extra = st.number_input("Costo por horas extra", min_value=0, step=1000, value=0)
                estado = st.selectbox("Estado del cobro", ["Pendiente", "Pagado"], index=1)

                # Calcular el monto del cobro
                monto_cobro = precio_mensual
                if es_primer_mes:
                    monto_cobro += precio_envio
                st.success(f"El monto sin contar horas extra es: ${monto_cobro:,.0f} (incluye envío solo en el primer mes)")

                monto_cobro += horas_extra * costo_hora_extra
                
                submit_button = st.form_submit_button("Agregar Cobro")
                if submit_button:
                    # Obtener mes y año de la fecha de facturación seleccionada
                    mes = int(fecha_facturacion_input.month)
                    anio = int(fecha_facturacion_input.year)
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO cobros (id_historial, numero_vigente, folio, fecha_pago, horas_extra, costo_hora_extra, cobro, estado, mes, anio)
                            VALUES (:id_historial, :numero_vigente, :folio, :fecha_pago, :horas_extra, :costo_hora_extra, :cobro, :estado, :mes, :anio)
                        """), {
                            "id_historial": int(id_historial_seleccionado),
                            "numero_vigente": str(equipo_actual),
                            "folio": int(folio_seleccionado),
                            "fecha_pago": fecha_pago,
                            "horas_extra": int(horas_extra),
                            "costo_hora_extra": int(costo_hora_extra),
                            "cobro": int(monto_cobro),
                            "estado": 2 if estado == "Pagado" else 1,
                            "mes": int(mes),
                            "anio": int(anio)
                        })
                    st.success(f"✅ Cobro de ${int(monto_cobro):,.0f} agregado exitosamente.")
                            
    elif opcion == "Editar o Eliminar Cobro":
        st.subheader("Editar o Eliminar Cobro")
        df_cobros = cargar_cobros()
        df_contratos = cargar_contratos()
        df_clientes = cargar_clientes() if 'cargar_clientes' in globals() else None
        import datetime
        hoy = datetime.date.today()
        df_contratos["vigente"] = (df_contratos["fecha_inicio_contrato"] <= hoy) & (df_contratos["fecha_termino_contrato"] >= hoy)
        filtro_vigencia = st.radio("Filtrar por contratos", ["Vigentes", "No vigentes"], horizontal=True)
        if filtro_vigencia == "Vigentes":
            folios_vigentes = df_contratos[df_contratos["vigente"]]["folio"].astype(str).tolist()
        else:
            folios_vigentes = df_contratos[~df_contratos["vigente"]]["folio"].astype(str).tolist()
        folios_disponibles = folios_vigentes
        if folios_disponibles:
            folio_seleccionado = st.selectbox("Seleccione el folio del contrato para editar un cobro", folios_disponibles)
            df_cobros = df_cobros.loc[:, ~df_cobros.columns.duplicated()]
            cobros_folio = df_cobros[df_cobros["folio"] == int(folio_seleccionado)]
            if "egreso_equipo" in cobros_folio.columns:
                cobros_folio = cobros_folio[cobros_folio["egreso_equipo"].isnull()]
            if "folio" in cobros_folio.columns and df_clientes is not None:
                cobros_folio = cobros_folio.merge(df_contratos[["folio", "rut_empresa"]], on="folio", how="left")
                if "rut_empresa" in cobros_folio.columns:
                    cobros_folio = cobros_folio.merge(df_clientes[["rut_empresa", "nombre_empresa"]], on="rut_empresa", how="left")
            cobros_folio = cobros_folio.rename(columns={
                "id_cobros": "ID cobro",
                "id_historial": "ID historial",
                "numero_vigente": "Numero vigente",
                "folio": "Folio",
                "fecha_pago": "Fecha en la que se paga",
                "horas_extra": "Horas extra",
                "costo_hora_extra": "Costo de horas extra",
                "estado": "Estado",
                "cobro": "Cobro",
                "mes": "Mes de facturacion",
                "anio": "Año de facturacion",
                "rut_empresa": "Rut de la empresa",
                "nombre_empresa": "Nombre de la empresa"
            })
            columnas_mostrar = [
                "ID cobro", "ID historial", "Numero vigente", "Folio", "Fecha en la que se paga",
                "Horas extra", "Costo de horas extra", "Estado", "Cobro", "Mes de facturacion",
                "Año de facturacion", "Rut de la empresa", "Nombre de la empresa"
            ]
            columnas_mostrar = [col for col in columnas_mostrar if col in cobros_folio.columns]
            st.write("Cobros encontrados para este folio:")
            st.dataframe(cobros_folio[columnas_mostrar] if columnas_mostrar else cobros_folio, use_container_width=True)
            if not cobros_folio.empty:
                if "ID cobro" not in cobros_folio.columns:
                    st.error("No se encontró la columna 'ID cobro' en los cobros. Revisa la estructura de la tabla.")
                else:
                    opciones_cobro = [
                        f"Mes: {row['Mes de facturacion']:02d} / Año: {row['Año de facturacion']} - ID: {row['ID cobro']}"
                        for _, row in cobros_folio.sort_values(['Año de facturacion','Mes de facturacion']).iterrows()
                    ]
                    if opciones_cobro:
                        seleccion_cobro = st.selectbox("Seleccione el mes y año del cobro a editar", opciones_cobro)
                        id_cobros_seleccionado = int(seleccion_cobro.split("ID: ")[1])
                        cobro_seleccionado = cobros_folio[cobros_folio["ID cobro"] == id_cobros_seleccionado].iloc[0]
                        contrato_seleccionado = df_contratos[df_contratos["folio"] == int(folio_seleccionado)].iloc[0]
                        equipo_actual = cobro_seleccionado["Numero vigente"]
                        precio_mensual = contrato_seleccionado["precio_mensual"]
                        precio_envio = contrato_seleccionado["precio_envio"]
                        st.write(f"Contrato seleccionado: Folio {contrato_seleccionado['folio']}, Empresa: {contrato_seleccionado['rut_empresa']}, Nombre: {contrato_seleccionado['nombre_empresa']}")
                        st.info(f"Monto pactado mensual: ${precio_mensual:,.0f}")
                        st.write(f"Equipo del pago: {equipo_actual}")
                        hoy = datetime.date.today()
                        if hoy.day <= 25:
                            fecha_facturacion = hoy.replace(day=25)
                        else:
                            if hoy.month == 12:
                                fecha_facturacion = hoy.replace(year=hoy.year+1, month=1, day=25)
                            else:
                                fecha_facturacion = hoy.replace(month=hoy.month+1, day=25)
                        fecha_pago = st.date_input("Fecha en la que se realiza el pago (cuando paga el cliente)", value=cobro_seleccionado["Fecha en la que se paga"])
                        horas_extra = st.number_input("Horas extra de uso", min_value=0, step=1, value=int(cobro_seleccionado["Horas extra"]))
                        costo_hora_extra = st.number_input("Costo por horas extra", min_value=0, step=1000, value=int(cobro_seleccionado["Costo de horas extra"]))
                        estado = st.selectbox("Estado del cobro", ["Pendiente", "Pagado"], index=1 if cobro_seleccionado["Estado"] == 2 else 0)
                        monto_cobro = precio_mensual
                        cobros_ordenados = cobros_folio.sort_values(["Año de facturacion", "Mes de facturacion"]).reset_index(drop=True)
                        es_primer_mes = False
                        if not cobros_ordenados.empty:
                            primer_cobro = cobros_ordenados.iloc[0]
                            if (
                                cobro_seleccionado["Mes de facturacion"] == primer_cobro["Mes de facturacion"]
                                and cobro_seleccionado["Año de facturacion"] == primer_cobro["Año de facturacion"]
                            ):
                                es_primer_mes = True
                        if es_primer_mes:
                            monto_cobro += precio_envio
                        st.success(f"El monto sin contar horas extra es: ${monto_cobro:,.0f} (incluye envío solo en el primer mes)")
                        monto_cobro += horas_extra * costo_hora_extra
                        with st.form("form_editar_cobro"):
                            st.success(f"El monto total del cobro es: ${monto_cobro:,.0f}")
                            submit_button = st.form_submit_button("Guardar Cambios")
                            eliminar_button = st.form_submit_button("Eliminar Cobro")
                            confirmacion = st.checkbox("CONFIRMAR ELIMINACIÓN")
                        if submit_button:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE cobros
                                    SET numero_vigente = :numero_vigente, folio = :folio, fecha_pago = :fecha_pago, horas_extra = :horas_extra, costo_hora_extra = :costo_hora_extra, cobro = :cobro, estado = :estado, mes = :mes, anio = :anio
                                    WHERE id_cobros = :id_cobros
                                """), {
                                    "numero_vigente": str(equipo_actual),
                                    "folio": int(folio_seleccionado),
                                    "fecha_pago": fecha_pago,
                                    "horas_extra": int(horas_extra),
                                    "costo_hora_extra": int(costo_hora_extra),
                                    "cobro": int(monto_cobro),
                                    "estado": 2 if estado == "Pagado" else 1,
                                    "mes": int(cobro_seleccionado["Mes de facturacion"]),
                                    "anio": int(cobro_seleccionado["Año de facturacion"]),
                                    "id_cobros": id_cobros_seleccionado
                                })
                            st.success(f"✅ Cobro de ${int(monto_cobro):,.0f} actualizado exitosamente.")
                        if eliminar_button:
                            if confirmacion:
                                with engine.begin() as conn:
                                    conn.execute(text("DELETE FROM cobros WHERE id_cobros = :id_cobros"), {"id_cobros": id_cobros_seleccionado})
                                    st.warning("✅ Cobro eliminado exitosamente.")
                    else:
                        st.warning("No hay opciones de cobro para mostrar.")
            else:
                st.warning("No hay cobros registrados para este folio de contrato.")
            
                        
