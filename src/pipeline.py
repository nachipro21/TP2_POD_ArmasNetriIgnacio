"""Módulo de procesamiento reproducible del catálogo de películas (TP2 - Tema 10).

Implementa las funciones requeridas por la consigna:
- `extraer_titulo_y_anio()`: aplica la expresión regular sobre el título y valida el año.
- `construir_catalogo()`: crea el índice de películas por `movieId`, validando unicidad y esquema.
- `acumular_valoraciones()`: calcula cantidad y media de opiniones y registra rechazos.
- `buscar_titulos()`: aplica búsqueda y filtros mediante `ConsultaCatalogo`.
- `generar_lista()`: filtra por mínimo de valoraciones, ordena con regla de desempate y exporta.
"""

import csv
from pathlib import Path
import re
from typing import Any

try:
    from src.modelo import ANIO_MAXIMO_CINE, ANIO_MINIMO_CINE, ConsultaCatalogo
except ImportError:
    from modelo import ANIO_MAXIMO_CINE, ANIO_MINIMO_CINE, ConsultaCatalogo

# Expresión regular que captura el título limpio en el grupo 1 y un año de 4 dígitos
# entre paréntesis al final de la cadena en el grupo 2. Ejemplo: "Toy Story (1995)"
PATRON_TITULO_ANIO = re.compile(r"^(.+?)\s*\((\d{4})\)\s*$")

ESCALA_MIN_RATING = 0.5
ESCALA_MAX_RATING = 5.0

COLUMNAS_REQUERIDAS_PELICULAS = {"movieId", "title", "genres"}
COLUMNAS_REQUERIDAS_CALIFICACIONES = {"userId", "movieId", "rating", "timestamp"}


def validar_esquema(filas: list[dict[str, str]], columnas_requeridas: set[str], nombre_tabla: str) -> None:
    """Verifica que la tabla cargada no esté vacía y posea las columnas esperadas."""
    if not filas:
        raise ValueError(f"La tabla '{nombre_tabla}' no contiene registros.")
    columnas_presentes = set(filas[0].keys())
    faltantes = columnas_requeridas - columnas_presentes
    if faltantes:
        faltantes_str = ", ".join(sorted(faltantes))
        raise ValueError(
            f"Faltan columnas obligatorias en '{nombre_tabla}': {faltantes_str}."
        )


def extraer_titulo_y_anio(titulo_crudo: str) -> tuple[str, int | None]:
    """Extrae el título limpio y el año de estreno al final entre paréntesis.

    Complementa la expresión regular con una validación numérica del rango de años
    para evitar aceptar cadenas como '(0000)' o '(9999)' como años válidos.
    Si el título no contiene año entre paréntesis al final, devuelve el título
    limpio y `None` como año.
    """
    texto = titulo_crudo.strip()
    coincidencia = PATRON_TITULO_ANIO.match(texto)
    if not coincidencia:
        return texto, None

    titulo_base = coincidencia.group(1).strip()
    anio_candidato = int(coincidencia.group(2))
    if ANIO_MINIMO_CINE <= anio_candidato <= ANIO_MAXIMO_CINE:
        return titulo_base, anio_candidato

    return texto, None


def separar_generos(cadena_generos: str) -> list[str]:
    """Divide la cadena de géneros separados por '|' en una lista de nombres limpios."""
    texto = cadena_generos.strip()
    if not texto or texto.lower() == "(no genres listed)":
        return []
    return [g.strip() for g in texto.split("|") if g.strip()]


