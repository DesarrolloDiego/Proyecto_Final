from __future__ import annotations

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


st.set_page_config(
    page_title="PeruRecetas",
    page_icon="P",
    layout="wide",
)

st.title("PeruRecetas")
st.caption("Agente de recetas y nutricion peruana con RAG, FAISS, Gemini y API externa.")


def api_key_ok() -> bool:
    try:
        obtener_api_key()
        return True
    except Exception:
        return False


with st.sidebar:
    st.header("Proyecto")
    st.write("Estado de configuracion")
    st.write(f"Google API key: {'lista' if api_key_ok() else 'pendiente'}")
    catalogo = catalogar_dataset()
    total_recetas = sum(item.get("recetas", 0) for item in catalogo)
    st.write(f"TXT RAG: {len(catalogo)}")
    st.write(f"Recetas etiquetadas: {total_recetas}")
    st.divider()

    if "agente" not in st.session_state:
        st.session_state.agente = AgenteRecetas(cargar_indice=True)

    if st.button("Reconstruir indice FAISS"):
        with st.spinner("Construyendo indice desde los TXT etiquetados..."):
            try:
                st.session_state.agente.construir_indice(force=True)
                st.success("Indice FAISS construido correctamente.")
            except Exception as exc:
                st.error(f"No se pudo construir el indice: {exc}")

    if st.button("Reiniciar memoria"):
        st.session_state.agente.reset()
        st.success("Memoria reiniciada.")


tab_chat, tab_api, tab_rag, tab_historial = st.tabs(
    ["Chat", "Consulta API", "RAG", "Historial"]
)


with tab_chat:
    st.subheader("Chat del agente")
    pregunta = st.chat_input("Pregunta por recetas, nutricion o platos por region...")
    for msg in st.session_state.agente.historial():
        rol = "user" if msg["role"] == "usuario" else "assistant"
        with st.chat_message(rol):
            st.write(msg["content"])

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
    st.subheader("Consulta directa a la API de comida peruana")
    col1, col2, col3 = st.columns(3)
    with col1:
        region = st.text_input("Region", value="arequipa")
    with col2:
        ingrediente = st.text_input("Ingrediente", value="aji")
    with col3:
        limite = st.number_input("Limite", min_value=1, max_value=10, value=5)

    tipo = st.text_input("Tipo de plato opcional", value="")
    consulta = st.text_input("Busqueda libre opcional", value="")

    if st.button("Consultar API"):
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
    st.subheader("Recetas TXT recuperadas con FAISS")
    consulta_rag = st.text_input("Consulta para RAG", value="receta de papa rellena ingredientes preparacion")
    top_k = st.slider("Recetas recuperadas", min_value=1, max_value=8, value=4)

    col_buscar, col_recargar = st.columns([2, 1])
    buscar = col_buscar.button("Buscar en TXT etiquetados")
    recargar = col_recargar.button("Recargar indice TXT")

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
        st.dataframe(catalogar_dataset(), use_container_width=True)


with tab_historial:
    st.subheader("Historial de conversacion")
    historial = st.session_state.agente.historial()
    if not historial:
        st.info("Aun no hay mensajes.")
    else:
        st.json(historial)
