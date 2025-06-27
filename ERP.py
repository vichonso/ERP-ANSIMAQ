import streamlit as st
import pandas as pd

# Simuladores de bases de datos en memoria
if 'generadores' not in st.session_state:
    st.session_state.generadores = []
if 'contratos' not in st.session_state:
    st.session_state.contratos = []

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
            "Total Arreglos": sum(g["arreglos"])
        } for g in st.session_state.generadores
    ]
    st.dataframe(pd.DataFrame(resumen))

# =======================
# 2. GESTIÓN DE CONTRATOS
# =======================
elif menu == "Contratos":
    st.header("📄 Registro de Contratos")

    if len(st.session_state.generadores) == 0:
        st.warning("Primero debes ingresar generadores.")
    else:
        with st.form("form_contrato"):
            cliente = st.text_input("Nombre del cliente")
            generador = st.selectbox("Asociar generador", [g["nombre"] for g in st.session_state.generadores])
            monto = st.number_input("Monto del contrato ($)", min_value=0.0)
            duracion = st.number_input("Duración en meses", min_value=1)
            submit_c = st.form_submit_button("Guardar contrato")

            if submit_c and cliente:
                st.session_state.contratos.append({
                    "cliente": cliente,
                    "generador": generador,
                    "monto": monto,
                    "duracion": duracion
                })
                st.success(f"Contrato con {cliente} guardado.")

        st.subheader("🗂 Contratos registrados")
        st.dataframe(pd.DataFrame(st.session_state.contratos))

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
        st.dataframe(df[["cliente", "generador", "total_mensual"]])

        total_ingresos = df["monto"].sum()
        total_mensual = df["total_mensual"].sum()

        st.metric("Ingreso total (todos los contratos)", f"${total_ingresos:,.0f}")
        st.metric("Ingreso mensual estimado", f"${total_mensual:,.0f}")

        st.subheader("📈 Ingresos por generador")
        ingresos_por_generador = df.groupby("generador")["monto"].sum()
        st.bar_chart(ingresos_por_generador)

        st.subheader("🔍 Análisis por contrato")
        contrato_seleccionado = st.selectbox("Selecciona un contrato", df["cliente"] + " - " + df["generador"])
        idx = df[(df["cliente"] + " - " + df["generador"]) == contrato_seleccionado].index[0]
        contrato = df.loc[idx]
        st.write(f"**Cliente:** {contrato['cliente']}")
        st.write(f"**Generador asociado:** {contrato['generador']}")
        st.write(f"**Monto total:** ${contrato['monto']:,.0f}")
        st.write(f"**Duración:** {contrato['duracion']} meses")
        st.write(f"**Ingreso mensual estimado:** ${contrato['total_mensual']:,.0f}")

    if len(st.session_state.generadores) > 0:
        st.subheader("🔍 Análisis por generador")
        gen_df = pd.DataFrame(st.session_state.generadores)
        generador_sel = st.selectbox("Selecciona un generador", gen_df["nombre"])
        g = gen_df[gen_df["nombre"] == generador_sel].iloc[0]

        st.write(f"**ID:** {g['id']}")
        st.write(f"**Tipo:** {g['tipo']}")
        st.write(f"**Potencia:** {g['potencia']} kV")
        st.write(f"**Horas de uso:** {g['horas_uso']} h")
        st.write(f"**Arreglos realizados:** {g['arreglos']}")
        st.write(f"**Monto total en arreglos:** ${sum(g['arreglos']):,.0f}")
