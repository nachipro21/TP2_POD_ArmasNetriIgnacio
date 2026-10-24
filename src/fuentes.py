"""Módulo de lectura y abstracción de fuentes de datos (CSV y JSON).

Implementa el contrato común `FuenteDatos` y sus dos implementaciones concretas
(`FuenteCSV` y `FuenteJSON`), devolviendo siempre una representación tabular
homogénea (`list[dict[str, str]]`) para desacoplar la lógica del dominio del
formato físico de entrada.
"""

from abc import ABC, abstractmethod
import csv
import json
from pathlib import Path
from typing import Any


class FuenteDatos(ABC):
    """Clase base abstracta para lectores de fuentes de datos tabulares."""

    def validar_ruta(self, ruta: str | Path) -> Path:
        """Verifica que la ruta exista, sea un archivo regular y no esté vacía.

        Args:
            ruta: Ruta hacia el archivo de entrada.

        Returns:
            Objeto `Path` validado.

        Raises:
            FileNotFoundError: Si la ruta no existe o no es un archivo.
            ValueError: Si el archivo está vacío (0 bytes).
        """
        path_obj = Path(ruta)
        if not path_obj.exists():
            raise FileNotFoundError(f"No se encontró el archivo de datos: '{path_obj}'")
        if not path_obj.is_file():
            raise FileNotFoundError(f"La ruta indicada no es un archivo válido: '{path_obj}'")
        if path_obj.stat().st_size == 0:
            raise ValueError(f"El archivo de datos está vacío: '{path_obj}'")
        return path_obj

    @abstractmethod
    def cargar(self, ruta: str | Path) -> list[dict[str, str]]:
        """Carga los registros desde la ruta indicada y devuelve una lista de diccionarios.

        Cada fila se normaliza como un diccionario `dict[str, str]` con claves y
        valores limpios de espacios extremos, garantizando equivalencia exacta
        entre lecturas CSV y JSON.
        """
        raise NotImplementedError


class FuenteCSV(FuenteDatos):
    """Lector concreto para archivos tabulares en formato CSV (UTF-8)."""

    def __init__(self, delimitador: str = ",") -> None:
        if not delimitador or len(delimitador) != 1:
            raise ValueError("El delimitador CSV debe ser un único carácter.")
        self.delimitador = delimitador

    def cargar(self, ruta: str | Path) -> list[dict[str, str]]:
        """Lee un archivo CSV y devuelve sus filas como lista de diccionarios."""
        path_obj = self.validar_ruta(ruta)

        with path_obj.open(mode="r", encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo, delimiter=self.delimitador)
            if not lector.fieldnames:
                raise ValueError(
                    f"El archivo CSV '{path_obj}' no contiene fila de encabezados."
                )

            encabezados_limpios = [
                col.strip() for col in lector.fieldnames if col is not None and col.strip()
            ]
            if not encabezados_limpios:
                raise ValueError(
                    f"Los encabezados del archivo CSV '{path_obj}' son inválidos o vacíos."
                )

            registros: list[dict[str, str]] = []
            for num_fila, fila in enumerate(lector, start=2):
                if None in fila:
                    raise ValueError(
                        f"Fila {num_fila} en '{path_obj}' tiene más columnas que el encabezado."
                    )
                fila_normalizada: dict[str, str] = {}
                for clave, valor in fila.items():
                    if clave is None:
                        continue
                    texto_val = "" if valor is None else str(valor).strip()
                    fila_normalizada[clave.strip()] = texto_val
                registros.append(fila_normalizada)

        return registros


class FuenteJSON(FuenteDatos):
    """Lector concreto para archivos en formato JSON (lista de objetos)."""

    def cargar(self, ruta: str | Path) -> list[dict[str, str]]:
        """Lee un archivo JSON con una lista de objetos y lo adapta al esquema común."""
        path_obj = self.validar_ruta(ruta)

        try:
            with path_obj.open(mode="r", encoding="utf-8") as archivo:
                contenido: Any = json.load(archivo)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"El archivo JSON '{path_obj}' tiene un formato inválido: {exc}"
            ) from exc

        if not isinstance(contenido, list):
            raise ValueError(
                f"Se esperaba una lista de objetos en '{path_obj}', "
                f"pero se recibió '{type(contenido).__name__}'."
            )

        registros: list[dict[str, str]] = []
        for indice, item in enumerate(contenido, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"El elemento #{indice} en '{path_obj}' no es un objeto JSON válido (dict)."
                )
            fila_normalizada: dict[str, str] = {}
            for clave, valor in item.items():
                clave_limpia = str(clave).strip()
                texto_val = "" if valor is None else str(valor).strip()
                fila_normalizada[clave_limpia] = texto_val
            registros.append(fila_normalizada)

        return registros


def crear_fuente(formato: str) -> FuenteDatos:
    """Fábrica que devuelve la implementación de `FuenteDatos` según el formato solicitado.

    Args:
        formato: `'csv'` o `'json'` (insensible a mayúsculas/minúsculas).

    Returns:
        Instancia de `FuenteCSV` o `FuenteJSON`.

    Raises:
        ValueError: Si el formato no es soportado.
    """
    fmt = formato.strip().lower()
    if fmt == "csv":
        return FuenteCSV()
    if fmt == "json":
        return FuenteJSON()
    raise ValueError(f"Formato de fuente no soportado: '{formato}'. Use 'csv' o 'json'.")