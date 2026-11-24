"""Prueba la conexión al SQL Server del ERP con lo configurado en .streamlit/secrets.toml.

Solo LEE: ejecuta las consultas de [datos.consultas] y dice cuántas filas trae
cada una, si faltan columnas y si la app las entiende. Uso (Windows):
    windows\\probar_conexion.bat
"""

from __future__ import annotations

import sys
import time
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def main() -> int:
    archivo = RAIZ / ".streamlit" / "secrets.toml"
    if not archivo.exists():
        print("No existe .streamlit/secrets.toml. Ejecuta primero windows\\instalar.bat.")
        return 1
    datos = tomllib.loads(archivo.read_text(encoding="utf-8")).get("datos", {})
    if not datos or str(datos.get("conector", "demo")).lower() == "demo":
        print("La sección [datos] no está configurada: la app usa DATOS DE DEMOSTRACIÓN.")
        print("Completa la conexión en .streamlit/secrets.toml y vuelve a probar.")
        return 0

    try:
        import pyodbc
        print("Drivers ODBC instalados en este servidor:", ", ".join(pyodbc.drivers()) or "(ninguno)")
    except ImportError:
        print("Aviso: pyodbc no está instalado (ejecuta windows\\instalar.bat).")

    from trazabilidad import costos
    from trazabilidad.conectores import ErrorDeDatos, obtener_conector, pedidos_desde_tablas

    try:
        conector = obtener_conector(datos)
        print(f"\nConectando ({conector.nombre})...")
        t0 = time.time()
        tablas = conector.leer_tablas()
    except ErrorDeDatos as exc:
        print(f"\n[ERROR de configuración] {exc}")
        return 1
    except Exception as exc:  # el mensaje del driver es lo que hay que leer
        print(f"\n[ERROR de conexión] {type(exc).__name__}: {exc}")
        print("Revisa: nombre del servidor e instancia, puerto 1433, usuario/clave y el nombre del driver.")
        return 1
    print(f"Conectado en {time.time() - t0:.1f} s")
    print(f"  pedidos: {len(tablas.pedidos)} filas · lineas: {len(tablas.lineas)} · eventos: {len(tablas.eventos)}")

    try:
        pedidos, avisos = pedidos_desde_tablas(tablas)
    except ErrorDeDatos as exc:
        print(f"\n[ERROR en las vistas] {exc}")
        return 1
    print(f"La app entiende {len(pedidos)} pedidos.")
    for aviso in avisos[:15]:
        print("  aviso:", aviso)
    if len(avisos) > 15:
        print(f"  ... y {len(avisos) - 15} avisos más")

    try:
        tc = conector.leer_costos()
    except Exception as exc:
        print(f"\n[ERROR en las consultas de costos] {type(exc).__name__}: {exc}")
        return 1
    if tc is None:
        print("\nCostos: no hay consultas costos_* configuradas (el módulo de costos queda vacío).")
    else:
        try:
            r = costos.costear(pedidos, tc)
            print(f"\nCostos: {r.kpis['ots']} órdenes de trabajo costeadas · costo total S/ {r.kpis['costo_total']:,.2f}")
        except costos.ErrorDeCostos as exc:
            print(f"\n[ERROR en las vistas de costos] {exc}")
            return 1
    print("\nTodo bien: la app puede leer el ERP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
