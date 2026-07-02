from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "Agente_Autónomo_Ver_1_0 (1).ipynb"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip().splitlines(True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(True),
    }


cells = [
    md(
        """
# PeruRecetas

**Agente de Recetas y Nutricion Peruana con RAG, FAISS y API externa**

Proyecto del curso Redes Neuronales Artificiales.

Integrantes:
- GIOVANNI FRANCO LUCA BARCENA ALDAVE
- DIEGO ALONSO MERINO CASTAÑEDA

Docente: EDUARDO YAURI LOZANO

Fecha de entrega: 04/07/2026
"""
    ),
    md(
        """
## 1. Objetivo

Implementar un agente AI sobre recetas y nutricion peruana que cumpla el flujo solicitado:

1. Agente LLM con Gemini.
2. Memoria de contexto.
3. Tools de Python con docstrings.
4. RAG con documentos reales en TXT etiquetados usando FAISS.
5. Pruebas del agente y de sus componentes.
6. Mejoramiento de tools mediante consulta de informacion a una API externa.
"""
    ),
    md(
        """
## 2. Instalacion de dependencias

Ejecutar una sola vez en el entorno de trabajo:

```bash
pip install -r requirements.txt
```

El archivo `.env` debe contener:

```bash
GOOGLE_API_KEY=tu_clave_de_google_ai_studio
GEMINI_MODEL=gemini-2.5-flash
```
"""
    ),
    code(
        """
from pathlib import Path

from perurecetas_core import (
    AgenteRecetas,
    PeruRecetasFAISS,
    catalogar_dataset,
    consultar_api_comida_peru,
    listar_regiones_api,
    recomendar_recetas_por_ingrediente,
    sugerir_sustitucion_ingredientes,
)

print("Modulos del proyecto cargados correctamente.")
"""
    ),
    md(
        """
## 3. Dataset RAG

Los documentos reales se encuentran en la carpeta `recetarios/`. El proyecto usa cinco TXT etiquetados como base documental para el RAG.
"""
    ),
    code(
        """
catalogo = catalogar_dataset()
catalogo
"""
    ),
    md(
        """
## 4. Construccion del indice FAISS

Esta celda lee los TXT etiquetados, divide las recetas en chunks, genera embeddings con Gemini y guarda el indice FAISS en `vectorstore/`.
"""
    ),
    code(
        """
rag = PeruRecetasFAISS()

# Ejecutar force=True cuando se quiera reconstruir el indice desde cero.
rag.construir(force=True)

print("Indice FAISS construido y guardado en vectorstore/.")
"""
    ),
    md(
        """
## 5. Tools locales

El agente incluye tools para recomendar recetas por ingrediente y sugerir sustituciones.
"""
    ),
    code(
        """
print(recomendar_recetas_por_ingrediente("pollo, papa, aji amarillo"))
print(sugerir_sustitucion_ingredientes("papa"))
"""
    ),
    md(
        """
## 6. Tool de API externa

El mejoramiento de tools se cumple consultando informacion desde la API de comida peruana:

https://api-comida-peru.luisgagocasas.com/
"""
    ),
    code(
        """
print(listar_regiones_api())
print()
print(consultar_api_comida_peru(region="arequipa", ingrediente="aji", limite=3))
"""
    ),
    md(
        """
## 7. Prueba de recuperacion RAG

La consulta se transforma en embedding y FAISS devuelve los chunks mas cercanos semanticamente.
"""
    ),
    code(
        """
rag = PeruRecetasFAISS()
rag.cargar()

resultados = rag.buscar("recetas peruanas con papa y aji", top_k=3)
for r in resultados:
    print(f"Fuente: {r['source']} | receta etiquetada | score: {r['score']:.3f}")
    print(r["text"][:500])
    print("-" * 80)
"""
    ),
    md(
        """
## 8. Agente con memoria, RAG, tools y LLM

`AgenteRecetas` integra:

- Memoria conversacional.
- Recuperacion FAISS/RAG.
- Tools locales.
- Consulta de API externa.
- Respuesta final con Gemini.
- Uso de AIsuite como cliente unificado cuando esta disponible, con fallback al SDK de Gemini.
"""
    ),
    code(
        """
agente = AgenteRecetas(cargar_indice=True)

respuesta = agente.enviar_mensaje(
    "Quiero una receta peruana con papa. Usa los recetarios si encuentras informacion relevante."
)
print(respuesta)
"""
    ),
    code(
        """
respuesta = agente.enviar_mensaje(
    "Recuerda mi pedido anterior y dame una alternativa mas saludable."
)
print(respuesta)

agente.historial()
"""
    ),
    md(
        """
## 9. Cinco pruebas del proyecto

Las pruebas cubren dataset, normalizacion de region, tool local, chunking, API externa, RAG FAISS y memoria del agente.

Para pruebas locales sin API/LLM:

```bash
python run_pruebas.py --offline
```

Para pruebas completas:

```bash
python run_pruebas.py
```
"""
    ),
    code(
        """
from run_pruebas import ejecutar

# Pruebas offline: no llaman API externa, FAISS ni LLM.
resultados_offline = ejecutar(offline=True)
resultados_offline
"""
    ),
    code(
        """
# Pruebas completas. Requieren dependencias, GOOGLE_API_KEY, FAISS, red y modelo Gemini.
resultados_completos = ejecutar(offline=False)
resultados_completos
"""
    ),
    md(
        """
## 10. Interfaz Streamlit

La interfaz web se llama **PeruRecetas** e incluye:

- Chat del agente.
- Consulta directa a la API por region/ingrediente.
- Visualizacion de documentos recuperados por FAISS.
- Historial de conversacion.

Ejecutar desde terminal:

```bash
streamlit run app.py
```
"""
    ),
]


notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.12",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Notebook generado: {NOTEBOOK_PATH}")
