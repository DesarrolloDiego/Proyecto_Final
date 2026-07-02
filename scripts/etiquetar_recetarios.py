from __future__ import annotations

import argparse
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECETARIOS_DIR = ROOT / "recetarios"
START = "<<<RECETA_INICIO>>>"
END = "<<<RECETA_FIN>>>"


REGIONES = {
    "AMAZONAS",
    "ANCASH",
    "APURIMAC",
    "APURÍMAC",
    "AREQUIPA",
    "AYACUCHO",
    "CAJAMARCA",
    "CUSCO",
    "HUANCAVELICA",
    "HUÁNUCO",
    "HUANUCO",
    "ICA",
    "JUNÍN",
    "JUNIN",
    "LA LIBERTAD",
    "LAMBAYEQUE",
    "LIMA",
    "LIMA Y CALLAO",
    "LORETO",
    "MADRE DE DIOS",
    "MOQUEGUA",
    "PASCO",
    "PIURA",
    "PUNO",
    "SAN MARTÍN",
    "SAN MARTIN",
    "TACNA",
    "TUMBES",
    "UCAYALI",
}

STOPWORDS = {
    "con",
    "para",
    "por",
    "una",
    "uno",
    "unos",
    "unas",
    "del",
    "las",
    "los",
    "de",
    "la",
    "el",
    "en",
    "al",
    "y",
    "a",
    "g",
    "kg",
    "gr",
    "taza",
    "tazas",
    "cucharada",
    "cucharadas",
    "cucharadita",
    "cucharaditas",
    "unidad",
    "unidades",
    "gusto",
    "sal",
}


@dataclass
class Recipe:
    source: str
    number: int
    name: str
    start: int
    end: int
    lines: list[str]
    region: str = "Peru"
    category: str = "Receta"
    portions: str = "No especificado"


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", text)


def clean_line(line: str) -> str:
    return line.strip().strip("\ufeff").strip()


def is_ingredient_header(line: str) -> bool:
    return bool(re.match(r"^\s*ingredientes\b", normalize(line)))


def is_preparation_header(line: str) -> bool:
    return bool(re.match(r"^\s*preparaci[oó]n\b|^\s*preparacion\b", normalize(line)))


def is_page_number(line: str) -> bool:
    return bool(re.match(r"^\s*\d+\s*$", line))


def is_noise_title_line(line: str) -> bool:
    raw = clean_line(line)
    norm = normalize(raw)
    if not raw:
        return True
    if is_page_number(raw):
        return True
    if re.match(r"^\(?\d+\s+(porciones|raciones|personas)\)?$", norm):
        return True
    if norm in {"fe", "el tip", "ingredientes", "preparacion", "preparación"}:
        return True
    if "chef del" in norm or "chef de" in norm:
        return True
    if "hierro:" in norm or "una porcion contiene" in norm or "una racion contiene" in norm:
        return True
    if "edicion especial" in norm or "edición especial" in norm:
        return True
    if "instituto nacional" in norm or "consumo per capita" in norm:
        return True
    if norm.startswith("peru:") or norm.startswith("perú:"):
        return True
    return False


def is_title_boundary(line: str) -> bool:
    norm = normalize(line)
    return (
        is_page_number(line)
        or norm in {"fe", "el tip"}
        or "hierro:" in norm
        or "una porcion contiene" in norm
        or "una racion contiene" in norm
        or "edicion especial" in norm
        or "edición especial" in norm
        or "composicion nutricional" in norm
        or norm.startswith("energia")
        or norm.startswith("proteinas")
        or norm.startswith("grasas")
        or norm.startswith("carbohidratos")
    )


