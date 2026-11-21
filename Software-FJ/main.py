# -*- coding: utf-8 -*-
"""
Punto de entrada de Software FJ.
Contiene la interfaz gráfica Tkinter y el modo de prueba en consola.
"""

from __future__ import annotations

import sys
from typing import Any

try:
    import tkinter as tk
    from tkinter import messagebox, ttk

    TKINTER_DISPONIBLE = True
except ImportError:  # pragma: no cover - entornos sin Tk
    tk = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    TKINTER_DISPONIBLE = False

from core import (
    AsesoriaEspecializada,
    Cliente,
    ErrorSoftwareFJ,
    LOG,
    LOG_FILE,
    OperacionNoPermitidaError,
    ParametrosFaltantesError,
    Reserva,
    Servicio,
    SistemaFJ,
    formatear_dinero,
)


# =============================================================================
# 10. INTERFAZ GRÁFICA (TKINTER)
# =============================================================================
class AplicacionSoftwareFJ:
    """Ventana principal: formularios, tablas, registro de eventos y demostración."""

    COLOR_FONDO = "#F1F5F9"
    COLOR_PRIMARIO = "#1E3A8A"
    COLOR_ACENTO = "#2563EB"
    COLOR_EXITO = "#047857"
    COLOR_PELIGRO = "#B91C1C"
    COLOR_TEXTO = "#1F2937"

    def __init__(self, root: Any) -> None:
        self.root = root
        self.sistema = SistemaFJ()
        self._clientes_por_etiqueta: dict[str, Cliente] = {}
        self._servicios_por_etiqueta: dict[str, Servicio] = {}
        self._campos_servicio: dict[str, list[tuple[Any, Any]]] = {
            "Sala": [],
            "Equipo": [],
            "Asesoría": [],
        }

        self._configurar_ventana()
        self._construir_encabezado()
        self._construir_barra_estado()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(8, 0))
        self._construir_pestana_clientes()
        self._construir_pestana_servicios()
        self._construir_pestana_reservas()
        self._construir_pestana_log()
        self._construir_pestana_demo()
        self._refrescar_todo()
        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)
        LOG.info("Interfaz gráfica iniciada.")

    # ------------------------------- Estilos ---------------------------------
    def _configurar_ventana(self) -> None:
        self.root.title("Software FJ - Clientes, Servicios y Reservas")
        self.root.geometry("1200x780")
        self.root.minsize(1020, 680)
        self.root.configure(bg=self.COLOR_FONDO)

        estilo = ttk.Style(self.root)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TFrame", background=self.COLOR_FONDO)
        estilo.configure(
            "Card.TFrame", background="#FFFFFF", relief="flat", borderwidth=1
        )
        estilo.configure("TLabel", background=self.COLOR_FONDO, font=("Segoe UI", 10))
        estilo.configure(
            "Card.TLabel", background="#FFFFFF", font=("Segoe UI", 10), foreground=self.COLOR_TEXTO
        )
        estilo.configure(
            "Titulo.TLabel",
            font=("Segoe UI", 13, "bold"),
            foreground=self.COLOR_PRIMARIO,
            background="#FFFFFF",
        )
        estilo.configure(
            "Subtitulo.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=self.COLOR_PRIMARIO,
            background="#FFFFFF",
        )
        estilo.configure(
            "Primario.TButton",
            font=("Segoe UI", 10, "bold"),
            background=self.COLOR_ACENTO,
            foreground="#FFFFFF",
            padding=(10, 6),
            borderwidth=0,
        )
        estilo.map("Primario.TButton", background=[("active", "#1D4ED8")])
        estilo.configure(
            "Exito.TButton",
            font=("Segoe UI", 10, "bold"),
            background=self.COLOR_EXITO,
            foreground="#FFFFFF",
            padding=(10, 6),
            borderwidth=0,
        )
        estilo.map("Exito.TButton", background=[("active", "#065F46")])
        estilo.configure(
            "Peligro.TButton",
            font=("Segoe UI", 10, "bold"),
            background=self.COLOR_PELIGRO,
            foreground="#FFFFFF",
            padding=(10, 6),
            borderwidth=0,
        )
        estilo.map("Peligro.TButton", background=[("active", "#991B1B")])
        estilo.configure(
            "Secundario.TButton",
            font=("Segoe UI", 10),
            background="#E2E8F0",
            foreground=self.COLOR_TEXTO,
            padding=(10, 6),
            borderwidth=0,
        )
        estilo.map("Secundario.TButton", background=[("active", "#CBD5E1")])
        estilo.configure(
            "TNotebook", background=self.COLOR_FONDO, borderwidth=0, tabmargins=(4, 4, 4, 0)
        )
        estilo.configure(
            "TNotebook.Tab",
            font=("Segoe UI", 10, "bold"),
            padding=(18, 7),
            background="#E2E8F0",
        )
        estilo.map(
            "TNotebook.Tab",
            background=[("selected", "#FFFFFF")],
            foreground=[("selected", self.COLOR_PRIMARIO)],
        )
        estilo.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=26,
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
        )
        estilo.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#E5E7EB",
            foreground=self.COLOR_TEXTO,
        )
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    def _construir_encabezado(self) -> None:
        encabezado = tk.Frame(self.root, bg=self.COLOR_PRIMARIO, height=64)
        encabezado.pack(fill="x", side="top")
        encabezado.pack_propagate(False)
        tk.Label(
            encabezado,
            text="Software FJ",
            bg=self.COLOR_PRIMARIO,
            fg="#FFFFFF",
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left", padx=(18, 12), pady=14)
        tk.Label(
            encabezado,
            text="Gestión de clientes, servicios y reservas",
            bg=self.COLOR_PRIMARIO,
            fg="#DBEAFE",
            font=("Segoe UI", 11),
        ).pack(side="left", pady=16)

    def _construir_barra_estado(self) -> None:
        self.lbl_estado = tk.Label(
            self.root,
            text="Iniciando sistema...",
            bg="#E2E8F0",
            fg=self.COLOR_TEXTO,
            anchor="w",
            font=("Segoe UI", 9),
            padx=12,
            pady=5,
        )
        self.lbl_estado.pack(fill="x", side="bottom")

    # ------------------------------- Utilidades ------------------------------
    def _notificar_error(self, exc: Exception, titulo: str = "Operación rechazada") -> None:
        LOG.error("Interfaz | %s: %s", titulo, exc)
        messagebox.showerror(titulo, str(exc))

    @staticmethod
    def _configurar_tabla(tabla: Any, definicion: list[tuple[str, str, int, str]]) -> None:
        for clave, titulo, ancho, anclaje in definicion:
            tabla.heading(clave, text=titulo)
            tabla.column(clave, width=ancho, anchor=anclaje, stretch=ancho >= 120)

    def _crear_treeview(
        self, padre: Any, definicion: list[tuple[str, str, int, str]], alto: int = 14
    ) -> Any:
        contenedor = ttk.Frame(padre, style="Card.TFrame")
        columnas = tuple(clave for clave, _, _, _ in definicion)
        tabla = ttk.Treeview(
            contenedor, columns=columnas, show="headings", height=alto, selectmode="browse"
        )
        self._configurar_tabla(tabla, definicion)
        barra_y = ttk.Scrollbar(contenedor, orient="vertical", command=tabla.yview)
        barra_x = ttk.Scrollbar(contenedor, orient="horizontal", command=tabla.xview)
        tabla.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        tabla.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        contenedor.rowconfigure(0, weight=1)
        contenedor.columnconfigure(0, weight=1)
        return contenedor, tabla

    @staticmethod
    def _limpiar_tabla(tabla: Any) -> None:
        for item in tabla.get_children():
            tabla.delete(item)

    # ------------------------------- Pestaña 1 -------------------------------
    def _construir_pestana_clientes(self) -> None:
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text="Clientes")

        formulario = ttk.Frame(marco, style="Card.TFrame", padding=18)
        formulario.pack(side="left", fill="y", padx=(0, 12))
        formulario.columnconfigure(1, weight=1)

        ttk.Label(formulario, text="Registrar cliente", style="Subtitulo.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self.var_cliente_nombre = tk.StringVar()
        self.var_cliente_documento = tk.StringVar()
        self.var_cliente_correo = tk.StringVar()
        self.var_cliente_telefono = tk.StringVar()
        self.var_cliente_tipo = tk.StringVar(value="Natural")

        campos = (
            ("Nombre completo", self.var_cliente_nombre),
            ("Documento", self.var_cliente_documento),
            ("Correo electrónico", self.var_cliente_correo),
            ("Teléfono", self.var_cliente_telefono),
        )
        for fila, (etiqueta, variable) in enumerate(campos, start=1):
            ttk.Label(formulario, text=etiqueta, style="Card.TLabel").grid(
                row=fila, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            ttk.Entry(formulario, textvariable=variable, width=30, font=("Segoe UI", 10)).grid(
                row=fila, column=1, sticky="ew", pady=5
            )

        ttk.Label(formulario, text="Tipo de cliente", style="Card.TLabel").grid(
            row=5, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        ttk.Combobox(
            formulario,
            textvariable=self.var_cliente_tipo,
            values=Cliente.TIPOS,
            state="readonly",
            width=28,
            font=("Segoe UI", 10),
        ).grid(row=5, column=1, sticky="ew", pady=5)

        ttk.Button(
            formulario,
            text="Registrar cliente",
            style="Primario.TButton",
            command=self._registrar_cliente,
        ).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(16, 6))

        ttk.Label(
            formulario,
            text="Los datos se validan antes de crear el objeto.\nCada intento queda registrado en el log.",
            style="Card.TLabel",
            font=("Segoe UI", 8, "italic"),
            foreground="#64748B",
            justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))

        panel = ttk.Frame(marco, style="Card.TFrame", padding=18)
        panel.pack(side="left", fill="both", expand=True)
        ttk.Label(panel, text="Clientes registrados", style="Subtitulo.TLabel").pack(
            anchor="w", pady=(0, 10)
        )
        contenedor, self.tabla_clientes = self._crear_treeview(
            panel,
            [
                ("codigo", "Código", 80, "center"),
                ("nombre", "Nombre", 160, "w"),
                ("documento", "Documento", 100, "center"),
                ("correo", "Correo", 190, "w"),
                ("telefono", "Teléfono", 120, "center"),
                ("tipo", "Tipo", 80, "center"),
                ("estado", "Estado", 75, "center"),
            ],
        )
        contenedor.pack(fill="both", expand=True)

    # ------------------------------- Pestaña 2 -------------------------------
    def _construir_pestana_servicios(self) -> None:
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text="Servicios")

        formulario = ttk.Frame(marco, style="Card.TFrame", padding=18)
        formulario.pack(side="left", fill="y", padx=(0, 12))
        formulario.columnconfigure(1, weight=1)

        ttk.Label(formulario, text="Crear servicio", style="Subtitulo.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )
        self.var_servicio_tipo = tk.StringVar(value="Sala")
        self.var_servicio_nombre = tk.StringVar()
        self.var_servicio_tarifa = tk.StringVar(value="45000")

        ttk.Label(formulario, text="Tipo de servicio", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        combo_tipo = ttk.Combobox(
            formulario,
            textvariable=self.var_servicio_tipo,
            values=("Sala", "Equipo", "Asesoría"),
            state="readonly",
            width=28,
            font=("Segoe UI", 10),
        )
        combo_tipo.grid(row=1, column=1, sticky="ew", pady=5)
        combo_tipo.bind("<<ComboboxSelected>>", self._al_cambiar_tipo_servicio)

        for fila, (etiqueta, variable) in enumerate(
            (("Nombre del servicio", self.var_servicio_nombre), ("Tarifa base ($/hora)", self.var_servicio_tarifa)),
            start=2,
        ):
            ttk.Label(formulario, text=etiqueta, style="Card.TLabel").grid(
                row=fila, column=0, sticky="w", pady=5, padx=(0, 10)
            )
            ttk.Entry(formulario, textvariable=variable, width=30, font=("Segoe UI", 10)).grid(
                row=fila, column=1, sticky="ew", pady=5
            )

        ttk.Label(
            formulario, text="Parámetros específicos", style="Subtitulo.TLabel"
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 6))

        self.marco_extras = ttk.Frame(formulario, style="Card.TFrame")
        self.marco_extras.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.marco_extras.columnconfigure(1, weight=1)

        self.var_sala_capacidad = tk.StringVar(value="20")
        self.var_sala_proyector = tk.StringVar(value="No")
        self.var_equipo_tipo = tk.StringVar(value="Computador portátil")
        self.var_equipo_unidades = tk.StringVar(value="1")
        self.var_equipo_tecnico = tk.StringVar(value="No")
        self.var_asesoria_area = tk.StringVar(value="Programación")
        self.var_asesoria_nivel = tk.StringVar(value="Intermedio")
        self.var_asesoria_asesor = tk.StringVar(value="Por asignar")

        fila_extra = 0

        def agregar_campo(
            etiqueta: str, widget: Any, tipos: tuple[str, ...]
        ) -> None:
            nonlocal fila_extra
            etiqueta_widget = ttk.Label(
                self.marco_extras, text=etiqueta, style="Card.TLabel"
            )
            etiqueta_widget.grid(row=fila_extra, column=0, sticky="w", pady=4, padx=(0, 10))
            widget.grid(row=fila_extra, column=1, sticky="ew", pady=4)
            fila_extra += 1
            for tipo in tipos:
                self._campos_servicio[tipo].append((etiqueta_widget, widget))

        agregar_campo(
            "Capacidad (personas)",
            ttk.Entry(self.marco_extras, textvariable=self.var_sala_capacidad, width=28),
            ("Sala",),
        )
        agregar_campo(
            "¿Tiene proyector?",
            ttk.Combobox(
                self.marco_extras,
                textvariable=self.var_sala_proyector,
                values=("Sí", "No"),
                state="readonly",
                width=26,
            ),
            ("Sala",),
        )
        agregar_campo(
            "Tipo de equipo",
            ttk.Entry(self.marco_extras, textvariable=self.var_equipo_tipo, width=28),
            ("Equipo",),
        )
        agregar_campo(
            "Unidades",
            ttk.Entry(self.marco_extras, textvariable=self.var_equipo_unidades, width=28),
            ("Equipo",),
        )
        agregar_campo(
            "¿Requiere técnico?",
            ttk.Combobox(
                self.marco_extras,
                textvariable=self.var_equipo_tecnico,
                values=("Sí", "No"),
                state="readonly",
                width=26,
            ),
            ("Equipo",),
        )
        agregar_campo(
            "Área de asesoría",
            ttk.Entry(self.marco_extras, textvariable=self.var_asesoria_area, width=28),
            ("Asesoría",),
        )
        agregar_campo(
            "Nivel",
            ttk.Combobox(
                self.marco_extras,
                textvariable=self.var_asesoria_nivel,
                values=tuple(AsesoriaEspecializada.NIVELES),
                state="readonly",
                width=26,
            ),
            ("Asesoría",),
        )
        agregar_campo(
            "Asesor asignado",
            ttk.Entry(self.marco_extras, textvariable=self.var_asesoria_asesor, width=28),
            ("Asesoría",),
        )
        self._al_cambiar_tipo_servicio()

        ttk.Button(
            formulario,
            text="Crear servicio",
            style="Primario.TButton",
            command=self._crear_servicio,
        ).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(16, 6))

        panel = ttk.Frame(marco, style="Card.TFrame", padding=18)
        panel.pack(side="left", fill="both", expand=True)
        ttk.Label(panel, text="Catálogo de servicios", style="Subtitulo.TLabel").pack(
            anchor="w", pady=(0, 10)
        )
        contenedor, self.tabla_servicios = self._crear_treeview(
            panel,
            [
                ("codigo", "Código", 80, "center"),
                ("tipo", "Tipo", 80, "center"),
                ("nombre", "Nombre", 140, "w"),
                ("tarifa", "Tarifa/h", 95, "e"),
                ("disponible", "Disponible", 80, "center"),
                ("detalle", "Descripción", 330, "w"),
            ],
        )
        contenedor.pack(fill="both", expand=True, pady=(0, 8))
        acciones = ttk.Frame(panel)
        acciones.pack(fill="x")
        ttk.Button(
            acciones,
            text="Cambiar disponibilidad",
            style="Secundario.TButton",
            command=self._cambiar_disponibilidad_servicio,
        ).pack(side="left")
        ttk.Label(
            acciones,
            text="Seleccione un servicio de la tabla para habilitarlo o deshabilitarlo.",
            style="Card.TLabel",
            font=("Segoe UI", 8, "italic"),
            foreground="#64748B",
        ).pack(side="left", padx=12)

    def _al_cambiar_tipo_servicio(self, evento: Any = None) -> None:
        tipo = self.var_servicio_tipo.get()
        for lista in self._campos_servicio.values():
            for etiqueta, widget in lista:
                etiqueta.grid_remove()
                widget.grid_remove()
        for etiqueta, widget in self._campos_servicio.get(tipo, []):
            etiqueta.grid()
            widget.grid()

    # ----------------------- Acciones de clientes ----------------------------
    def _registrar_cliente(self) -> None:
        try:
            cliente = self.sistema.registrar_cliente(
                self.var_cliente_nombre.get(),
                self.var_cliente_documento.get(),
                self.var_cliente_correo.get(),
                self.var_cliente_telefono.get(),
                self.var_cliente_tipo.get(),
            )
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Cliente no registrado")
        else:
            messagebox.showinfo("Cliente registrado", cliente.describir())
            self.var_cliente_nombre.set("")
            self.var_cliente_documento.set("")
            self.var_cliente_correo.set("")
            self.var_cliente_telefono.set("")
            self.var_cliente_tipo.set("Natural")
            self._refrescar_clientes()
            self._refrescar_combos()
            self._refrescar_estado()
        finally:
            LOG.debug("Interfaz | Registro de cliente finalizado.")

    # ----------------------- Acciones de servicios ---------------------------
    def _crear_servicio(self) -> None:
        tipo = self.var_servicio_tipo.get()
        try:
            if tipo == "Sala":
                parametros = {
                    "capacidad": self.var_sala_capacidad.get(),
                    "tiene_proyector": self.var_sala_proyector.get(),
                }
            elif tipo == "Equipo":
                parametros = {
                    "tipo_equipo": self.var_equipo_tipo.get(),
                    "unidades": self.var_equipo_unidades.get(),
                    "requiere_tecnico": self.var_equipo_tecnico.get(),
                }
            else:
                parametros = {
                    "area": self.var_asesoria_area.get(),
                    "nivel": self.var_asesoria_nivel.get(),
                    "asesor": self.var_asesoria_asesor.get(),
                }
            servicio = self.sistema.crear_servicio(
                tipo,
                self.var_servicio_nombre.get(),
                self.var_servicio_tarifa.get(),
                **parametros,
            )
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Servicio no creado")
        else:
            messagebox.showinfo("Servicio creado", servicio.describir())
            self.var_servicio_nombre.set("")
            self._refrescar_servicios()
            self._refrescar_combos()
            self._refrescar_estado()
        finally:
            LOG.debug("Interfaz | Creación de servicio finalizada.")

    def _cambiar_disponibilidad_servicio(self) -> None:
        seleccion = self.tabla_servicios.selection()
        try:
            if not seleccion:
                raise OperacionNoPermitidaError(
                    "Seleccione un servicio de la tabla para cambiar su disponibilidad."
                )
            servicio = self.sistema.buscar_servicio(seleccion[0])
            servicio.cambiar_disponibilidad(
                not servicio.disponible, "Cambio manual desde la interfaz"
            )
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Disponibilidad no modificada")
        else:
            estado = "disponible" if servicio.disponible else "no disponible"
            messagebox.showinfo(
                "Disponibilidad actualizada", f"{servicio.nombre} ahora está {estado}."
            )
            self._refrescar_servicios()
            self._refrescar_combos()
        finally:
            LOG.debug("Interfaz | Cambio de disponibilidad finalizado.")

    # ------------------------------- Pestaña 3 -------------------------------
    def _construir_pestana_reservas(self) -> None:
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text="Reservas")

        formulario = ttk.Frame(marco, style="Card.TFrame", padding=18)
        formulario.pack(fill="x", pady=(0, 10))
        for columna in range(6):
            formulario.columnconfigure(columna, weight=1 if columna < 2 else 0)

        ttk.Label(formulario, text="Nueva reserva", style="Subtitulo.TLabel").grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 10)
        )

        self.var_cliente_reserva = tk.StringVar()
        self.var_servicio_reserva = tk.StringVar()
        self.var_duracion_reserva = tk.StringVar(value="2")
        self.var_impuesto_reserva = tk.StringVar(value="19")
        self.var_descuento_reserva = tk.StringVar(value="0")

        ttk.Label(formulario, text="Cliente", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8)
        )
        self.combo_cliente_reserva = ttk.Combobox(
            formulario,
            textvariable=self.var_cliente_reserva,
            state="readonly",
            width=34,
            font=("Segoe UI", 9),
        )
        self.combo_cliente_reserva.grid(row=2, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(formulario, text="Servicio", style="Card.TLabel").grid(
            row=1, column=1, sticky="w", padx=(0, 8)
        )
        self.combo_servicio_reserva = ttk.Combobox(
            formulario,
            textvariable=self.var_servicio_reserva,
            state="readonly",
            width=34,
            font=("Segoe UI", 9),
        )
        self.combo_servicio_reserva.grid(row=2, column=1, sticky="ew", padx=(0, 8))

        for columna, (etiqueta, variable, ancho) in enumerate(
            (
                ("Duración (h)", self.var_duracion_reserva, 8),
                ("Impuesto (%)", self.var_impuesto_reserva, 8),
                ("Descuento (%)", self.var_descuento_reserva, 8),
            ),
            start=2,
        ):
            ttk.Label(formulario, text=etiqueta, style="Card.TLabel").grid(
                row=1, column=columna, sticky="w", padx=(0, 8)
            )
            ttk.Entry(
                formulario,
                textvariable=variable,
                width=ancho,
                font=("Segoe UI", 10),
                justify="center",
            ).grid(row=2, column=columna, sticky="ew", padx=(0, 8))

        ttk.Button(
            formulario,
            text="Crear reserva",
            style="Primario.TButton",
            command=self._crear_reserva,
        ).grid(row=2, column=5, sticky="ew", padx=(6, 0))

        panel = ttk.Frame(marco, style="Card.TFrame", padding=18)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Reservas registradas", style="Subtitulo.TLabel").pack(
            anchor="w", pady=(0, 10)
        )
        contenedor, self.tabla_reservas = self._crear_treeview(
            panel,
            [
                ("codigo", "Código", 85, "center"),
                ("cliente", "Cliente", 170, "w"),
                ("servicio", "Servicio", 170, "w"),
                ("horas", "Horas", 65, "center"),
                ("estado", "Estado", 105, "center"),
                ("total", "Costo total", 120, "e"),
            ],
            alto=12,
        )
        contenedor.pack(fill="both", expand=True, pady=(0, 8))
        self.tabla_reservas.bind("<<TreeviewSelect>>", self._al_seleccionar_reserva)

        acciones = ttk.Frame(panel)
        acciones.pack(fill="x")
        ttk.Button(
            acciones,
            text="Confirmar seleccionada",
            style="Exito.TButton",
            command=self._confirmar_reserva,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            acciones,
            text="Procesar seleccionada",
            style="Primario.TButton",
            command=self._procesar_reserva,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            acciones,
            text="Cancelar seleccionada",
            style="Peligro.TButton",
            command=self._cancelar_reserva,
        ).pack(side="left")
        self.lbl_detalle_reserva = ttk.Label(
            panel,
            text="Seleccione una reserva para ver su detalle.",
            style="Card.TLabel",
            font=("Segoe UI", 9, "italic"),
            foreground="#475569",
        )
        self.lbl_detalle_reserva.pack(anchor="w", pady=(10, 0))

    # ----------------------- Acciones de reservas ----------------------------
    def _crear_reserva(self) -> None:
        try:
            cliente = self._clientes_por_etiqueta.get(self.var_cliente_reserva.get())
            servicio = self._servicios_por_etiqueta.get(self.var_servicio_reserva.get())
            if cliente is None:
                raise ParametrosFaltantesError("Seleccione un cliente registrado.")
            if servicio is None:
                raise ParametrosFaltantesError("Seleccione un servicio del catálogo.")
            reserva = self.sistema.crear_reserva(
                cliente,
                servicio,
                self.var_duracion_reserva.get(),
                self.var_impuesto_reserva.get(),
                self.var_descuento_reserva.get(),
            )
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Reserva no creada")
        else:
            messagebox.showinfo(
                "Reserva creada",
                f"{reserva.codigo} registrada en estado {reserva.estado}.\n"
                "Confírmela cuando el cliente acepte las condiciones.",
            )
            self._refrescar_reservas()
            self._refrescar_estado()
        finally:
            LOG.debug("Interfaz | Creación de reserva finalizada.")

    def _reserva_seleccionada(self) -> Reserva:
        seleccion = self.tabla_reservas.selection()
        if not seleccion:
            raise OperacionNoPermitidaError("Seleccione una reserva de la tabla.")
        return self.sistema.buscar_reserva(seleccion[0])

    def _al_seleccionar_reserva(self, evento: Any = None) -> None:
        try:
            reserva = self._reserva_seleccionada()
        except ErrorSoftwareFJ:
            self.lbl_detalle_reserva.configure(
                text="Seleccione una reserva para ver su detalle."
            )
            return
        self.lbl_detalle_reserva.configure(
            text=(
                f"{reserva.describir()} | Impuesto: {reserva.impuesto:g}% | "
                f"Descuento: {reserva.descuento:g}%"
            )
        )

    def _confirmar_reserva(self) -> None:
        try:
            reserva = self._reserva_seleccionada()
            total = self.sistema.confirmar_reserva(reserva)
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Confirmación rechazada")
        else:
            messagebox.showinfo(
                "Reserva confirmada",
                f"{reserva.codigo} confirmada por {formatear_dinero(total)}.",
            )
        finally:
            self._refrescar_reservas()
            self._refrescar_estado()

    def _procesar_reserva(self) -> None:
        try:
            reserva = self._reserva_seleccionada()
            total = self.sistema.procesar_reserva(reserva)
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Procesamiento rechazado")
        else:
            messagebox.showinfo(
                "Reserva procesada",
                f"{reserva.codigo} procesada. Cobro final: {formatear_dinero(total)}.",
            )
        finally:
            self._refrescar_reservas()
            self._refrescar_estado()

    def _cancelar_reserva(self) -> None:
        try:
            reserva = self._reserva_seleccionada()
            if not messagebox.askyesno(
                "Cancelar reserva",
                f"¿Confirma la cancelación de la reserva {reserva.codigo}?",
            ):
                return
            self.sistema.cancelar_reserva(
                reserva, "Cancelación solicitada desde la interfaz"
            )
        except ErrorSoftwareFJ as exc:
            self._notificar_error(exc, "Cancelación rechazada")
        else:
            messagebox.showinfo(
                "Reserva cancelada", f"{reserva.codigo} quedó en estado CANCELADA."
            )
        finally:
            self._refrescar_reservas()
            self._refrescar_estado()

    # ------------------------------- Pestaña 4 -------------------------------
    def _construir_pestana_log(self) -> None:
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text="Registro de eventos")

        barra = ttk.Frame(marco)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Label(
            barra, text=f"Archivo de logs: {LOG_FILE}", font=("Segoe UI", 9)
        ).pack(side="left")
        ttk.Button(
            barra, text="Actualizar", style="Secundario.TButton", command=self._refrescar_log
        ).pack(side="right")

        contenedor = ttk.Frame(marco, style="Card.TFrame")
        contenedor.pack(fill="both", expand=True)
        self.texto_log = tk.Text(
            contenedor,
            wrap="none",
            font=("Consolas", 9),
            bg="#0F172A",
            fg="#E2E8F0",
            insertbackground="#FFFFFF",
            padx=10,
            pady=10,
            state="disabled",
        )
        barra_y = ttk.Scrollbar(contenedor, orient="vertical", command=self.texto_log.yview)
        barra_x = ttk.Scrollbar(contenedor, orient="horizontal", command=self.texto_log.xview)
        self.texto_log.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        self.texto_log.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        contenedor.rowconfigure(0, weight=1)
        contenedor.columnconfigure(0, weight=1)

    # ------------------------------- Pestaña 5 -------------------------------
    def _construir_pestana_demo(self) -> None:
        marco = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(marco, text="Demostración")

        tarjeta = ttk.Frame(marco, style="Card.TFrame", padding=18)
        tarjeta.pack(fill="x")
        ttk.Label(
            tarjeta, text="Demostración automática de operaciones", style="Subtitulo.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            tarjeta,
            text=(
                "Ejecuta 18 operaciones completas con registros válidos e inválidos de "
                "clientes, creación correcta e incorrecta de servicios y reservas exitosas "
                "y fallidas. Cada error se captura, se registra en el log y el sistema "
                "continúa funcionando."
            ),
            style="Card.TLabel",
            wraplength=1050,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))
        ttk.Button(
            tarjeta,
            text="Ejecutar demostración (18 operaciones)",
            style="Primario.TButton",
            command=self._ejecutar_demostracion,
        ).pack(anchor="w")

        contenedor = ttk.Frame(marco, style="Card.TFrame")
        contenedor.pack(fill="both", expand=True, pady=(10, 0))
        self.texto_demo = tk.Text(
            contenedor,
            wrap="word",
            font=("Consolas", 9),
            bg="#F8FAFC",
            fg=self.COLOR_TEXTO,
            padx=10,
            pady=10,
        )
        barra = ttk.Scrollbar(contenedor, orient="vertical", command=self.texto_demo.yview)
        self.texto_demo.configure(yscrollcommand=barra.set)
        self.texto_demo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.texto_demo.insert(
            "1.0",
            "Presione el botón para ejecutar la demostración.\n"
            "Los resultados aparecerán aquí y en la pestaña 'Registro de eventos'.",
        )

    def _ejecutar_demostracion(self) -> None:
        try:
            resultados = self.sistema.ejecutar_demostracion()
        except Exception as exc:
            LOG.exception("Interfaz | Fallo inesperado durante la demostración.")
            self._notificar_error(exc, "Demostración interrumpida")
            return
        else:
            self.texto_demo.delete("1.0", tk.END)
            for numero, resultado in enumerate(resultados, start=1):
                estado = "OK" if resultado["exito"] else "ERROR CONTROLADO"
                self.texto_demo.insert(
                    tk.END,
                    f"{numero:02d}. [{estado}] {resultado['operacion']}\n"
                    f"    {resultado['detalle']}\n\n",
                )
            exitos = sum(1 for resultado in resultados if resultado["exito"])
            self.texto_demo.insert(
                tk.END,
                f"Resumen: {exitos} operaciones exitosas y "
                f"{len(resultados) - exitos} errores controlados.\n",
            )
            self.texto_demo.see("1.0")
            self._refrescar_todo()
        finally:
            LOG.info("Interfaz | Demostración finalizada.")

    # ----------------------------- Refrescar vistas --------------------------
    def _refrescar_clientes(self) -> None:
        self._limpiar_tabla(self.tabla_clientes)
        for cliente in self.sistema.clientes:
            self.tabla_clientes.insert(
                "",
                "end",
                iid=cliente.codigo,
                values=(
                    cliente.codigo,
                    cliente.nombre,
                    cliente.documento,
                    cliente.correo,
                    cliente.telefono,
                    cliente.tipo,
                    "Activo" if cliente.activo else "Inactivo",
                ),
            )

    def _refrescar_servicios(self) -> None:
        self._limpiar_tabla(self.tabla_servicios)
        for servicio in self.sistema.servicios:
            self.tabla_servicios.insert(
                "",
                "end",
                iid=servicio.codigo,
                values=(
                    servicio.codigo,
                    servicio.tipo_servicio,
                    servicio.nombre,
                    formatear_dinero(servicio.tarifa_base),
                    "Sí" if servicio.disponible else "No",
                    servicio.describir(),
                ),
            )

    def _refrescar_reservas(self) -> None:
        self._limpiar_tabla(self.tabla_reservas)
        for reserva in self.sistema.reservas:
            total = (
                formatear_dinero(reserva.costo_total)
                if reserva.costo_total is not None
                else "Por calcular"
            )
            self.tabla_reservas.insert(
                "",
                "end",
                iid=reserva.codigo,
                values=(
                    reserva.codigo,
                    reserva.cliente.nombre,
                    reserva.servicio.nombre,
                    f"{reserva.duracion_horas:g}",
                    reserva.estado,
                    total,
                ),
            )
        self.lbl_detalle_reserva.configure(
            text="Seleccione una reserva para ver su detalle."
        )

    def _refrescar_combos(self) -> None:
        seleccion_cliente = self.var_cliente_reserva.get()
        seleccion_servicio = self.var_servicio_reserva.get()

        self._clientes_por_etiqueta = {
            f"{cliente.codigo} · {cliente.nombre}": cliente
            for cliente in self.sistema.clientes
        }
        valores_clientes = list(self._clientes_por_etiqueta)
        self.combo_cliente_reserva["values"] = valores_clientes
        if seleccion_cliente in valores_clientes:
            self.var_cliente_reserva.set(seleccion_cliente)
        elif valores_clientes:
            self.var_cliente_reserva.set(valores_clientes[0])
        else:
            self.var_cliente_reserva.set("")

        self._servicios_por_etiqueta = {
            f"{servicio.codigo} · {servicio.nombre} ({servicio.tipo_servicio})": servicio
            for servicio in self.sistema.servicios
            if servicio.disponible
        }
        valores_servicios = list(self._servicios_por_etiqueta)
        self.combo_servicio_reserva["values"] = valores_servicios
        if seleccion_servicio in valores_servicios:
            self.var_servicio_reserva.set(seleccion_servicio)
        elif valores_servicios:
            self.var_servicio_reserva.set(valores_servicios[0])
        else:
            self.var_servicio_reserva.set("")

    def _refrescar_log(self) -> None:
        contenido = ""
        try:
            if LOG_FILE.exists():
                lineas = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
                contenido = "\n".join(lineas[-500:])
        except OSError as exc:
            contenido = f"No fue posible leer el archivo de logs: {exc}"
            LOG.error("Interfaz | %s", contenido)
        self.texto_log.configure(state="normal")
        self.texto_log.delete("1.0", tk.END)
        self.texto_log.insert(
            tk.END, contenido or "(Aún no hay eventos registrados en el archivo)."
        )
        self.texto_log.see(tk.END)
        self.texto_log.configure(state="disabled")

    def _refrescar_estado(self) -> None:
        resumen = self.sistema.resumen()
        self.lbl_estado.configure(
            text=(
                f"Clientes: {resumen['clientes']}   |   Servicios: {resumen['servicios']}   |   "
                f"Reservas: {resumen['reservas']}   |   Facturado: "
                f"{formatear_dinero(resumen['facturado'])}      ·      Log: {LOG_FILE}"
            )
        )

    def _refrescar_todo(self) -> None:
        self._refrescar_clientes()
        self._refrescar_servicios()
        self._refrescar_reservas()
        self._refrescar_combos()
        self._refrescar_log()
        self._refrescar_estado()

    def _cerrar(self) -> None:
        LOG.info("Interfaz gráfica cerrada por el usuario.")
        self.root.destroy()


