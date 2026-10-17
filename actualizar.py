#!/usr/bin/env python3
"""Genera data/articulos.json con 3000+ fichas de anime y manga desde la API pública de AniList.

Uso (en tu ordenador, con internet):
    python3 actualizar.py            # unas 3600 entradas
    python3 actualizar.py 5000       # otra cantidad

Vuelve a ejecutarlo cuando quieras (a mano o con una tarea programada, por ejemplo un
cron diario o GitHub Actions) y el sitio se actualiza con los anuncios y estrenos nuevos.
Solo usa la biblioteca estándar de Python.
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

OBJETIVO = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
SALIDA = Path(__file__).parent / "articulos.json"
API = "https://graphql.anilist.co"

CONSULTA = """
query ($page: Int, $tipo: MediaType, $estado: MediaStatus, $orden: [MediaSort]) {
  Page(page: $page, perPage: 50) {
    pageInfo { hasNextPage }
    media(type: $tipo, status: $estado, sort: $orden, isAdult: false) {
      id
      title { romaji english }
      format
      status
      description(asHtml: false)
      genres
      averageScore
      siteUrl
      coverImage { large }
      startDate { year }
      studios(isMain: true) { nodes { name } }
      staff(perPage: 2, sort: RELEVANCE) { nodes { name { full } } }
    }
  }
}
"""

GENEROS = {
    "Action": "Acción", "Adventure": "Aventura", "Comedy": "Comedia", "Drama": "Drama",
    "Fantasy": "Fantasía", "Horror": "Terror", "Mahou Shoujo": "Magia", "Mecha": "Mecha",
    "Music": "Música", "Mystery": "Misterio", "Psychological": "Psicológico",
    "Romance": "Romance", "Sci-Fi": "Ciencia ficción", "Slice of Life": "Slice of life",
    "Sports": "Deportes", "Supernatural": "Sobrenatural", "Thriller": "Thriller",
    "Ecchi": "Ecchi",
}
ESTADOS = {
    "FINISHED": "Finalizado", "RELEASING": "En curso", "NOT_YET_RELEASED": "Anunciado",
    "CANCELLED": "Cancelado", "HIATUS": "En pausa",
}

# (tipo, estado o None, orden, máximo de entradas). Primero lo más reciente: anuncios y estrenos.
TANDAS = [
    ("ANIME", "NOT_YET_RELEASED", "POPULARITY_DESC", 300),
    ("MANGA", "NOT_YET_RELEASED", "POPULARITY_DESC", 300),
    ("ANIME", "RELEASING", "POPULARITY_DESC", 350),
    ("MANGA", "RELEASING", "POPULARITY_DESC", 350),
    ("ANIME", None, "POPULARITY_DESC", 1500),
    ("MANGA", None, "POPULARITY_DESC", 1500),
]


def pedir(variables):
    cuerpo = json.dumps({"query": CONSULTA, "variables": variables}).encode()
    peticion = urllib.request.Request(
        API, cuerpo, {"Content-Type": "application/json", "Accept": "application/json"}
    )
    for intento in range(6):
        try:
            with urllib.request.urlopen(peticion, timeout=30) as r:
                return json.load(r)["data"]["Page"]
        except urllib.error.HTTPError as e:
            espera = int(e.headers.get("Retry-After", 20)) if e.code == 429 else 5 * (intento + 1)
            print(f"  HTTP {e.code}, espero {espera}s")
            time.sleep(espera)
        except Exception as e:  # red caída, timeout...
            print(f"  error: {e}, reintento")
            time.sleep(5 * (intento + 1))
    raise SystemExit("AniList no responde. Prueba más tarde.")


def limpiar(texto):
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = re.sub(r"\(Source:[^)]*\)|\[Written by[^\]]*\]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) > 240:
        texto = texto[:240].rsplit(" ", 1)[0] + "…"
    return texto


def convertir(m, tipo):
    titulo = m["title"]["english"] or m["title"]["romaji"]
    if tipo == "ANIME":
        por = ", ".join(n["name"] for n in m["studios"]["nodes"][:2])
    else:
        por = ", ".join(n["name"]["full"] for n in m["staff"]["nodes"][:2])
    return {
        "id": m["id"],
        "t": titulo,
        "tipo": tipo.lower(),
        "y": m["startDate"]["year"],
        "por": por,
        "g": [GENEROS.get(g, g) for g in m["genres"]][:4],
        "s": limpiar(m["description"]),
        "e": ESTADOS.get(m["status"], "Sin datos"),
        "n": m["averageScore"],
        "f": m["siteUrl"],
        "img": (m["coverImage"] or {}).get("large"),
        "a": date.today().isoformat(),
    }


def main():
    vistos = {}
    for tipo, estado, orden, maximo in TANDAS:
        pagina, cuenta = 1, 0
        print(f"{tipo} {estado or 'todos'}: hasta {maximo}")
        while cuenta < maximo and len(vistos) < OBJETIVO:
            res = pedir({"page": pagina, "tipo": tipo, "estado": estado, "orden": [orden]})
            for m in res["media"]:
                clave = (tipo, m["id"])
                if clave not in vistos:
                    vistos[clave] = convertir(m, tipo)
                cuenta += 1
            print(f"  página {pagina}: {len(vistos)} en total")
            if not res["pageInfo"]["hasNextPage"]:
                break
            pagina += 1
            time.sleep(0.8)  # AniList permite unas 90 peticiones por minuto
    # Los anuncios primero; después lo más reciente y mejor valorado.
    orden_estado = {"Anunciado": 0, "En curso": 1}
    lista = sorted(
        vistos.values(),
        key=lambda x: (orden_estado.get(x["e"], 2), -(x["y"] or 0), -(x["n"] or 0)),
    )
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(lista, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Listo: {len(lista)} fichas en {SALIDA}")


if __name__ == "__main__":
    main()
