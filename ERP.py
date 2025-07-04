import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import time

engine = create_engine('postgresql://postgres:pc-database@localhost:5432/ansimaq')  # Simulador de base de datos en memoria


st.set_page_config(page_title="ERP Generadores", layout="wide")

st.markdown("""
    <style>
        .big-title {
            font-size: 36px;
            color: #A4DE02;
            font-weight: bold;
        }
        .stButton>button {
            background-color: #A4DE02;
            color: black;
            font-weight: bold;
            border: none;
        }
        .stButton>button:hover {
            background-color: #8BC34A;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">⚙️ ERP de Generadores y Contratos</div>', unsafe_allow_html=True)

menu = st.sidebar.radio("Menú", ["Generadores", "Contratos", "Análisis Financiero"])

# =======================
# 1. GESTIÓN DE GENERADORES (MODIFICADO)
# =======================
if menu == "Generadores":
    st.header("📦 Registro de Generadores")

    with st.form("form_generador"):
        id_manual = st.text_input("ID único del generador")
        nombre = st.text_input("Nombre del generador")
        tipo = st.selectbox("Tipo de generador", ["Diesel", "Gas", "Eléctrico"])
        potencia = st.number_input("Potencia (kV)", min_value=0.0)
        horas_uso = st.number_input("Horas de uso acumuladas", min_value=0.0)
        arreglo = st.number_input("Monto de arreglo (último)", min_value=0.0)
        submit = st.form_submit_button("Guardar generador")

        if submit:
            ids = [g["id"] for g in st.session_state.generadores]
            if id_manual in ids:
                st.error("⚠️ Ya existe un generador con ese ID. Usa uno único.")
            else:
                st.session_state.generadores.append({
                    "id": id_manual,
                    "nombre": nombre,
                    "tipo": tipo,
                    "potencia": potencia,
                    "horas_uso": horas_uso,
                    "estado": "Disponible",
                    "arreglos": [arreglo] if arreglo > 0 else []
                })
                st.success(f"✅ Generador '{nombre}' guardado correctamente.")

    st.subheader("🛠 Editar generadores")

    if len(st.session_state.generadores) == 0:
        st.info("No hay generadores registrados aún.")
    else:
        for i, gen in enumerate(st.session_state.generadores):
            with st.expander(f"🔧 {gen['id']} - {gen['nombre']}"):
                gen["nombre"] = st.text_input(f"Nombre [{gen['id']}]", gen["nombre"], key=f"n_{i}")
                gen["tipo"] = st.selectbox(f"Tipo [{gen['id']}]", ["Diesel", "Gas", "Eléctrico"], index=["Diesel", "Gas", "Eléctrico"].index(gen["tipo"]), key=f"t_{i}")
                gen["potencia"] = st.number_input(f"Potencia (kV) [{gen['id']}]", value=gen["potencia"], min_value=0.0, key=f"p_{i}")
                gen["horas_uso"] = st.number_input(f"Horas de uso acumuladas [{gen['id']}]", value=gen["horas_uso"], min_value=0.0, key=f"h_{i}")
                gen["estado"] = st.selectbox(f"Estado [{gen['id']}]", ["Disponible", "En arriendo", "En reparacion", "Averiado", "Reservado"], index=["Disponible", "En arriendo", "En reparacion", "Averiado", "Reservado"].index(gen.get("estado", "Disponible")), key=f"e_{i}")
                nuevo_arreglo = st.number_input(f"Nuevo monto de arreglo [{gen['id']}]", min_value=0.0, key=f"a_{i}")
                if st.button(f"Añadir arreglo [{gen['id']}]", key=f"btn_a_{i}") and nuevo_arreglo > 0:
                    gen["arreglos"].append(nuevo_arreglo)
                    st.success("✅ Arreglo añadido")
                if len(gen["arreglos"]) > 0:
                    st.write("🧾 Arreglos realizados:")
                    st.write(gen["arreglos"])
                else:
                    st.write("⚠️ No hay arreglos registrados.")

    st.subheader("📋 Tabla general de generadores")
    resumen = [
        {
            "ID": g["id"],
            "Nombre": g["nombre"],
            "Tipo": g["tipo"],
            "Potencia (kV)": g["potencia"],
            "Horas Uso": g["horas_uso"],
            "Estado": g["estado"],
            "Total Arreglos": sum(g["arreglos"])
        } for g in st.session_state.generadores
    ]
    st.dataframe(pd.DataFrame(resumen))

# =======================
# 2. GESTIÓN DE CONTRATOS (MODIFICADO)
# =======================
elif menu == "Contratos":
    st.header("📄 Registro de Contratos")

    if len(st.session_state.generadores) == 0:
        st.warning("Primero debes ingresar generadores.")
    else:
        with st.form("form_contrato"):
            cliente = st.text_input("Nombre del cliente")
            generadores_disponibles = [g for g in st.session_state.generadores if g["estado"] == "Disponible"]
            generadores_seleccionados = st.multiselect("Selecciona generadores para arriendo", [g["id"] for g in generadores_disponibles])
            monto = st.number_input("Monto del contrato ($)", min_value=0.0)
            duracion = st.number_input("Duración en meses", min_value=1)
            submit_c = st.form_submit_button("Guardar contrato")

            if submit_c and cliente:
                for g in st.session_state.generadores:
                    if g["id"] in generadores_seleccionados:
                        g["estado"] = "En arriendo"

                st.session_state.contratos.append({
                    "cliente": cliente,
                    "generadores": generadores_seleccionados,
                    "monto": monto,
                    "duracion": duracion,
                    "historial": generadores_seleccionados.copy()
                })
                st.success(f"Contrato con {cliente} guardado.")

        st.subheader("🗂 Contratos registrados")
        for i, c in enumerate(st.session_state.contratos):
            with st.expander(f"📄 Contrato {i+1} - {c['cliente']}"):
                st.write(f"Generadores actuales: {c['generadores']}")
                agregar = st.multiselect("Agregar generadores", [g["id"] for g in st.session_state.generadores if g["estado"] == "Disponible"], key=f"add_{i}")
                quitar = st.multiselect("Quitar generadores", c["generadores"], key=f"remove_{i}")
                if st.button(f"Actualizar contrato {i+1}", key=f"btn_update_{i}"):
                    for g in st.session_state.generadores:
                        if g["id"] in agregar:
                            g["estado"] = "En arriendo"
                        if g["id"] in quitar:
                            g["estado"] = "Disponible"
                    c["generadores"] = list(set(c["generadores"]) - set(quitar) | set(agregar))
                    c["historial"].extend([g for g in agregar if g not in c["historial"]])
                    st.success("Contrato actualizado.")
                st.write(f"Historial de generadores por este contrato: {c['historial']}")

# =======================
# 3. ANÁLISIS FINANCIERO (AMPLIADO)
# =======================
elif menu == "Análisis Financiero":
    st.header("📊 Análisis financiero")

    if len(st.session_state.contratos) == 0:
        st.info("No hay contratos registrados para analizar.")
    else:
        df = pd.DataFrame(st.session_state.contratos)
        df["total_mensual"] = df["monto"] / df["duracion"]

        st.subheader("📌 Ingresos mensuales por contrato")
        st.dataframe(df[["cliente", "generadores", "total_mensual"]])

        total_ingresos = df["monto"].sum()
        total_mensual = df["total_mensual"].sum()

        st.metric("Ingreso total (todos los contratos)", f"${total_ingresos:,.0f}")
        st.metric("Ingreso mensual estimado", f"${total_mensual:,.0f}")

        st.subheader("📈 Ingresos por generador")
        ingresos_por_generador = {}
        for contrato in st.session_state.contratos:
            monto_por_generador = contrato["monto"] / len(contrato["generadores"])
            for gid in contrato["generadores"]:
                ingresos_por_generador[gid] = ingresos_por_generador.get(gid, 0) + monto_por_generador
        st.bar_chart(pd.Series(ingresos_por_generador))

        st.subheader("💡 Rentabilidad por generador")
        data = []
        for g in st.session_state.generadores:
            ingreso = ingresos_por_generador.get(g["id"], 0)
            costo = sum(g["arreglos"])
            utilidad = ingreso - costo
            data.append({
                "ID": g["id"],
                "Nombre": g["nombre"],
                "Ingreso": ingreso,
                "Costo Arreglos": costo,
                "Rentabilidad": utilidad
            })
        st.dataframe(pd.DataFrame(data))

        st.subheader("🔍 Análisis por contrato")
        contrato_seleccionado = st.selectbox("Selecciona un contrato", [f"Contrato {i+1} - {c['cliente']}" for i, c in enumerate(st.session_state.contratos)])
        index = int(contrato_seleccionado.split()[1]) - 1
        contrato = st.session_state.contratos[index]
        st.write(f"**Cliente:** {contrato['cliente']}")
        st.write(f"**Generadores actuales:** {contrato['generadores']}")
        st.write(f"**Historial de generadores:** {contrato['historial']}")
        st.write(f"**Monto total:** ${contrato['monto']:,.0f}")
        st.write(f"**Duración:** {contrato['duracion']} meses")
        st.write(f"**Ingreso mensual estimado:** ${contrato['monto'] / contrato['duracion']:,.0f}")
