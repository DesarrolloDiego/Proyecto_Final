# Dataset RAG

El dataset RAG del proyecto esta compuesto por los cinco archivos TXT etiquetados ubicados en:

- `recetarios/recetario1.txt`
- `recetarios/recetario2.txt`
- `recetarios/recetario3.txt`
- `recetarios/recetario4.txt`
- `recetarios/recetario5.txt`

Cada receta esta delimitada por `<<<RECETA_INICIO>>>` y `<<<RECETA_FIN>>>`,
con campos estandarizados como `NOMBRE`, `INGREDIENTES`, `PREPARACION` y
`ETIQUETAS`. Estos bloques se dividen en chunks y se indexan en FAISS con
embeddings de Gemini (`models/gemini-embedding-001`).

Si la cuota de Gemini no esta disponible, se puede construir un indice FAISS de
demostracion con `GEMINI_EMBEDDING_MODEL=local-hash`.

El indice generado se guarda en `vectorstore/`:

- `vectorstore/perurecetas.faiss`
- `vectorstore/chunks.json`
- `vectorstore/catalogo_recetarios.json`

Para construir el indice desde el notebook o desde Python:

```python
from perurecetas_core import PeruRecetasFAISS

rag = PeruRecetasFAISS()
rag.construir(force=True)
```
