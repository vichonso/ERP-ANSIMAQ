import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from sqlalchemy import create_engine

# Conexión a la base de datos PostgreSQL
engine = create_engine('postgresql+psycopg2://postgres:pc-database@localhost:5432/ansimaq')

st.set_page_config(page_title="ERP Generadores", layout="wide")
st.title("⚙️ ERP de Generadores y Contratos")

menu = st.sidebar.radio("Menú", [
    "Lista de Generadores", "Lista de Contratos", "Añadir Generador", "Editar Generador",
    "Añadir Contrato", "Editar Contrato", "Agregar Arreglo o Mantención", "Ver/Editar Arreglos o Mantenciones", "Análisis Financiero",
    "Añadir Cliente", "Eliminar Cliente"
])



# Función auxiliar para forzar int puro en columnas
def forzar_int_puro(df, columnas):
    for col in columnas:
        if col in df.columns:
            # Elimina nulos y fuerza int puro
            df = df[df[col].notnull()]
            df[col] = df[col].apply(lambda x: int(x))
    return df

# Función para limpiar RUT (elimina guion antes del dígito verificador)
def limpiar_rut(rut):
    if isinstance(rut, str):
        rut = rut.strip()
        # Si hay guion antes del último dígito, lo elimina
        if '-' in rut:
            partes = rut.split('-')
            if len(partes) == 2 and partes[0].isdigit() and partes[1].isdigit():
                return partes[0] + partes[1]
            # Si hay más de un guion, elimina todos menos el último
            rut = ''.join(rut.split('-'))
        # Si después de limpiar no es numérico, retorna como está
        if rut.isdigit():
            return rut
        else:
            return rut  # Devolver como string para validación posterior
    return rut

# Funciones auxiliares para cargar datos
def cargar_generadores():
    df = pd.read_sql("SELECT * FROM generadores", engine)
    return forzar_int_puro(df, ["id_generador", "voltamperio", "estado"])

# Incluye id_generador en contratos
def cargar_contratos():
    df = pd.read_sql("SELECT * FROM contrato", engine)
    return forzar_int_puro(df, ["id_contrato", "id_cliente", "id_generador", "costo_arriendo", "costo_envio", "costo_arreglo", "costo_mantencion"])

def cargar_arreglos():
    df = pd.read_sql("SELECT * FROM arreglos_y_mantenciones", engine)
    return forzar_int_puro(df, ["id_generador", "costo", "tipo"])

def cargar_clientes():
    df = pd.read_sql("SELECT * FROM clientes", engine)
    return forzar_int_puro(df, ["id_cliente"])

# 1. Lista de Generadores
if menu == "Lista de Generadores":
    st.subheader("📦 Lista de Generadores")
    df = cargar_generadores()
    # Mapea el estado numérico a texto
    estados_map = {1: "Disponible", 2: "En arriendo", 3: "En reparación", 4: "Averiado"}
    df["estado_texto"] = df["estado"].map(estados_map)
    columnas_visibles = ["id_generador", "codigo_interno", "nombre_modelo", "marca", "voltamperio", "estado_texto"]
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
                    text("INSERT INTO generadores (codigo_interno, nombre_modelo, marca, voltamperio, estado) VALUES (:ci, :nm, :ma, :va, :es)"),
                    {"ci": codigo_interno, "nm": nombre, "ma": marca, "va": voltamperio, "es": estado}
                )
            st.success("✅ Generador guardado correctamente")