def clean_recipe_name(name: str) -> str:
    name = re.sub(r"^\s*\d+\)\s*", "", name.strip())
    name = re.sub(r"\bPreparaci[oó]n\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\bPreparacion\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\.{2,}\s*\d+\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip(" -:;")
    return name or "Receta sin titulo"


def infer_portions(lines: list[str]) -> str:
    joined = "\n".join(lines[:12])
    patterns = [
        r"\(?\s*(\d+\s*(?:porciones|raciones|personas))\s*\)?",
        r"Ingredientes\s*:?\s*\(([^)]+)\)",
        r"INGREDIENTES\s*:?\s*\(([^)]+)\)",
    ]
    for pattern in patterns:
        m = re.search(pattern, joined, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "No especificado"


def extract_section(lines: list[str], start_pred, end_preds: list) -> list[str]:
    start_idx = None
    for i, line in enumerate(lines):
        if start_pred(line):
            start_idx = i + 1
            break
    if start_idx is None:
        return []
    end_idx = len(lines)
    for i in range(start_idx, len(lines)):
        if any(pred(lines[i]) for pred in end_preds):
            end_idx = i
            break
    return [clean_line(x) for x in lines[start_idx:end_idx] if clean_line(x)]


def extract_nutrition(lines: list[str]) -> list[str]:
    starts = [
        i
        for i, line in enumerate(lines)
        if "aporte nutricional" in normalize(line)
        or normalize(line) == "aporte"
        or "una porcion contiene" in normalize(line)
        or "una racion" in normalize(line)
        or "composicion nutricional" in normalize(line)
    ]
    if not starts:
        return []
    return [clean_line(x) for x in lines[starts[0] :] if clean_line(x)][:18]


def keywords_from(recipe: Recipe, ingredients: list[str]) -> list[str]:
    text = " ".join([recipe.name] + ingredients[:20])
    words = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]+", text)
    tags = []
    for word in words:
        norm = normalize(word).replace(" ", "_")
        if len(norm) < 3 or norm in STOPWORDS:
            continue
        if norm not in tags:
            tags.append(norm)
        if len(tags) >= 16:
            break
    base = ["receta_peruana"]
    if "andino" in normalize(recipe.source) or recipe.source == "recetario1.txt":
        base.append("receta_andina")
    return base + tags


def block_for(recipe: Recipe) -> list[str]:
    ingredients = extract_section(
        recipe.lines,
        is_ingredient_header,
        [is_preparation_header, lambda line: "aporte nutricional" in normalize(line)],
    )
    preparation = extract_section(
        recipe.lines,
        is_preparation_header,
        [lambda line: "aporte nutricional" in normalize(line), lambda line: normalize(line) == "el tip"],
    )
    nutrition = extract_nutrition(recipe.lines)
    tags = keywords_from(recipe, ingredients)
    original = [clean_line(x) for x in recipe.lines if clean_line(x)]

    out = [
        START,
        f"ID_RECETA: {Path(recipe.source).stem}_{recipe.number:03d}",
        f"NOMBRE: {recipe.name.upper()}",
        f"FUENTE: {recipe.source}",
        f"REGION: {recipe.region}",
        f"CATEGORIA: {recipe.category}",
        f"PORCIONES: {recipe.portions}",
        f"INGREDIENTE_PRINCIPAL: {tags[2] if len(tags) > 2 else 'No especificado'}",
        "",
        "INGREDIENTES_CLAVE:",
        ", ".join(tags[2:12]) if len(tags) > 2 else "No especificado",
        "",
        "INGREDIENTES:",
    ]
    if ingredients:
        out.extend(f"- {item}" for item in ingredients)
    else:
        out.append("- No especificado en el texto original.")

    out.extend(["", "PREPARACION:"])
    if preparation:
        for idx, step in enumerate(preparation, start=1):
            if re.match(r"^\d+[\).]", step):
                out.append(step)
            else:
                out.append(f"{idx}. {step}")
    else:
        out.append("1. No especificado en el texto original.")

    if nutrition:
        out.extend(["", "APORTE_NUTRICIONAL:"])
        out.extend(nutrition)

    out.extend(["", "TEXTO_ORIGINAL:"])
    out.extend(original)
    out.extend(["", "ETIQUETAS:", ", ".join(tags), END])
    return out


def find_next_heading(lines: list[str], start: int) -> int:
    for i in range(start + 1, len(lines)):
        if re.match(r"^\s*\d+\)\s+\S+", lines[i]):
            return i
        if re.match(r"^\s*Detalles de las recetas\b", lines[i], flags=re.IGNORECASE):
            return i
    return len(lines)


def tag_recetario1(lines: list[str], source: str) -> tuple[list[str], list[Recipe]]:
    out: list[str] = []
    recipes: list[Recipe] = []
    i = 0
    number = 1
    while i < len(lines):
        if clean_line(lines[i]) == START:
            block = []
            while i < len(lines):
                block.append(lines[i])
                if clean_line(lines[i]) == END:
                    break
                i += 1
            out.extend(block)
            recipes.append(Recipe(source, number, "BLOQUE YA ETIQUETADO", i, i, block))
            number += 1
            i += 1
            continue

        m = re.match(r"^\s*(\d+)\)\s+(.+)", lines[i])
        if m:
            end = find_next_heading(lines, i)
            chunk = lines[i:end]
            name = clean_recipe_name(m.group(2))
            recipe = Recipe(
                source=source,
                number=int(m.group(1)),
                name=name,
                start=i,
                end=end,
                lines=chunk,
                region="Andes del Peru",
                category="Receta andina",
                portions=infer_portions(chunk),
            )
            recipes.append(recipe)
            out.extend(block_for(recipe))
            i = end
            continue

        out.append(lines[i])
        i += 1
    return out, recipes


def infer_title_generic(lines: list[str], ing_idx: int) -> tuple[int, str]:
    candidates: list[tuple[int, str]] = []
    for j in range(ing_idx - 1, max(-1, ing_idx - 12), -1):
        line = clean_line(lines[j])
        if is_title_boundary(line):
            if candidates:
                break
            continue
        if is_noise_title_line(line):
            continue
        if j + 1 < len(lines) and "chef" in normalize(lines[j + 1]):
            continue
        if is_ingredient_header(line) or is_preparation_header(line):
            continue
        if len(line) > 85:
            continue
        candidates.append((j, line))
        if len(candidates) >= 3:
            break
    candidates.reverse()
    if not candidates:
        return ing_idx, "Receta sin titulo"

    start = candidates[0][0]
    title_lines = [c[1] for c in candidates]
    # Evita arrastrar autores o categorias largas cuando el titulo esta en las ultimas lineas.
    if len(title_lines) > 1 and any("/" in x for x in title_lines[:-1]):
        title_lines = title_lines[-2:]
        start = candidates[-2][0] if len(candidates) >= 2 else candidates[-1][0]
    title = clean_recipe_name(" ".join(title_lines))
    return start, title


def extract_index_titles(path_name: str, lines: list[str]) -> list[str]:
    titles: list[str] = []
    if path_name == "recetario4.txt":
        return [
            "Paiche a la plancha con majao de yuca",
            "Explosión de paiche (Paiche dorado en jugo de lulo)",
            "Picadillo de paiche",
            "Chupe de gamitana",
            "Cebiche de paiche",
            "Paiche con quinua y salsa curry",
            "Causa rellena con paiche",
            "Paiche envuelto en hoja de bijao con patacones",
            "Empanada de yuca con picadillo de paiche",
            "Abruto tu paiche",
        ]

    if path_name == "recetario2.txt":
        for line in lines[100:160]:
            s = clean_line(line)
            m = re.search(r"^(.+?)\s+\d+\s*$", s)
            if not m:
                continue
            title = clean_recipe_name(m.group(1))
            if any(x in normalize(title) for x in ["acerca", "servir", "preparaciones previas"]):
                continue
            titles.append(title)
        return titles

    if path_name == "recetario5.txt":
        for line in lines[:120]:
            s = clean_line(line)
            m = re.search(r"^(.+?)\.{2,}\s*\d+\s*$", s)
            if not m:
                continue
            title = clean_recipe_name(m.group(1))
            if normalize(title).upper() in REGIONES:
                continue
            titles.append(title)
        return titles

    return []


def find_generic_recipes(lines: list[str], source: str) -> list[Recipe]:
    ing_indices = [i for i, line in enumerate(lines) if is_ingredient_header(line)]
    index_titles = extract_index_titles(source, lines)
    recipes: list[Recipe] = []
    starts: list[int] = []
    titles: list[str] = []
    for idx, ing_idx in enumerate(ing_indices):
        start, title = infer_title_generic(lines, ing_idx)
        if idx < len(index_titles):
            title = index_titles[idx]
        if starts and start <= starts[-1]:
            start = ing_idx
        starts.append(start)
        titles.append(title)

    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        chunk = lines[start:end]
        recipes.append(
            Recipe(
                source=source,
                number=idx + 1,
                name=titles[idx],
                start=start,
                end=end,
                lines=chunk,
                region="Peru",
                category="Receta",
                portions=infer_portions(chunk),
            )
        )
    return recipes


def tag_generic(lines: list[str], source: str) -> tuple[list[str], list[Recipe]]:
    recipes = find_generic_recipes(lines, source)
    if not recipes:
        return lines, []
    out: list[str] = []
    cursor = 0
    for recipe in recipes:
        out.extend(lines[cursor : recipe.start])
        out.extend(block_for(recipe))
        cursor = recipe.end
    out.extend(lines[cursor:])
    return out, recipes


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def process_file(path: Path) -> tuple[list[str], list[Recipe]]:
    lines = read_lines(path)
    if path.name == "recetario1.txt":
        return tag_recetario1(lines, path.name)
    return tag_generic(lines, path.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Escribe cambios en los .txt.")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Crea copias .bak antes de escribir cambios.",
    )
    args = parser.parse_args()

    paths = sorted(RECETARIOS_DIR.glob("recetario*.txt"))
    for path in paths:
        new_lines, recipes = process_file(path)
        names = [r.name for r in recipes[:8]]
        print(f"{path.name}: recetas_detectadas={len(recipes)}")
        for name in names:
            print(f"  - {name}")
        if len(recipes) > len(names):
            print(f"  ... {len(recipes) - len(names)} mas")
        if args.apply:
            if args.backup:
                backup = path.with_suffix(path.suffix + ".bak")
                if not backup.exists():
                    shutil.copy2(path, backup)
            write_lines(path, new_lines)
            print("  escrito")


if __name__ == "__main__":
    main()
