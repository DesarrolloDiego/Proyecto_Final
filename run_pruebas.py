from __future__ import annotations

import argparse
import json
from pathlib import Path

from perurecetas_core import (
    AgenteRecetas,
    catalogar_dataset,
    consultar_api_comida_peru,
    dividir_en_chunks,
    normalizar_texto,
    slug_region,
    sugerir_sustitucion_ingredientes,
)


def ok(nombre: str, detalle: str) -> dict:
    return {"prueba": nombre, "estado": "OK", "detalle": detalle}


def fail(nombre: str, exc: Exception) -> dict:
    return {"prueba": nombre, "estado": "ERROR", "detalle": str(exc)}


def prueba_dataset_minimo() -> dict:
    catalogo = catalogar_dataset()
    assert len(catalogo) >= 5, "El RAG debe tener al menos 5 documentos TXT."
    recetas = sum(item.get("recetas", 0) for item in catalogo)
    assert recetas > 0, "Los TXT deben contener bloques <<<RECETA_INICIO>>>."
    return ok("dataset_minimo_5_txt", f"{len(catalogo)} TXT y {recetas} recetas etiquetadas.")


def prueba_normalizacion_region() -> dict:
    assert slug_region("San Martin") == "san-martin"
    assert slug_region("La Libertad") == "la-libertad"
    return ok("normalizacion_region_api", "Slugs de region correctos.")


def prueba_tool_sustitucion() -> dict:
    respuesta = sugerir_sustitucion_ingredientes("papa")
    assert "yuca" in normalizar_texto(respuesta)
    return ok("tool_sustitucion", respuesta)


def prueba_chunking() -> dict:
    texto = " ".join(["receta"] * 1800)
    chunks = dividir_en_chunks(texto, chunk_size=500, overlap=80)
    assert len(chunks) >= 4
    return ok("chunking_rag", f"{len(chunks)} chunks generados.")


def prueba_api_externa() -> dict:
    respuesta = consultar_api_comida_peru("arequipa", ingrediente="aji", limite=3)
    assert "API comida peruana" in respuesta
    return ok("api_externa_comida_peru", respuesta.splitlines()[0])


def prueba_rag_faiss() -> dict:
    agente = AgenteRecetas(cargar_indice=True)
    resultados = agente.rag.buscar("recetas peruanas con papa y aji", top_k=3)
    assert resultados, "No se recuperaron documentos desde FAISS."
    return ok("rag_faiss", f"{len(resultados)} chunks recuperados.")


def prueba_agente_memoria() -> dict:
    agente = AgenteRecetas(cargar_indice=True)
    respuesta1 = agente.enviar_mensaje("Recomiendame una receta peruana con papa.")
    respuesta2 = agente.enviar_mensaje("Recuerda mi pedido anterior y dame una alternativa saludable.")
    assert respuesta1 and respuesta2
    assert len(agente.historial()) >= 4
    return ok("agente_memoria_llm", "El agente respondio dos turnos y guardo memoria.")


def ejecutar(offline: bool = False) -> list[dict]:
    pruebas = [
        prueba_dataset_minimo,
        prueba_normalizacion_region,
        prueba_tool_sustitucion,
        prueba_chunking,
    ]
    if not offline:
        pruebas.extend([prueba_api_externa, prueba_rag_faiss, prueba_agente_memoria])

    resultados = []
    for prueba in pruebas:
        try:
            resultados.append(prueba())
        except Exception as exc:
            resultados.append(fail(prueba.__name__, exc))
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="No ejecuta API, FAISS ni LLM.")
    parser.add_argument("--out", default="output/resultados_pruebas.json")
    args = parser.parse_args()

    resultados = ejecutar(offline=args.offline)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultados, ensure_ascii=False, indent=2))

    errores = [r for r in resultados if r["estado"] != "OK"]
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