# 4. Editar Generador
elif menu == "Editar Generador":
    st.subheader("🛠 Editar Generador")
    df = cargar_generadores()
    if df.empty or "codigo_interno" not in df.columns or df["codigo_interno"].dropna().empty:
        st.warning("No hay generadores disponibles para editar.")
    else:
        codigos = df["codigo_interno"].drop_duplicates().dropna().astype(str).tolist()
        codigo_sel = st.selectbox("Selecciona un generador (por código interno)", codigos)
        g = df[df["codigo_interno"] == codigo_sel].iloc[0]
        codigo_interno_original = g["codigo_interno"]  # Guarda el original

        # Manejo de estado para confirmación de borrado
        if "confirmar_borrado" not in st.session_state:
            st.session_state.confirmar_borrado = False

        with st.form("editar_generador"):
            codigo_interno = st.text_input("Código interno", value=g["codigo_interno"])
            nombre = st.text_input("Nombre del modelo", value=g["nombre_modelo"])
            marca = st.text_input("Marca", value=g["marca"])
            voltamperio = st.number_input("Volt-Amperios", min_value=0, value=int(g["voltamperio"]))
            estado = st.selectbox(
                "Estado",
                [1, 2, 3, 4],
                index=int(g["estado"])-1,
                format_func=lambda x: ["Disponible", "En arriendo", "En reparación", "Averiado"][x-1]
            )
            col1, col2 = st.columns(2)
            actualizar = col1.form_submit_button("Actualizar")
            eliminar = col2.form_submit_button("Eliminar")

        if actualizar:
            with engine.begin() as conn:
                result = conn.execute(
                    text("UPDATE generadores SET codigo_interno=:ci, nombre_modelo=:nm, marca=:ma, voltamperio=:va, estado=:es WHERE codigo_interno=:ci_orig"),
                    {"ci": codigo_interno, "nm": nombre, "ma": marca, "va": voltamperio, "es": estado, "ci_orig": codigo_interno_original}
                )
            st.info(f"Filas modificadas: {result.rowcount} (ci_orig={codigo_interno_original})")
            if result.rowcount > 0:
                st.success("✅ Generador actualizado")
            else:
                st.warning("No se encontró el generador para actualizar. ¿Cambiaste el código interno antes de guardar?")

        # Confirmación de borrado fuera del formulario
        if eliminar or st.session_state.get("confirmar_borrado", False):
            st.session_state.confirmar_borrado = True
            st.warning(
                "¿Estás seguro que deseas eliminar este generador? Esta acción no se puede deshacer.",
                icon="⚠️"
            )
            confirmar_eliminar = st.checkbox("Confirmo que deseo eliminar este generador", key="checkbox_confirmar_borrado")
            confirmar_click = st.button("Confirmar eliminación", key="boton_confirmar_borrado")
            if confirmar_eliminar and confirmar_click:
                with engine.begin() as conn:
                    result = conn.execute(
                        text("DELETE FROM generadores WHERE codigo_interno=:ci"),
                        {"ci": codigo_interno_original}
                    )
                if result.rowcount > 0:
                    st.success("🗑️ Generador eliminado correctamente")
                else:
                    st.warning("No se encontró el generador para eliminar.")
                st.session_state.confirmar_borrado = False
            elif confirmar_click and not confirmar_eliminar:
                st.warning("Debes marcar la casilla de confirmación para eliminar.")


