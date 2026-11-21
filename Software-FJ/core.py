# -*- coding: utf-8 -*-
"""
=============================================================================
 SOFTWARE FJ - SISTEMA INTEGRAL DE GESTIÓN DE CLIENTES, SERVICIOS Y RESERVAS
=============================================================================
Proyecto académico de Programación Orientada a Objetos (sin base de datos).

Principios aplicados:
  * Abstracción ....... Entidad y Servicio son clases abstractas (ABC).
  * Herencia .......... Cliente, Reserva y los servicios heredan de Entidad;
                        Sala, AlquilerEquipo y AsesoriaEspecializada heredan
                        de Servicio.
  * Polimorfismo ...... cada servicio sobrescribe calcular_costo() y describir();
                        Reserva trabaja con cualquier Servicio.
  * Encapsulación ..... atributos privados ("_") con propiedades validadas.
  * Sobrecarga ........ calcular_costo_flexible() usa singledispatchmethod y
                        calcular_con_impuesto() admite impuesto y descuento.
  * Excepciones ....... jerarquía propia, try/except, try/except/else,
                        try/except/else/finally y encadenamiento con "from".
  * Persistencia ...... solo archivo de logs (logs/sistema_fj.log); todos los
                        datos viven en objetos y listas en memoria.

Ejecución:
    python main.py            -> interfaz gráfica Tkinter
    python main.py --test     -> ejecuta la demostración de 18 operaciones en
                                 consola, sin abrir ventana.

Autor: ALEXANDER FLOREZ MONTIEL Y BRENDA ALVAREZ MANCHEGO- Software FJ.
=============================================================================
"""

from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from datetime import datetime
from functools import singledispatchmethod
from pathlib import Path
from typing import Any, Callable

# =============================================================================
# 1. CONFIGURACIÓN DEL ARCHIVO DE LOGS
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "sistema_fj.log"


def configurar_logger() -> logging.Logger:
    """Crea (una sola vez) el logger que escribe eventos y errores en disco."""
    logger = logging.getLogger("software_fj")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not logger.handlers:
        manejador = logging.FileHandler(LOG_FILE, encoding="utf-8")
        manejador.setLevel(logging.DEBUG)
        manejador.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(manejador)
    return logger


LOG = configurar_logger()


# =============================================================================
# 2. EXCEPCIONES PERSONALIZADAS
# =============================================================================
class ErrorSoftwareFJ(Exception):
    """Excepción base de todos los errores controlados por Software FJ."""

    def __init__(self, mensaje: str, detalle: str | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle = detalle

    def __str__(self) -> str:
        if self.detalle:
            return f"{self.mensaje} ({self.detalle})"
        return self.mensaje


class ParametrosFaltantesError(ErrorSoftwareFJ):
    """Se lanza cuando falta un dato obligatorio para una operación."""


class DatosInvalidosError(ErrorSoftwareFJ):
    """Se lanza cuando un dato no cumple el formato o el rango permitido."""


class OperacionNoPermitidaError(ErrorSoftwareFJ):
    """Se lanza al intentar una transición de estado no permitida."""


class ServicioNoDisponibleError(ErrorSoftwareFJ):
    """Se lanza cuando se intenta confirmar una reserva de un servicio ocupado."""


class ReservaInvalidaError(ErrorSoftwareFJ):
    """Se lanza cuando una reserva no cumple las reglas del negocio."""


class CalculoInconsistenteError(ErrorSoftwareFJ):
    """Se lanza cuando un cálculo produce valores imposibles o inválidos."""


class RecursoNoEncontradoError(ErrorSoftwareFJ):
    """Se lanza cuando no se localiza un cliente, servicio o reserva."""


# =============================================================================
# 3. FUNCIONES AUXILIARES DE VALIDACIÓN Y FORMATO
# =============================================================================
def formatear_dinero(valor: float | int | None) -> str:
    """Devuelve un monto con separadores de miles y dos decimales."""
    try:
        return f"${float(valor):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def texto_obligatorio(valor: Any, campo: str, minimo: int = 1, maximo: int = 120) -> str:
    """Valida que un dato de texto exista y tenga una longitud razonable."""
    if valor is None:
        raise ParametrosFaltantesError(f"El campo '{campo}' es obligatorio.")
    texto = str(valor).strip()
    if not texto:
        raise ParametrosFaltantesError(f"El campo '{campo}' es obligatorio.")
    if len(texto) < minimo:
        raise DatosInvalidosError(
            f"El campo '{campo}' debe tener al menos {minimo} caracteres."
        )
    if len(texto) > maximo:
        raise DatosInvalidosError(
            f"El campo '{campo}' no puede superar los {maximo} caracteres."
        )
    return texto


def convertir_entero(valor: Any, campo: str, minimo: int, maximo: int) -> int:
    """Convierte y valida un número entero dentro de un rango."""
    if valor is None or str(valor).strip() == "":
        raise ParametrosFaltantesError(f"El campo '{campo}' es obligatorio.")
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError) as exc:
        raise DatosInvalidosError(
            f"El campo '{campo}' debe ser un número entero (recibido: '{valor}')."
        ) from exc
    if not minimo <= numero <= maximo:
        raise DatosInvalidosError(
            f"El campo '{campo}' debe estar entre {minimo} y {maximo}."
        )
    return numero


