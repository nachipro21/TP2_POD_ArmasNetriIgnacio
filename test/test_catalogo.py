"""Pruebas unitarias y de integración para el Catálogo de Películas (TP2 - Tema 10).

Cubre los requisitos del Paso 5 de la consigna y las verificaciones específicas
del Tema 10:
1. Caso normal: una película con valoraciones 3 y 5 debe tener media 4.0 y conteo 2.
2. Exclusión por mínimo de valoraciones: película con 1 sola opinión de 5.0 queda excluida.
3. Casos límite y entradas inválidas: títulos sin año, múltiples géneros, IDs duplicados,
   calificaciones fuera de escala y referencias a películas inexistentes.
4. Búsqueda sin coincidencias: devuelve lista vacía explícita.
5. Propiedades del resultado: combinar catálogo y calificaciones no duplica opiniones,
   y las entradas equivalentes en CSV y JSON producen exactamente el mismo resultado.
6. Validaciones adicionales: valoraciones repetidas de un mismo usuario, escala y timestamp,
   esquema incompleto, películas sin valoraciones, errores de lectura y ejecución por consola.
"""

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUTA_RAIZ = Path(__file__).resolve().parent.parent
if str(RUTA_RAIZ) not in sys.path:
    sys.path.insert(0, str(RUTA_RAIZ))

try:
    from src.fuentes import FuenteCSV, FuenteJSON, crear_fuente
    from src.modelo import ConsultaCatalogo
    from src.pipeline import (
        acumular_valoraciones,
        buscar_titulos,
        construir_catalogo,
        extraer_titulo_y_anio,
        generar_lista,
    )
except ImportError:
    from fuentes import FuenteCSV, FuenteJSON, crear_fuente
    from modelo import ConsultaCatalogo
    from pipeline import (
        acumular_valoraciones,
        buscar_titulos,
        construir_catalogo,
        extraer_titulo_y_anio,
        generar_lista,
    )


def localizar_archivo_datos(nombre: str) -> Path:
    """Localiza el archivo de datos tanto en `data/` como en el directorio actual."""
    candidatos = [
        RUTA_RAIZ / "data" / nombre,
        Path("data") / nombre,
        Path(__file__).resolve().parent / nombre,
    ]
    for ruta in candidatos:
        if ruta.exists():
            return ruta
    raise FileNotFoundError(f"No se pudo localizar '{nombre}' para las pruebas.")


