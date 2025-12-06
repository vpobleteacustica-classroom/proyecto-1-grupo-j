#!/usr/bin/env python3
"""Script de prueba para verificar la configuración."""

import json

# Cargar tipos de locales
with open("tipos_locales.json", "r", encoding="utf-8") as f:
    tipos_locales = json.load(f)

print("=" * 60)
print("TIPOS DE LOCALES CARGADOS")
print("=" * 60)

for idx, local in enumerate(tipos_locales["tipos_locales"], 1):
    print(f"\n{idx}. {local['nombre']}")
    print(f"   - Superficie: {local['superficie_m2']} m²")
    print(
        f"   - Nivel de ruido: {local['nivel_ruido_min']}-{local['nivel_ruido_max']} dB(A)"
    )
    print(f"   - Límite D: {local['limite_d']} dB")
    print(f"   - Clasificación base: {local['clasificacion_base']}")

print("\n" + "=" * 60)
print("CLASIFICACIONES")
print("=" * 60)

for clave, info in tipos_locales["clasificaciones"].items():
    print(f"\n{clave}: {info['descripcion']}")
    print(f"   - Color: {info['color']}")
    print(f"   - Nivel máximo: {info['nivel_max']} dB(A)")

print("\n" + "=" * 60)
print("PRUEBA DE CLASIFICACIÓN")
print("=" * 60)

# Simular clasificaciones
test_values = [75, 85, 92, 98, 103]

for dba in test_values:
    if dba <= 90:
        clasificacion = "A - Tranquilo"
        color = tipos_locales["clasificaciones"]["A"]["color"]
    elif dba <= 100:
        clasificacion = "B - Ruidoso"
        color = tipos_locales["clasificaciones"]["B"]["color"]
    else:
        clasificacion = "C - Muy ruidoso"
        color = tipos_locales["clasificaciones"]["C"]["color"]

    print(f"{dba} dB(A) -> {clasificacion} (color: {color})")

print("\n¡Configuración validada correctamente!")