def convertir_decimal(
    valor: Any, campo: str, minimo: float, maximo: float
) -> float:
    """Convierte y valida un número decimal, rechazando NaN e infinitos."""
    if valor is None or str(valor).strip() == "":
        raise ParametrosFaltantesError(f"El campo '{campo}' es obligatorio.")
    try:
        numero = float(str(valor).strip().replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise DatosInvalidosError(
            f"El campo '{campo}' debe ser numérico (recibido: '{valor}')."
        ) from exc
    if not math.isfinite(numero):
        raise DatosInvalidosError(f"El campo '{campo}' no admite valores infinitos.")
    if not minimo <= numero <= maximo:
        raise DatosInvalidosError(
            f"El campo '{campo}' debe estar entre {minimo} y {maximo}."
        )
    return round(numero, 2)


def convertir_booleano(valor: Any, campo: str) -> bool:
    """Normaliza textos como Sí/No, true/false, 1/0 a un booleano real."""
    if isinstance(valor, bool):
        return valor
    if valor is None:
        raise ParametrosFaltantesError(f"El campo '{campo}' es obligatorio.")
    texto = str(valor).strip().lower()
    if texto in {"sí", "si", "s", "true", "1", "yes"}:
        return True
    if texto in {"no", "n", "false", "0"}:
        return False
    raise DatosInvalidosError(
        f"El campo '{campo}' debe ser Sí/No (recibido: '{valor}')."
    )


# =============================================================================
# 4. CLASE ABSTRACTA ENTIDAD
# =============================================================================
class Entidad(ABC):
    """Clase abstracta raíz: todo objeto del sistema tiene código y se describe."""

    def __init__(self, codigo: str) -> None:
        self._codigo = self._validar_codigo(codigo)

    @staticmethod
    def _validar_codigo(codigo: Any) -> str:
        texto = texto_obligatorio(codigo, "código", minimo=3, maximo=20).upper()
        if not re.fullmatch(r"[A-Z]{2,6}-\d{3,6}", texto):
            raise DatosInvalidosError(
                f"El código '{texto}' no cumple el formato PREFIJO-NÚMERO (ej. CLI-0001)."
            )
        return texto

    @property
    def codigo(self) -> str:
        """Código único e inmutable de la entidad."""
        return self._codigo

    @abstractmethod
    def describir(self) -> str:
        """Devuelve una descripción legible de la entidad."""

    @abstractmethod
    def validar(self) -> bool:
        """Verifica la consistencia interna de la entidad."""

    def __str__(self) -> str:
        return self.describir()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(codigo={self._codigo!r})"


# =============================================================================
# 5. CLIENTE
# =============================================================================
class Cliente(Entidad):
    """
    Cliente de Software FJ. Todos sus datos personales están encapsulados y
    cada asignación pasa por un validador estricto.
    """

    TIPOS = ("Natural", "Empresa")

    def __init__(
        self,
        codigo: str,
        nombre: str,
        documento: str,
        correo: str,
        telefono: str,
        tipo: str = "Natural",
    ) -> None:
        super().__init__(codigo)
        self.nombre = nombre
        self._documento = self._validar_documento(documento)
        self.correo = correo
        self.telefono = telefono
        self.tipo = tipo
        self._activo = True
        self._fecha_registro = datetime.now()
        self.validar()

    # ------------------------- Propiedades validadas -------------------------
    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: Any) -> None:
        texto = texto_obligatorio(valor, "nombre", minimo=3, maximo=80)
        if not any(caracter.isalpha() for caracter in texto):
            raise DatosInvalidosError("El nombre debe contener al menos una letra.")
        if any(caracter in texto for caracter in "<>@#/\\"):
            raise DatosInvalidosError(
                "El nombre contiene caracteres no permitidos (< > @ # / \\)."
            )
        self._nombre = texto

    @property
    def documento(self) -> str:
        return self._documento

    @staticmethod
    def _validar_documento(valor: Any) -> str:
        texto = texto_obligatorio(valor, "documento").replace(" ", "")
        if not texto.isdigit():
            raise DatosInvalidosError(
                "El documento de identidad solo debe contener dígitos."
            )
        if not 6 <= len(texto) <= 15:
            raise DatosInvalidosError(
                "El documento debe tener entre 6 y 15 dígitos."
            )
        return texto

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor: Any) -> None:
        texto = texto_obligatorio(valor, "correo", maximo=100)
        patron = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
        if not re.fullmatch(patron, texto):
            raise DatosInvalidosError(
                f"El correo '{texto}' no tiene un formato válido (ej. nombre@dominio.com)."
            )
        self._correo = texto

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: Any) -> None:
        texto = texto_obligatorio(valor, "teléfono", maximo=25)
        if not re.fullmatch(r"[\d+()\-.\s]+", texto):
            raise DatosInvalidosError(
                "El teléfono solo admite dígitos, espacios, +, -, paréntesis y puntos."
            )
        if not 7 <= sum(caracter.isdigit() for caracter in texto) <= 15:
            raise DatosInvalidosError(
                "El teléfono debe contener entre 7 y 15 dígitos."
            )
        self._telefono = texto

    @property
    def tipo(self) -> str:
        return self._tipo

    @tipo.setter
    def tipo(self, valor: Any) -> None:
        texto = texto_obligatorio(valor, "tipo de cliente", maximo=20).capitalize()
        if texto not in self.TIPOS:
            raise DatosInvalidosError(
                f"Tipo de cliente inválido: '{texto}'. Use: {', '.join(self.TIPOS)}."
            )
        self._tipo = texto

    @property
    def activo(self) -> bool:
        return self._activo

    @property
    def fecha_registro(self) -> datetime:
        return self._fecha_registro

    # ----------------------------- Operaciones ------------------------------
    def cambiar_estado(self, activo: Any) -> None:
        """Activa o desactiva al cliente con validación del valor recibido."""
        self._activo = convertir_booleano(activo, "estado del cliente")
        estado = "activo" if self._activo else "inactivo"
        LOG.info("Cliente %s (%s) marcado como %s.", self._codigo, self._nombre, estado)

    def validar(self) -> bool:
        if not all((self._nombre, self._documento, self._correo, self._telefono)):
            raise DatosInvalidosError(
                f"El cliente {self._codigo} tiene datos obligatorios incompletos."
            )
        return True

    def describir(self) -> str:
        estado = "Activo" if self._activo else "Inactivo"
        return (
            f"Cliente {self._codigo} | {self._nombre} | {self._tipo} | "
            f"Doc. {self._documento} | {self._correo} | {self._telefono} | {estado}"
        )


