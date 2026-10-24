# Ficha Técnica de los Archivos de Datos (`data/`)

Este directorio aloja los conjuntos de datos de entrada en formatos equivalentes **CSV** y **JSON** para el catálogo de películas y sus calificaciones.

## 1. Procedencia y método de construcción (Datos adaptados y simulados)
1. **Catálogo base inspirado en MovieLens (`peliculas.csv` / `peliculas.json`):** Se tomaron 54 películas reales del conjunto público *MovieLens Latest Datasets (Small)* de **GroupLens Research** (University of Minnesota, `https://grouplens.org/datasets/movielens/`, licencia académica abierta *Harper & Konstan, 2015*), respetando su esquema original (`movieId`, `title`, `genres`). A esa base se le agregaron **2 títulos sin año** (`"Cosmos"` y `"Metropolis Restaurada"`) y **2 registros inválidos de prueba** (`movieId="10"` duplicado y `movieId="57"` con título vacío).
2. **Valoraciones simuladas (`calificaciones.csv` / `calificaciones.json`):** Se generaron mediante un script reproducible **150 valoraciones válidas** dentro de la escala `[0.5, 5.0]` y **5 registros con errores intencionales** (`movieId` inexistentes `"9999"` y `"8888"`, puntajes fuera de rango `"6.5"` y `"-1.0"`, y valor no numérico `"N/A"`). Esta simulación controlada garantiza que se puedan verificar de forma exacta todos los casos exigidos por el Tema 10 (como el caso de una película con valoraciones `3` y `5` que da media `4.0` y conteo `2`, la exclusión por mínimo de opiniones y las reglas de desempate).

* **Fecha de consulta y generación:** Octubre de 2026.
* **Privacidad:** Ningún archivo contiene datos personales reales ni información sensible.

## 2. Resumen de archivos incluidos en esta carpeta

| Archivo | Formato | Filas totales | Filas válidas | Filas con errores de prueba |
| :--- | :--- | :--- | :--- | :--- |
| `peliculas.csv` | CSV (UTF-8, separado por `,`) | 58 | 56 (54 con año + 2 sin año) | 2 (`movieId="10"` duplicado y `movieId="57"` sin título) |
| `peliculas.json` | JSON (lista de objetos) | 58 | 56 (idénticas a `peliculas.csv`) | 2 (idénticas a `peliculas.csv`) |
| `calificaciones.csv` | CSV (UTF-8, separado por `,`) | 155 | 150 (simuladas en `[0.5, 5.0]`) | 5 (`movieId` `9999` y `8888` inexistentes; ratings `6.5`, `-1.0` y `"N/A"`) |
| `calificaciones.json` | JSON (lista de objetos) | 155 | 150 (idénticas a `calificaciones.csv`) | 5 (idénticas a `calificaciones.csv`) |

## 3. Esquema detallado de campos

### `peliculas.csv` / `peliculas.json`
* **`movieId`** (`str`): Identificador único de la película en el catálogo.
* **`title`** (`str`): Nombre de la obra con el año de lanzamiento entre paréntesis al final, p. ej. `"Toy Story (1995)"`. Incluye dos títulos sin año (`"Cosmos"` y `"Metropolis Restaurada"`) para verificar la tolerancia del parser de expresiones regulares.
* **`genres`** (`str`): Categorías separadas por el carácter `|` (p. ej. `"Adventure|Children|Fantasy"`).

### `calificaciones.csv` / `calificaciones.json`
* **`userId`** (`str`): Código sintético del usuario evaluador (p. ej. `"101"` a `"110"`).
* **`movieId`** (`str`): Identificador de la película evaluada (clave foránea hacia `peliculas`).
* **`rating`** (`str` / convertible a `float`): Calificación en escala de `0.5` a `5.0` con incrementos de `0.5`.
* **`timestamp`** (`str` / convertible a `int`): Instante sintético de la calificación en segundos Unix UTC.