def construir_catalogo(
    filas_peliculas: list[dict[str, str]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Crea un índice de películas por `movieId`, validando unicidad y campos obligatorios.

    Args:
        filas_peliculas: Lista de diccionarios leída desde `peliculas.csv` o `peliculas.json`.

    Returns:
        Tupla `(catalogo, rechazos_catalogo)` donde `catalogo` es un diccionario
        indexado por `movieId` y `rechazos_catalogo` documenta las filas descartadas.
    """
    validar_esquema(filas_peliculas, COLUMNAS_REQUERIDAS_PELICULAS, "peliculas")

    catalogo: dict[str, dict[str, Any]] = {}
    rechazos: list[dict[str, Any]] = []

    for indice, fila in enumerate(filas_peliculas, start=1):
        movie_id = str(fila.get("movieId", "")).strip()
        title_raw = str(fila.get("title", "")).strip()
        genres_raw = str(fila.get("genres", "")).strip()

        if not movie_id:
            rechazos.append({
                "origen": "catalogo",
                "fila": indice,
                "movieId": "",
                "detalle": title_raw,
                "motivo": "movieId vacio",
            })
            continue

        if not title_raw:
            rechazos.append({
                "origen": "catalogo",
                "fila": indice,
                "movieId": movie_id,
                "detalle": "",
                "motivo": "titulo vacio",
            })
            continue

        if movie_id in catalogo:
            rechazos.append({
                "origen": "catalogo",
                "fila": indice,
                "movieId": movie_id,
                "detalle": title_raw,
                "motivo": "movieId duplicado",
            })
            continue

        titulo_limpio, anio = extraer_titulo_y_anio(title_raw)
        generos = separar_generos(genres_raw)

        catalogo[movie_id] = {
            "movieId": movie_id,
            "title": title_raw,
            "titulo_limpio": titulo_limpio,
            "anio": anio,
            "generos": generos,
            "cantidad_valoraciones": 0,
            "suma_valoraciones": 0.0,
            "media_valoraciones": 0.0,
        }

    return catalogo, rechazos


def acumular_valoraciones(
    catalogo: dict[str, dict[str, Any]],
    filas_calificaciones: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Calcula cantidad y media de valoraciones por película y registra incidencias.

    Reinicia los contadores del catálogo antes de acumular para garantizar que
    múltiples ejecuciones sobre la misma estructura no dupliquen opiniones.

    Args:
        catalogo: Diccionario de películas generado por `construir_catalogo()`.
        filas_calificaciones: Registros leídos desde `calificaciones.csv` o `.json`.

    Returns:
        Lista de diccionarios con las calificaciones rechazadas y su motivo.
    """
    validar_esquema(
        filas_calificaciones, COLUMNAS_REQUERIDAS_CALIFICACIONES, "calificaciones"
    )

    for ficha in catalogo.values():
        ficha["cantidad_valoraciones"] = 0
        ficha["suma_valoraciones"] = 0.0
        ficha["media_valoraciones"] = 0.0

    rechazos_calificaciones: list[dict[str, Any]] = []

    for indice, fila in enumerate(filas_calificaciones, start=1):
        movie_id = str(fila.get("movieId", "")).strip()
        rating_raw = str(fila.get("rating", "")).strip()
        user_id = str(fila.get("userId", "")).strip()

        if not movie_id or movie_id not in catalogo:
            rechazos_calificaciones.append({
                "origen": "calificaciones",
                "fila": indice,
                "movieId": movie_id,
                "detalle": f"userId={user_id}, rating={rating_raw}",
                "motivo": "movieId inexistente en catalogo",
            })
            continue

        try:
            valor_rating = float(rating_raw)
        except ValueError:
            rechazos_calificaciones.append({
                "origen": "calificaciones",
                "fila": indice,
                "movieId": movie_id,
                "detalle": f"userId={user_id}, rating={rating_raw}",
                "motivo": "rating no numerico",
            })
            continue

        if not (ESCALA_MIN_RATING <= valor_rating <= ESCALA_MAX_RATING):
            rechazos_calificaciones.append({
                "origen": "calificaciones",
                "fila": indice,
                "movieId": movie_id,
                "detalle": f"userId={user_id}, rating={rating_raw}",
                "motivo": f"rating fuera de escala [{ESCALA_MIN_RATING}, {ESCALA_MAX_RATING}]",
            })
            continue

        ficha = catalogo[movie_id]
        ficha["cantidad_valoraciones"] += 1
        ficha["suma_valoraciones"] += valor_rating
        ficha["media_valoraciones"] = (
            ficha["suma_valoraciones"] / ficha["cantidad_valoraciones"]
        )

    return rechazos_calificaciones


def buscar_titulos(
    catalogo: dict[str, dict[str, Any]],
    consulta: ConsultaCatalogo,
) -> list[dict[str, Any]]:
    """Aplica la búsqueda por texto y los filtros de género y año sobre el catálogo."""
    consulta.validar_parametros()
    seleccionadas: list[dict[str, Any]] = []
    for pelicula in catalogo.values():
        if consulta.coincide_con_pelicula(pelicula):
            seleccionadas.append(pelicula)
    return seleccionadas


def generar_lista(
    peliculas_filtradas: list[dict[str, Any]],
    min_valoraciones: int = 1,
    ruta_salida: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Aplica el mínimo de valoraciones, ordena con regla de desempate y exporta si se indica.

    Regla de desempate documentada:
        1. `media_valoraciones` descendente (redondeada a 6 decimales para evitar ruido flotante).
        2. `cantidad_valoraciones` descendente (mayor respaldo de opiniones primero).
        3. `titulo_limpio` alfabético ascendente (insensible a mayúsculas/minúsculas).
        4. `movieId` ascendente como cierre determinista.
    """
    if min_valoraciones < 0:
        raise ValueError("El mínimo de valoraciones no puede ser negativo.")

    respaldadas = [
        p for p in peliculas_filtradas if p.get("cantidad_valoraciones", 0) >= min_valoraciones
    ]

    ordenadas = sorted(
        respaldadas,
        key=lambda p: (
            -round(float(p.get("media_valoraciones", 0.0)), 6),
            -int(p.get("cantidad_valoraciones", 0)),
            str(p.get("titulo_limpio", "")).lower(),
            str(p.get("movieId", "")),
        ),
    )

    if ruta_salida is not None:
        exportar_lista_csv(ordenadas, ruta_salida)

    return ordenadas


def exportar_lista_csv(lista_peliculas: list[dict[str, Any]], ruta_salida: str | Path) -> Path:
    """Guarda la lista ordenada de películas en un archivo CSV."""
    path_obj = Path(ruta_salida)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    columnas = [
        "movieId",
        "titulo_limpio",
        "anio",
        "generos",
        "cantidad_valoraciones",
        "media_valoraciones",
    ]
    with path_obj.open(mode="w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for p in lista_peliculas:
            escritor.writerow({
                "movieId": p["movieId"],
                "titulo_limpio": p["titulo_limpio"],
                "anio": "" if p["anio"] is None else p["anio"],
                "generos": "|".join(p["generos"]),
                "cantidad_valoraciones": p["cantidad_valoraciones"],
                "media_valoraciones": f"{p['media_valoraciones']:.2f}",
            })
    return path_obj


def exportar_rechazos_csv(rechazos: list[dict[str, Any]], ruta_rechazos: str | Path) -> Path:
    """Guarda el listado consolidado de registros rechazados y sus motivos en CSV."""
    path_obj = Path(ruta_rechazos)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    columnas = ["origen", "fila", "movieId", "detalle", "motivo"]
    with path_obj.open(mode="w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for r in rechazos:
            escritor.writerow({
                "origen": r.get("origen", ""),
                "fila": r.get("fila", ""),
                "movieId": r.get("movieId", ""),
                "detalle": r.get("detalle", ""),
                "motivo": r.get("motivo", ""),
            })
    return path_obj