"""
Nucleo del proyecto PeruRecetas.

Incluye:
- Carga de variables de entorno.
- Lectura de TXT etiquetados del dataset RAG.
- Construccion y consulta de un indice FAISS con embeddings de Gemini.
- Tools del agente, incluida la consulta a la API externa de comida peruana.
- Agente conversacional con memoria, contexto RAG y uso de LLM Gemini.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import unicodedata
import urllib.parse
import urllib.request
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np

warnings.filterwarnings(
    "ignore",
    message=".*google.generativeai.*",
    category=FutureWarning,
)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependencia declarada en requirements.txt
    load_dotenv = None

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    import aisuite as ai
except ImportError:  # pragma: no cover
    ai = None


BASE_DIR = Path(__file__).resolve().parent
RECETARIOS_DIR = BASE_DIR / "recetarios"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
DATASET_DIR = BASE_DIR / "dataset_rag"
API_BASE_URL = "https://api-comida-peru.luisgagocasas.com/api"
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
DEFAULT_CHAT_MODEL = "gemini-2.5-flash"


REGIONES_PERU = {
    "amazonas": "amazonas",
    "ancash": "ancash",
    "apurimac": "apurimac",
    "arequipa": "arequipa",
    "ayacucho": "ayacucho",
    "cajamarca": "cajamarca",
    "callao": "callao",
    "cusco": "cusco",
    "huancavelica": "huancavelica",
    "huanuco": "huanuco",
    "ica": "ica",
    "junin": "junin",
    "la libertad": "la-libertad",
    "lambayeque": "lambayeque",
    "lima": "lima",
    "loreto": "loreto",
    "madre de dios": "madre-de-dios",
    "moquegua": "moquegua",
    "pasco": "pasco",
    "piura": "piura",
    "puno": "puno",
    "san martin": "san-martin",
    "tacna": "tacna",
    "tumbes": "tumbes",
    "ucayali": "ucayali",
}


@dataclass
class RagChunk:
    id: str
    source: str
    page: Optional[int]
    chunk_id: int
    text: str


def cargar_entorno(env_path: Path | str = BASE_DIR / ".env") -> None:
    """Carga variables de entorno desde un archivo .env si python-dotenv esta disponible."""
    if load_dotenv is not None:
        load_dotenv(dotenv_path=env_path)


def obtener_api_key() -> str:
    """Obtiene la clave de Gemini desde GOOGLE_API_KEY."""
    cargar_entorno()
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Falta GOOGLE_API_KEY. Crea un archivo .env basado en .env.example."
        )
    return api_key


def configurar_gemini() -> None:
    """Configura el SDK de Gemini usando GOOGLE_API_KEY."""
    if genai is None:
        raise RuntimeError(
            "Falta google-generativeai. Instala dependencias con: pip install -r requirements.txt"
        )
    genai.configure(api_key=obtener_api_key())


def normalizar_texto(texto: str) -> str:
    """Normaliza tildes, espacios y mayusculas para comparaciones simples."""
    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", texto)


def slug_region(region: str) -> str:
    """Convierte el nombre de una region peruana a slug valido para la API."""
    region_normalizada = normalizar_texto(region).replace("-", " ")
    if region_normalizada in REGIONES_PERU:
        return REGIONES_PERU[region_normalizada]
    return region_normalizada.replace(" ", "-")


def listar_pdfs_recetarios(recetarios_dir: Path | str = RECETARIOS_DIR) -> List[Path]:
    """Lista los TXT disponibles para el dataset RAG."""
    carpeta = Path(recetarios_dir)
    return sorted(carpeta.glob("*.txt"))


def contar_recetas_txt(txt_path: Path) -> int:
    """Cuenta bloques etiquetados de recetas en un TXT."""
    texto = txt_path.read_text(encoding="utf-8", errors="replace")
    return texto.count("<<<RECETA_INICIO>>>")


def catalogar_dataset(recetarios_dir: Path | str = RECETARIOS_DIR) -> List[Dict[str, Any]]:
    """Genera un catalogo de TXT usados como dataset RAG."""
    registros = []
    for txt_path in listar_pdfs_recetarios(recetarios_dir):
        registros.append(
            {
                "archivo": txt_path.name,
                "ruta": str(txt_path.relative_to(BASE_DIR)),
                "tamano_bytes": txt_path.stat().st_size,
                "recetas": contar_recetas_txt(txt_path),
            }
        )
    return registros


def extraer_recetas_txt(txt_path: Path) -> List[Dict[str, Any]]:
    """Extrae bloques de receta etiquetados desde un TXT."""
    texto = txt_path.read_text(encoding="utf-8", errors="replace")
    patron = re.compile(
        r"<<<RECETA_INICIO>>>(.*?)<<<RECETA_FIN>>>",
        flags=re.DOTALL | re.IGNORECASE,
    )
    recetas: List[Dict[str, Any]] = []
    for idx, match in enumerate(patron.finditer(texto), start=1):
        bloque = match.group(1).strip()
        nombre_match = re.search(r"^NOMBRE:\s*(.+)$", bloque, flags=re.MULTILINE)
        id_match = re.search(r"^ID_RECETA:\s*(.+)$", bloque, flags=re.MULTILINE)
        recetas.append(
            {
                "id": id_match.group(1).strip() if id_match else f"{txt_path.stem}_{idx:03d}",
                "name": nombre_match.group(1).strip() if nombre_match else f"Receta {idx}",
                "text": bloque,
            }
        )
    return recetas


def dividir_en_chunks(
    texto: str, chunk_size: int = 850, overlap: int = 120
) -> List[str]:
    """Divide texto largo en chunks de palabras con solapamiento."""
    palabras = re.split(r"\s+", texto.strip())
    if not palabras or palabras == [""]:
        return []

    chunks = []
    paso = max(chunk_size - overlap, 1)
    for inicio in range(0, len(palabras), paso):
        bloque = palabras[inicio : inicio + chunk_size]
        if len(bloque) < 40 and chunks:
            break
        chunks.append(" ".join(bloque))
    return chunks


def cargar_chunks_recetarios(
    recetarios_dir: Path | str = RECETARIOS_DIR,
    chunk_size: int = 850,
    overlap: int = 120,
) -> List[RagChunk]:
    """Lee todos los TXT etiquetados y devuelve chunks listos para indexar."""
    chunks: List[RagChunk] = []
    for txt_path in listar_pdfs_recetarios(recetarios_dir):
        recetas = extraer_recetas_txt(txt_path)
        for receta in recetas:
            textos = dividir_en_chunks(receta["text"], chunk_size=chunk_size, overlap=overlap)
            if not textos and receta["text"].strip():
                textos = [receta["text"].strip()]
            for local_idx, chunk_text in enumerate(textos):
                chunk_id = len(chunks)
                chunks.append(
                    RagChunk(
                        id=f"{receta['id']}-c{local_idx}",
                        source=txt_path.name,
                        page=None,
                        chunk_id=chunk_id,
                        text=f"RECETA: {receta['name']}\n{chunk_text}",
                    )
                )
    return chunks


def generar_embeddings(
    textos: Sequence[str],
    task_type: str,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 32,
) -> np.ndarray:
    """Genera embeddings con Gemini para documentos o consultas."""
    cargar_entorno()
    if model_name in {"local-hash", "hashing"}:
        return generar_embeddings_locales(textos)

    configurar_gemini()
    vectores: List[List[float]] = []
    try:
        for inicio in range(0, len(textos), batch_size):
            batch = list(textos[inicio : inicio + batch_size])
            respuesta = genai.embed_content(
                model=model_name,
                content=batch,
                task_type=task_type,
            )
            embeddings = respuesta["embedding"]
            if batch and isinstance(embeddings[0], (int, float)):
                embeddings = [embeddings]
            vectores.extend(embeddings)
        return np.array(vectores, dtype="float32")
    except Exception:
        if os.getenv("ALLOW_LOCAL_EMBEDDING_FALLBACK", "1") == "1":
            return generar_embeddings_locales(textos)
        raise


def normalizar_vectores(vectores: np.ndarray) -> np.ndarray:
    """Normaliza vectores para usar producto interno como similitud coseno en FAISS."""
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return (vectores / normas).astype("float32")


def generar_embeddings_locales(textos: Sequence[str], dim: int = 768) -> np.ndarray:
    """
    Genera embeddings locales deterministas por hashing.

    Este fallback permite demostrar FAISS/RAG cuando la cuota de Gemini no esta disponible.
    No reemplaza la ruta principal con embeddings Gemini.
    """
    matriz = np.zeros((len(textos), dim), dtype="float32")
    for row, texto in enumerate(textos):
        tokens = re.findall(r"[a-z0-9ñ]+", normalizar_texto(texto))
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            idx = value % dim
            signo = 1.0 if ((value >> 8) & 1) else -1.0
            matriz[row, idx] += signo
    return normalizar_vectores(matriz)


class PeruRecetasFAISS:
    """Indice FAISS para recuperar contexto desde los TXT etiquetados."""

    def __init__(
        self,
        recetarios_dir: Path | str = RECETARIOS_DIR,
        vectorstore_dir: Path | str = VECTORSTORE_DIR,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self.recetarios_dir = Path(recetarios_dir)
        self.vectorstore_dir = Path(vectorstore_dir)
        cargar_entorno()
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", embedding_model)
        self.index_path = self.vectorstore_dir / "perurecetas.faiss"
        self.chunks_path = self.vectorstore_dir / "chunks.json"
        self.catalog_path = self.vectorstore_dir / "catalogo_recetarios.json"
        self.config_path = self.vectorstore_dir / "config.json"
        self.index = None
        self.chunks: List[RagChunk] = []

    def construir(self, force: bool = False) -> None:
        """Construye el indice FAISS desde los TXT etiquetados del directorio recetarios."""
        if faiss is None:
            raise RuntimeError(
                "Falta FAISS. Instala faiss-cpu o usa conda install -c pytorch faiss-cpu."
            )
        if self.index_path.exists() and self.chunks_path.exists() and not force:
            self.cargar()
            return

        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)
        self.chunks = cargar_chunks_recetarios(self.recetarios_dir)
        if not self.chunks:
            raise RuntimeError("No se encontraron recetas etiquetadas en los TXT de recetarios.")

        embeddings = generar_embeddings(
            [chunk.text for chunk in self.chunks],
            task_type="RETRIEVAL_DOCUMENT",
            model_name=self.embedding_model,
        )
        embeddings = normalizar_vectores(embeddings)

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        faiss.write_index(self.index, str(self.index_path))
        self.chunks_path.write_text(
            json.dumps([asdict(chunk) for chunk in self.chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.catalog_path.write_text(
            json.dumps(catalogar_dataset(self.recetarios_dir), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.config_path.write_text(
            json.dumps(
                {
                    "embedding_model": self.embedding_model,
                    "chunk_count": len(self.chunks),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def cargar(self) -> None:
        """Carga el indice FAISS y los chunks desde disco."""
        if faiss is None:
            raise RuntimeError("Falta FAISS para cargar el indice vectorial.")
        if not self.index_path.exists() or not self.chunks_path.exists():
            raise FileNotFoundError(
                "No existe el indice FAISS. Ejecuta rag.construir(force=True)."
            )
        self.index = faiss.read_index(str(self.index_path))
        if self.config_path.exists():
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.embedding_model = config.get("embedding_model", self.embedding_model)
        data = json.loads(self.chunks_path.read_text(encoding="utf-8"))
        self.chunks = [RagChunk(**item) for item in data]

    def buscar(self, consulta: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Búsqueda directa en los archivos TXT de recetas.
        Busca coincidencias en el nombre de la receta o en su contenido completo,
        basada en tokens extraídos de la consulta del usuario."""
        tokens = re.findall(r"[a-zñ0-9]+", consulta.lower())
        resultados: List[Dict[str, Any]] = []
        for txt_path in self.recetarios_dir.glob("*.txt"):
            for receta in extraer_recetas_txt(txt_path):
                nombre_norm = normalizar_texto(receta["name"])
                texto_norm = normalizar_texto(receta["text"])
                if any(tok in nombre_norm or tok in texto_norm for tok in tokens):
                    resultados.append({
                        "score": 1.0,
                        "source": txt_path.name,
                        "page": None,
                        "text": receta["text"],
                    })
                    if len(resultados) >= top_k:
                        return resultados
        return resultados

    def contexto(self, consulta: str, top_k: int = 4) -> str:
        """Devuelve contexto RAG formateado para el prompt.
        Utiliza `buscar`, que busca directamente en los archivos TXT.
        Si `buscar` devuelve resultados, se formatean; de lo contrario se devuelve
        un mensaje indicando que no hay contexto relevante.
        """
        resultados = self.buscar(consulta, top_k=top_k)

        # No se encontró nada
        if not resultados:
            return "No se recuperó contexto relevante desde los recetarios."

        # Formateo de los resultados encontrados
        partes = []
        for i, item in enumerate(resultados, start=1):
            partes.append(
                f"[RAG {i}] Fuente: {item['source']}, receta etiquetada, "
                f"score {item['score']:.3f}\n{item['text']}"
            )
        return "\n\n".join(partes)


