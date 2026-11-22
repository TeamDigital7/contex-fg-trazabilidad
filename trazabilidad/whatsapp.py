"""Envío del avance del pedido por WhatsApp: mensaje + PDF + Excel, con un clic.

Va por la **WhatsApp Business Cloud API de Meta**, que es la vía oficial para
mandar archivos sin que nadie toque el teléfono. Dos reglas de WhatsApp que
deciden cómo está armado esto:

1. **Un mensaje que inicia la empresa tiene que ser una PLANTILLA aprobada por
   Meta.** Texto libre solo se permite dentro de las 24 h después de que el
   cliente escribió. Por eso el mensaje principal es la plantilla
   `avance_pedido`, con el PDF como cabecera y los datos del pedido como
   variables. Las variables no admiten saltos de línea: `_variable()` las limpia.
2. **Una plantilla lleva UN solo documento.** El Excel va después como un
   documento suelto, y WhatsApp solo lo entrega si el cliente escribió en las
   últimas 24 h. Si no, Meta responde el error 131047: eso es un AVISO, no un
   fallo (el mensaje y el PDF ya llegaron), y se dice tal cual.

Sin `[whatsapp]` en Secrets no se envía nada: `enlace_wa_me` abre WhatsApp con
el mensaje escrito (sin archivos, porque un enlace no puede adjuntarlos).
"""

from __future__ import annotations

import json
import re
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date

from trazabilidad.modelo import ETAPAS_POR_CLAVE, Pedido, avance_general, etiqueta

VERSION_API = "v21.0"
CODIGO_FUERA_DE_VENTANA = 131047  # el cliente no escribió en 24 h: solo plantillas
MIME_PDF = "application/pdf"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Texto de la plantilla que hay que dar de alta en Meta (categoría "Utilidad").
PLANTILLA_SUGERIDA = (
    "Hola {{1}}, le saluda Contex FYG. Le compartimos el avance de su pedido {{2}}: "
    "se encuentra en la etapa {{3}} con un avance de {{4}}. Entrega comprometida: {{5}}. "
    "{{6}} Adjuntamos el detalle en PDF. Quedamos atentos a cualquier consulta."
)

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


# --- Teléfono ------------------------------------------------------------------

def normalizar_telefono(numero: str, pais: str = "51") -> str:
    """Devuelve solo dígitos con código de país (WhatsApp lo pide así), o "".

    "987 654 321" -> "51987654321" · "+51 987-654-321" -> "51987654321".
    Un celular peruano son 9 dígitos que empiezan por 9.
    """
    digitos = re.sub(r"\D", "", str(numero or ""))
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) == 9 and digitos.startswith("9") and pais == "51":
        digitos = pais + digitos
    return digitos if 10 <= len(digitos) <= 15 else ""


# --- El speech -----------------------------------------------------------------

def _fecha(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]}"


def frase_de_estado(p: Pedido, hoy: date, dias_produccion: int = 15) -> str:
    """Una frase honesta según el estado: lo que el cliente necesita saber."""
    texto, tono = etiqueta(p, hoy, dias_produccion)
    if texto == "Atrasado":
        return "Le pedimos disculpas: el pedido está fuera de la fecha comprometida y lo estamos priorizando."
    if tono == "rojo":
        return "Estamos priorizando su pedido en planta para cumplir la fecha de entrega."
    if p.etapa == "produccion":
        return f"Actualmente estamos en {p.subetapa.lower()}."
    if p.etapa == "inspeccion" and p.no_conformes:
        return (f"Calidad separó {p.no_conformes} observación(es) que ya están en reproceso "
                "antes de liberar el lote.")
    if p.etapa == "inspeccion":
        return "El lote pasó la inspección de calidad y está por liberarse."
    if p.etapa == "despacho" and 0 < p.cantidad_despachada < p.cantidad_total:
        return f"Ya entregamos {p.cantidad_despachada} de {p.cantidad_total} prendas."
    if p.etapa == "despacho":
        return "El pedido está liberado y listo para despacho."
    if p.etapa == "entregado" and p.encuesta is None:
        return "Le agradeceremos responder la encuesta de satisfacción."
    if p.etapa == "entregado":
        return "Gracias por responder la encuesta de satisfacción."
    return "Estamos revisando los requisitos y gestionando los insumos."


def saludo(p: Pedido) -> str:
    return p.contacto or p.cliente.replace(" (demo)", "")


def variables_de_plantilla(p: Pedido, hoy: date, dias_produccion: int = 15) -> list[str]:
    etapa = ETAPAS_POR_CLAVE[p.etapa].nombre
    return [_variable(v) for v in (
        saludo(p), p.codigo, etapa, f"{avance_general(p):.0%}", _fecha(p.fecha_entrega),
        frase_de_estado(p, hoy, dias_produccion),
    )]