# =============================================================================
# 11. MODO DE PRUEBA EN CONSOLA Y PUNTO DE ENTRADA
# =============================================================================
def ejecutar_modo_prueba() -> None:
    """Ejecuta la demostración sin abrir la ventana (útil para sustentar)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 78)
    print("SOFTWARE FJ - DEMOSTRACIÓN DE 18 OPERACIONES (SIN BASE DE DATOS)")
    print("=" * 78)
    sistema = SistemaFJ()
    resultados = sistema.ejecutar_demostracion()
    for numero, resultado in enumerate(resultados, start=1):
        etiqueta = "OK" if resultado["exito"] else "ERROR CONTROLADO"
        print(f"{numero:02d}. [{etiqueta}] {resultado['operacion']}")
        print(f"    {resultado['detalle']}")
    exitos = sum(1 for resultado in resultados if resultado["exito"])
    print("-" * 78)
    print(
        f"Total: {len(resultados)} | Exitosas: {exitos} | "
        f"Errores controlados: {len(resultados) - exitos}"
    )
    resumen = sistema.resumen()
    print(
        f"Clientes: {resumen['clientes']} | Servicios: {resumen['servicios']} | "
        f"Reservas: {resumen['reservas']} | Facturado: {formatear_dinero(resumen['facturado'])}"
    )
    print(f"Archivo de logs: {LOG_FILE}")
    print("=" * 78)


def main() -> None:
    """Punto de entrada: GUI por defecto, demostración con --test."""
    if "--test" in sys.argv:
        ejecutar_modo_prueba()
        return

    if not TKINTER_DISPONIBLE:
        mensaje = (
            "No se pudo importar tkinter. Instale el soporte de Tk para Python "
            "o ejecute 'python main.py --test' para ver la demostración en consola."
        )
        LOG.error(mensaje)
        print(mensaje)
        return

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        LOG.error("No se pudo iniciar la interfaz gráfica: %s", exc)
        print(f"No se pudo iniciar la interfaz gráfica: {exc}")
        return

    AplicacionSoftwareFJ(root)
    root.mainloop()


if __name__ == "__main__":
    main()