# 5. Añadir Contrato
elif menu == "Añadir Contrato":
    st.subheader("➕ Añadir Contrato")

    # Selección entre cliente nuevo o existente
    cliente_opcion = st.radio("¿El cliente ya está inscrito?", ["Seleccionar cliente existente", "Agregar nuevo cliente"], horizontal=True)

    # Inicializar ID cliente
    id_cliente = None

    generadores = cargar_generadores()
    codigos = generadores["codigo_interno"].drop_duplicates().dropna().astype(str).tolist()
    generadores_codigos = generadores.set_index("codigo_interno")

    with st.form("form_contrato"):

        if cliente_opcion == "Seleccionar cliente existente":
            clientes = cargar_clientes()
            if clientes.empty:
                st.warning("No hay clientes registrados.")
            else:
                opciones_clientes = [(row["id_cliente"], f"{row['nombre_empresa']} ({row['rut_empresa']})") for _, row in clientes.iterrows()]
                cliente_sel = st.selectbox("Cliente", opciones_clientes, format_func=lambda x: x[1])
                id_cliente = cliente_sel[0]

        elif cliente_opcion == "Agregar nuevo cliente":
            st.markdown("### Datos del nuevo cliente")
            rut_empresa = st.text_input("RUT empresa")
            nombre_empresa = st.text_input("Nombre empresa")
            nombre_representante = st.text_input("Nombre representante")
            rut_representante = st.text_input("RUT representante")
            correo = st.text_input("Correo electrónico")
            telefono = st.text_input("Teléfono")

        st.markdown("### Datos del Contrato")
        # Selección de generador para el contrato
        if not codigos:
            st.warning("No hay generadores disponibles para asociar al contrato.")
            st.stop()
        codigo_sel = st.selectbox("Selecciona un generador (por código interno)", codigos)
        id_generador = int(generadores_codigos.loc[codigo_sel]["id_generador"])

        fecha_inicio = st.date_input("Fecha inicio del contrato")
        fecha_termino = st.date_input("Fecha término del contrato")
        costo_arriendo = st.number_input("Costo de arriendo", min_value=0, value=0)
        costo_envio = st.number_input("Costo de envío", min_value=0, value=0)
        submit = st.form_submit_button("Guardar contrato")

        if submit:
            with engine.begin() as conn:
                if cliente_opcion == "Agregar nuevo cliente":
                    # Validar y limpiar RUT
                    rut_empresa_limpio = limpiar_rut(rut_empresa)
                    rut_representante_limpio = limpiar_rut(rut_representante)
                    # Validación básica de RUT numérico
                    if not rut_empresa_limpio.isdigit() or not rut_representante_limpio.isdigit():
                        st.error("❌ El RUT de empresa y representante debe ser numérico (sin guiones ni puntos).")
                        st.stop()
                    result_cliente = conn.execute(
                        text("INSERT INTO clientes (rut_empresa, nombre_empresa, nombre_representante, rut_representante, correo, telefono) VALUES (:rut_empresa, :nombre_empresa, :nombre_representante, :rut_representante, :correo, :telefono) RETURNING id_cliente"),
                        {
                            "rut_empresa": rut_empresa_limpio,
                            "nombre_empresa": nombre_empresa,
                            "nombre_representante": nombre_representante,
                            "rut_representante": rut_representante_limpio,
                            "correo": correo,
                            "telefono": telefono
                        }
                    )
                    id_cliente = result_cliente.fetchone()[0]
                # Inserta el contrato (id_cliente ya definido en ambos casos)
                result_contrato = conn.execute(
                    text("INSERT INTO contrato (id_cliente, id_generador, fecha_inicio_contrato, fecha_termino_contrato, costo_arriendo, costo_envio, costo_arreglo, costo_mantencion) VALUES (:ic, :idg, :fic, :ftc, :ca, :ce, :car, :cm) RETURNING id_contrato"),
                    {
                        "ic": id_cliente,
                        "idg": id_generador,
                        "fic": fecha_inicio,
                        "ftc": fecha_termino,
                        "ca": costo_arriendo,
                        "ce": costo_envio,
                        "car": 0,
                        "cm": 0
                    }
                )
                id_contrato = result_contrato.fetchone()[0]
                # Actualiza el estado del generador a "En arriendo" (2)
                conn.execute(
                    text("UPDATE generadores SET estado=2 WHERE id_generador=:idg"),
                    {"idg": id_generador}
                )
            st.success("✅ Contrato guardado correctamente y generador marcado como 'En arriendo'")


# 6. Editar Contrato (simple)
elif menu == "Editar Contrato":

    st.subheader("🛠 Editar Contrato")
    contratos = cargar_contratos()
    opciones_contratos = [int(x) for x in contratos["id_contrato"].tolist() if pd.notnull(x)]
    if not opciones_contratos:
        st.warning("No hay contratos disponibles para editar.")
    else:
        contrato_id = st.selectbox("Selecciona un contrato", opciones_contratos)
        contrato_id = int(contrato_id)
        c = contratos[contratos["id_contrato"] == contrato_id].iloc[0]

        def safe_int(val):
            try:
                return int(val) if val is not None else 0
            except Exception:
                return 0

        with st.form("editar_contrato"):
            costo_arriendo = st.number_input("Costo de arriendo", min_value=0, value=safe_int(c["costo_arriendo"]))
            costo_envio = st.number_input("Costo de envío", min_value=0, value=safe_int(c["costo_envio"]))
            costo_arreglo = st.number_input("Costo de arreglo", min_value=0, value=safe_int(c["costo_arreglo"]))
            costo_mantencion = st.number_input("Costo de mantención", min_value=0, value=safe_int(c["costo_mantencion"]))
            col1, col2 = st.columns(2)
            actualizar = col1.form_submit_button("Actualizar contrato")
            eliminar = col2.form_submit_button("Eliminar contrato")

        if actualizar:
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE contrato SET costo_arriendo=:ca, costo_envio=:ce, costo_arreglo=:car, costo_mantencion=:cm WHERE id_contrato=:idc"),
                    {
                        "ca": costo_arriendo,
                        "ce": costo_envio,
                        "car": costo_arreglo,
                        "cm": costo_mantencion,
                        "idc": contrato_id
                    }
                )
            st.success("✅ Contrato actualizado")

        if eliminar:
            st.warning(
                "¿Estás seguro que deseas eliminar este contrato? Esta acción no se puede deshacer.",
                icon="⚠️"
            )
            confirmar_eliminar_contrato = st.checkbox("Confirmo que deseo eliminar este contrato")
            confirmar_click_contrato = st.button("Confirmar eliminación de contrato")
            if confirmar_eliminar_contrato and confirmar_click_contrato:
                with engine.begin() as conn:
                    result = conn.execute(
                        text("DELETE FROM contrato WHERE id_contrato=:idc"),
                        {"idc": contrato_id}
                    )
                if result.rowcount > 0:
                    st.success("🗑️ Contrato eliminado correctamente")
                else:
                    st.warning("No se encontró el contrato para eliminar.")