# =============================================================================
# 6. CLASE ABSTRACTA SERVICIO
# =============================================================================
class Servicio(Entidad, ABC):
    """
    Contrato común de todos los servicios. Define el costo base, la
    disponibilidad y las validaciones compartidas; las subclases deciden
    cómo calcular el precio (polimorfismo).
    """

    TIPO = "Servicio"

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float | str,
        disponible: Any = True,
    ) -> None:
        super().__init__(codigo)
        self.nombre = nombre
        self.tarifa_base = tarifa_base
        self.disponible = disponible
        self._reservas_atendidas = 0

    # ------------------------- Propiedades validadas -------------------------
    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: Any) -> None:
        self._nombre = texto_obligatorio(valor, "nombre del servicio", minimo=3, maximo=80)

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @tarifa_base.setter
    def tarifa_base(self, valor: Any) -> None:
        if valor is None or str(valor).strip() == "":
            raise ParametrosFaltantesError("La tarifa base es obligatoria.")
        try:
            numero = float(str(valor).strip().replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise DatosInvalidosError(
                f"La tarifa base '{valor}' no es un número válido."
            ) from exc
        if not math.isfinite(numero):
            raise DatosInvalidosError("La tarifa base no admite valores infinitos.")
        if numero <= 0:
            raise DatosInvalidosError("La tarifa base debe ser mayor que cero.")
        if numero > 100_000_000:
            raise DatosInvalidosError("La tarifa base supera el máximo permitido.")
        self._tarifa_base = round(numero, 2)

    @property
    def disponible(self) -> bool:
        return self._disponible

    @disponible.setter
    def disponible(self, valor: Any) -> None:
        self._disponible = convertir_booleano(valor, "disponibilidad")

    @property
    def tipo_servicio(self) -> str:
        return self.TIPO

    @property
    def reservas_atendidas(self) -> int:
        return self._reservas_atendidas

    # ---------------------- Validaciones reutilizables -----------------------
    @staticmethod
    def validar_duracion(duracion: Any) -> float:
        """Valida la duración en horas y la devuelve redondeada a 2 decimales."""
        if duracion is None or str(duracion).strip() == "":
            raise ParametrosFaltantesError("La duración en horas es obligatoria.")
        try:
            horas = float(str(duracion).strip().replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise DatosInvalidosError(
                f"La duración '{duracion}' debe ser numérica."
            ) from exc
        if not math.isfinite(horas):
            raise DatosInvalidosError("La duración no admite valores infinitos.")
        if horas <= 0:
            raise ReservaInvalidaError("La duración debe ser mayor que cero horas.")
        if horas > 24:
            raise ReservaInvalidaError("Una reserva no puede superar las 24 horas.")
        return round(horas, 2)

    @staticmethod
    def validar_porcentaje(valor: Any, campo: str, maximo: float) -> float:
        """Valida un porcentaje (0..maximo) y lo devuelve como número."""
        if valor is None or str(valor).strip() == "":
            raise ParametrosFaltantesError(f"El campo '{campo}' es obligatorio.")
        try:
            numero = float(str(valor).strip().replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise DatosInvalidosError(
                f"El campo '{campo}' debe ser numérico (recibido: '{valor}')."
            ) from exc
        if not 0 <= numero <= maximo:
            raise DatosInvalidosError(
                f"El campo '{campo}' debe estar entre 0 y {maximo:g}."
            )
        return numero

    # ------------------------- Métodos abstractos ----------------------------
    @abstractmethod
    def calcular_costo(self, duracion_horas: float | str) -> float:
        """Calcula el costo del servicio para una duración dada."""

    # --------------------- Sobrecarga de calcular costo ----------------------
    def calcular_con_impuesto(
        self,
        duracion_horas: float | str,
        impuesto: float | str = 19.0,
        descuento: float | str = 0.0,
    ) -> float:
        """
        Variante 1 del cálculo: costo base + impuesto (%) - descuento (%).
        El descuento se aplica sobre el subtotal y luego se suma el impuesto.
        """
        horas = self.validar_duracion(duracion_horas)
        base = self.calcular_costo(horas)
        if base is None or not math.isfinite(base) or base <= 0:
            raise CalculoInconsistenteError(
                f"El servicio '{self.nombre}' generó un costo base inválido: {base!r}."
            )
        porcentaje_impuesto = self.validar_porcentaje(impuesto, "impuesto", 50)
        porcentaje_descuento = self.validar_porcentaje(descuento, "descuento", 60)
        subtotal = base * (1 - porcentaje_descuento / 100)
        total = subtotal * (1 + porcentaje_impuesto / 100)
        return round(total, 2)

    @singledispatchmethod
    def calcular_costo_flexible(
        self,
        parametro: Any,
        impuesto: float | str = 19.0,
        descuento: float | str = 0.0,
    ) -> float:
        """
        Variante sobrecargada: acepta horas como int, como float o una tupla
        (horas, descuento). El despacho lo resuelve functools.singledispatchmethod.
        """
        raise DatosInvalidosError(
            f"No existe variante de cálculo para '{type(parametro).__name__}'. "
            "Use horas (int/float) o una tupla (horas, descuento)."
        )

    @calcular_costo_flexible.register(int)
    def _flexible_entero(
        self, duracion: int, impuesto: float | str = 19.0, descuento: float | str = 0.0
    ) -> float:
        return self.calcular_con_impuesto(duracion, impuesto, descuento)

    @calcular_costo_flexible.register(float)
    def _flexible_decimal(
        self, duracion: float, impuesto: float | str = 19.0, descuento: float | str = 0.0
    ) -> float:
        return self.calcular_con_impuesto(duracion, impuesto, descuento)

    @calcular_costo_flexible.register(tuple)
    def _flexible_tupla(
        self,
        parametro: tuple,
        impuesto: float | str = 19.0,
        descuento: float | str | None = None,
    ) -> float:
        if len(parametro) != 2:
            raise DatosInvalidosError(
                "La tupla debe tener la forma (horas, descuento)."
            )
        horas, descuento_tupla = parametro
        return self.calcular_con_impuesto(
            horas, impuesto, descuento_tupla if descuento is None else descuento
        )

    def cambiar_disponibilidad(self, disponible: Any, motivo: str = "") -> None:
        """Cambia la disponibilidad y deja constancia en el log."""
        self.disponible = disponible
        estado = "disponible" if self._disponible else "no disponible"
        LOG.info(
            "Servicio %s (%s) marcado como %s. %s",
            self._codigo,
            self._nombre,
            estado,
            motivo.strip(),
        )

    def registrar_uso(self) -> None:
        self._reservas_atendidas += 1

    def validar(self) -> bool:
        if not self._nombre:
            raise DatosInvalidosError("El servicio no tiene nombre.")
        if self._tarifa_base <= 0:
            raise DatosInvalidosError("La tarifa base debe ser positiva.")
        return True


# =============================================================================
# 7. SERVICIOS ESPECIALIZADOS (HERENCIA Y POLIMORFISMO)
# =============================================================================
class Sala(Servicio):
    """Reserva de salas: cobra por hora y aplica recargos por capacidad y proyector."""

    TIPO = "Sala"

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float | str,
        capacidad: Any = 10,
        tiene_proyector: Any = False,
        disponible: Any = True,
    ) -> None:
        super().__init__(codigo, nombre, tarifa_base, disponible)
        self.capacidad = capacidad
        self.tiene_proyector = tiene_proyector
        self.validar()

    @property
    def capacidad(self) -> int:
        return self._capacidad

    @capacidad.setter
    def capacidad(self, valor: Any) -> None:
        self._capacidad = convertir_entero(valor, "capacidad de la sala", 1, 200)

    @property
    def tiene_proyector(self) -> bool:
        return self._tiene_proyector

    @tiene_proyector.setter
    def tiene_proyector(self, valor: Any) -> None:
        self._tiene_proyector = convertir_booleano(valor, "proyector")

    def calcular_costo(self, duracion_horas: float | str) -> float:
        horas = self.validar_duracion(duracion_horas)
        recargo = 0.0
        if self._capacidad > 20:
            recargo += 0.10  # salas grandes consumen más recursos
        if self._tiene_proyector:
            recargo += 0.08  # mantenimiento del equipo audiovisual
        return round(self._tarifa_base * horas * (1 + recargo), 2)

    def describir(self) -> str:
        proyector = "sí" if self._tiene_proyector else "no"
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"Sala '{self._nombre}' ({self._codigo}) | capacidad: {self._capacidad} "
            f"personas | proyector: {proyector} | tarifa: {formatear_dinero(self._tarifa_base)}/h "
            f"| {estado}"
        )


class AlquilerEquipo(Servicio):
    """Alquiler de equipos: cobra por hora y unidad, con descuento por jornada."""

    TIPO = "Equipo"

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float | str,
        tipo_equipo: str = "Computador portátil",
        unidades: Any = 1,
        requiere_tecnico: Any = False,
        disponible: Any = True,
    ) -> None:
        super().__init__(codigo, nombre, tarifa_base, disponible)
        self.tipo_equipo = tipo_equipo
        self.unidades = unidades
        self.requiere_tecnico = requiere_tecnico
        self.validar()

    @property
    def tipo_equipo(self) -> str:
        return self._tipo_equipo

    @tipo_equipo.setter
    def tipo_equipo(self, valor: Any) -> None:
        self._tipo_equipo = texto_obligatorio(
            valor, "tipo de equipo", minimo=3, maximo=60
        )

    @property
    def unidades(self) -> int:
        return self._unidades

    @unidades.setter
    def unidades(self, valor: Any) -> None:
        self._unidades = convertir_entero(valor, "unidades", 1, 50)

    @property
    def requiere_tecnico(self) -> bool:
        return self._requiere_tecnico

    @requiere_tecnico.setter
    def requiere_tecnico(self, valor: Any) -> None:
        self._requiere_tecnico = convertir_booleano(valor, "requiere técnico")

    def calcular_costo(self, duracion_horas: float | str) -> float:
        horas = self.validar_duracion(duracion_horas)
        total = self._tarifa_base * horas * self._unidades
        if horas >= 8:
            total *= 0.90  # descuento por jornada completa
        if self._requiere_tecnico:
            total += self._tarifa_base * 0.25 * horas  # acompañamiento técnico
        return round(total, 2)

    def describir(self) -> str:
        tecnico = "sí" if self._requiere_tecnico else "no"
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"Equipo '{self._nombre}' ({self._codigo}) | {self._tipo_equipo} | "
            f"{self._unidades} unidad(es) | técnico: {tecnico} | "
            f"tarifa: {formatear_dinero(self._tarifa_base)}/h por unidad | {estado}"
        )