class TestCatalogoPeliculas(unittest.TestCase):
    """Suite de pruebas ejecutables con `python3 -m unittest discover -s tests -v`."""

    def test_1_caso_normal_media_y_conteo(self) -> None:
        """Verifica que con valoraciones 3 y 5 una película tenga media 4.0 y conteo 2."""
        peliculas = [
            {"movieId": "1", "title": "Toy Story (1995)", "genres": "Animation|Comedy"}
        ]
        calificaciones = [
            {"userId": "101", "movieId": "1", "rating": "3.0", "timestamp": "100"},
            {"userId": "102", "movieId": "1", "rating": "5.0", "timestamp": "101"},
        ]
        catalogo, rechazos_cat = construir_catalogo(peliculas)
        rechazos_cal = acumular_valoraciones(catalogo, calificaciones)

        self.assertEqual(len(rechazos_cat), 0)
        self.assertEqual(len(rechazos_cal), 0)
        self.assertEqual(catalogo["1"]["cantidad_valoraciones"], 2)
        self.assertAlmostEqual(catalogo["1"]["media_valoraciones"], 4.0, places=5)

    def test_2_exclusion_por_minimo_de_valoraciones(self) -> None:
        """Comprueba que una película con una sola valoración de 5.0 quede excluida si min=2."""
        peliculas = [
            {"movieId": "1", "title": "Toy Story (1995)", "genres": "Drama"},
            {"movieId": "53", "title": "Lamerica (1994)", "genres": "Drama"},
        ]
        calificaciones = [
            {"userId": "1", "movieId": "1", "rating": "3.0", "timestamp": "10"},
            {"userId": "2", "movieId": "1", "rating": "5.0", "timestamp": "11"},
            {"userId": "1", "movieId": "53", "rating": "5.0", "timestamp": "12"},
        ]
        catalogo, _ = construir_catalogo(peliculas)
        acumular_valoraciones(catalogo, calificaciones)

        consulta = ConsultaCatalogo(genero="Drama", min_valoraciones=2)
        filtradas = buscar_titulos(catalogo, consulta)
        lista_final = generar_lista(filtradas, min_valoraciones=consulta.min_valoraciones)

        ids_seleccionados = [p["movieId"] for p in lista_final]
        self.assertEqual(ids_seleccionados, ["1"])
        self.assertNotIn("53", ids_seleccionados)

    def test_3_regex_titulos_sin_anio_y_multiples_generos(self) -> None:
        """Verifica la expresión regular ante títulos con año, sin año y fuera de rango."""
        titulo, anio = extraer_titulo_y_anio("Star Wars: Episode IV (1977)")
        self.assertEqual(titulo, "Star Wars: Episode IV")
        self.assertEqual(anio, 1977)

        titulo_sin_anio, anio_nulo = extraer_titulo_y_anio("Cosmos")
        self.assertEqual(titulo_sin_anio, "Cosmos")
        self.assertIsNone(anio_nulo)

        titulo_anio_invalido, anio_inv = extraer_titulo_y_anio("Pelicula Futura (9999)")
        self.assertIsNone(anio_inv)

        peliculas = [
            {"movieId": "54", "title": "Cosmos", "genres": "Documentary|Sci-Fi"}
        ]
        catalogo, _ = construir_catalogo(peliculas)
        self.assertEqual(catalogo["54"]["generos"], ["Documentary", "Sci-Fi"])
        self.assertIsNone(catalogo["54"]["anio"])

        # Debe encontrarse por cualquiera de sus múltiples géneros si no se filtra por año
        c_scifi = ConsultaCatalogo(genero="Sci-Fi", min_valoraciones=0)
        self.assertEqual(len(buscar_titulos(catalogo, c_scifi)), 1)

        # Debe excluirse si se exige un año específico
        c_con_anio = ConsultaCatalogo(genero="Sci-Fi", anio=1995, min_valoraciones=0)
        self.assertEqual(len(buscar_titulos(catalogo, c_con_anio)), 0)

    def test_4_entradas_invalidas_y_registro_de_rechazos(self) -> None:
        """Comprueba unicidad de IDs, escala de calificación, referencias huérfanas y parámetros."""
        peliculas = [
            {"movieId": "10", "title": "GoldenEye (1995)", "genres": "Action"},
            {"movieId": "10", "title": "GoldenEye Duplicado (1995)", "genres": "Action"},
            {"movieId": "57", "title": "   ", "genres": "Drama"},
        ]
        calificaciones = [
            {"userId": "1", "movieId": "10", "rating": "4.0", "timestamp": "1"},
            {"userId": "2", "movieId": "9999", "rating": "4.5", "timestamp": "2"},
            {"userId": "3", "movieId": "10", "rating": "6.5", "timestamp": "3"},
            {"userId": "4", "movieId": "10", "rating": "-1.0", "timestamp": "4"},
            {"userId": "5", "movieId": "10", "rating": "N/A", "timestamp": "5"},
        ]
        catalogo, rechazos_cat = construir_catalogo(peliculas)
        rechazos_cal = acumular_valoraciones(catalogo, calificaciones)

        self.assertEqual(len(catalogo), 1)
        self.assertEqual(len(rechazos_cat), 2)
        self.assertEqual(len(rechazos_cal), 4)
        self.assertEqual(catalogo["10"]["cantidad_valoraciones"], 1)
        self.assertAlmostEqual(catalogo["10"]["media_valoraciones"], 4.0)

        with self.assertRaises(ValueError):
            ConsultaCatalogo(min_valoraciones=-1)
        with self.assertRaises(ValueError):
            ConsultaCatalogo(anio=1500)

    def test_5_busqueda_sin_coincidencias_y_desempate(self) -> None:
        """Verifica respuesta vacía cuando no hay coincidencias y orden de desempate."""
        peliculas = [
            {"movieId": "50", "title": "Usual Suspects, The (1995)", "genres": "Crime"},
            {"movieId": "6", "title": "Heat (1995)", "genres": "Crime"},
            {"movieId": "47", "title": "Seven (1995)", "genres": "Crime"},
        ]
        calificaciones = [
            # Seven: 3 valoraciones de 4.5
            {"userId": "1", "movieId": "47", "rating": "4.5", "timestamp": "1"},
            {"userId": "2", "movieId": "47", "rating": "4.5", "timestamp": "2"},
            {"userId": "3", "movieId": "47", "rating": "4.5", "timestamp": "3"},
            # Heat y Usual Suspects: 2 valoraciones de 4.5 cada una
            {"userId": "1", "movieId": "50", "rating": "4.5", "timestamp": "4"},
            {"userId": "2", "movieId": "50", "rating": "4.5", "timestamp": "5"},
            {"userId": "1", "movieId": "6", "rating": "4.5", "timestamp": "6"},
            {"userId": "2", "movieId": "6", "rating": "4.5", "timestamp": "7"},
        ]
        catalogo, _ = construir_catalogo(peliculas)
        acumular_valoraciones(catalogo, calificaciones)

        consulta_vacia = ConsultaCatalogo(genero="Musical", min_valoraciones=1)
        self.assertEqual(buscar_titulos(catalogo, consulta_vacia), [])

        consulta_crime = ConsultaCatalogo(genero="Crime", min_valoraciones=2)
        lista = generar_lista(buscar_titulos(catalogo, consulta_crime), min_valoraciones=2)
        # Orden esperado: 1º Seven (conteo 3), 2º Heat (conteo 2, H antes que U), 3º Usual Suspects
        self.assertEqual([p["movieId"] for p in lista], ["47", "6", "50"])

    def test_6_propiedad_no_duplicacion_y_equivalencia_csv_json(self) -> None:
        """Comprueba que no se dupliquen opiniones y que CSV y JSON generen idéntica salida."""
        ruta_p_csv = localizar_archivo_datos("peliculas.csv")
        ruta_p_json = localizar_archivo_datos("peliculas.json")
        ruta_c_csv = localizar_archivo_datos("calificaciones.csv")
        ruta_c_json = localizar_archivo_datos("calificaciones.json")

        p_csv = FuenteCSV().cargar(ruta_p_csv)
        p_json = FuenteJSON().cargar(ruta_p_json)
        c_csv = crear_fuente("csv").cargar(ruta_c_csv)
        c_json = crear_fuente("json").cargar(ruta_c_json)

        cat_csv, rech_cat_csv = construir_catalogo(p_csv)
        rech_cal_csv = acumular_valoraciones(cat_csv, c_csv)
        # Segunda llamada para comprobar que re-acumular no duplica opiniones
        rech_cal_csv_2 = acumular_valoraciones(cat_csv, c_csv)
        self.assertEqual(len(rech_cal_csv), len(rech_cal_csv_2))

        total_opiniones_validas = sum(
            f["cantidad_valoraciones"] for f in cat_csv.values()
        )
        self.assertEqual(
            total_opiniones_validas + len(rech_cal_csv),
            len(c_csv),
            "La suma de opiniones válidas en el catálogo más las rechazadas debe igualar el total leído.",
        )

        cat_json, rech_cat_json = construir_catalogo(p_json)
        rech_cal_json = acumular_valoraciones(cat_json, c_json)

        consulta = ConsultaCatalogo(genero="Crime", anio=1995, min_valoraciones=3)
        with tempfile.TemporaryDirectory() as tmpdir:
            salida_csv = Path(tmpdir) / "out_csv.csv"
            salida_json = Path(tmpdir) / "out_json.csv"
            lista_csv = generar_lista(
                buscar_titulos(cat_csv, consulta),
                min_valoraciones=3,
                ruta_salida=salida_csv,
            )
            lista_json = generar_lista(
                buscar_titulos(cat_json, consulta),
                min_valoraciones=3,
                ruta_salida=salida_json,
            )
            self.assertEqual(lista_csv, lista_json)
            self.assertEqual(rech_cat_csv, rech_cat_json)
            self.assertEqual(rech_cal_csv, rech_cal_json)
            self.assertEqual(
                salida_csv.read_text(encoding="utf-8"),
                salida_json.read_text(encoding="utf-8"),
            )


    def test_7_una_sola_opinion_por_usuario_y_pelicula(self) -> None:
        """Si un usuario valora dos veces la misma película cuenta la más reciente."""
        peliculas = [
            {"movieId": "1", "title": "Toy Story (1995)", "genres": "Comedy"},
            {"movieId": "2", "title": "Heat (1995)", "genres": "Crime"},
        ]
        calificaciones = [
            {"userId": "1", "movieId": "1", "rating": "2.0", "timestamp": "100"},
            {"userId": "1", "movieId": "1", "rating": "5.0", "timestamp": "200"},  # más reciente
            {"userId": "2", "movieId": "1", "rating": "3.0", "timestamp": "150"},
            # Empate de timestamp: se conserva la que aparece más abajo en el archivo
            {"userId": "3", "movieId": "2", "rating": "1.0", "timestamp": "300"},
            {"userId": "3", "movieId": "2", "rating": "4.0", "timestamp": "300"},
        ]
        catalogo, _ = construir_catalogo(peliculas)
        rechazos = acumular_valoraciones(catalogo, calificaciones)

        self.assertEqual(catalogo["1"]["cantidad_valoraciones"], 2)
        self.assertAlmostEqual(catalogo["1"]["media_valoraciones"], 4.0)  # (5.0 + 3.0) / 2
        self.assertEqual(catalogo["2"]["cantidad_valoraciones"], 1)
        self.assertAlmostEqual(catalogo["2"]["media_valoraciones"], 4.0)
        self.assertEqual([r["fila"] for r in rechazos], [1, 4])
        for rechazo in rechazos:
            self.assertIn("duplicada", rechazo["motivo"])

    def test_8_validacion_de_escala_usuario_y_timestamp(self) -> None:
        """Rechaza ratings que no son múltiplo de 0.5, userId vacío y timestamps inválidos."""
        peliculas = [{"movieId": "1", "title": "Toy Story (1995)", "genres": "Comedy"}]
        calificaciones = [
            {"userId": "1", "movieId": "1", "rating": "4.0", "timestamp": "10"},    # válida
            {"userId": "2", "movieId": "1", "rating": "3.7", "timestamp": "11"},    # no múltiplo de 0.5
            {"userId": "",  "movieId": "1", "rating": "4.0", "timestamp": "12"},    # userId vacío
            {"userId": "4", "movieId": "1", "rating": "4.0", "timestamp": "abc"},   # timestamp no numérico
            {"userId": "5", "movieId": "1", "rating": "4.0", "timestamp": "-5"},    # timestamp negativo
            {"userId": "6", "movieId": "1", "rating": "nan", "timestamp": "14"},    # no es un número válido
            {"userId": "7", "movieId": "1", "rating": "",    "timestamp": "15"},    # valor faltante
        ]
        catalogo, _ = construir_catalogo(peliculas)
        rechazos = acumular_valoraciones(catalogo, calificaciones)

        self.assertEqual(catalogo["1"]["cantidad_valoraciones"], 1)
        self.assertEqual(len(rechazos), 6)
        motivos = [r["motivo"] for r in rechazos]
        self.assertIn("rating no es multiplo de 0.5", motivos)
        self.assertIn("userId vacio", motivos)
        self.assertEqual(motivos.count("timestamp invalido"), 2)

    def test_9_pelicula_sin_valoraciones_no_tiene_media_cero(self) -> None:
        """Una película sin opiniones queda con media None (no 0.0) y se exporta vacía."""
        peliculas = [
            {"movieId": "1", "title": "Toy Story (1995)", "genres": "Comedy"},
            {"movieId": "2", "title": "Heat (1995)", "genres": "Comedy"},
        ]
        calificaciones = [
            {"userId": "1", "movieId": "1", "rating": "4.0", "timestamp": "1"},
        ]
        catalogo, _ = construir_catalogo(peliculas)
        acumular_valoraciones(catalogo, calificaciones)

        self.assertEqual(catalogo["2"]["cantidad_valoraciones"], 0)
        self.assertIsNone(catalogo["2"]["media_valoraciones"])

        consulta = ConsultaCatalogo(min_valoraciones=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            salida = Path(tmpdir) / "lista.csv"
            lista = generar_lista(
                buscar_titulos(catalogo, consulta), min_valoraciones=0, ruta_salida=salida
            )
            self.assertEqual([p["movieId"] for p in lista], ["1", "2"])
            with salida.open(encoding="utf-8", newline="") as archivo:
                filas = list(csv.DictReader(archivo))
        self.assertEqual(filas[1]["media_valoraciones"], "")

        # Con el mínimo habitual (>= 1) la película sin opiniones no aparece.
        lista_min1 = generar_lista(buscar_titulos(catalogo, consulta), min_valoraciones=1)
        self.assertEqual([p["movieId"] for p in lista_min1], ["1"])

    def test_10_esquema_incompleto_en_cualquier_registro(self) -> None:
        """Un registro sin una columna obligatoria (no solo el primero) produce un error claro."""
        peliculas = [
            {"movieId": "1", "title": "Toy Story (1995)", "genres": "Comedy"},
            {"movieId": "2", "title": "Heat (1995)"},  # falta 'genres'
        ]
        with self.assertRaises(ValueError) as contexto:
            construir_catalogo(peliculas)
        self.assertIn("genres", str(contexto.exception))
        self.assertIn("registro 2", str(contexto.exception))

        catalogo, _ = construir_catalogo(
            [{"movieId": "1", "title": "Toy Story (1995)", "genres": "Comedy"}]
        )
        with self.assertRaises(ValueError):
            acumular_valoraciones(catalogo, [])  # tabla vacía

    def test_11_errores_de_lectura_no_se_ocultan_y_csv_json_equivalen(self) -> None:
        """Archivo inexistente, vacío o mal formado fallan con error explícito."""
        with tempfile.TemporaryDirectory() as tmpdir:
            carpeta = Path(tmpdir)

            with self.assertRaises(FileNotFoundError):
                FuenteCSV().cargar(carpeta / "no_existe.csv")

            vacio = carpeta / "vacio.csv"
            vacio.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                FuenteCSV().cargar(vacio)

            roto = carpeta / "roto.json"
            roto.write_text("{esto no es json", encoding="utf-8")
            with self.assertRaises(ValueError):
                FuenteJSON().cargar(roto)

            no_lista = carpeta / "objeto.json"
            no_lista.write_text('{"movieId": "1"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                FuenteJSON().cargar(no_lista)

            # Mismo contenido en ambos formatos (incluye una coma dentro de un título entre comillas)
            ruta_csv = carpeta / "mini.csv"
            ruta_csv.write_text(
                'movieId,title,genres\n11,"American President, The (1995)",Comedy|Drama\n',
                encoding="utf-8",
            )
            ruta_json = carpeta / "mini.json"
            ruta_json.write_text(
                json.dumps(
                    [{"movieId": 11, "title": "American President, The (1995)", "genres": "Comedy|Drama"}]
                ),
                encoding="utf-8",
            )
            self.assertEqual(FuenteCSV().cargar(ruta_csv), FuenteJSON().cargar(ruta_json))

        with self.assertRaises(ValueError):
            crear_fuente("xml")
        with self.assertRaises(ValueError):
            FuenteCSV(delimitador=";;")

    def test_12_ejecucion_por_consola_desde_cualquier_directorio(self) -> None:
        """La CLI funciona desde otro directorio y falla con código 1 ante parámetros inválidos."""
        main_py = RUTA_RAIZ / "src" / "main.py"
        entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        with tempfile.TemporaryDirectory() as tmpdir:
            salida = Path(tmpdir) / "lista.csv"
            rechazos = Path(tmpdir) / "rechazos.csv"
            ok = subprocess.run(
                [sys.executable, str(main_py), "--genero", "Crime",
                 "--ruta-salida", str(salida), "--ruta-rechazos", str(rechazos)],
                cwd=tmpdir, env=entorno, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertTrue(salida.exists())
            self.assertTrue(rechazos.exists())
            self.assertIn("Total seleccionadas", ok.stdout)

            error = subprocess.run(
                [sys.executable, str(main_py), "--anio", "1500",
                 "--ruta-salida", str(salida), "--ruta-rechazos", str(rechazos)],
                cwd=tmpdir, env=entorno, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(error.returncode, 1)
            self.assertIn("1888", error.stderr)


if __name__ == "__main__":
    unittest.main()