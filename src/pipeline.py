"""Módulo de procesamiento reproducible del catálogo de películas (TP2 - Tema 10).

Implementa las funciones requeridas por la consigna:
- `extraer_titulo_y_anio()`: aplica la expresión regular sobre el título y valida el año.
- `construir_catalogo()`: crea el índice de películas por `movieId`, validando unicidad y esquema.
- `acumular_valoraciones()`: valida cada calificación, descarta duplicados, calcula cantidad y
  media de opiniones y registra rechazos.
- `buscar_titulos()`: aplica búsqueda y filtros mediante `ConsultaCatalogo`.
- `generar_lista()`: filtra por mínimo de valoraciones, ordena con regla de desempate y exporta.
"""

import csv
from pathlib import Path
import re
from typing import Any

from src.modelo import ANIO_MAXIMO_CINE, ANIO_MINIMO_CINE, ConsultaCatalogo

# Expresión regular que captura el título limpio en el grupo 1 y un año de 4 dígitos
# entre paréntesis al final de la cadena en el grupo 2. Ejemplo: "Toy Story (1995)".
# Solo comprueba la FORMA del texto (cuatro dígitos entre paréntesis al final); que el
# año sea plausible se comprueba aparte en `extraer_titulo_y_anio()`.
PATRON_TITULO_ANIO = re.compile(r"^(.+?)\s*\((\d{4})\)\s*$")

ESCALA_MIN_RATING = 0.5
ESCALA_MAX_RATING = 5.0
PASO_RATING = 0.5

COLUMNAS_REQUERIDAS_PELICULAS = {"movieId", "title", "genres"}
COLUMNAS_REQUERIDAS_CALIFICACIONES = {"userId", "movieId", "rating", "timestamp"}


def validar_esquema(filas: list[dict[str, str]], columnas_requeridas: set[str], nombre_tabla: str) -> None:
    """Verifica que la tabla no esté vacía y que TODOS sus registros tengan las columnas esperadas."""
    if not filas:
        raise ValueError(f"La tabla '{nombre_tabla}' no contiene registros.")
    for numero, fila in enumerate(filas, start=1):
        faltantes = columnas_requeridas - set(fila.keys())
        if faltantes:
            faltantes_str = ", ".join(sorted(faltantes))
            raise ValueError(
                f"Faltan columnas obligatorias en '{nombre_tabla}' "
                f"(registro {numero}): {faltantes_str}."
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
        Una película sin valoraciones queda con `media_valoraciones = None` (no 0.0,
        que sería un valor fuera de la escala de calificación).
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
            "media_valoraciones": None,
        }

    return catalogo, rechazos


def _rechazo_calificacion(
    indice: int, movie_id: str, user_id: str, rating_raw: str, motivo: str
) -> dict[str, Any]:
    """Arma el registro de una calificación rechazada, con el mismo formato siempre."""
    return {
        "origen": "calificaciones",
        "fila": indice,
        "movieId": movie_id,
        "detalle": f"userId={user_id}, rating={rating_raw}",
        "motivo": motivo,
    }


