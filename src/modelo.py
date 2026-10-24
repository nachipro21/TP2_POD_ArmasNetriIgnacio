"""Módulo del modelo de dominio para el catálogo de películas (TP2 - Tema 10).

Define la clase `ConsultaCatalogo`, que encapsula los criterios de búsqueda y
filtrado solicitados por quien utiliza el programa, validando sus supuestos
antes de aplicar la selección sobre el catálogo.
"""

from typing import Any


ANIO_MINIMO_CINE = 1888
ANIO_MAXIMO_CINE = 2030


class ConsultaCatalogo:
    """Representa y valida los filtros de búsqueda sobre el catálogo de películas.

    Atributos:
        texto_busqueda: Subcadena a buscar en el título limpio (opcional).
        genero: Género cinematográfico requerido (opcional).
        anio: Año de estreno exacto requerido (opcional).
        min_valoraciones: Cantidad mínima de opiniones válidas exigida (>= 0).
    """

    def __init__(
        self,
        texto_busqueda: str | None = None,
        genero: str | None = None,
        anio: int | None = None,
        min_valoraciones: int = 1,
    ) -> None:
        self.texto_busqueda = (
            texto_busqueda.strip() if texto_busqueda and texto_busqueda.strip() else None
        )
        self.genero = genero.strip() if genero and genero.strip() else None
        self.anio = anio
        self.min_valoraciones = min_valoraciones
        self.validar_parametros()

    def validar_parametros(self) -> None:
        """Comprueba que los parámetros de la consulta cumplan los supuestos del dominio.

        Raises:
            ValueError: Si `min_valoraciones` es negativo o si `anio` está fuera
                del rango histórico válido `[1888, 2030]`.
        """
        if not isinstance(self.min_valoraciones, int) or isinstance(self.min_valoraciones, bool):
            raise ValueError("El mínimo de valoraciones debe ser un número entero.")
        if self.min_valoraciones < 0:
            raise ValueError(
                f"El mínimo de valoraciones no puede ser negativo (recibido: {self.min_valoraciones})."
            )

        if self.anio is not None:
            if not isinstance(self.anio, int) or isinstance(self.anio, bool):
                raise ValueError("El año de filtro debe ser un número entero.")
            if not (ANIO_MINIMO_CINE <= self.anio <= ANIO_MAXIMO_CINE):
                raise ValueError(
                    f"El año de filtro ({self.anio}) debe estar entre "
                    f"{ANIO_MINIMO_CINE} y {ANIO_MAXIMO_CINE}."
                )

    def coincide_con_pelicula(self, pelicula: dict[str, Any]) -> bool:
        """Evalúa si un registro del catálogo cumple con los filtros de texto, género y año.

        Nota:
            El umbral `min_valoraciones` se aplica en `generar_lista()` tal como
            especifica el diseño del Tema 10, aunque este método verifica todos
            los criterios de búsqueda sobre los metadatos de la película.
        """
        if self.texto_busqueda is not None:
            titulo_limpio = str(pelicula.get("titulo_limpio", "")).lower()
            titulo_original = str(pelicula.get("title", "")).lower()
            busqueda = self.texto_busqueda.lower()
            if busqueda not in titulo_limpio and busqueda not in titulo_original:
                return False

        if self.genero is not None:
            generos_pelicula = [g.lower() for g in pelicula.get("generos", [])]
            if self.genero.lower() not in generos_pelicula:
                return False

        if self.anio is not None:
            anio_pelicula = pelicula.get("anio")
            if anio_pelicula is None or anio_pelicula != self.anio:
                return False

        return True

    def resumen_filtros(self) -> str:
        """Devuelve una descripción legible de los filtros configurados."""
        txt = f"'{self.texto_busqueda}'" if self.texto_busqueda else "Todos"
        gen = self.genero if self.genero else "Todos"
        anio_str = str(self.anio) if self.anio is not None else "Todos"
        return (
            f"texto={txt} | genero={gen} | anio={anio_str} | "
            f"min_valoraciones={self.min_valoraciones}"
        )