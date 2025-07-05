import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# Conexión a la base de datos PostgreSQL
engine = create_engine('postgresql://postgres:pc-database@localhost:5432/ansimaq')

st.set_page_config(page_title="ERP Generadores", layout="wide")
st.title("⚙️ ERP de Generadores y Contratos")

menu = st.sidebar.radio("Menú", [
    "Lista de Generadores", "Lista de Contratos", "Añadir Generador", "Editar Generador",
    "Añadir Contrato", "Editar Contrato", "Agregar Arreglo o Mantención", "Análisis Financiero"
])

# Funciones auxiliares para cargar datos
def cargar_generadores():
    return pd.read_sql("SELECT * FROM generadores", engine)

def cargar_contratos():
    return pd.read_sql("SELECT * FROM contrato", engine)

def cargar_arreglos():
    return pd.read_sql("SELECT * FROM arreglos_y_mantenciones", engine)

def cargar_clientes():
    return pd.read_sql("SELECT * FROM clientes", engine)

# 1. Lista de Generadores
if menu == "Lista de Generadores":
    st.subheader("📦 Lista de Generadores")
    df = cargar_generadores()
    columnas_visibles = ["id_generador", "codigo_interno", "nombre_modelo", "marca", "voltamperio", "estado"]
    st.dataframe(df[columnas_visibles])

# 2. Lista de Contratos
elif menu == "Lista de Contratos":
    st.subheader("📄 Lista de Contratos")
    df = cargar_contratos()
    st.dataframe(df)

# 3. Añadir Generador
elif menu == "Añadir Generador":
    st.subheader("➕ Añadir Generador")
    with st.form("form_generador"):
        codigo_interno = st.text_input("Código interno del generador")
        nombre = st.text_input("Nombre del modelo")
        marca = st.text_input("Marca")
        voltamperio = st.number_input("Volt-Amperios", min_value=0)
        estado = st.selectbox("Estado", [1, 2, 3, 4], format_func=lambda x: ["Disponible", "En arriendo", "En reparación", "Averiado"][x-1])
        
        submit = st.form_submit_button("Guardar Generador")

        if submit:
            with engine.begin() as conn:
                conn.execute(
                    "INSERT INTO generadores (codigo_interno, nombre_modelo, marca, voltamperio, estado) VALUES (%s, %s, %s, %s, %s)",
                    [(codigo_interno, nombre, marca, voltamperio, estado)]
                )
            st.success("✅ Generador guardado correctamente")

# 4. Editar Generador
elif menu == "Editar Generador":
    st.subheader("🛠 Editar Generador")
    df = cargar_generadores()
    generador = st.selectbox("Selecciona un generador", df["id_generador"])
    g = df[df["id_generador"] == generador].iloc[0]

    with st.form("editar_generador"):
        codigo_interno = st.text_input("Código interno", value=g["codigo_interno"])
        nombre = st.text_input("Nombre del modelo", value=g["nombre_modelo"])
        marca = st.text_input("Marca", value=g["marca"])
        voltamperio = st.number_input("Volt-Amperios", min_value=0, value=g["voltamperio"])
        estado = st.selectbox("Estado", [1, 2, 3, 4], index=g["estado"]-1, format_func=lambda x: ["Disponible", "En arriendo", "En reparación", "Averiado"][x-1])
        actualizar = st.form_submit_button("Actualizar")
        if actualizar:
            with engine.begin() as conn:
                conn.execute(
                    "UPDATE generadores SET codigo_interno=%s, nombre_modelo=%s, marca=%s, voltamperio=%s, estado=%s WHERE id_generador=%s",
                    (codigo_interno, nombre, marca, voltamperio, estado, generador)
                )
            st.success("✅ Generador actualizado")

