# TP2_POD_ArmasNetriIgnacio
# Catálogo de películas con listas de selección — TP2

**Asignatura:** Programación Orientada a Datos — Licenciatura en Ciencia de Datos, UCA  
**Autor:** Ignacio Armas Netri
**Modalidad:** Trabajo Práctico 2 individual

## 1. Problema y solución

Pregunta que busca resolver la aplicación: ¿Cómo crear una lista de películas según su género, año o título sin que una película con muy pocas valoraciones aparezca en los primeros puestos solo por tener un promedio alto?

La aplicación permitirá buscar y filtrar películas, calcular la cantidad y el promedio de sus valoraciones, establecer un mínimo de opiniones y ordenar los resultados. Está pensada para quien quiera explorar un catálogo o preparar una lista temática de películas.

**Alcance:** lectura de CSV y JSON, validación y limpieza, búsqueda y filtros combinables, cálculo de cantidad y promedio de valoraciones y exportación de resultados. No incluye interfaz gráfica o web, recomendaciones con aprendizaje automático ni conexión a servicios externos.

## 2. Datos y procedencia

La carpeta `data/` contiene muestras equivalentes en CSV y JSON:

| Archivo | Unidad de análisis | Variables principales |
|---|---|---|
| `peliculas.csv` / `peliculas.json` | Una película por fila/objeto | `movieId`, `title`, `genres` |
| `valoraciones.csv` / `valoraciones.json` | Una valoración por fila/objeto | `userId`, `movieId`, `rating`, `timestamp` |

El catálogo contiene **90 películas** y la tabla contiene **1254 valoraciones**. `movieId` relaciona ambas tablas; `genres` contiene géneros separados por `|`; `rating` usa una escala de 0.5 a 5.0; `timestamp` es una marca temporal Unix.

**Procedencia:** los archivos CSV fueron generados por la IA gemini, para este trabajo. Los JSON contienen los mismos datos para comprobar la lectura de ambos formatos. Las valoraciones, los identificadores de usuario y las fechas también son sintéticos. No es una descarga oficial de MovieLens y las puntuaciones no representan opiniones reales.

**Limitaciones:** es una muestra pequeña y sus valoraciones son simuladas, por lo que no permite concluir cuáles son las películas mejor valoradas por el público real.

## 3. Flujo de procesamiento

La aplicación sigue el flujo **leer → inspeccionar y validar → limpiar → analizar → exportar**. Los rechazos se registran con el motivo correspondiente, en lugar de ocultarse.

- Catálogo: validar que `movieId` y `title` no estén vacíos y que `movieId` sea único; conservar la primera aparición y registrar duplicados.
- Título y año: extraer el año final con la expresión regular `^(.+?)\s*\((\d{4})\)\s*$`; complementar el patrón con la validación del rango `1888–2030`. Si no hay año, conservarlo como desconocido.
- Géneros: dividir el campo por `|`, quitar espacios y representar el valor vacío o `(no genres listed)` como una lista vacía.
- Valoraciones: convertir `rating` a número, aceptar solo valores en `[0.5, 5.0]` y rechazar referencias a películas inexistentes. Las filas inválidas no modifican los promedios.
- Ranking: aplicar los filtros y el mínimo de valoraciones; ordenar por promedio descendente, cantidad de valoraciones descendente y título ascendente.

## 4. Diseño del programa

- `src/fuentes.py`: clase común `FuenteDatos` con `cargar(ruta)` y sus implementaciones `FuenteCSV` y `FuenteJSON`, que devuelven una lista de diccionarios con la misma estructura.
- `src/modelo.py`: clase `ConsultaCatalogo`, que contiene y valida los filtros de la consulta.
- `src/pipeline.py`: funciones para construir el catálogo, validar y acumular valoraciones, buscar, generar la lista y exportar rechazos.
- `src/main.py`: recibe los parámetros de consola y coordina el flujo.
- `tests/`: pruebas automatizadas; `data/`: entradas documentadas; `outputs/`: resultados generados.

## 5. Requisitos

Python 3.10 o superior. Se utiliza la biblioteca estándar de Python, sin dependencias externas.