def mensaje_de_avance(p: Pedido, hoy: date, dias_produccion: int = 15) -> str:
    """El speech completo, para el enlace wa.me y para la vista previa."""
    etapa = ETAPAS_POR_CLAVE[p.etapa]
    linea_etapa = f"{etapa.nombre} ({etapa.referencia})"
    if p.subetapa:
        linea_etapa += f" · {p.subetapa}"
    return "\n".join([
        f"Hola {saludo(p)}, le saluda *Contex FYG* 👋",
        "",
        f"Le compartimos el avance de su pedido *{p.codigo}*:",
        f"• Productos: {p.resumen} prendas",
        f"• Etapa actual: {linea_etapa}",
        f"• Avance general: {avance_general(p):.0%}",
        f"• Entrega comprometida: {_fecha(p.fecha_entrega)}",
        "",
        frase_de_estado(p, hoy, dias_produccion),
        "",
        "Le adjuntamos el estado del pedido en PDF y el detalle en Excel. "
        "Quedamos atentos a cualquier consulta.",
    ])


def mensaje_de_resumen(cliente: str, pedidos: list[Pedido], hoy: date, dias_produccion: int = 15) -> str:
    activos = [p for p in pedidos if not p.entregado]
    lineas = [f"Hola {cliente}, le saluda *Contex FYG* 👋", "",
              f"Le compartimos el avance de sus {len(activos)} pedido(s) en curso:"]
    for p in sorted(activos, key=lambda x: x.fecha_entrega):
        lineas.append(f"• *{p.codigo}* · {ETAPAS_POR_CLAVE[p.etapa].nombre} · "
                      f"{avance_general(p):.0%} · entrega {_fecha(p.fecha_entrega)}")
    lineas += ["", "Le adjuntamos el resumen en PDF y el detalle en Excel. Quedamos atentos."]
    return "\n".join(lineas)


def _variable(texto: str) -> str:
    """WhatsApp rechaza variables con saltos de línea, tabuladores o 4+ espacios seguidos."""
    limpio = re.sub(r"[\n\r\t]+", " ", str(texto))
    limpio = re.sub(r" {4,}", "   ", limpio).strip()
    return limpio[:1000] or "-"


def enlace_wa_me(telefono: str, texto: str) -> str:
    """Abre WhatsApp con el mensaje escrito. Sin número, deja elegir el contacto."""
    base = f"https://wa.me/{telefono}" if telefono else "https://wa.me/"
    return f"{base}?text={urllib.parse.quote(texto)}"


# --- Cliente de la Cloud API -----------------------------------------------------

class ErrorWhatsApp(Exception):
    def __init__(self, mensaje: str, codigo: int | None = None):
        super().__init__(mensaje)
        self.codigo = codigo


@dataclass
class Documento:
    contenido: bytes
    nombre: str
    mime: str


@dataclass
class Paso:
    nombre: str
    estado: str  # "ok" | "aviso" | "error"
    detalle: str = ""


@dataclass
class Resultado:
    pasos: list[Paso] = field(default_factory=list)

    @property
    def enviado(self) -> bool:
        """El mensaje principal llegó (con o sin el Excel)."""
        return any(p.nombre == "Mensaje" and p.estado == "ok" for p in self.pasos)