# 5. Añadir Contrato
elif menu == "Añadir Contrato":
    st.subheader("➕ Añadir Contrato")
    clientes = cargar_clientes()
    generadores = cargar_generadores()
    with st.form("form_contrato"):
        cliente = st.selectbox("Cliente", clientes["id_cliente"])
        fecha_inicio = st.date_input("Fecha inicio del contrato")
        fecha_termino = st.date_input("Fecha término del contrato")
        costo_arriendo = st.number_input("Costo de arriendo", min_value=0)
        costo_envio = st.number_input("Costo de envío", min_value=0)
        costo_arreglo = st.number_input("Costo de arreglo", min_value=0)
        costo_mantencion = st.number_input("Costo de mantención", min_value=0)
        generadores_ids = st.multiselect("Selecciona generadores", generadores["id_generador"])
        submit = st.form_submit_button("Guardar contrato")
        if submit:
            with engine.begin() as conn:
                result = conn.execute(
                    "INSERT INTO contrato (id_cliente, fecha_inicio_contrato, fecha_termino_contrato, costo_arriendo, costo_envio, costo_arreglo, costo_mantencion) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_contrato",
                    (cliente, fecha_inicio, fecha_termino, costo_arriendo, costo_envio, costo_arreglo, costo_mantencion)
                )
                id_contrato = result.fetchone()[0]
                for gid in generadores_ids:
                    conn.execute(
                        "INSERT INTO generador_en_contrato (id_contrato, id_generador, fecha_inicio_arriendo, fecha_termino_arriendo) VALUES (%s, %s, %s, %s)",
                        (id_contrato, gid, fecha_inicio, fecha_termino)
                    )
            st.success("✅ Contrato guardado correctamente")

# 6. Editar Contrato (simple)
elif menu == "Editar Contrato":
    st.subheader("🛠 Editar Contrato")
    contratos = cargar_contratos()
    contrato_id = st.selectbox("Selecciona un contrato", contratos["id_contrato"])
    c = contratos[contratos["id_contrato"] == contrato_id].iloc[0]

    with st.form("editar_contrato"):
        costo_arriendo = st.number_input("Costo de arriendo", min_value=0, value=c["costo_arriendo"])
        costo_envio = st.number_input("Costo de envío", min_value=0, value=c["costo_envio"])
        costo_arreglo = st.number_input("Costo de arreglo", min_value=0, value=c["costo_arreglo"])
        costo_mantencion = st.number_input("Costo de mantención", min_value=0, value=c["costo_mantencion"])
        actualizar = st.form_submit_button("Actualizar contrato")
        if actualizar:
            with engine.begin() as conn:
                conn.execute(
                    "UPDATE contrato SET costo_arriendo=%s, costo_envio=%s, costo_arreglo=%s, costo_mantencion=%s WHERE id_contrato=%s",
                    (costo_arriendo, costo_envio, costo_arreglo, costo_mantencion, contrato_id)
                )
            st.success("✅ Contrato actualizado")

# 7. Agregar Arreglo o Mantención
elif menu == "Agregar Arreglo o Mantención":
    st.subheader("🔧 Agregar Arreglo o Mantención")
    generadores = cargar_generadores()
    with st.form("form_arreglo"):
        id_generador = st.selectbox("Generador", generadores["id_generador"])
        fecha_inicio = st.date_input("Fecha inicio")
        fecha_termino = st.date_input("Fecha término")
        costo = st.number_input("Costo", min_value=0)
        tipo = st.selectbox("Tipo", [1, 2], format_func=lambda x: "Arreglo" if x == 1 else "Mantención")
        submit = st.form_submit_button("Guardar")
        if submit:
            with engine.begin() as conn:
                conn.execute(
                    "INSERT INTO arreglos_y_mantenciones (id_generador, fecha_inicio_arreglo, fecha_termino_arreglo, costo, tipo) VALUES (%s, %s, %s, %s, %s)",
                    (id_generador, fecha_inicio, fecha_termino, costo, tipo)
                )
            st.success("✅ Registro guardado")

# 8. Análisis Financiero
elif menu == "Análisis Financiero":
    st.subheader("📊 Análisis Financiero")
    contratos = cargar_contratos()
    arreglos = cargar_arreglos()
    if contratos.empty:
        st.info("No hay contratos registrados.")
    else:
        contratos["costo_total"] = contratos[["costo_arriendo", "costo_envio", "costo_arreglo", "costo_mantencion"]].sum(axis=1)
        fig = px.bar(contratos, x="id_contrato", y="costo_total", title="Costo Total por Contrato")
        st.plotly_chart(fig)

        costo_por_generador = arreglos.groupby("id_generador")["costo"].sum().reset_index()
        fig2 = px.bar(costo_por_generador, x="id_generador", y="costo", title="Costo de Arreglos/Mantenciones por Generador")
        st.plotly_chart(fig2)
