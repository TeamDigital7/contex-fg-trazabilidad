"""Modelo de la trazabilidad: etapas, pedidos y la regla de cada etiqueta.

Sin Streamlit: todo lo que decide "en qué estado está un pedido" vive aquí, para
que el tablero, el detalle y las pruebas digan lo mismo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class Etapa:
    clave: str
    nombre: str
    referencia: str  # cláusula ISO o documento que deja la etapa
    descripcion: str


ETAPAS: tuple[Etapa, ...] = (
    Etapa("recibido", "Pedido recibido", "ISO 8.2.3",
          "Revisión de requisitos del cliente y compra de insumos."),
    Etapa("produccion", "Producción", "ISO 8.5",
          "Corte, confección, estampado o bordado, acabado y empaque."),
    Etapa("inspeccion", "Inspección final", "ISO 8.6 · 8.7",
          "Liberación del producto y control de salidas no conformes."),
    Etapa("despacho", "Despacho", "Guía · factura",
          "Emisión de guía de remisión, factura y entregas parciales."),
    Etapa("entregado", "Entregado", "ISO 9.1.2",
          "Pedido entregado y encuesta de satisfacción del cliente."),
)

ETAPAS_POR_CLAVE = {e.clave: e for e in ETAPAS}
ORDEN_ETAPA = {e.clave: i for i, e in enumerate(ETAPAS)}

# Sub-etapas de producción, en orden. El avance de producción (0 a 1) dice en cuál va.
SUBETAPAS_PRODUCCION: tuple[str, ...] = (
    "Corte",
    "Confección",
    "Estampado / bordado",
    "Acabado y empaque",
)

# Días hábiles que suele tomar producir un pedido completo. Sirve para proyectar
# si un pedido llega a tiempo; se puede ajustar en Secrets (`dias_produccion`).
DIAS_PRODUCCION_POR_DEFECTO = 15

# El tablero muestra lo entregado en los últimos N días: más atrás ya es historia.
DIAS_ENTREGADO_VISIBLE = 30

# Nombres con los que una base de datos puede escribir cada etapa.
ALIAS_ETAPA = {
    "recibido": "recibido", "pedido recibido": "recibido", "nuevo": "recibido",
    "revision": "recibido", "revisión": "recibido", "compras": "recibido",
    "produccion": "produccion", "producción": "produccion", "en produccion": "produccion",
    "en producción": "produccion", "confeccion": "produccion", "confección": "produccion",
    "inspeccion": "inspeccion", "inspección": "inspeccion", "inspeccion final": "inspeccion",
    "inspección final": "inspeccion", "calidad": "inspeccion",
    "despacho": "despacho", "en despacho": "despacho", "despachado": "despacho",
    "entregado": "entregado", "entregada": "entregado", "cerrado": "entregado",
}


def normalizar_etapa(valor: object) -> str:
    """Devuelve la clave de etapa o "" si no se reconoce."""
    texto = str(valor or "").strip().lower()
    return ALIAS_ETAPA.get(texto, "")


@dataclass
class Linea:
    producto: str
    cantidad: int
    precio_unitario: float | None = None  # opcional: con precio, la descarga es una proforma

    @property
    def importe(self) -> float | None:
        return None if self.precio_unitario is None else self.precio_unitario * self.cantidad


@dataclass
class Evento:
    fecha: datetime
    etapa: str
    clausula: str
    descripcion: str
    responsable: str = ""
    evidencia: str = ""


@dataclass
class Pedido:
    codigo: str
    cliente: str
    etapa: str
    fecha_pedido: date
    fecha_entrega: date
    lineas: list[Linea] = field(default_factory=list)
    avance_produccion: float = 0.0
    no_conformes: int = 0
    cantidad_despachada: int = 0
    liberado: bool = False
    encuesta: float | None = None
    fecha_entregado: date | None = None
    eventos: list[Evento] = field(default_factory=list)

    @property
    def cantidad_total(self) -> int:
        return sum(l.cantidad for l in self.lineas)

    @property
    def con_precios(self) -> bool:
        return bool(self.lineas) and all(l.precio_unitario is not None for l in self.lineas)

    @property
    def subtotal(self) -> float:
        return sum(l.importe or 0 for l in self.lineas)

    @property
    def productos(self) -> str:
        return " + ".join(l.producto for l in self.lineas)

    @property
    def resumen(self) -> str:
        """"Chaleco drill naranja + Pantalón jean · 250", como en la tarjeta."""
        return f"{self.productos} · {self.cantidad_total:,}".replace(",", ".")

    @property
    def subetapa(self) -> str:
        if self.etapa != "produccion":
            return ""
        indice = min(int(self.avance_produccion * len(SUBETAPAS_PRODUCCION)),
                     len(SUBETAPAS_PRODUCCION) - 1)
        return SUBETAPAS_PRODUCCION[indice]

    @property
    def entregado(self) -> bool:
        return self.etapa == "entregado"


# --- Reglas -------------------------------------------------------------------

TONOS = ("rojo", "ambar", "azul", "verde", "gris")


def en_riesgo(pedido: Pedido, hoy: date, dias_produccion: int = DIAS_PRODUCCION_POR_DEFECTO) -> bool:
    """Un pedido en producción está en riesgo si lo que le falta no entra antes de la entrega.

    Se proyecta con el avance: si va al 30 % y producir todo toma 15 días, le
    faltan ~10,5 días. Se reservan 2 días para inspección y despacho.
    """
    if pedido.etapa not in ("recibido", "produccion"):
        return False
    avance = pedido.avance_produccion if pedido.etapa == "produccion" else 0.0
    dias_faltantes = (1 - avance) * dias_produccion + 2
    return hoy + timedelta(days=dias_faltantes) > pedido.fecha_entrega


def atrasado(pedido: Pedido, hoy: date) -> bool:
    return not pedido.entregado and pedido.fecha_entrega < hoy


def etiqueta(pedido: Pedido, hoy: date,
             dias_produccion: int = DIAS_PRODUCCION_POR_DEFECTO) -> tuple[str, str]:
    """La etiqueta de la tarjeta: (texto, tono). Una sola regla para todas las vistas."""
    if atrasado(pedido, hoy):
        return "Atrasado", "rojo"
    if pedido.etapa == "recibido":
        if en_riesgo(pedido, hoy, dias_produccion):
            return "En riesgo", "rojo"
        return "Revisión", "gris"
    if pedido.etapa == "produccion":
        if en_riesgo(pedido, hoy, dias_produccion):
            return "En riesgo", "rojo"
        return pedido.subetapa, "gris"
    if pedido.etapa == "inspeccion":
        if pedido.no_conformes:
            return f"{pedido.no_conformes} no conforme(s)", "ambar"
        return "Conforme · por liberar", "verde"
    if pedido.etapa == "despacho":
        total = pedido.cantidad_total
        if 0 < pedido.cantidad_despachada < total:
            return f"Entrega {pedido.cantidad_despachada}/{total}", "azul"
        return "Liberado · emitir guía", "verde"
    if pedido.etapa == "entregado":
        if pedido.encuesta is not None:
            return f"Encuesta {pedido.encuesta:.1f} / 5", "verde"
        return "Encuesta pendiente", "gris"
    return "Sin etapa", "gris"


def avance_general(pedido: Pedido) -> float:
    """Avance del pedido completo, de 0 a 1, para la barra del detalle."""
    orden = ORDEN_ETAPA.get(pedido.etapa, 0)
    if pedido.etapa == "entregado":
        return 1.0
    base = orden / (len(ETAPAS) - 1)
    if pedido.etapa == "produccion":
        base += pedido.avance_produccion / (len(ETAPAS) - 1)
    if pedido.etapa == "despacho" and pedido.cantidad_total:
        base += (pedido.cantidad_despachada / pedido.cantidad_total) / (len(ETAPAS) - 1)
    return min(base, 1.0)


def visible_en_tablero(pedido: Pedido, hoy: date, dias_entregado: int | None = DIAS_ENTREGADO_VISIBLE) -> bool:
    """`dias_entregado=None` muestra también los entregados antiguos (el historial completo)."""
    if not pedido.entregado or dias_entregado is None:
        return True
    cuando = pedido.fecha_entregado or pedido.fecha_entrega
    return (hoy - cuando).days <= dias_entregado


def por_etapa(pedidos: list[Pedido], hoy: date,
              dias_entregado: int | None = DIAS_ENTREGADO_VISIBLE) -> dict[str, list[Pedido]]:
    """Los pedidos del tablero, agrupados por etapa y ordenados por fecha de entrega."""
    grupos: dict[str, list[Pedido]] = {e.clave: [] for e in ETAPAS}
    for p in pedidos:
        if p.etapa in grupos and visible_en_tablero(p, hoy, dias_entregado):
            grupos[p.etapa].append(p)
    for clave, lista in grupos.items():
        lista.sort(key=lambda p: (p.fecha_entregado or p.fecha_entrega),
                   reverse=(clave == "entregado"))
    return grupos


def indicadores(pedidos: list[Pedido], hoy: date,
                dias_produccion: int = DIAS_PRODUCCION_POR_DEFECTO) -> dict[str, object]:
    activos = [p for p in pedidos if not p.entregado]
    entregados = [p for p in pedidos if p.entregado]
    a_tiempo = [p for p in entregados
                if (p.fecha_entregado or p.fecha_entrega) <= p.fecha_entrega]
    encuestas = [p.encuesta for p in entregados if p.encuesta is not None]
    return {
        "activos": len(activos),
        "prendas_en_curso": sum(p.cantidad_total for p in activos),
        "en_riesgo": sum(1 for p in activos
                         if en_riesgo(p, hoy, dias_produccion) or atrasado(p, hoy)),
        "no_conformes": sum(p.no_conformes for p in activos if p.etapa == "inspeccion"),
        "a_tiempo": (len(a_tiempo) / len(entregados)) if entregados else None,
        "satisfaccion": (sum(encuestas) / len(encuestas)) if encuestas else None,
        "entregados": len(entregados),
    }