class WhatsAppCloud:
    def __init__(self, token: str, phone_number_id: str, plantilla: str = "avance_pedido",
                 idioma: str = "es", version: str = VERSION_API, abrir=urllib.request.urlopen):
        if not token or not phone_number_id:
            raise ErrorWhatsApp("Faltan `token` o `phone_number_id` en la sección [whatsapp] de Secrets.")
        self.token, self.numero_id = token, str(phone_number_id)
        self.plantilla, self.idioma, self.version = plantilla, idioma, version
        self._abrir = abrir

    @classmethod
    def desde_config(cls, config: dict | None) -> "WhatsAppCloud | None":
        config = dict(config or {})
        if not config.get("token"):
            return None
        return cls(str(config.get("token", "")), str(config.get("phone_number_id", "")),
                   str(config.get("plantilla", "avance_pedido")), str(config.get("idioma", "es")),
                   str(config.get("version", VERSION_API)))

    # --- HTTP ---
    def _url(self, recurso: str) -> str:
        return f"https://graph.facebook.com/{self.version}/{self.numero_id}/{recurso}"

    def _pedir(self, req: urllib.request.Request) -> dict:
        req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with self._abrir(req, timeout=40) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read().decode()).get("error", {})
            except Exception:
                error = {}
            detalle = (error.get("error_data") or {}).get("details") or error.get("message") or str(exc)
            raise ErrorWhatsApp(f"WhatsApp respondió {exc.code}: {detalle}", error.get("code")) from exc
        except urllib.error.URLError as exc:
            raise ErrorWhatsApp(f"No se pudo conectar con WhatsApp: {exc.reason}") from exc

    def subir(self, doc: Documento) -> str:
        """Sube el archivo a Meta y devuelve su id (vale 30 días)."""
        borde = uuid.uuid4().hex
        partes = []
        for nombre, valor in (("messaging_product", "whatsapp"), ("type", doc.mime)):
            partes.append(f'--{borde}\r\nContent-Disposition: form-data; name="{nombre}"\r\n\r\n{valor}\r\n'.encode())
        partes.append(f'--{borde}\r\nContent-Disposition: form-data; name="file"; filename="{doc.nombre}"\r\n'
                      f"Content-Type: {doc.mime}\r\n\r\n".encode() + doc.contenido + b"\r\n")
        partes.append(f"--{borde}--\r\n".encode())
        req = urllib.request.Request(self._url("media"), data=b"".join(partes), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={borde}")
        respuesta = self._pedir(req)
        if not respuesta.get("id"):
            raise ErrorWhatsApp("WhatsApp no devolvió el id del archivo subido.")
        return respuesta["id"]

    def _mensaje(self, cuerpo: dict) -> str:
        cuerpo = {"messaging_product": "whatsapp", "recipient_type": "individual", **cuerpo}
        req = urllib.request.Request(self._url("messages"), data=json.dumps(cuerpo).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        respuesta = self._pedir(req)
        return ((respuesta.get("messages") or [{}])[0]).get("id", "")

    def enviar_plantilla(self, telefono: str, variables: list[str], media_id: str, nombre_pdf: str) -> str:
        return self._mensaje({"to": telefono, "type": "template", "template": {
            "name": self.plantilla, "language": {"code": self.idioma},
            "components": [
                {"type": "header", "parameters": [
                    {"type": "document", "document": {"id": media_id, "filename": nombre_pdf}}]},
                {"type": "body", "parameters": [{"type": "text", "text": v} for v in variables]},
            ]}})

    def enviar_texto(self, telefono: str, texto: str) -> str:
        return self._mensaje({"to": telefono, "type": "text", "text": {"body": texto[:4096]}})

    def enviar_documento(self, telefono: str, media_id: str, nombre: str, leyenda: str = "") -> str:
        doc = {"id": media_id, "filename": nombre}
        if leyenda:
            doc["caption"] = leyenda
        return self._mensaje({"to": telefono, "type": "document", "document": doc})

    # --- El envío completo ---
    def enviar_avance(self, telefono: str, texto: str, variables: list[str],
                      documentos: list[Documento]) -> Resultado:
        """Mensaje + PDF (en la plantilla) + los demás documentos. Nunca levanta.

        Para en el primer fallo del mensaje principal: sin él no tiene sentido
        mandar los adjuntos sueltos.
        """
        res = Resultado()
        if not telefono:
            res.pasos.append(Paso("Mensaje", "error", "El número de WhatsApp no es válido."))
            return res
        pdf = next((d for d in documentos if d.mime == MIME_PDF), None)
        resto = [d for d in documentos if d is not pdf]
        try:
            if self.plantilla:
                if pdf is None:
                    raise ErrorWhatsApp("La plantilla necesita el PDF como cabecera.")
                media = self.subir(pdf)
                wamid = self.enviar_plantilla(telefono, variables, media, pdf.nombre)
                res.pasos.append(Paso("Mensaje", "ok",
                                      f"WhatsApp lo aceptó (plantilla «{self.plantilla}» con {pdf.nombre}) · id {wamid}"))
            else:  # sin plantilla: texto libre, solo vale si el destino escribió en las últimas 24 h
                wamid = self.enviar_texto(telefono, texto)
                res.pasos.append(Paso("Mensaje", "ok", f"WhatsApp lo aceptó (texto libre) · id {wamid}"))
                if pdf is not None:
                    resto.insert(0, pdf)
        except ErrorWhatsApp as exc:
            res.pasos.append(Paso("Mensaje", "error", _explicar(exc)))
            return res

        for doc in resto:
            try:
                wamid = self.enviar_documento(telefono, self.subir(doc), doc.nombre)
                res.pasos.append(Paso(doc.nombre, "ok", f"WhatsApp lo aceptó · id {wamid}"))
            except ErrorWhatsApp as exc:
                estado = "aviso" if exc.codigo == CODIGO_FUERA_DE_VENTANA else "error"
                res.pasos.append(Paso(doc.nombre, estado, _explicar(exc)))
        return res


def _explicar(exc: ErrorWhatsApp) -> str:
    if exc.codigo == CODIGO_FUERA_DE_VENTANA:
        return ("WhatsApp solo permite enviar archivos sueltos si el cliente escribió en las últimas "
                "24 h. El mensaje con el PDF sí llegó; el Excel se puede reenviar cuando responda.")
    if exc.codigo == 131030:
        return ("Con el número de prueba de Meta solo se puede enviar a los números agregados como "
                "destinatarios en el panel de la app (WhatsApp → API Setup → «To»).")
    if exc.codigo == 132001:
        return "La plantilla no existe o no está aprobada en Meta para ese idioma."
    if exc.codigo in (190, 401):
        return "El token de WhatsApp venció o no es válido."
    return str(exc)