class AsesoriaEspecializada(Servicio):
    """Asesorías: tarifa por hora según el nivel del especialista."""

    TIPO = "Asesoría"
    NIVELES = {"Básico": 1.0, "Intermedio": 1.3, "Avanzado": 1.6}

    def __init__(
        self,
        codigo: str,
        nombre: str,
        tarifa_base: float | str,
        area: str = "Tecnología",
        nivel: str = "Básico",
        asesor: str = "Por asignar",
        disponible: Any = True,
    ) -> None:
        super().__init__(codigo, nombre, tarifa_base, disponible)
        self.area = area
        self.nivel = nivel
        self.asesor = asesor
        self.validar()

    @property
    def area(self) -> str:
        return self._area

    @area.setter
    def area(self, valor: Any) -> None:
        self._area = texto_obligatorio(valor, "área de asesoría", minimo=3, maximo=60)

    @property
    def nivel(self) -> str:
        return self._nivel

    @nivel.setter
    def nivel(self, valor: Any) -> None:
        texto = texto_obligatorio(valor, "nivel", maximo=20).capitalize()
        if texto not in self.NIVELES:
            raise DatosInvalidosError(
                f"Nivel inválido: '{texto}'. Use: {', '.join(self.NIVELES)}."
            )
        self._nivel = texto

    @property
    def asesor(self) -> str:
        return self._asesor

    @asesor.setter
    def asesor(self, valor: Any) -> None:
        self._asesor = texto_obligatorio(valor, "asesor", minimo=3, maximo=80)

    def calcular_costo(self, duracion_horas: float | str) -> float:
        horas = self.validar_duracion(duracion_horas)
        if horas < 1:
            raise ReservaInvalidaError(
                "Una asesoría especializada requiere como mínimo 1 hora."
            )
        factor = self.NIVELES[self._nivel]
        return round(self._tarifa_base * horas * factor, 2)

    def describir(self) -> str:
        estado = "Disponible" if self._disponible else "No disponible"
        return (
            f"Asesoría '{self._nombre}' ({self._codigo}) | área: {self._area} | "
            f"nivel: {self._nivel} | asesor: {self._asesor} | "
            f"tarifa: {formatear_dinero(self._tarifa_base)}/h | {estado}"
        )