def _http_get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """GET JSON usando requests si esta disponible, o urllib como alternativa."""
    params = {k: v for k, v in (params or {}).items() if v not in (None, "", [])}
    if requests is not None:
        respuesta = requests.get(url, params=params, timeout=15)
        respuesta.raise_for_status()
        return respuesta.json()

    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full_url, headers={"User-Agent": "PeruRecetas/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def listar_regiones_api() -> str:
    """
    Consulta la API externa de comida peruana y devuelve las regiones disponibles.

    Returns:
        str: Lista resumida de regiones disponibles en la API.
    """
    data = _http_get_json(API_BASE_URL)
    regiones = data.get("regiones", [])
    nombres = [item.get("nombre", item.get("slug", "")) for item in regiones]
    return "Regiones disponibles en la API: " + ", ".join(nombres)


def consultar_api_comida_peru(
    region: str,
    ingrediente: Optional[str] = None,
    tipo: Optional[str] = None,
    consulta: Optional[str] = None,
    limite: int = 5,
    offset: int = 0,
    ordenar: Optional[str] = None,
) -> str:
    """
    Consulta informacion de platos peruanos desde una API externa.

    Args:
        region: Region peruana que se desea consultar, por ejemplo "arequipa" o "lima".
        ingrediente: Ingrediente opcional para filtrar platos.
        tipo: Tipo opcional de plato, por ejemplo "Entrada" o "Fondo".
        consulta: Texto opcional para busqueda libre.
        limite: Numero maximo de platos a devolver.
        offset: Desplazamiento de paginacion.
        ordenar: Criterio de ordenamiento aceptado por la API.

    Returns:
        str: Resumen de platos encontrados con ingredientes y preparacion breve.
    """
    region_slug = slug_region(region)
    params = {
        "ingrediente": ingrediente,
        "tipo": tipo,
        "q": consulta,
        "limit": max(1, min(int(limite), 10)),
        "offset": max(0, int(offset)),
        "sort": ordenar,
    }
    data = _http_get_json(f"{API_BASE_URL}/{region_slug}", params=params)
    platos = data.get("platos", [])
    if not platos:
        return f"No se encontraron platos para la region {region_slug} con esos filtros."

    lineas = [
        f"API comida peruana - {data.get('nombre_region', region_slug)}: "
        f"{data.get('total', len(platos))} resultado(s)."
    ]
    for plato in platos[: max(1, min(int(limite), 10))]:
        ingredientes = ", ".join(plato.get("ingredientes", [])[:6])
        preparacion = " ".join(plato.get("preparacion", [])[:2])
        lineas.append(
            f"- {plato.get('nombre')} ({plato.get('tipo', 'sin tipo')}): "
            f"ingredientes principales: {ingredientes}. Preparacion: {preparacion}"
        )
    return "\n".join(lineas)


def recomendar_recetas_por_ingrediente(ingredientes: str) -> str:
    """
    Recomienda recetas peruanas basadas en ingredientes dados por el usuario.

    Args:
        ingredientes: Lista de ingredientes separados por comas.

    Returns:
        str: Recomendaciones de recetas compatibles con los ingredientes.
    """
    ingredientes_norm = [
        normalizar_texto(item) for item in ingredientes.split(",") if item.strip()
    ]
    base_recetas = {
        "causa rellena": ["papa", "aji amarillo", "limon", "pollo", "atun"],
        "lomo saltado": ["carne", "cebolla", "tomate", "papa", "arroz"],
        "aji de gallina": ["pollo", "aji amarillo", "leche", "pan", "papa"],
        "ceviche": ["pescado", "limon", "cebolla", "aji limo", "camote"],
        "tacu tacu": ["arroz", "frejol", "frijol", "huevo", "platano"],
        "ocopa": ["papa", "huacatay", "mani", "aji mirasol", "queso"],
    }
    coincidencias = []
    for receta, receta_ingredientes in base_recetas.items():
        score = sum(
            1
            for ing in ingredientes_norm
            if any(ing in normalizar_texto(base) for base in receta_ingredientes)
        )
        if score > 0:
            coincidencias.append((score, receta.title()))
    coincidencias.sort(reverse=True)
    if not coincidencias:
        return (
            "No encontre una receta local con esos ingredientes. "
            "Puedes consultar la API externa por region para ampliar opciones."
        )
    recetas = ", ".join(nombre for _, nombre in coincidencias[:5])
    return f"Con esos ingredientes podrias preparar: {recetas}."


def sugerir_sustitucion_ingredientes(
    ingrediente_original: str, sustituto_deseado: Optional[str] = None
) -> str:
    """
    Sugiere sustituciones para un ingrediente de recetas peruanas.

    Args:
        ingrediente_original: Ingrediente que se desea reemplazar.
        sustituto_deseado: Sustituto propuesto por el usuario, si existe.

    Returns:
        str: Sugerencia o validacion de sustitucion.
    """
    sustituciones = {
        "pollo": ["pavo", "tofu", "champinones"],
        "carne de res": ["cerdo", "pollo", "seitán", "champinones portobello"],
        "papa": ["yuca", "camote", "oca"],
        "limon": ["lima", "vinagre blanco suave"],
        "aji amarillo": ["aji mirasol", "pimiento amarillo", "rocoto suave"],
        "arroz": ["quinua", "arroz integral", "trigo mote"],
        "frejol": ["lentejas", "garbanzos", "pallares"],
        "frijol": ["lentejas", "garbanzos", "pallares"],
        "huevo": ["semillas de chia hidratadas", "pure de manzana"],
        "leche": ["leche evaporada sin lactosa", "leche de almendras", "leche de soya"],
    }
    original = normalizar_texto(ingrediente_original)
    opciones = sustituciones.get(original)
    if not opciones:
        return f"No tengo una sustitucion especifica registrada para {ingrediente_original}."

    if sustituto_deseado:
        sustituto = normalizar_texto(sustituto_deseado)
        valido = any(sustituto in normalizar_texto(opcion) for opcion in opciones)
        if valido:
            return f"Si, {sustituto_deseado} puede funcionar como sustituto de {ingrediente_original}."
        return (
            f"{sustituto_deseado} no aparece como sustituto recomendado de "
            f"{ingrediente_original}. Opciones sugeridas: {', '.join(opciones)}."
        )
    return f"Para sustituir {ingrediente_original}, puedes usar: {', '.join(opciones)}."


def detectar_region_en_texto(texto: str) -> Optional[str]:
    """Detecta una region peruana mencionada en un texto."""
    normalizado = normalizar_texto(texto)
    for nombre, slug in REGIONES_PERU.items():
        if nombre in normalizado or slug.replace("-", " ") in normalizado:
            return slug
    return None


def extraer_ingrediente_en_texto(texto: str) -> Optional[str]:
    """Extrae de forma simple un posible ingrediente desde la consulta del usuario."""
    normalizado = normalizar_texto(texto)
    patrones = [
        r"ingrediente[s]?\s+(?:de|con)?\s*([a-zñ\s]+)",
        r"con\s+([a-zñ\s]+)",
        r"que\s+tengan\s+([a-zñ\s]+)",
    ]
    for patron in patrones:
        match = re.search(patron, normalizado)
        if match:
            candidato = match.group(1).strip()
            candidato = re.split(r"\b(en|para|de|del|por|y)\b", candidato)[0].strip()
            if 2 <= len(candidato) <= 40:
                return candidato
    return None


class AgenteRecetas:
    """Agente de recetas y nutricion peruana con memoria, tools, RAG y API externa."""

    def __init__(
        self,
        modelo: str = DEFAULT_CHAT_MODEL,
        temperature: float = 0.4,
        usar_aisuite: bool = True,
        cargar_indice: bool = True,
    ) -> None:
        self.modelo = os.getenv("GEMINI_MODEL", modelo)
        self.temperature = temperature
        self.usar_aisuite = usar_aisuite
        self.memoria: List[Dict[str, str]] = []
        self.rag = PeruRecetasFAISS()
        self.tools = {
            "recomendar_recetas_por_ingrediente": recomendar_recetas_por_ingrediente,
            "sugerir_sustitucion_ingredientes": sugerir_sustitucion_ingredientes,
            "consultar_api_comida_peru": consultar_api_comida_peru,
            "listar_regiones_api": listar_regiones_api,
        }
        if cargar_indice:
            try:
                self.rag.cargar()
            except Exception:
                pass

    def construir_indice(self, force: bool = False) -> None:
        """Construye o reconstruye el indice FAISS del RAG."""
        self.rag.construir(force=force)

    def _memoria_reciente(self, limite: int = 6) -> str:
        mensajes = self.memoria[-limite:]
        if not mensajes:
            return "Sin mensajes anteriores."
        return "\n".join(f"{m['role']}: {m['content']}" for m in mensajes)

    def _consultar_api_si_aplica(self, mensaje: str) -> str:
        normalizado = normalizar_texto(mensaje)
        palabras_api = ["api", "region", "plato tipico", "platos tipicos", "arequipa", "lima", "cusco"]
        region = detectar_region_en_texto(mensaje)
        if region is None or not any(p in normalizado for p in palabras_api):
            return "No se consulto la API externa para esta pregunta."
        ingrediente = extraer_ingrediente_en_texto(mensaje)
        try:
            return consultar_api_comida_peru(region=region, ingrediente=ingrediente, limite=5)
        except Exception as exc:
            return f"No se pudo consultar la API externa: {exc}"

    def _contexto_rag(self, mensaje: str) -> str:
        try:
            return self.rag.contexto(mensaje, top_k=4)
        except Exception as exc:
            return f"Contexto RAG no disponible: {exc}"

    def _llamar_llm(self, prompt: str) -> str:
        messages = [
            {
                "role": "system",
                "content": "Eres PeruRecetas, un asistente experto en recetas peruanas y nutricion basica.",
            },
            {"role": "user", "content": prompt},
        ]

        if self.usar_aisuite and ai is not None:
            try:
                client = ai.Client()
                response = client.chat.completions.create(
                    model=f"google:{self.modelo}",
                    messages=messages,
                    temperature=self.temperature,
                )
                return response.choices[0].message.content
            except Exception:
                # Fallback controlado al SDK oficial de Gemini.
                pass

        configurar_gemini()
        model = genai.GenerativeModel(self.modelo)
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": 2048,
                "top_p": 0.95,
            },
        )
        return getattr(response, "text", str(response))

    def enviar_mensaje(self, mensaje: str) -> str:
        """Procesa un mensaje usando memoria, RAG, API externa y LLM."""
        # Obtiene contexto RAG. Si no se encontró información relevante, el método devuelve un mensaje estándar.
        contexto_rag_raw = self._contexto_rag(mensaje)
        if contexto_rag_raw.startswith("No se recuperó"):
            # No se incluye la sección de contexto en el prompt.
            contexto_section = ""
        else:
            contexto_section = f"\nContexto recuperado por FAISS/RAG:\n{contexto_rag_raw}\n"
        resultado_api = self._consultar_api_si_aplica(mensaje)
        memoria = self._memoria_reciente()
        prompt = f"""Instrucciones:
- Tu objetivo principal es que, a partir de una solicitud de un producto o ingrediente, encuentres y proporciones una receta adecuada.
- Responde en espanol claro y util.
- Usa el contexto RAG como fuente principal cuando sea relevante.
- Usa el resultado de API cuando el usuario pida platos por region, ingrediente o datos externos.
- Si no hay suficiente informacion, dilo y propone una consulta mas especifica.
- No inventes fuentes; cita el archivo TXT y el nombre de la receta cuando uses RAG.

Memoria reciente:
{memoria}
{contexto_section}
Resultado de API externa:
{resultado_api}

Pregunta del usuario:
{mensaje}
"""
        respuesta = self._llamar_llm(prompt)
        self.memoria.append({"role": "usuario", "content": mensaje})
        self.memoria.append({"role": "asistente", "content": respuesta})
        return respuesta

    def reset(self) -> None:
        """Reinicia la memoria conversacional del agente."""
        self.memoria = []

    def historial(self) -> List[Dict[str, str]]:
        """Devuelve el historial de conversacion."""
        return list(self.memoria)
