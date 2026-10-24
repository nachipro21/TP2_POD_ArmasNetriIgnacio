"""Punto de entrada por línea de comandos para el Catálogo de Películas (TP2 - Tema 10).

Permite ejecutar el flujo reproducible completo desde la terminal:
leer -> inspeccionar y validar -> limpiar y transformar -> analizar -> comunicar el resultado.
"""

import argparse
from pathlib import Path
import sys
from typing import Any

# Soporte para ejecución tanto con `python3 src/main.py` como con `python3 -m src.main`
RUTA_RAIZ = Path(__file__).resolve().parent.parent
if str(RUTA_RAIZ) not in sys.path:
    sys.path.insert(0, str(RUTA_RAIZ))

# Las rutas por defecto se resuelven desde la raíz del repositorio, para que la
# aplicación funcione sin importar desde qué directorio se ejecute.
DIR_DATOS = RUTA_RAIZ / "data"
RUTA_SALIDA_POR_DEFECTO = RUTA_RAIZ / "outputs" / "lista_seleccionada.csv"
RUTA_RECHAZOS_POR_DEFECTO = RUTA_RAIZ / "outputs" / "rechazos.csv"

try:
    from src.fuentes import crear_fuente
    from src.modelo import ConsultaCatalogo
    from src.pipeline import (
        acumular_valoraciones,
        buscar_titulos,
        construir_catalogo,
        exportar_rechazos_csv,
        generar_lista,
    )
except ImportError:
    from fuentes import crear_fuente
    from modelo import ConsultaCatalogo
    from pipeline import (
        acumular_valoraciones,
        buscar_titulos,
        construir_catalogo,
        exportar_rechazos_csv,
        generar_lista,
    )


def construir_parser() -> argparse.ArgumentParser:
    """Define los argumentos de línea de comandos de la aplicación."""
    parser = argparse.ArgumentParser(
        description="Catálogo de películas con búsqueda, filtros y mínimo de valoraciones (TP2 - Tema 10)."
    )
    parser.add_argument(
        "--formato",
        choices=["csv", "json"],
        default="csv",
        help="Formato de los archivos de entrada en data/ ('csv' o 'json'). Por defecto: csv.",
    )
    parser.add_argument(
        "--ruta-peliculas",
        type=str,
        default=None,
        help="Ruta personalizada al archivo de películas (opcional).",
    )
    parser.add_argument(
        "--ruta-calificaciones",
        type=str,
        default=None,
        help="Ruta personalizada al archivo de calificaciones (opcional).",
    )
    parser.add_argument(
        "--texto",
        type=str,
        default=None,
        help="Texto a buscar dentro del título de la película (opcional).",
    )
    parser.add_argument(
        "--genero",
        type=str,
        default=None,
        help="Filtrar por género cinematográfico, ej. 'Crime', 'Sci-Fi', 'Drama' (opcional).",
    )
    parser.add_argument(
        "--anio",
        type=int,
        default=None,
        help="Filtrar por año de estreno exacto, ej. 1995 (opcional).",
    )
    parser.add_argument(
        "--min-valoraciones",
        type=int,
        default=2,
        help="Cantidad mínima de valoraciones válidas requerida (por defecto: 2).",
    )
    parser.add_argument(
        "--ruta-salida",
        type=str,
        default=None,
        help="Ruta del CSV donde se exportará la lista seleccionada (por defecto: outputs/lista_seleccionada.csv).",
    )
    parser.add_argument(
        "--ruta-rechazos",
        type=str,
        default=None,
        help="Ruta del CSV donde se exportarán los registros rechazados (por defecto: outputs/rechazos.csv).",
    )
    return parser


def ruta_legible(ruta: str | Path) -> str:
    """Muestra una ruta relativa a la raíz del repositorio cuando está dentro de ella."""
    try:
        return str(Path(ruta).resolve().relative_to(RUTA_RAIZ))
    except ValueError:
        return str(ruta)