# =============================================================================
# 8. RESERVA
# =============================================================================
class Reserva(Entidad):
    """
    Integra un cliente, un servicio, una duración y un estado. Controla el
    ciclo PENDIENTE -> CONFIRMADA -> PROCESADA o CANCELADA con excepciones.
    """

    ESTADOS = ("PENDIENTE", "CONFIRMADA", "CANCELADA", "PROCESADA")
    _consecutivo = 0

    def __init__(
        self,
        cliente: Cliente,
        servicio: Servicio,
        duracion_horas: float | str,
        impuesto: float | str = 19.0,
        descuento: float | str = 0.0,
    ) -> None:
        Reserva._consecutivo += 1
        super().__init__(f"RES-{Reserva._consecutivo:04d}")
        if cliente is None:
            raise ParametrosFaltantesError("La reserva requiere un cliente.")
        if servicio is None:
            raise ParametrosFaltantesError("La reserva requiere un servicio.")
        if not isinstance(cliente, Cliente):
            raise DatosInvalidosError("El cliente debe ser una instancia de Cliente.")
        if not isinstance(servicio, Servicio):
            raise DatosInvalidosError("El servicio debe heredar de Servicio.")
        self._cliente = cliente
        self._servicio = servicio
        self._duracion_horas = Servicio.validar_duracion(duracion_horas)
        self._impuesto = Servicio.validar_porcentaje(impuesto, "impuesto", 50)
        self._descuento = Servicio.validar_porcentaje(descuento, "descuento", 60)
        self._estado = "PENDIENTE"
        self._costo_total: float | None = None
        self._motivo_cancelacion = ""
        self._fecha_creacion = datetime.now()
        self._historial: list[str] = [
            f"{self._fecha_creacion:%d/%m/%Y %H:%M} - Reserva creada en estado PENDIENTE."
        ]
        LOG.info(
            "Reserva %s creada: cliente=%s, servicio=%s, horas=%s.",
            self._codigo,
            self._cliente.codigo,
            self._servicio.codigo,
            self._duracion_horas,
        )

    # ------------------------------- Lectura --------------------------------
    @property
    def cliente(self) -> Cliente:
        return self._cliente

    @property
    def servicio(self) -> Servicio:
        return self._servicio

    @property
    def duracion_horas(self) -> float:
        return self._duracion_horas

    @property
    def impuesto(self) -> float:
        return self._impuesto

    @property
    def descuento(self) -> float:
        return self._descuento

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def costo_total(self) -> float | None:
        return self._costo_total

    @property
    def fecha_creacion(self) -> datetime:
        return self._fecha_creacion

    @property
    def historial(self) -> tuple[str, ...]:
        return tuple(self._historial)

    # ------------------------------ Utilidades ------------------------------
    def _registrar_evento(self, mensaje: str) -> None:
        self._historial.append(f"{datetime.now():%d/%m/%Y %H:%M} - {mensaje}")

    def calcular_costo(self) -> float:
        """Calcula el total usando el servicio concreto (polimorfismo) y encadena errores."""
        try:
            total = self._servicio.calcular_con_impuesto(
                self._duracion_horas, self._impuesto, self._descuento
            )
            if total is None or not math.isfinite(total):
                raise CalculoInconsistenteError(
                    f"El cálculo de la reserva {self._codigo} produjo un valor inválido."
                )
            if total <= 0:
                raise CalculoInconsistenteError(
                    f"El total calculado de la reserva {self._codigo} debe ser positivo."
                )
        except CalculoInconsistenteError:
            raise
        except ErrorSoftwareFJ as exc:
            raise CalculoInconsistenteError(
                f"No fue posible calcular el costo de la reserva {self._codigo}: {exc}"
            ) from exc
        except Exception as exc:  # salvaguarda ante errores inesperados
            raise CalculoInconsistenteError(
                f"Error inesperado al calcular la reserva {self._codigo}."
            ) from exc
        return total

    # --------------------------- Ciclo de vida -------------------------------
    def confirmar(self) -> float:
        """Confirma la reserva. Usa try/except/else/finally y registra todo."""
        LOG.info("Reserva %s | Intento de confirmación.", self._codigo)
        try:
            if self._estado != "PENDIENTE":
                raise OperacionNoPermitidaError(
                    f"La reserva {self._codigo} está {self._estado} y no puede confirmarse."
                )
            if not self._cliente.activo:
                raise OperacionNoPermitidaError(
                    f"El cliente '{self._cliente.nombre}' está inactivo."
                )
            if not self._servicio.disponible:
                raise ServicioNoDisponibleError(
                    f"El servicio '{self._servicio.nombre}' no está disponible."
                )
            total = self.calcular_costo()
        except ErrorSoftwareFJ as exc:
            LOG.error("Reserva %s | Confirmación fallida: %s", self._codigo, exc)
            self._registrar_evento(f"Confirmación fallida: {exc}")
            raise
        else:
            self._costo_total = total
            self._estado = "CONFIRMADA"
            self._registrar_evento(
                f"Reserva confirmada por {formatear_dinero(total)}."
            )
            LOG.info(
                "Reserva %s | Confirmada por %s.", self._codigo, formatear_dinero(total)
            )
            return total
        finally:
            LOG.debug(
                "Reserva %s | Confirmación finalizada. Estado actual: %s.",
                self._codigo,
                self._estado,
            )

    def cancelar(self, motivo: str = "") -> None:
        """Cancela una reserva no procesada."""
        LOG.info("Reserva %s | Intento de cancelación.", self._codigo)
        try:
            if self._estado == "PROCESADA":
                raise OperacionNoPermitidaError(
                    f"La reserva {self._codigo} ya fue procesada y no puede cancelarse."
                )
            if self._estado == "CANCELADA":
                raise OperacionNoPermitidaError(
                    f"La reserva {self._codigo} ya estaba cancelada."
                )
        except ErrorSoftwareFJ as exc:
            LOG.error("Reserva %s | Cancelación rechazada: %s", self._codigo, exc)
            raise
        else:
            estado_anterior = self._estado
            self._estado = "CANCELADA"
            self._costo_total = None
            self._motivo_cancelacion = motivo.strip() or "Sin motivo especificado"
            self._registrar_evento(
                f"Reserva cancelada (estado anterior: {estado_anterior}). "
                f"Motivo: {self._motivo_cancelacion}"
            )
            LOG.info(
                "Reserva %s | Cancelada. Motivo: %s",
                self._codigo,
                self._motivo_cancelacion,
            )
        finally:
            LOG.debug(
                "Reserva %s | Cancelación finalizada. Estado actual: %s.",
                self._codigo,
                self._estado,
            )

    def procesar(self) -> float:
        """Presta el servicio: solo reservas CONFIRMADAS pueden procesarse."""
        LOG.info("Reserva %s | Intento de procesamiento.", self._codigo)
        try:
            if self._estado != "CONFIRMADA":
                raise OperacionNoPermitidaError(
                    f"Solo se procesan reservas CONFIRMADAS (estado actual: {self._estado})."
                )
            if self._costo_total is None:
                raise CalculoInconsistenteError(
                    f"La reserva {self._codigo} no tiene costo calculado."
                )
        except ErrorSoftwareFJ as exc:
            LOG.error("Reserva %s | Procesamiento rechazado: %s", self._codigo, exc)
            raise
        else:
            self._estado = "PROCESADA"
            self._servicio.registrar_uso()
            self._registrar_evento(
                f"Servicio procesado. Cobro final: {formatear_dinero(self._costo_total)}."
            )
            LOG.info(
                "Reserva %s | Procesada. Cobro: %s",
                self._codigo,
                formatear_dinero(self._costo_total),
            )
            return self._costo_total
        finally:
            LOG.debug(
                "Reserva %s | Procesamiento finalizado. Estado actual: %s.",
                self._codigo,
                self._estado,
            )

    def validar(self) -> bool:
        if not isinstance(self._cliente, Cliente):
            raise DatosInvalidosError("La reserva no tiene un cliente válido.")
        if not isinstance(self._servicio, Servicio):
            raise DatosInvalidosError("La reserva no tiene un servicio válido.")
        if self._estado not in self.ESTADOS:
            raise DatosInvalidosError(f"Estado de reserva desconocido: {self._estado}.")
        return True

    def describir(self) -> str:
        total = (
            formatear_dinero(self._costo_total)
            if self._costo_total is not None
            else "por calcular"
        )
        return (
            f"Reserva {self._codigo} | {self._cliente.nombre} | {self._servicio.nombre} | "
            f"{self._duracion_horas:g} h | {self._estado} | Total: {total}"
        )


