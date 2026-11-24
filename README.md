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

## Analítica del negocio (dashboard de KPIs)

Menú **Analítica** (solo equipo interno). Periodo de 3, 6 o 12 meses y filtro por cliente.

- **Indicadores principales**: ventas sin IGV, margen bruto, prendas entregadas, entregas a
  tiempo y satisfacción, con su mini tendencia mensual y la variación contra el
  periodo anterior (solo si ese periodo tiene datos comparables).
- **Indicadores del SGC** con semáforo Bueno / Regular / Malo y las metas de Contex:
  satisfacción del cliente (FO-EST-CONT-03), cumplimiento del plazo de entrega y
  conformidad del producto (CA-OPE-CONT-01), tiempo de procesamiento de pedidos
  (informe final del ERP), margen bruto y costo de no calidad (metas de la app,
  ajustables) y calidad del corte («Por conectar» hasta tener el FO-OPE-CONT-02:
  nunca se muestra un número inventado).
- **Gráficos interactivos** (tooltip al pasar el mouse): ventas contra costo real por
  mes, pedidos en curso por etapa, entregas a tiempo y conformidad contra la meta,
  margen por cliente, gasto por material (Pareto) y ranking de clientes.
- **Reporte de KPIs** descargable en PDF ejecutivo y Excel (5 hojas).

## Módulo de costos

Menú **Costos** (solo equipo interno; los clientes no ven costos ni márgenes). Costea
cada orden de trabajo con el modelo del ERP de Contex (liquidación de órdenes de
proceso) y agrega lo que el reporte «Costos de Orden de Trabajo» no tiene:

- **Costo de la OT** = materia prima consumida + merma + mano de obra directa
  (horas × tarifa) + servicios de terceros (órdenes de servicio de confección,
  bordado, estampado, lavado) + **costos indirectos (CIF) asignados**.
- **Centros de costo**: Corte, Bordado, Estampado, Confección, Lavado, Taller de
  arreglos, Limpieza y acabado (productivos) y Planta general (apoyo).
- **Regla de asignación de CIF** elegible: horas de mano de obra, unidades o costo de
  materia prima. Un centro productivo solo carga a las OT que pasaron por él; el de
  apoyo, a todas. Lo que no se puede asignar se reporta, no se esconde.
- **Margen** contra la venta (sin IGV), solo en OT que ya salieron de producción;
  alerta bajo el 15 %. **Costo de no calidad** (merma + taller de arreglos) y
  **desvíos de consumo** contra la ficha técnica.
- **Cierre mensual** con revisión previa y Excel congelado del cierre; **tablas
  maestras** (tarifas por hora, centros de costo) y CIF del mes editables.
- Descargas: Excel de costos (7 hojas) y el **reporte de costo de la OT en PDF**.

Para la base real: consultas `costos_materiales`, `costos_mano_obra`,
`costos_terceros` y `costos_cif` en `[datos.consultas]` (columnas en la pantalla
«Conexión de datos»).

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

### Probarlo primero en tu propio WhatsApp

**Sin ningún token:** en la ventana, el botón verde **«Compartir por WhatsApp»** abre el
menú *Compartir* del celular con el mensaje, el PDF y el Excel adjuntos; se elige
WhatsApp y el propio chat. En un computador que no comparte archivos, los descarga
y abre WhatsApp con el texto.

La ventana tiene **«Enviar a: Mi número (prueba) | Cliente»** y abre siempre en
*Mi número*. Con `numero_pruebas` en Secrets tu número ya viene escrito, y con
`solo_pruebas = true` el envío a clientes queda bloqueado mientras pruebas.

- **Hoy (sin API):** pon tu número y pulsa «Abrir WhatsApp»: se abre el chat contigo
  mismo con el mensaje escrito. Así ves el speech tal como lo verá el cliente.
- **Con la API, sin esperar la aprobación de la plantilla:** Meta da gratis un
  *número de prueba* en developers.facebook.com (app de tipo Business → WhatsApp →
  API Setup). Agrega tu celular como destinatario (te llega un código), copia el
  token temporal y el *Phone number ID* a `[whatsapp]` con `plantilla = ""`.
  Escribe «hola» desde tu celular al número de prueba (abre la ventana de 24 h) y
  pulsa **«Enviarme la prueba»**: te llegan el mensaje, el PDF y el Excel.
- La app muestra el id que devuelve WhatsApp por cada envío: quiere decir que Meta
  lo **aceptó**. La confirmación de *entregado / leído* (los dos checks) requiere un
  webhook, que es un paso aparte.

## Instalación (uso interno, en un servidor de Contex)

La app es de **uso interno de Contex** y corre en un servidor Windows de la empresa, junto al
SQL Server del ERP: se abre desde la red de la oficina en `http://SERVIDOR:8501`. Guía completa
en **[docs/INSTALACION_LOCAL.md](docs/INSTALACION_LOCAL.md)**; en resumen:

1. `windows\instalar.bat` · 2. completar `.streamlit\secrets.toml` (plantilla en
`.streamlit/secrets.local.example.toml`) · 3. `windows\probar_conexion.bat` ·
4. `windows\servicio_instalar.bat` como administrador (arranca sola con el servidor).

Para desarrollo en cualquier equipo:

```bash
pip install -r requirements.txt
streamlit run app.py
python tests/test_trazabilidad.py
```

## Estructura

```
app.py                         pantallas y navegación
trazabilidad/modelo.py         etapas, pedidos y reglas de cada estado (sin Streamlit)
trazabilidad/vistas.py         HTML del tablero y del detalle
trazabilidad/estilos.py        CSS
trazabilidad/conectores/       demo, SQL y el mapeo único tablas → pedidos
tests/test_trazabilidad.py     modelo, mapeo, SQLite real y la app con AppTest
```

**El selector «Cliente» es solo un filtro** (la app es interna). Si no todos en Contex deben ver
costos y márgenes, el siguiente paso es un acceso con usuario y rol.
