#!/usr/bin/env python3
"""Arma la carpeta _site/ lista para publicar: envuelve index.html en un documento completo y copia los datos."""
import shutil
from pathlib import Path

raiz = Path(__file__).parent
salida = raiz / "_site"
if salida.exists():
    shutil.rmtree(salida)
(salida / "data").mkdir(parents=True)

html = (raiz / "index.html").read_text(encoding="utf-8")
cabecera, cuerpo = html.split("</style>", 1)
documento = (
    '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    + cabecera
    + "</style>\n</head>\n<body>"
    + cuerpo
    + "\n</body>\n</html>\n"
)
(salida / "index.html").write_text(documento, encoding="utf-8")
shutil.copy(raiz / "articulos.json", salida / "data" / "articulos.json")
print("Sitio listo en", salida)