# =============================================================================
# 9. SISTEMA CENTRAL (COLECCIONES EN MEMORIA)
# =============================================================================
class SistemaFJ:
    """
    Fachada del sistema: administra clientes, servicios y reservas en listas
    internas, aplica reglas de negocio y centraliza el registro en el log.
    """

    def __init__(self) -> None:
        self._clientes: list[Cliente] = []
        self._servicios: list[Servicio] = []
        self._reservas: list[Reserva] = []
        self._demo_ejecutado = 0
        LOG.info("Sistema Software FJ inicializado.")

    # ------------------------------ Colecciones ------------------------------
    @property
    def clientes(self) -> list[Cliente]:
        return list(self._clientes)

    @property
    def servicios(self) -> list[Servicio]:
        return list(self._servicios)

    @property
    def reservas(self) -> list[Reserva]:
        return list(self._reservas)

    @staticmethod
    def _siguiente_codigo(prefijo: str, numero: int) -> str:
        return f"{prefijo}-{numero:04d}"

    def resumen(self) -> dict[str, float]:
        facturado = sum(
            reserva.costo_total or 0.0
            for reserva in self._reservas
            if reserva.estado == "PROCESADA"
        )
        return {
            "clientes": len(self._clientes),
            "servicios": len(self._servicios),
            "reservas": len(self._reservas),
            "facturado": round(facturado, 2),
        }

    # -------------------------------- Clientes -------------------------------
    def registrar_cliente(
        self,
        nombre: str,
        documento: str,
        correo: str,
        telefono: str,
        tipo: str = "Natural",
    ) -> Cliente:
        """Registra un cliente. Demuestra try/except/else/finally y encadenamiento."""
        documento_limpio = str(documento or "").strip().replace(" ", "")
        if documento_limpio and any(
            cliente.documento == documento_limpio for cliente in self._clientes
        ):
            error = OperacionNoPermitidaError(
                f"Ya existe un cliente con el documento {documento_limpio}."
            )
            LOG.error("Registro de cliente rechazado: %s", error)
            raise error

        codigo = self._siguiente_codigo("CLI", len(self._clientes) + 1)
        try:
            cliente = Cliente(codigo, nombre, documento, correo, telefono, tipo)
        except ErrorSoftwareFJ as exc:
            LOG.error("No se pudo registrar el cliente %s: %s", codigo, exc)
            raise
        except Exception as exc:
            LOG.exception("Error inesperado al registrar el cliente %s.", codigo)
            raise DatosInvalidosError(
                "Ocurrió un error inesperado al registrar el cliente."
            ) from exc
        else:
            self._clientes.append(cliente)
            LOG.info("Cliente registrado: %s (%s).", cliente.nombre, cliente.codigo)
            return cliente
        finally:
            LOG.debug(
                "Intento de registro del documento %s finalizado.",
                documento_limpio or "(vacío)",
            )

    def buscar_cliente(self, documento: str) -> Cliente:
        buscado = str(documento or "").strip().replace(" ", "")
        for cliente in self._clientes:
            if cliente.documento == buscado:
                return cliente
        raise RecursoNoEncontradoError(
            f"No existe un cliente con documento {buscado or '(vacío)'}."
        )

    # -------------------------------- Servicios ------------------------------
    def crear_servicio(
        self, tipo: str, nombre: str, tarifa_base: float | str, **parametros: Any
    ) -> Servicio:
        """Fábrica de servicios. Convierte un tipo de texto en la subclase correcta."""
        mapa: dict[str, type[Servicio]] = {
            "sala": Sala,
            "equipo": AlquilerEquipo,
            "asesoría": AsesoriaEspecializada,
            "asesoria": AsesoriaEspecializada,
        }
        clave = str(tipo or "").strip().lower()
        clase = mapa.get(clave)
        if clase is None:
            raise DatosInvalidosError(
                f"Tipo de servicio '{tipo}' no reconocido. Use: Sala, Equipo o Asesoría."
            )

        codigo = self._siguiente_codigo("SRV", len(self._servicios) + 1)
        try:
            servicio = clase(
                codigo=codigo,
                nombre=nombre,
                tarifa_base=tarifa_base,
                **parametros,
            )
        except TypeError as exc:
            raise DatosInvalidosError(
                f"Parámetros no válidos para el servicio {clave}: {exc}"
            ) from exc
        except ErrorSoftwareFJ as exc:
            LOG.error("No se pudo crear el servicio %s: %s", codigo, exc)
            raise
        else:
            self._servicios.append(servicio)
            LOG.info(
                "Servicio creado: %s (%s) - %s",
                servicio.nombre,
                servicio.codigo,
                servicio.tipo_servicio,
            )
            return servicio
        finally:
            LOG.debug("Intento de creación de servicio tipo '%s' finalizado.", tipo)

    def buscar_servicio(self, codigo: str) -> Servicio:
        buscado = str(codigo or "").strip().upper()
        for servicio in self._servicios:
            if servicio.codigo == buscado:
                return servicio
        raise RecursoNoEncontradoError(f"No existe el servicio {buscado or '(vacío)'}.")

    # -------------------------------- Reservas -------------------------------
    def crear_reserva(
        self,
        cliente: Cliente,
        servicio: Servicio,
        duracion_horas: float | str,
        impuesto: float | str = 19.0,
        descuento: float | str = 0.0,
    ) -> Reserva:
        if cliente is None or servicio is None:
            raise ParametrosFaltantesError(
                "Debe seleccionar un cliente y un servicio para reservar."
            )
        try:
            reserva = Reserva(cliente, servicio, duracion_horas, impuesto, descuento)
        except ErrorSoftwareFJ as exc:
            LOG.error("No se pudo crear la reserva: %s", exc)
            raise
        except Exception as exc:
            LOG.exception("Error inesperado al crear una reserva.")
            raise ReservaInvalidaError(
                "Ocurrió un error inesperado al crear la reserva."
            ) from exc
        else:
            self._reservas.append(reserva)
            LOG.info("Reserva registrada: %s.", reserva.codigo)
            return reserva
        finally:
            LOG.debug("Intento de creación de reserva finalizado.")

    def buscar_reserva(self, codigo: str) -> Reserva:
        buscado = str(codigo or "").strip().upper()
        for reserva in self._reservas:
            if reserva.codigo == buscado:
                return reserva
        raise RecursoNoEncontradoError(f"No existe la reserva {buscado or '(vacío)'}.")

    def confirmar_reserva(self, reserva: Reserva) -> float:
        try:
            total = reserva.confirmar()
        except ErrorSoftwareFJ as exc:
            LOG.error("Confirmación de %s rechazada: %s", reserva.codigo, exc)
            raise
        else:
            LOG.info("Confirmación de %s aceptada por %s.", reserva.codigo, formatear_dinero(total))
            return total
        finally:
            LOG.debug("Operación confirmar_reserva(%s) finalizada.", reserva.codigo)

    def procesar_reserva(self, reserva: Reserva) -> float:
        try:
            total = reserva.procesar()
        except ErrorSoftwareFJ as exc:
            LOG.error("Procesamiento de %s rechazado: %s", reserva.codigo, exc)
            raise
        else:
            LOG.info("Procesamiento de %s completado.", reserva.codigo)
            return total
        finally:
            LOG.debug("Operación procesar_reserva(%s) finalizada.", reserva.codigo)

    def cancelar_reserva(self, reserva: Reserva, motivo: str = "") -> None:
        try:
            reserva.cancelar(motivo)
        except ErrorSoftwareFJ as exc:
            LOG.error("Cancelación de %s rechazada: %s", reserva.codigo, exc)
            raise
        else:
            LOG.info("Cancelación de %s registrada.", reserva.codigo)
        finally:
            LOG.debug("Operación cancelar_reserva(%s) finalizada.", reserva.codigo)

    # ------------------------------ Demostración -----------------------------
    def ejecutar_demostracion(self) -> list[dict[str, Any]]:
        """
        Ejecuta 18 operaciones completas (válidas e inválidas) sin detener la
        aplicación. Devuelve un reporte con el resultado de cada operación.
        """
        self._demo_ejecutado += 1
        sufijo = f"{self._demo_ejecutado:02d}{datetime.now():%H%M%S}"
        resultados: list[dict[str, Any]] = []
        clientes: dict[str, Cliente] = {}
        servicios: dict[str, Servicio] = {}
        reservas: dict[str, Reserva] = {}
        LOG.info("DEMO | Inicio de la demostración #%d.", self._demo_ejecutado)

        def ejecutar(descripcion: str, accion: Callable[[], str]) -> None:
            """Aísla cada operación para que un error no detenga la demostración."""
            LOG.info("DEMO | Inicio: %s", descripcion)
            try:
                detalle = accion()
            except ErrorSoftwareFJ as exc:
                LOG.warning(
                    "DEMO | Error controlado en '%s': %s: %s",
                    descripcion,
                    type(exc).__name__,
                    exc,
                )
                resultados.append(
                    {
                        "operacion": descripcion,
                        "exito": False,
                        "detalle": f"{type(exc).__name__}: {exc}",
                    }
                )
            except Exception as exc:  # red de seguridad de último nivel
                LOG.exception("DEMO | Error inesperado en '%s'.", descripcion)
                resultados.append(
                    {
                        "operacion": descripcion,
                        "exito": False,
                        "detalle": f"Error inesperado: {exc}",
                    }
                )
            else:
                resultados.append(
                    {"operacion": descripcion, "exito": True, "detalle": detalle}
                )
            finally:
                LOG.info("DEMO | Fin: %s", descripcion)

        # 01 - Cliente válido -------------------------------------------------
        def op01() -> str:
            cliente = self.registrar_cliente(
                "Ana María Torres",
                f"10{sufijo}1",
                f"ana.{sufijo}@correo.com",
                "+57 300 123 4567",
                "Natural",
            )
            clientes["ana"] = cliente
            return f"Cliente {cliente.codigo} registrado: {cliente.describir()}"

        # 02 - Cliente con correo inválido ------------------------------------
        def op02() -> str:
            self.registrar_cliente(
                "Carlos Ruiz",
                f"20{sufijo}2",
                "correo-sin-arroba",
                "3105557788",
                "Natural",
            )
            return "No debería llegar aquí."

        # 03 - Cliente sin nombre ---------------------------------------------
        def op03() -> str:
            self.registrar_cliente(
                "   ", f"30{sufijo}3", f"sin.nombre.{sufijo}@correo.com", "3114445566"
            )
            return "No debería llegar aquí."

        # 04 - Documento duplicado --------------------------------------------
        def op04() -> str:
            self.registrar_cliente(
                "Otra Persona",
                clientes["ana"].documento,
                f"duplicado.{sufijo}@correo.com",
                "3127778899",
            )
            return "No debería llegar aquí."

        # 05 - Servicio Sala válido -------------------------------------------
        def op05() -> str:
            sala = self.crear_servicio(
                "Sala", "Sala Creativa", 45000, capacidad=25, tiene_proyector=True
            )
            servicios["sala"] = sala
            return f"Servicio creado: {sala.describir()}"

        # 06 - Servicio Equipo válido -----------------------------------------
        def op06() -> str:
            equipo = self.crear_servicio(
                "Equipo",
                "Portátiles Dell",
                12000,
                tipo_equipo="Computador portátil",
                unidades=5,
                requiere_tecnico=True,
            )
            servicios["equipo"] = equipo
            return f"Servicio creado: {equipo.describir()}"

        # 07 - Servicio Asesoría válido ---------------------------------------
        def op07() -> str:
            asesoria = self.crear_servicio(
                "Asesoría",
                "Asesoría en Python",
                80000,
                area="Programación",
                nivel="Avanzado",
                asesor="Ing. Laura Gómez",
            )
            servicios["asesoria"] = asesoria
            return f"Servicio creado: {asesoria.describir()}"

        # 08 - Tipo de servicio inexistente -----------------------------------
        def op08() -> str:
            self.crear_servicio("Dron", "Servicio fantasma", 1000)
            return "No debería llegar aquí."

        # 09 - Servicio con tarifa negativa -----------------------------------
        def op09() -> str:
            self.crear_servicio("Sala", "Sala Económica", -500, capacidad=5)
            return "No debería llegar aquí."

        # 10 - Reserva válida y confirmación ----------------------------------
        def op10() -> str:
            reserva = self.crear_reserva(
                clientes["ana"], servicios["sala"], 3, impuesto=19, descuento=5
            )
            total = self.confirmar_reserva(reserva)
            reservas["sala"] = reserva
            return (
                f"Reserva {reserva.codigo} confirmada para {reserva.cliente.nombre} "
                f"por {formatear_dinero(total)}."
            )

        # 11 - Reserva con duración negativa ----------------------------------
        def op11() -> str:
            self.crear_reserva(clientes["ana"], servicios["sala"], -2)
            return "No debería llegar aquí."

        # 12 - Reserva sobre servicio no disponible (finally restaura) --------
        def op12() -> str:
            equipo = servicios["equipo"]
            equipo.cambiar_disponibilidad(False, "Mantenimiento programado")
            try:
                reserva = self.crear_reserva(clientes["ana"], equipo, 4)
                reservas["no_disponible"] = reserva
                self.confirmar_reserva(reserva)
            finally:
                equipo.cambiar_disponibilidad(True, "Mantenimiento finalizado")
            return "No debería llegar aquí."

        # 13 - Asesoría de menos de una hora ----------------------------------
        def op13() -> str:
            reserva = self.crear_reserva(clientes["ana"], servicios["asesoria"], 0.5)
            self.confirmar_reserva(reserva)
            return "No debería llegar aquí."

        # 14 - Procesar la reserva confirmada ---------------------------------
        def op14() -> str:
            reserva = reservas["sala"]
            total = self.procesar_reserva(reserva)
            return (
                f"Reserva {reserva.codigo} procesada. Cobro final: "
                f"{formatear_dinero(total)}. Estado: {reserva.estado}."
            )

        # 15 - Cancelar una reserva ya procesada ------------------------------
        def op15() -> str:
            self.cancelar_reserva(reservas["sala"], "El cliente cambió de opinión")
            return "No debería llegar aquí."

        # 16 - Confirmar dos veces la misma reserva ---------------------------
        def op16() -> str:
            reserva = self.crear_reserva(
                clientes["ana"], servicios["equipo"], 2, impuesto=19
            )
            reservas["equipo"] = reserva
            self.confirmar_reserva(reserva)
            self.confirmar_reserva(reserva)  # la segunda debe fallar
            return "No debería llegar aquí."

        # 17 - Cancelar una reserva confirmada --------------------------------
        def op17() -> str:
            reserva = reservas["equipo"]
            self.cancelar_reserva(reserva, "El cliente reprogramó la actividad")
            return f"Reserva {reserva.codigo} cancelada. Estado: {reserva.estado}."

        # 18 - Búsqueda de un cliente inexistente -----------------------------
        def op18() -> str:
            self.buscar_cliente("999999999")
            return "No debería llegar aquí."

        operaciones: list[tuple[str, Callable[[], str]]] = [
            ("01. Registrar cliente válido (Ana María Torres)", op01),
            ("02. Registrar cliente con correo inválido", op02),
            ("03. Registrar cliente sin nombre (parámetros faltantes)", op03),
            ("04. Registrar cliente con documento duplicado", op04),
            ("05. Crear servicio de sala válido", op05),
            ("06. Crear servicio de alquiler de equipos válido", op06),
            ("07. Crear servicio de asesoría válido", op07),
            ("08. Crear servicio con tipo inexistente", op08),
            ("09. Crear servicio con tarifa negativa", op09),
            ("10. Crear y confirmar una reserva válida", op10),
            ("11. Crear reserva con duración negativa", op11),
            ("12. Confirmar reserva de un servicio no disponible", op12),
            ("13. Confirmar asesoría de menos de una hora", op13),
            ("14. Procesar la reserva confirmada", op14),
            ("15. Cancelar una reserva ya procesada", op15),
            ("16. Confirmar dos veces la misma reserva", op16),
            ("17. Cancelar una reserva confirmada", op17),
            ("18. Buscar un cliente inexistente", op18),
        ]
        for descripcion, accion in operaciones:
            ejecutar(descripcion, accion)

        LOG.info(
            "DEMO | Demostración finalizada: %d operaciones, %d exitosas.",
            len(resultados),
            sum(1 for resultado in resultados if resultado["exito"]),
        )
        return resultados