def acumular_valoraciones(
    catalogo: dict[str, dict[str, Any]],
    filas_calificaciones: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Valida las calificaciones, descarta duplicados y calcula cantidad y media por película.

    Reglas aplicadas a cada fila, en este orden (la primera que falla la rechaza):
        1. `movieId` debe existir en el catálogo.
        2. `userId` no puede estar vacío.
        3. `rating` debe ser numérico, estar en [0.5, 5.0] y ser múltiplo de 0.5.
        4. `timestamp` debe ser un entero no negativo (segundos Unix).
    Luego, para cada par (`userId`, `movieId`) se cuenta UNA sola opinión: la de
    `timestamp` más reciente (si empatan, la que aparece más abajo en el archivo). Las
    demás se registran como rechazos "valoracion duplicada".

    Reinicia los contadores del catálogo antes de acumular para garantizar que
    múltiples ejecuciones sobre la misma estructura no dupliquen opiniones.

    Args:
        catalogo: Diccionario de películas generado por `construir_catalogo()`.
        filas_calificaciones: Registros leídos desde `calificaciones.csv` o `.json`.

    Returns:
        Lista de diccionarios con las calificaciones rechazadas y su motivo, en el
        orden de aparición en el archivo de entrada.
    """
    validar_esquema(
        filas_calificaciones, COLUMNAS_REQUERIDAS_CALIFICACIONES, "calificaciones"
    )

    for ficha in catalogo.values():
        ficha["cantidad_valoraciones"] = 0
        ficha["suma_valoraciones"] = 0.0
        ficha["media_valoraciones"] = None

    rechazos_calificaciones: list[dict[str, Any]] = []
    validas: list[dict[str, Any]] = []

    for indice, fila in enumerate(filas_calificaciones, start=1):
        movie_id = str(fila.get("movieId", "")).strip()
        rating_raw = str(fila.get("rating", "")).strip()
        user_id = str(fila.get("userId", "")).strip()
        timestamp_raw = str(fila.get("timestamp", "")).strip()

        def rechazar(motivo: str) -> None:
            rechazos_calificaciones.append(
                _rechazo_calificacion(indice, movie_id, user_id, rating_raw, motivo)
            )

        if not movie_id or movie_id not in catalogo:
            rechazar("movieId inexistente en catalogo")
            continue

        if not user_id:
            rechazar("userId vacio")
            continue

        try:
            valor_rating = float(rating_raw)
        except ValueError:
            rechazar("rating no numerico")
            continue

        if not (ESCALA_MIN_RATING <= valor_rating <= ESCALA_MAX_RATING):
            rechazar(f"rating fuera de escala [{ESCALA_MIN_RATING}, {ESCALA_MAX_RATING}]")
            continue

        if (valor_rating / PASO_RATING) % 1 != 0:
            rechazar(f"rating no es multiplo de {PASO_RATING}")
            continue

        try:
            valor_timestamp = int(timestamp_raw)
        except ValueError:
            rechazar("timestamp invalido")
            continue
        if valor_timestamp < 0:
            rechazar("timestamp invalido")
            continue

        validas.append({
            "fila": indice,
            "movie_id": movie_id,
            "user_id": user_id,
            "rating": valor_rating,
            "rating_raw": rating_raw,
            "timestamp": valor_timestamp,
        })

    # Una sola opinión por (userId, movieId): se conserva la más reciente.
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for registro in validas:
        grupos.setdefault((registro["user_id"], registro["movie_id"]), []).append(registro)

    conservadas: list[dict[str, Any]] = []
    for grupo in grupos.values():
        ganadora = max(grupo, key=lambda r: (r["timestamp"], r["fila"]))
        conservadas.append(ganadora)
        for descartada in grupo:
            if descartada is not ganadora:
                rechazos_calificaciones.append(
                    _rechazo_calificacion(
                        descartada["fila"],
                        descartada["movie_id"],
                        descartada["user_id"],
                        descartada["rating_raw"],
                        f"valoracion duplicada (userId, movieId); se conserva la fila {ganadora['fila']}",
                    )
                )

    rechazos_calificaciones.sort(key=lambda r: r["fila"])
    conservadas.sort(key=lambda r: r["fila"])

    for registro in conservadas:
        ficha = catalogo[registro["movie_id"]]
        ficha["cantidad_valoraciones"] += 1
        ficha["suma_valoraciones"] += registro["rating"]
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


def _clave_de_orden(pelicula: dict[str, Any]) -> tuple[float, int, str, str]:
    """Clave de ordenamiento del ranking (ver regla de desempate en `generar_lista`)."""
    media = pelicula.get("media_valoraciones")
    # Sin valoraciones no hay media: se ubica después de cualquier película valorada.
    media_orden = -1.0 if media is None else round(float(media), 6)
    return (
        -media_orden,
        -int(pelicula.get("cantidad_valoraciones", 0)),
        str(pelicula.get("titulo_limpio", "")).lower(),
        str(pelicula.get("movieId", "")),
    )


def generar_lista(
    peliculas_filtradas: list[dict[str, Any]],
    min_valoraciones: int = 1,
    ruta_salida: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Aplica el mínimo de valoraciones, ordena con regla de desempate y exporta si se indica.

    Regla de desempate documentada:
        1. `media_valoraciones` descendente (redondeada a 6 decimales para evitar ruido flotante;
           las películas sin valoraciones, posibles solo con `min_valoraciones = 0`, van al final).
        2. `cantidad_valoraciones` descendente (mayor respaldo de opiniones primero).
        3. `titulo_limpio` alfabético ascendente (insensible a mayúsculas/minúsculas).
        4. `movieId` ascendente como cierre determinista.
    """
    if min_valoraciones < 0:
        raise ValueError("El mínimo de valoraciones no puede ser negativo.")

    respaldadas = [
        p for p in peliculas_filtradas if p.get("cantidad_valoraciones", 0) >= min_valoraciones
    ]

    ordenadas = sorted(respaldadas, key=_clave_de_orden)

    if ruta_salida is not None:
        exportar_lista_csv(ordenadas, ruta_salida)

    return ordenadas


def exportar_lista_csv(lista_peliculas: list[dict[str, Any]], ruta_salida: str | Path) -> Path:
    """Guarda la lista ordenada de películas en un archivo CSV.

    La media de una película sin valoraciones se exporta como campo vacío.
    """
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
            media = p["media_valoraciones"]
            escritor.writerow({
                "movieId": p["movieId"],
                "titulo_limpio": p["titulo_limpio"],
                "anio": "" if p["anio"] is None else p["anio"],
                "generos": "|".join(p["generos"]),
                "cantidad_valoraciones": p["cantidad_valoraciones"],
                "media_valoraciones": "" if media is None else f"{media:.2f}",
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

