from __future__ import annotations

from pathlib import Path

import streamlit as st

from perurecetas_core import (
    AgenteRecetas,
    catalogar_dataset,
    consultar_api_comida_peru,
    detectar_region_en_texto,
    listar_regiones_api,
    obtener_api_key,
    slug_region,
)


BASE_DIR = Path(__file__).resolve().parent
BANNER_PATH = BASE_DIR / "assets" / "banner.png"

CUSTOM_CSS = """
<style>
:root {
    --ink: #1f211d;
    --muted: #5f6b62;
    --paper: #fffcf7;
    --surface: #ffffff;
    --surface-soft: #f2f7f4;
    --line: #dce8df;
    --primary: #b23a2b;
    --primary-dark: #7d251e;
    --accent: #2f6f5e;
    --accent-dark: #173d34;
    --gold: #c9972f;
}

html, body, [class*="css"] {
    font-family: Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background:
        linear-gradient(180deg, rgba(255, 252, 247, 0.96) 0%, rgba(242, 247, 244, 0.98) 48%, #ffffff 100%);
    color: var(--ink);
}

.block-container {
    max-width: 1180px;
    padding-top: 1.6rem;
    padding-bottom: 3rem;
}

h1, h2, h3, p, label, span, div {
    letter-spacing: 0;
}

.app-header {
    padding: 0.2rem 0 0.9rem;
}

.app-header h1 {
    color: var(--ink);
    font-size: 3.4rem;
    line-height: 1;
    margin: 0;
    font-weight: 850;
}

.app-header p {
    color: var(--muted);
    font-size: 1.04rem;
    line-height: 1.55;
    margin: 0.8rem 0 0;
    max-width: 760px;
}

[data-testid="stImage"] img {
    width: 100%;
    height: 320px;
    object-fit: cover;
    border: 1px solid rgba(47, 111, 94, 0.18);
    border-radius: 18px;
    box-shadow: 0 18px 44px rgba(31, 33, 29, 0.14);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #173d34 0%, #102a25 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.12);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
    color: #f8f7ef;
}

.sidebar-brand {
    padding: 0.2rem 0 0.75rem;
}

.sidebar-brand strong {
    display: block;
    font-size: 1.35rem;
    line-height: 1.1;
    margin-bottom: 0.35rem;
}

.sidebar-brand span {
    color: rgba(248, 247, 239, 0.72) !important;
    font-size: 0.9rem;
}

.status-card {
    align-items: center;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 12px;
    display: flex;
    justify-content: space-between;
    margin: 0.6rem 0 1rem;
    padding: 0.8rem 0.85rem;
}

.status-card span {
    color: rgba(248, 247, 239, 0.78) !important;
    font-size: 0.86rem;
}

.status-ok,
.status-warn {
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
    padding: 0.22rem 0.6rem;
}

.status-ok {
    background: #dff4e8;
    color: #174d37 !important;
}

.status-warn {
    background: #fff1c7;
    color: #6f4300 !important;
}

[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 12px;
    padding: 0.8rem;
}

[data-testid="stSidebar"] [data-testid="stMetricLabel"] p {
    color: rgba(248, 247, 239, 0.72) !important;
}

[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #ffffff;
    font-weight: 850;
}

[data-testid="stSidebar"] .stButton > button {
    background: #eef6f1;
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: var(--accent-dark) !important;
    font-weight: 800;
}

[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    color: var(--accent-dark) !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--primary);
    color: #ffffff !important;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] p,
[data-testid="stSidebar"] .stButton > button[kind="primary"] span {
    color: #ffffff !important;
}

.section-heading {
    margin: 1rem 0 1rem;
}

.section-heading h2 {
    color: var(--ink);
    font-size: 1.45rem;
    font-weight: 820;
    line-height: 1.2;
    margin: 0;
}

.section-heading p {
    color: var(--muted);
    margin: 0.35rem 0 0;
}

.stTabs [data-baseweb="tab-list"] {
    background: rgba(47, 111, 94, 0.08);
    border: 1px solid var(--line);
    border-radius: 14px;
    gap: 0.25rem;
    padding: 0.35rem;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    color: var(--muted);
    font-weight: 800;
    height: 2.6rem;
    padding: 0 1rem;
}

.stTabs [aria-selected="true"] {
    background: #ffffff;
    box-shadow: 0 8px 20px rgba(31, 33, 29, 0.08);
    color: var(--primary-dark);
}

.stButton > button {
    border-radius: 10px;
    font-weight: 800;
    min-height: 2.72rem;
}

.stTextInput input,
.stNumberInput input {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 10px;
}

.stTextInput input:focus,
.stNumberInput input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 0.18rem rgba(47, 111, 94, 0.14);
}

[data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(220, 232, 223, 0.96);
    border-radius: 16px;
    box-shadow: 0 10px 28px rgba(31, 33, 29, 0.06);
    margin: 0.75rem 0;
    padding: 0.75rem 0.9rem;
}

[data-testid="stChatInput"] {
    border-top: 1px solid rgba(220, 232, 223, 0.7);
}

[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
}

[data-testid="stDataFrame"],
[data-testid="stJson"] {
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
}

pre {
    border: 1px solid rgba(47, 111, 94, 0.18) !important;
    border-radius: 12px !important;
}

hr {
    border-color: rgba(47, 111, 94, 0.14);
}

@media (max-width: 700px) {
    .block-container {
        padding-top: 1rem;
    }

    .app-header h1 {
        font-size: 2.35rem;
    }

    .app-header p {
        font-size: 0.98rem;
    }

    [data-testid="stImage"] img {
        height: 220px;
        border-radius: 14px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0 0.65rem;
    }
}
</style>
"""


