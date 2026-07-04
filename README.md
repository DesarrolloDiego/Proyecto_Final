# PeruRecetas

Agente de Recetas y Nutricion Peruana con RAG, FAISS, Gemini, Streamlit y consulta a una API externa de comida peruana.

## Componentes

- `Agente_Autónomo_Ver_1_0 (1).ipynb`: notebook principal del proyecto.
- `perurecetas_core.py`: logica del agente, RAG, FAISS, tools y API externa.
- `app.py`: interfaz Streamlit llamada PeruRecetas.
- `recetarios/`: cinco TXT etiquetados usados como dataset RAG.
- `dataset_rag/`: descripcion del dataset.
- `run_pruebas.py`: pruebas del proyecto.
- `generar_informe.py`: genera informe Word y PDF.

## Configuracion

1. Crear un entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear `.env` tomando `.env.example` como referencia:

```bash
GOOGLE_API_KEY=tu_clave
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-001
ALLOW_LOCAL_EMBEDDING_FALLBACK=1
```

Si la cuota de embeddings de Gemini se agota durante la construccion del indice,
el proyecto puede usar embeddings locales por hashing para demostrar FAISS:

```bash
GEMINI_EMBEDDING_MODEL=local-hash
```

## Construir FAISS

```python
from perurecetas_core import PeruRecetasFAISS

rag = PeruRecetasFAISS()
rag.construir(force=True)
```

## Ejecutar Streamlit

```bash
streamlit run app.py
```

## Guia rapida de consultas

### Consultar la API

Para que el chat use la API externa, escribe una region del Peru, un ingrediente y un limite de resultados:

```text
Dame 3 platos de Arequipa con cerdo
Arequipa aji 5
Platos de Lima con pollo limite 2
```

### Consultar los recetarios TXT

Para que el chat use los documentos locales, menciona `TXT`, `RAG`, `recetario`, `recetarios` o `documentos`, junto con el nombre de la receta o ingrediente:

```text
Busca en recetarios TXT ENSALADA DE OCORURO
Ingredientes de la ensalada de ocoruro segun los documentos
Preparacion de watya en el recetario
Busca en recetario5.txt ADOBO AREQUIPEÑO
Busca en recetario4.txt PAICHE ENVUELTO EN HOJA DE BIJAO
```

## Ejecutar pruebas

Pruebas locales sin API/LLM:

```bash
python run_pruebas.py --offline
```

Pruebas completas:

```bash
python run_pruebas.py
```