# 7. Agregar Arreglo o Mantención
elif menu == "Agregar Arreglo o Mantención":
    st.subheader("🔧 Añadir Arreglo o Mantención")
    generadores = cargar_generadores()
    contratos = cargar_contratos()
    codigos = generadores["codigo_interno"].drop_duplicates().dropna().astype(str).tolist()
    generadores_codigos = generadores.set_index("codigo_interno")
    if not codigos:
        st.warning("No hay generadores disponibles para registrar arreglos o mantenciones.")
    else:
        with st.form("form_arreglo"):
            codigo_sel = st.selectbox("Selecciona un generador (por código interno)", codigos)
            id_generador = int(generadores_codigos.loc[codigo_sel]["id_generador"])
            fecha_inicio = st.date_input("Fecha inicio del arreglo/mantención")
            fecha_termino = st.date_input("Fecha término del arreglo/mantención")
            costo = st.number_input("Costo", min_value=0)
            tipo = st.selectbox("Tipo", [1, 2], format_func=lambda x: "Arreglo" if x == 1 else "Mantención")
            submit = st.form_submit_button("Guardar")
            if submit:
                if "id_generador" in contratos.columns:
                    contratos_generador = contratos[contratos["id_generador"] == id_generador]
                else:
                    contratos_generador = pd.DataFrame()
                contratos_afectados = []
                for _, row in contratos_generador.iterrows():
                    if row["fecha_inicio_contrato"] <= fecha_inicio <= row["fecha_termino_contrato"]:
                        contratos_afectados.append(row["id_contrato"])
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO arreglos_y_mantenciones (id_generador, fecha_inicio_arreglo, fecha_termino_arreglo, costo, tipo) VALUES (:idg, :fi, :ft, :c, :t)"),
                        {"idg": id_generador, "fi": fecha_inicio, "ft": fecha_termino, "c": costo, "t": tipo}
                    )
                    for id_contrato in contratos_afectados:
                        if tipo == 1:
                            conn.execute(
                                text("UPDATE contrato SET costo_arreglo = costo_arreglo + :c WHERE id_contrato = :idc"),
                                {"c": costo, "idc": id_contrato}
                            )
                        elif tipo == 2:
                            conn.execute(
                                text("UPDATE contrato SET costo_mantencion = costo_mantencion + :c WHERE id_contrato = :idc"),
                                {"c": costo, "idc": id_contrato}
                            )
                if contratos_afectados:
                    st.success(f"✅ Registro guardado y costo sumado a contratos: {', '.join(str(x) for x in contratos_afectados)}")
                else:
                    st.success("✅ Registro guardado (sin contrato asociado en el periodo)")