st.set_page_config(
    page_title="PeruRecetas",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <section class="app-header">
        <h1>PeruRecetas</h1>
        <p>Recetas, regiones e ingredientes conectados al dataset RAG del proyecto.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
st.image(str(BANNER_PATH), width="stretch")


def section_heading(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="section-heading">
            <h2>{title}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def api_key_ok() -> bool:
    try:
        obtener_api_key()
        return True
    except Exception:
        return False


with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <strong>PeruRecetas</strong>
            <span>Panel de proyecto</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    api_ready = api_key_ok()
    status_label = "Lista" if api_ready else "Pendiente"
    status_class = "status-ok" if api_ready else "status-warn"
    st.markdown(
        f"""
        <div class="status-card">
            <span>Google API key</span>
            <strong class="{status_class}">{status_label}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    catalogo = catalogar_dataset()
    total_recetas = sum(item.get("recetas", 0) for item in catalogo)
    col_txt, col_recetas = st.columns(2)
    col_txt.metric("TXT RAG", len(catalogo))
    col_recetas.metric("Recetas", total_recetas)
    st.divider()

    if "agente" not in st.session_state:
        st.session_state.agente = AgenteRecetas(cargar_indice=True)

    if st.button("Reconstruir indice FAISS", type="primary", width="stretch"):
        with st.spinner("Construyendo indice desde los TXT etiquetados..."):
            try:
                st.session_state.agente.construir_indice(force=True)
                st.success("Indice FAISS construido correctamente.")
            except Exception as exc:
                st.error(f"No se pudo construir el indice: {exc}")

    if st.button("Reiniciar memoria", width="stretch"):
        st.session_state.agente.reset()
        st.success("Memoria reiniciada.")


tab_chat, tab_api, tab_rag, tab_historial = st.tabs(
    ["Chat", "Consulta API", "RAG", "Historial"]
)


with tab_chat:
    section_heading("Chat del agente")

    with st.expander("Guia rapida de consultas"):
        st.markdown(
            """
            **Para consultar la API**

            Escribe una region del Peru, un ingrediente y un limite de resultados.

            - `Dame 3 platos de Arequipa con cerdo`
            - `Arequipa aji 5`
            - `Platos de Lima con pollo limite 2`

            **Para consultar los recetarios TXT**

            Menciona `TXT`, `RAG`, `recetario`, `recetarios` o `documentos`, junto con el nombre de la receta o ingrediente.

            - `Busca en recetarios TXT ENSALADA DE OCORURO`
            - `Ingredientes de la ensalada de ocoruro segun los documentos`
            - `Preparacion de watya en el recetario`
            - `Busca en recetario5.txt ADOBO AREQUIPEÑO`
            - `Busca en recetario4.txt PAICHE ENVUELTO EN HOJA DE BIJAO`
            """
        )

    for msg in st.session_state.agente.historial():
        rol = "user" if msg["role"] == "usuario" else "assistant"
        with st.chat_message(rol):
            st.write(msg["content"])

    pregunta = st.chat_input("Pregunta por una receta o region...")

    if pregunta:
        with st.chat_message("user"):
            st.write(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Consultando RAG, API y modelo..."):
                try:
                    respuesta = st.session_state.agente.enviar_mensaje(pregunta)
                    st.write(respuesta)
                except Exception as exc:
                    st.error(f"No se pudo generar respuesta: {exc}")


with tab_api:
    section_heading("Consulta directa a la API")

    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 1, 0.62])
        with col1:
            region = st.text_input("Region", value="arequipa")
        with col2:
            ingrediente = st.text_input("Ingrediente", value="aji")
        with col3:
            limite = st.number_input("Limite", min_value=1, max_value=10, value=5)

        col_tipo, col_consulta = st.columns(2)
        with col_tipo:
            tipo = st.text_input("Tipo de plato opcional", value="")
        with col_consulta:
            consulta = st.text_input("Busqueda libre opcional", value="")

        if st.button("Consultar API", type="primary", width="stretch"):
            with st.spinner("Consultando API externa..."):
                try:
                    respuesta_api = consultar_api_comida_peru(
                        region=region,
                        ingrediente=ingrediente or None,
                        tipo=tipo or None,
                        consulta=consulta or None,
                        limite=int(limite),
                    )
                    st.code(respuesta_api, language="text")
                except Exception as exc:
                    st.error(f"Error al consultar API: {exc}")

    with st.expander("Regiones disponibles"):
        try:
            st.write(listar_regiones_api())
        except Exception as exc:
            st.warning(f"No se pudieron cargar regiones: {exc}")


with tab_rag:
    section_heading("Recetas TXT recuperadas con FAISS")

    with st.container(border=True):
        consulta_rag = st.text_input(
            "Consulta para RAG",
            value="receta de papa rellena ingredientes preparacion",
        )
        top_k = st.slider("Recetas recuperadas", min_value=1, max_value=8, value=4)

        col_buscar, col_recargar = st.columns([2, 1])
        buscar = col_buscar.button(
            "Buscar en TXT etiquetados",
            type="primary",
            width="stretch",
        )
        recargar = col_recargar.button("Recargar indice TXT", width="stretch")

    if recargar:
        try:
            st.session_state.agente.rag.cargar()
            st.success("Indice FAISS recargado desde vectorstore/ con recetas TXT.")
        except Exception as exc:
            st.error(f"No se pudo recargar el indice: {exc}")

    if buscar:
        with st.spinner("Buscando recetas etiquetadas en el indice FAISS..."):
            try:
                # Evita usar un indice viejo que haya quedado en memoria antes de migrar de PDF a TXT.
                st.session_state.agente.rag.cargar()
                resultados = st.session_state.agente.rag.buscar(consulta_rag, top_k=top_k)
                for item in resultados:
                    st.markdown(
                        f"**{item['source']} - TXT etiquetado** "
                        f"(score {item['score']:.3f})"
                    )
                    st.code(item["text"][:1600], language="text")
                    st.divider()
            except Exception as exc:
                st.error(f"No se pudo consultar el RAG: {exc}")

    with st.expander("Catalogo del dataset RAG en TXT"):
        st.dataframe(catalogo, width="stretch")


with tab_historial:
    section_heading("Historial de conversacion")
    historial = st.session_state.agente.historial()
    if not historial:
        st.info("Aun no hay mensajes.")
    else:
        st.json(historial)
