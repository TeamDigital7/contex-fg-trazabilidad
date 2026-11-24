# Instalación local en un servidor Windows de Contex

La app es de **uso interno de Contex**: corre en un servidor (o PC siempre
encendida) dentro de la red de la empresa, lee directo el SQL Server del ERP
(HDSOFT) y se abre desde cualquier PC o celular conectado a la red de la oficina.
No necesita internet ni Streamlit Cloud, y el SQL Server nunca queda expuesto.

```
PC / celular de la oficina ──► http://SERVIDOR:8501 ──► App (Python) ──► SQL Server del ERP
                                (solo red interna)                        (usuario de solo lectura)
```

## Requisitos

| Qué | Detalle |
|---|---|
| Servidor | Windows 10/11 o Windows Server, encendido siempre (puede ser el mismo del ERP). 4 GB de RAM libres. |
| Python | 3.11 o superior, de https://www.python.org/downloads/ · marcar **Install for all users** y **Add python.exe to PATH** |
| Driver ODBC | «ODBC Driver 17 (o 18) for SQL Server». Suele venir con SQL Server Management Studio; si no, se descarga de Microsoft. |
| Base de datos | Usuario de **solo lectura** y las 7 vistas del esquema `app` (ver abajo). |

## Pasos

1. **Copiar la app al servidor.** Descargar el repositorio (botón *Code → Download ZIP* en
   GitHub) y descomprimirlo, por ejemplo en `C:\ContexTrazabilidad`. Con Git:
   `git clone https://github.com/TeamDigital7/contex-fg-trazabilidad C:\ContexTrazabilidad`
2. **Instalar:** doble clic en `windows\instalar.bat`. Crea el entorno de Python, instala las
   librerías y crea `.streamlit\secrets.toml`.
3. **Preparar la base** (lo hace el administrador del SQL Server):
   - `sql\01_explorar_esquema.sql` → exportar el resultado a Excel (para escribir las vistas).
   - `sql\02_usuario_solo_lectura.sql` → crea el usuario `app_trazabilidad`, que **solo puede leer** el esquema `app`.
   - Crear las 7 vistas del esquema `app` (se escriben con el resultado del paso anterior).
4. **Configurar la conexión:** editar `.streamlit\secrets.toml` (con el Bloc de notas): quitar los
   `#` de la sección `[datos]` y completar servidor, base, usuario, clave y driver.
5. **Probar la conexión:** doble clic en `windows\probar_conexion.bat`. Debe terminar con
   *«Todo bien: la app puede leer el ERP»*. Si no, el mensaje dice qué revisar.
6. **Abrir la app:** `windows\iniciar.bat` y entrar a `http://localhost:8501`.
7. **Que arranque sola con el servidor:** clic derecho en `windows\servicio_instalar.bat` →
   **Ejecutar como administrador**. Registra la tarea programada *Contex Trazabilidad* (sin límite
   de tiempo y con reinicio automático si se cae) y abre el puerto 8501 **solo para la red interna**.

Desde cualquier PC o celular de la oficina: `http://NOMBRE-DEL-SERVIDOR:8501`
(o con la IP, p. ej. `http://192.168.1.20:8501`). Conviene crear un acceso directo en el escritorio
de quienes la usan.

## Las 7 vistas que lee la app

| Vista | Columnas |
|---|---|
| `app.v_pedidos` | codigo, cliente, etapa, fecha_pedido, fecha_entrega · opcionales: avance_produccion, no_conformes, cantidad_despachada, liberado, encuesta, fecha_entregado, telefono, contacto |
| `app.v_pedido_lineas` | codigo_pedido, producto, cantidad · opcional: precio_unitario |
| `app.v_pedido_eventos` | codigo_pedido, fecha, etapa, descripcion · opcionales: clausula, responsable, evidencia |
| `app.v_liquidacion_mp` | codigo_pedido, fecha, proceso, codigo, descripcion, um, cant_requerida, cant_consumida, cant_merma, costo_unitario |
| `app.v_liquidacion_mo` | codigo_pedido, fecha, proceso, personal, horas, tarifa_hora |
| `app.v_ordenes_servicio` | codigo_pedido, fecha, proceso, proveedor, cantidad, costo_unitario |
| `app.v_cif_mensual` | periodo, centro, concepto, monto |

Etapas: `recibido`, `produccion`, `inspeccion`, `despacho`, `entregado`. Procesos: COR corte,
BOR bordado, EST estampado, CNF confección, LAV lavado, ARR arreglos, ACA limpieza y acabado;
centro PLA = planta general.

## Mantenimiento

| Tarea | Cómo |
|---|---|
| Actualizar la app | Detenerla (`windows\servicio_quitar.bat` o cerrar la ventana), reemplazar los archivos (o `git pull`), ejecutar `windows\instalar.bat` y volver a arrancarla. `secrets.toml` no se pisa. |
| Ver qué pasó si falla | `logs\app.log` |
| Quitar el arranque automático | `windows\servicio_quitar.bat` como administrador |
| Cambiar el puerto | Reemplazar `8501` en `windows\iniciar*.bat` y en la regla del firewall |

## Problemas comunes

- **«Login failed for user»**: usuario o clave mal escritos, o el SQL Server no acepta usuarios
  SQL (activar *SQL Server and Windows Authentication mode* en las propiedades del servidor).
- **«Data source name not found»**: el nombre del driver en `url` no coincide con el instalado;
  `probar_conexion.bat` lista los drivers disponibles.
- **No abre desde otra PC**: revisar que el servidor esté en red *Privada* o de *Dominio* (la regla
  del firewall no se aplica a redes *Públicas*) y usar el nombre o la IP correctos.
- **La clave tiene @ # : / %**: en `url` se escribe codificada (`@` → `%40`, `#` → `%23`).
- **Autenticación de Windows**: la tarea programada corre como SYSTEM, así que se recomienda el
  usuario SQL de solo lectura en lugar de `trusted_connection`.