def mostrar_tabla_resultados(
    lista_peliculas: list[dict[str, Any]],
    consulta: ConsultaCatalogo,
    cant_rechazos_cat: int,
    cant_rechazos_cal: int,
    ruta_salida: str | Path,
    ruta_rechazos: str | Path,
) -> None:
    """Imprime en consola un resumen legible de la ejecución y la tabla ordenada."""
    linea = "-" * 84
    print("=== LISTA DE PELÍCULAS SELECCIONADAS ===")
    print(f"Filtros: {consulta.resumen_filtros()}")
    print(linea)
    print(f"{'ID':<5} | {'Título':<30} | {'Año':<4} | {'Géneros':<24} | {'Val.':<4} | {'Media':<5}")
    print(linea)

    if not lista_peliculas:
        print("No se encontraron películas que coincidan con los criterios especificados.")
    else:
        for p in lista_peliculas:
            titulo_corto = p["titulo_limpio"][:30]
            anio_str = str(p["anio"]) if p["anio"] is not None else "S/A"
            generos_str = ", ".join(p["generos"])[:24]
            val_str = str(p["cantidad_valoraciones"])
            media = p["media_valoraciones"]
            media_str = "s/d" if media is None else f"{media:.2f}"
            print(
                f"{p['movieId']:<5} | {titulo_corto:<30} | {anio_str:<4} | "
                f"{generos_str:<24} | {val_str:<4} | {media_str:<5}"
            )

    print(linea)
    print(
        f"Total seleccionadas: {len(lista_peliculas)} | "
        f"Rechazos de catálogo: {cant_rechazos_cat} | "
        f"Rechazos de calificaciones: {cant_rechazos_cal}"
    )
    print(f"Archivos exportados en: {ruta_legible(ruta_salida)} y {ruta_legible(ruta_rechazos)}")


def ejecutar_flujo(args: argparse.Namespace) -> int:
    """Coordina el flujo reproducible de punta a punta."""
    formato = args.formato.lower()
    ruta_peliculas = (
        Path(args.ruta_peliculas)
        if args.ruta_peliculas
        else DIR_DATOS / f"peliculas.{formato}"
    )
    ruta_calificaciones = (
        Path(args.ruta_calificaciones)
        if args.ruta_calificaciones
        else DIR_DATOS / f"calificaciones.{formato}"
    )

    ruta_salida = Path(args.ruta_salida) if args.ruta_salida else RUTA_SALIDA_POR_DEFECTO
    ruta_rechazos = Path(args.ruta_rechazos) if args.ruta_rechazos else RUTA_RECHAZOS_POR_DEFECTO

    fuente = crear_fuente(formato)
    filas_peliculas = fuente.cargar(ruta_peliculas)
    filas_calificaciones = fuente.cargar(ruta_calificaciones)

    catalogo, rechazos_catalogo = construir_catalogo(filas_peliculas)
    rechazos_calificaciones = acumular_valoraciones(catalogo, filas_calificaciones)

    consulta = ConsultaCatalogo(
        texto_busqueda=args.texto,
        genero=args.genero,
        anio=args.anio,
        min_valoraciones=args.min_valoraciones,
    )

    peliculas_filtradas = buscar_titulos(catalogo, consulta)
    lista_final = generar_lista(
        peliculas_filtradas,
        min_valoraciones=consulta.min_valoraciones,
        ruta_salida=ruta_salida,
    )

    todos_los_rechazos = rechazos_catalogo + rechazos_calificaciones
    exportar_rechazos_csv(todos_los_rechazos, ruta_rechazos)

    mostrar_tabla_resultados(
        lista_peliculas=lista_final,
        consulta=consulta,
        cant_rechazos_cat=len(rechazos_catalogo),
        cant_rechazos_cal=len(rechazos_calificaciones),
        ruta_salida=ruta_salida,
        ruta_rechazos=ruta_rechazos,
    )
    return 0


def main() -> int:
    """Punto de entrada principal con manejo explícito de errores."""
    parser = construir_parser()
    args = parser.parse_args()
    try:
        return ejecutar_flujo(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error en la ejecución: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())