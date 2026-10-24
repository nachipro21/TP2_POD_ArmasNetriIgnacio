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

El catálogo contiene **58 películas** y la tabla contiene **155 valoraciones**. `movieId` relaciona ambas tablas; `genres` contiene géneros separados por `|`; `rating` usa una escala de 0.5 a 5.0; `timestamp` es una marca temporal Unix.

**Procedencia:** los archivos CSV fueron generados por la IA gemini, para este trabajo. Los JSON contienen los mismos datos para comprobar la lectura de ambos formatos. Las valoraciones, los identificadores de usuario y las fechas también son sintéticos. No es una descarga oficial de MovieLens y las puntuaciones no representan opiniones reales.

**Limitaciones:** es una muestra pequeña y sus valoraciones son simuladas, por lo que no permite concluir cuáles son las películas mejor valoradas por el público real.

## 3. Flujo de procesamiento

Se implementa una aplicación en Python ejecutable por línea de comandos que:
1. Carga datos tabulares equivalentes desde archivos **CSV** o **JSON** mediante una interfaz polimórfica común (`FuenteDatos`).
2. Construye un índice validado del catálogo (`construir_catalogo()`), extrayendo el año de estreno mediante expresiones regulares, separando géneros múltiples y descartando registros inválidos o con identificadores duplicados.
3. Acumula las valoraciones por película (`acumular_valoraciones()`), calculando cantidad de opiniones y promedio, y registrando en un archivo de incidencias aquellas calificaciones fuera de la escala `[0.5, 5.0]` o asociadas a identificadores de películas inexistentes.
4. Aplica búsquedas por texto en el título, filtro por género y filtro por año (`buscar_titulos()`) encapsulados en la clase de dominio `ConsultaCatalogo`.
5. Filtra por cantidad mínima configurable de valoraciones, ordena los resultados con una regla de desempate explícita (`media` descendente, `cantidad` descendente y `titulo` ascendente) y exporta tanto la lista seleccionada como el registro de filas rechazadas (`generar_lista()`).


## 4. Diseño del programa

- `src/fuentes.py`: clase común `FuenteDatos` con `cargar(ruta)` y sus implementaciones `FuenteCSV` y `FuenteJSON`, que devuelven una lista de diccionarios con la misma estructura.
- `src/modelo.py`: clase `ConsultaCatalogo`, que contiene y valida los filtros de la consulta.
- `src/pipeline.py`: funciones para construir el catálogo, validar y acumular valoraciones, buscar, generar la lista y exportar rechazos.
- `src/main.py`: recibe los parámetros de consola y coordina el flujo.
- `tests/`: pruebas automatizadas; `data/`: entradas documentadas; `outputs/`: resultados generados.

```text
tp2-apellido/
|-- README.md               # Documentación integral del proyecto
|-- requirements.txt        # Especificación del entorno (biblioteca estándar Python 3.10+)
|-- .gitignore              # Exclusión de entornos virtuales, cachés y archivos temporales
|-- src/
|   |-- main.py             # Interfaz de línea de comandos (CLI) y coordinación del flujo
|   |-- fuentes.py          # Clase base abstracta FuenteDatos y clases FuenteCSV / FuenteJSON
|   |-- modelo.py           # Clase de dominio ConsultaCatalogo y validación de filtros
|   `-- pipeline.py         # Funciones de limpieza, regex, acumulación, búsqueda y exportación
|-- tests/
|   `-- test_catalogo.py    # Suite de pruebas automatizadas con unittest
|-- data/
|   |-- README.md           # Ficha técnica específica de los archivos de datos
|   |-- peliculas.csv
|   |-- peliculas.json
|   |-- calificaciones.csv
|   `-- calificaciones.json
`-- outputs/                # Directorio de salida para listas generadas y reporte de rechazos

## 5. Requisitos

Python 3.10 o superior. Se utiliza la biblioteca estándar de Python, sin dependencias externas.

## 6. Resultado esperado e interpretación
El programa produce una tabla de salida (en consola y exportada a `outputs/`) con las películas que superan el umbral mínimo de respaldo y coinciden con los filtros solicitados, indicando su identificador, título limpio, año de estreno, géneros, cantidad de valoraciones válidas y calificación media redondeada a dos decimales. Adicionalmente, genera un reporte de rechazos detallando qué filas de entrada fueron descartadas y el motivo exacto.

## 7. Decisiones de limpieza y reglas de negocio

1. **Unicidad y completitud en el catálogo (`construir_catalogo`):**
   * Se rechazan filas con `movieId` vacío, `title` vacío o `movieId` repetido (conservando la primera aparición válida y enviando las duplicadas a la lista de rechazos con el motivo `"movieId duplicado"`).
   * Los géneros en `genres` se dividen por `|` eliminando espacios sobrantes; si figura `(no genres listed)` o vacío, se asigna lista vacía `[]`.
2. **Integridad referencial y escala en valoraciones (`acumular_valoraciones`):**
   * Se verifica que `rating` pueda convertirse a `float` y pertenezca al intervalo cerrado `[0.5, 5.0]`. Valores como `6.5`, `-1.0` o `"N/A"` se registran en rechazos.
   * Se verifica que `movieId` exista en el índice del catálogo previamente construido. Las calificaciones hacia identificadores inexistentes (ej. `9999`) se registran en rechazos como `"movieId inexistente en catalogo"` sin alterar los conteos.
   * Cada calificación válida se contabiliza una única vez sobre su película correspondiente.
3. **Regla de desempate en el ranking (`generar_lista`):**
   * Luego de aplicar los filtros de `ConsultaCatalogo` y descartar películas con `cantidad < min_valoraciones`, la lista se ordena por:
     1. `media` descendente (mayor puntuación promedio primero),
     2. `cantidad` descendente (ante igual promedio, prioriza la película con mayor respaldo de opiniones),
     3. `titulo_limpio` alfabético ascendente (criterio determinista final).