# 7b. Visualizar y Editar Arreglos/Mantenciones
elif menu == "Ver/Editar Arreglos o Mantenciones":
    st.subheader("🔍 Ver, Editar o Eliminar Arreglos/Mantenciones")
    arreglos = cargar_arreglos()
    generadores = cargar_generadores()
    if arreglos.empty:
        st.info("No hay arreglos o mantenciones registrados.")
    else:
        generadores_codigos = generadores.set_index("codigo_interno")
        codigos = generadores["codigo_interno"].drop_duplicates().dropna().astype(str).tolist()
        codigo_sel = st.selectbox("Selecciona un generador (por código interno)", codigos)
        if codigo_sel:
            id_generador_sel = generadores_codigos.loc[codigo_sel]["id_generador"]
            arreglos_gen = arreglos[arreglos["id_generador"] == id_generador_sel]
            df_show = arreglos_gen.copy()
            df_show = df_show.merge(generadores[["id_generador", "codigo_interno"]], on="id_generador", how="left")
            st.dataframe(df_show)
            opciones_arreglos = [(int(row["id_generador"]), row["fecha_inicio_arreglo"]) for _, row in arreglos_gen.iterrows()]
            st.markdown("### Editar o Eliminar")
            selected = st.selectbox("Selecciona un registro", opciones_arreglos, format_func=lambda x: f"Generador {x[0]} - {x[1]}")
            if selected:
                row = arreglos_gen[(arreglos_gen["id_generador"] == selected[0]) & (arreglos_gen["fecha_inicio_arreglo"] == selected[1])].iloc[0]
                with st.form("editar_arreglo"):
                    nuevo_costo = st.number_input("Costo", min_value=0, value=int(row["costo"]))
                    nuevo_tipo = st.selectbox("Tipo", [1, 2], index=int(row["tipo"])-1, format_func=lambda x: "Arreglo" if x == 1 else "Mantención")
                    nueva_fecha_inicio = st.date_input("Fecha inicio", value=row["fecha_inicio_arreglo"])
                    nueva_fecha_termino = st.date_input("Fecha término", value=row["fecha_termino_arreglo"])
                    col1, col2 = st.columns(2)
                    actualizar = col1.form_submit_button("Actualizar")
                    eliminar = col2.form_submit_button("Eliminar")
                if actualizar:
                    with engine.begin() as conn:
                        conn.execute(
                            text("UPDATE arreglos_y_mantenciones SET costo=:c, tipo=:t, fecha_inicio_arreglo=:fi, fecha_termino_arreglo=:ft WHERE id_generador=:idg AND fecha_inicio_arreglo=:fi_orig"),
                            {"c": nuevo_costo, "t": nuevo_tipo, "fi": nueva_fecha_inicio, "ft": nueva_fecha_termino, "idg": selected[0], "fi_orig": selected[1]}
                        )
                    st.success("✅ Registro actualizado")
                if eliminar:
                    with engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM arreglos_y_mantenciones WHERE id_generador=:idg AND fecha_inicio_arreglo=:fi"),
                            {"idg": selected[0], "fi": selected[1]}
                        )
                    st.success("🗑️ Registro eliminado")
# 8. Añadir Cliente
elif menu == "Añadir Cliente":
    st.subheader("➕ Añadir Cliente")
    with st.form("form_cliente"):
        rut_empresa = st.text_input("RUT empresa")
        nombre_empresa = st.text_input("Nombre empresa")
        nombre_representante = st.text_input("Nombre representante")
        rut_representante = st.text_input("RUT representante")
        correo = st.text_input("Correo electrónico")
        telefono = st.text_input("Teléfono")
        submit = st.form_submit_button("Guardar cliente")
        if submit:
            rut_empresa_limpio = limpiar_rut(rut_empresa)
            rut_representante_limpio = limpiar_rut(rut_representante)
            if (rut_empresa_limpio is not None and not str(rut_empresa_limpio).isdigit()) or (rut_representante_limpio is not None and not str(rut_representante_limpio).isdigit()):
                st.error("❌ El RUT de la empresa y/o representante debe ser numérico (sin puntos ni guion). Corrige e intenta de nuevo.")
            else:
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO clientes (rut_empresa, nombre_empresa, nombre_representante, rut_representante, correo, telefono) VALUES (:rut_empresa, :nombre_empresa, :nombre_representante, :rut_representante, :correo, :telefono)"),
                        {
                            "rut_empresa": rut_empresa_limpio,
                            "nombre_empresa": nombre_empresa,
                            "nombre_representante": nombre_representante,
                            "rut_representante": rut_representante_limpio,
                            "correo": correo,
                            "telefono": telefono
                        }
                    )
                st.success("✅ Cliente guardado correctamente")
# 9. Eliminar Cliente
elif menu == "Eliminar Cliente":
    st.subheader("🗑️ Eliminar Cliente")
    clientes = cargar_clientes()
    if clientes.empty:
        st.info("No hay clientes para eliminar.")
    else:
        opciones_clientes = [(row["id_cliente"], f"{row['nombre_empresa']} ({row['rut_empresa']})") for _, row in clientes.iterrows()]
        cliente_sel = st.selectbox("Selecciona un cliente", opciones_clientes, format_func=lambda x: x[1])
        confirmar = st.checkbox("Confirmo que deseo eliminar este cliente")
        eliminar = st.button("Eliminar cliente")
        if eliminar and confirmar:
            with engine.begin() as conn:
                result = conn.execute(
                    text("DELETE FROM clientes WHERE id_cliente=:idc"),
                    {"idc": cliente_sel[0]}
                )
            if result.rowcount > 0:
                st.success("🗑️ Cliente eliminado correctamente")
            else:
                st.warning("No se encontró el cliente para eliminar.")
        elif eliminar and not confirmar:
            st.warning("Debes confirmar la eliminación.")

# 10. Análisis Financiero
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
