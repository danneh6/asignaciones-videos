import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px

# Configuración de página
st.set_page_config(layout="wide", page_title="Asignación de Videos")

# CSS para ocultar los botones internos de los number_input y también los de Streamlit
st.markdown("""
    <style>
    /* Oculta los botones de incremento/decremento internos del navegador */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    input[type=number] {
        -moz-appearance: textfield; /* Firefox */
    }
    /* Oculta los botones personalizados que genera Streamlit */
    div[data-baseweb="input"] button {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.title("📊 Asignación de Videos a Revisores")

# --- Subir archivo CSV ---
uploaded_file = st.file_uploader("Cargar reporte diario (CSV)", type="csv")

# Lista inicial de revisores
lista_original_revisores = [
    "antonia.cutino@iie.cl","antonia.rios@iie.cl","claudia.sanjuan@iie.cl",
    "diego.moya@iie.cl","daniela.medel@iie.cl", "alexandra.castro@iie.cl",
    "isabella.iubini@iie.cl","javiera.arriagada@iie.cl","katherine.marilaf@iie.cl",
    "javiera.narvaez@iie.cl","maria.salinas@iie.cl","mariela.arevalo@iie.cl",
    "kerim.segura@iie.cl","pamela.alarcon@iie.cl","pedro.salinas@iie.cl",
    "rebeca.benavides@iie.cl","rocio.betancur@iie.cl","rocio.concha@iie.cl",
    "rocio.vasquez@iie.cl","rodrigo.zamorano@iie.cl","stefany.leon@iie.cl",
    "tomas.andrade@iie.cl","valeria.henriquezvilla@iie.cl","veronica.gutierrez@iie.cl",
    "ximena.bastias@iie.cl","pablo.casanueva@iie.cl","pavlo.saldano@iie.cl","valentina.altamirano@iie.cl","valentina.altamirano@iie.cl",
    "amapola.cirano@iie.cl","lukas.redel@iie.cl","antonia.lomboy@iie.cl", "carol.nova@iie.cl"
]
# Lista de revisores en session_state
if "revisores" not in st.session_state:
    st.session_state["revisores"] = lista_original_revisores.copy()

# Revisores que se omiten del Top3
omitidos_top3 = [
    "daniela.jara@iie.cl", "daniela.sanhueza@iie.cl", "gabriela.forte@iie.cl",
    "leslie.segura@iie.cl", "natalia.espinoza@iie.cl", "pamela.alarcon@iie.cl",
    "veronica.gutierrez@iie.cl"
]

# Estado de asignaciones temporalesvalentina.altamirano@iie.cl
if "asignaciones" not in st.session_state:
    st.session_state["asignaciones"] = []

if uploaded_file is not None:
    try:
        # Leer CSV
        df = pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=None, engine="python")
        df.columns = df.columns.str.strip().str.replace('"', "").str.replace("﻿", "")

        # ✅ Crear columna "llave" y eliminar duplicados
        if all(col in df.columns for col in ["id_revision", "estado_nombre", "tipo_incidencia"]):
            df["llave"] = (
                df["id_revision"].astype(str)
                + df["estado_nombre"].astype(str)
                + df["tipo_incidencia"].astype(str)
            )
            antes = len(df)
            df = df.drop_duplicates(subset=["llave"])
            eliminados = antes - len(df)
            st.success(f"🔑 Columna 'llave' creada. Se eliminaron {eliminados} duplicados basados en esa combinación.")
        else:
            st.warning("⚠️ No se encontraron todas las columnas necesarias para generar la llave (id_revision, estado_nombre, tipo_incidencia).")

        # Pendientes sin revisor
        pendientes_sin_revisor = df[
            (df["revisor"].isna()) & (df["estado_nombre"] == "pendiente_de_revision")
        ]
        pendientes_sin_revisor = pendientes_sin_revisor.drop_duplicates(subset=["rut_docente"])
        pendientes_shuffled = pendientes_sin_revisor.sample(frac=1, random_state=42).reset_index(drop=True)

        # Layout columnas: izquierda (ranking + asignación), derecha (Top3 + gráficos)
        col_left, col_right = st.columns([3,1])

        # Función para limpiar nombre de email
        def nombre_limpio(email):
            return email.split("@")[0].replace(".", " ").title()

        # Columna izquierda
        with col_left:
            # Ranking de carga
            resumen = []
            for rev in st.session_state["revisores"]:
                df_rev = df[df["revisor"] == rev]
                revisados = df_rev[df_rev["estado_nombre"].isin(["sin_incidencias","con_incidencias_a_revisar"])].shape[0]
                en_revision = df_rev[df_rev["estado_nombre"] == "en_revision"].shape[0]
                pendientes_asignados = df_rev[df_rev["estado_nombre"] == "pendiente_de_revision"].shape[0]
                resumen.append({
                    "revisor": rev,
                    "revisados": revisados,
                    "en_revision": en_revision,
                    "pendientes_asignados": pendientes_asignados
                })
            resumen_df = pd.DataFrame(resumen).sort_values("pendientes_asignados", ascending=False)
            st.subheader("📊 Ranking de carga por revisor")
            st.dataframe(resumen_df, use_container_width=True)

            # Asignación manual con contador dinámico
            st.subheader("⚖️ Asignación manual")

            # Inicializar selección temporal si no existe
            if "seleccion_temporal" not in st.session_state:
                st.session_state["seleccion_temporal"] = {rev: 0 for rev in st.session_state["revisores"]}

            # Campo para agregar nuevos revisores
            nuevo_revisor = st.text_input("➕ Agregar nuevo revisor (correo electrónico)")
            if st.button("Agregar revisor"):
                if not nuevo_revisor:
                    st.error("❌ Debes ingresar un correo.")
                elif not nuevo_revisor.endswith("@iie.cl"):
                    st.error("⚠️ Solo se permiten correos con dominio @iie.cl")
                elif nuevo_revisor in st.session_state["revisores"]:
                    st.warning("⚠️ Ese revisor ya existe en la lista.")
                else:
                    st.session_state["revisores"].append(nuevo_revisor)
                    st.session_state["seleccion_temporal"][nuevo_revisor] = 0
                    st.success(f"✅ Revisor agregado: {nuevo_revisor}")

            # Opción para eliminar revisores agregados manualmente
            revisores_agregados = [rev for rev in st.session_state["revisores"] if rev not in lista_original_revisores]
            if revisores_agregados:
                st.markdown("### 🗑️ Eliminar revisores agregados manualmente")
                revisor_a_eliminar = st.selectbox("Selecciona revisor a eliminar", revisores_agregados)
                if st.button("Eliminar revisor"):
                    st.session_state["revisores"].remove(revisor_a_eliminar)
                    if revisor_a_eliminar in st.session_state["seleccion_temporal"]:
                        del st.session_state["seleccion_temporal"][revisor_a_eliminar]
                    st.success(f"🗑️ Revisor eliminado: {revisor_a_eliminar}")

            # Total de pendientes
            pendientes_restantes = len(pendientes_sin_revisor) - len(st.session_state["asignaciones"])

            # Función para recalcular max_value
            def actualizar_maximos():
                totales_seleccionados = sum(st.session_state["seleccion_temporal"].values())
                maximos = {}
                for rev in st.session_state["revisores"]:
                    max_valor = pendientes_restantes - totales_seleccionados + st.session_state["seleccion_temporal"][rev]
                    maximos[rev] = max(max_valor, 0)
                return maximos

            maximos_revisores = actualizar_maximos()

            # Mostrar cada revisor en fila unificada con input
            for revisor in st.session_state["revisores"]:
                carga_actual = int(resumen_df.loc[resumen_df["revisor"] == revisor, "pendientes_asignados"].values[0]) if revisor in resumen_df["revisor"].values else 0
                cantidad_actual = st.session_state["seleccion_temporal"].get(revisor, 0)
                maximo = maximos_revisores[revisor]

                with st.container():
                    col_name, col_input = st.columns([3,2])
                    with col_name:
                        st.markdown(f"**{nombre_limpio(revisor)}** (ya tiene {carga_actual} pendientes asignados)")
                    with col_input:
                        cantidad = st.number_input(
                            "",
                            min_value=0,
                            max_value=maximo,
                            value=cantidad_actual,
                            step=1,
                            key=f"num_{revisor}"
                        )
                    st.session_state["seleccion_temporal"][revisor] = cantidad
                    maximos_revisores = actualizar_maximos()

            # Contador flotante siempre presente
            pendientes_aun = pendientes_restantes - sum(st.session_state["seleccion_temporal"].values())
            if pendientes_aun > 5:
                color = "#d4edda"
            elif 2 <= pendientes_aun <= 5:
                color = "#fff3cd"
            else:
                color = "#f8d7da"
            st.markdown(
                f"""<div style="position: fixed; bottom: 20px; right: 20px; background-color:{color}; padding:20px; border-radius:15px; border:2px solid #ff9900; text-align:center; font-size:20px; font-weight:bold; z-index:999;">
                ⚠️ Videos pendientes sin asignar: {pendientes_aun}
                </div>""",
                unsafe_allow_html=True
            )

            # Botón para asignar videos
            if st.button("▶️ Asignar videos seleccionados"):
                for revisor, cant in st.session_state["seleccion_temporal"].items():
                    if cant > 0:
                        seleccionados = pendientes_sin_revisor.head(cant)
                        pendientes_sin_revisor = pendientes_sin_revisor.iloc[cant:]
                        for rut in seleccionados["rut_docente"].tolist():
                            if rut not in [x["rut_docente"] for x in st.session_state["asignaciones"]]:
                                st.session_state["asignaciones"].append({"id_revisor": revisor, "rut_docente": rut})
                        st.session_state["seleccion_temporal"][revisor] = 0

            # Mostrar asignaciones
            if st.session_state["asignaciones"]:
                resultado = pd.DataFrame(st.session_state["asignaciones"])
                st.subheader("📄 Vista previa de asignaciones")
                st.dataframe(resultado.head(20))
                csv_buffer = BytesIO()
                resultado.to_csv(csv_buffer, index=False, sep=";")
                st.download_button(
                    label="⬇️ Descargar CSV de asignaciones",
                    data=csv_buffer.getvalue(),
                    file_name="asignaciones.csv",
                    mime="text/csv"
                )

        # Columna derecha (Top3 y gráficos)
        with col_right:
            df_top = df[~df["revisor"].isin(omitidos_top3)]
            df_aprobado = df_top[df_top["estado_incidencia"] == "Aprobado"]
            top_aprobado = df_aprobado.groupby("revisor").size() / df_top.groupby("revisor").size() * 100
            top_aprobado = top_aprobado.dropna().sort_values(ascending=False).head(3).round(0).astype(int)
            st.subheader("🏆 Top 3 incidencias aprobadas")
            for rev, pct in top_aprobado.items():
                st.markdown(f"""<div style="background-color:#cde8ff;padding:10px;border-radius:10px;margin-bottom:5px;text-align:center;font-weight:bold;">{nombre_limpio(rev)}<br>{pct}%</div>""", unsafe_allow_html=True)

            df_no_aprobado = df_top[df_top["estado_incidencia"] == "No Aprobado"]
            top_no_aprobado = df_no_aprobado.groupby("revisor").size() / df_top.groupby("revisor").size() * 100
            top_no_aprobado = top_no_aprobado.dropna().sort_values(ascending=False).head(3).round(0).astype(int)
            st.subheader("🏆 Top 3 incidencias no aprobadas")
            for rev, pct in top_no_aprobado.items():
                st.markdown(f"""<div style="background-color:#ffc9c9;padding:10px;border-radius:10px;margin-bottom:5px;text-align:center;font-weight:bold;">{nombre_limpio(rev)}<br>{pct}%</div>""", unsafe_allow_html=True)

            df_videos = df.drop_duplicates(subset=["rut_docente"])
            revisados = df_videos[df_videos["estado_nombre"].isin(["sin_incidencias","con_incidencias_a_revisar"])].shape[0]
            en_revision = df_videos[df_videos["estado_nombre"] == "en_revision"].shape[0]
            pendiente_total = df_videos[df_videos["estado_nombre"] == "pendiente_de_revision"].shape[0]

            fig_torta = px.pie(
                names=["Revisados", "En revisión", "Pendientes"],
                values=[revisados, en_revision, pendiente_total],
                color=["Revisados", "En revisión", "Pendientes"],
                color_discrete_map={"Revisados": "#a1d99b", "En revisión": "#9ecae1", "Pendientes": "#fdae6b"},
                title="📊 Distribución de videos"
            )
            fig_torta.update_traces(textinfo="label+value", textfont_size=14)
            st.plotly_chart(fig_torta, use_container_width=True)

            # Top 3 incidencias por tipo
            df_top_tipo = df[df["estado_incidencia"] == "Aprobado"]
            top_tipo_aprobado = df_top_tipo.groupby("tipo_incidencia").size() / len(df_top_tipo) * 100
            top_tipo_aprobado = top_tipo_aprobado.sort_values(ascending=False).head(3).round(0).astype(int)
            st.subheader("🏆 Top 3 incidencias aprobadas por tipo")
            for tipo, pct in top_tipo_aprobado.items():
                st.markdown(f"""<div style="background-color:#cde8ff;padding:10px;border-radius:10px;margin-bottom:5px;text-align:center;font-weight:bold;">{tipo}<br>{pct}%</div>""", unsafe_allow_html=True)

            df_top_tipo_na = df[df["estado_incidencia"] == "No Aprobado"]
            top_tipo_no_aprobado = df_top_tipo_na.groupby("tipo_incidencia").size() / len(df_top_tipo_na) * 100
            top_tipo_no_aprobado = top_tipo_no_aprobado.sort_values(ascending=False).head(3).round(0).astype(int)
            st.subheader("🏆 Top 3 incidencias no aprobadas por tipo")
            for tipo, pct in top_tipo_no_aprobado.items():
                st.markdown(f"""<div style="background-color:#ffc9c9;padding:10px;border-radius:10px;margin-bottom:5px;text-align:center;font-weight:bold;">{tipo}<br>{pct}%</div>""", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
