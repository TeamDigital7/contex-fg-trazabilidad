# Contex · Trazabilidad de pedidos

App de Streamlit para que el cliente vea cómo va su pedido, etapa por etapa,
con el registro ISO 9001 que deja cada una.

```
Pedido recibido → Producción → Inspección final → Despacho → Entregado · 30 días
   ISO 8.2.3        ISO 8.5      ISO 8.6 · 8.7    Guía·factura    ISO 9.1.2
```

- **Tablero** tipo kanban: una columna por etapa, una tarjeta por pedido con su
  avance, su estado (*En riesgo*, *1 no conforme(s)*, *Entrega 22/40*,
  *Encuesta 5.0 / 5*…) y la fecha de entrega.
- **Detalle del pedido** (tocando la tarjeta): avance general, las cinco etapas,
  las sub-etapas de producción y la línea de tiempo con cada registro ISO,
  responsable y evidencia.
- **Cliente** (barra lateral): cada opción es un cliente y muestra solo sus pedidos;
  «Todos los clientes» muestra todos. En el tablero, «Todo el historial» incluye
  los entregados antiguos.
- **Descargas**: resumen en PDF y Excel con detalle, y la **proforma** de cada pedido
  (PDF con logo, precios, IGV, total y el estado de la trazabilidad).
- **Lista de pedidos** con filtro y descarga CSV, y **Conexión de datos**.

## Datos: demo hoy, la base del cliente mañana

Sin configuración la app muestra **datos de demostración** (fechas relativas al
día de hoy, así la demo nunca envejece). Para conectar la base real basta con
agregar la sección `[datos]` en *Secrets* (ver `.streamlit/secrets.example.toml`):
una URL de SQLAlchemy y tres consultas `SELECT` que devuelvan estas columnas.

| Tabla | Obligatorias | Opcionales |
|---|---|---|
| pedidos | codigo, cliente, etapa, fecha_pedido, fecha_entrega | avance_produccion (0-1), no_conformes, cantidad_despachada, liberado, encuesta, fecha_entregado |
| lineas | codigo_pedido, producto, cantidad | |
| eventos | codigo_pedido, fecha, etapa, descripcion | clausula, responsable, evidencia |

La demo y la base real pasan por **la misma función** (`pedidos_desde_tablas`),
así que lo que el cliente ve en la demo es exactamente lo que verá con sus datos.
Agregar el driver de su base en `requirements.txt` (psycopg2-binary, pymysql,
pyodbc u oracledb).

## WhatsApp: el avance al cliente con un clic

Botón **"Enviar por WhatsApp"** en el detalle de cada pedido (mensaje + PDF + Excel
del pedido) y en el tablero cuando se elige un cliente (resumen de todos sus pedidos).
El número sale de la columna opcional `telefono` de la tabla `pedidos` (y el saludo
de `contacto`); si no viene, se escribe en la ventana antes de enviar.

- **Sin configurar (demo):** abre WhatsApp con el mensaje ya escrito; los archivos se
  adjuntan a mano. Un enlace no puede adjuntar archivos: eso solo lo hace la API.
- **Con la API de WhatsApp Business (Meta Cloud API):** el envío es automático.
  Pasos, una sola vez:
  1. Cuenta de Meta Business verificada y un número de WhatsApp para la empresa
     (no puede estar usándose en la app normal de WhatsApp).
  2. En Meta, crear la plantilla `avance_pedido` (categoría *Utilidad*, idioma
     español, cabecera **Documento**) con este texto:

     > Hola {{1}}, le saluda Contex FYG. Le compartimos el avance de su pedido {{2}}:
     > se encuentra en la etapa {{3}} con un avance de {{4}}. Entrega comprometida: {{5}}.
     > {{6}} Adjuntamos el detalle en PDF. Quedamos atentos a cualquier consulta.

  3. Poner `token` y `phone_number_id` en la sección `[whatsapp]` de Secrets
     (ver `.streamlit/secrets.example.toml`).

  WhatsApp exige que el primer mensaje de la empresa sea una plantilla aprobada, y
  una plantilla lleva **un** documento: el PDF va en la plantilla y el Excel después,
  como archivo aparte. Ese segundo archivo solo llega si el cliente escribió en las
  últimas 24 h; si no, la app lo avisa (el mensaje y el PDF sí llegan).
  Meta cobra por conversación iniciada por la empresa.

## Correr y desplegar

```bash
pip install -r requirements.txt
streamlit run app.py
python tests/test_trazabilidad.py
```

En Streamlit Community Cloud: *New app* → este repositorio → `app.py`.

La barra lateral lleva el logo de Contex FYG (`assets/logo_contex.png`) y el menú
con botones; los colores salen del logo (azul marino `#12386B` y gris `#909090`).

## Estructura

```
app.py                         pantallas y navegación
trazabilidad/modelo.py         etapas, pedidos y reglas de cada estado (sin Streamlit)
trazabilidad/vistas.py         HTML del tablero y del detalle
trazabilidad/estilos.py        CSS
trazabilidad/conectores/       demo, SQL y el mapeo único tablas → pedidos
tests/test_trazabilidad.py     modelo, mapeo, SQLite real y la app con AppTest
```

**Pendiente antes de producción:** login. Hoy el selector de cliente es libre; con
datos reales cada cliente debe entrar con su usuario y ver solo lo suyo.
