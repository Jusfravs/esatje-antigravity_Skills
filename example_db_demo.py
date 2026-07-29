# example_db_demo.py
"""Demo rápido para validar los wrappers en db_manager.py
Este script inicializa la BD, pobla un par de causas, procesa una, y muestra estadísticas.
"""
from pathlib import Path
import pandas as pd
from db_manager import inicializar_bd, poblar_causas, obtener_estadisticas, obtener_siguiente_pendiente, registrar_extraccion


def main():
    inicializar_bd()
    causas = ["JUICIO-TEST-001", "JUICIO-TEST-002"]
    poblar_causas(causas)
    print("Estadísticas iniciales:", obtener_estadisticas())

    siguiente = obtener_siguiente_pendiente()
    print("Siguiente pendiente:", siguiente)

    if siguiente:
        df = pd.DataFrame([{"origen": "ejemplo", "valor": 1}])
        registrar_extraccion(siguiente, df)
        print("Registro de extracción para:", siguiente)

    print("Estadísticas finales:", obtener_estadisticas())


if __name__ == '__main__':
    main()
