# Ficha Técnica de los Archivos de Datos (`data/`)

Este directorio aloja los conjuntos de datos de entrada en formatos equivalentes **CSV** y **JSON** para el catálogo de películas y sus calificaciones.

## 1. Procedencia
Los archivos **CSV fueron creados con ayuda de la IA Gemini**. Los JSON contienen los mismos datos, para comprobar la lectura de ambos formatos.

- **Datos sintéticos:** películas, valoraciones, usuarios (`101` a `110`) y fechas son simulados; no representan opiniones reales.
- **Responsable y fecha:** Ignacio Armas Netri, octubre de 2026.
- **Condiciones de uso:** datos creados para este trabajo, sin datos personales ni información sensible.
- **Casos de prueba incluidos a propósito:** 2 títulos sin año (`movieId` 54 `"Cosmos"` y 55 `"Metropolis Restaurada"`), 2 películas inválidas (`movieId="10"` repetido y `movieId="57"` sin título) y 5 calificaciones inválidas (`movieId` inexistentes `9999` y `8888`, ratings `6.5` y `-1.0`, y el valor no numérico `"N/A"`). Permiten verificar la validación y los casos del Tema 10 (valoraciones 3 y 5 → media 4.0, exclusión por mínimo y desempate).

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

## 4. Limitaciones

- La muestra es pequeña (58 películas, 155 valoraciones) y la mayoría de las películas tiene pocas opiniones.
- Las valoraciones son simuladas, así que los promedios no reflejan el gusto del público real.
- Los 7 registros con errores intencionales (2 del catálogo y 5 de calificaciones) y los 2 títulos sin año existen para probar la validación; no son datos reales.
