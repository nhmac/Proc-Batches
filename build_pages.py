"""
Gera o site do AutoBatch para o GitHub Pages na pasta _site/.

Build: py build_pages.py
Publicar: commit e git push para o main. O GitHub Actions (.github/workflows/pages.yml)
corre este script e publica a pasta _site/ no GitHub Pages.
(Só biblioteca padrão: corre com o Python instalado, sem .venv.)

A fonte é o web\\autobatch.html (a mesma página publicada como Artifact no claude.ai).
Diferenças no site:
    - pdf.js e fonte Inter servidos pelo próprio site (web\\vendor, Inter\\static), sem CDNs
    - o pdf.js usa um Web Worker a sério (mais rápido com muitos PDFs)
    - manifest + service worker: a página pode ser instalada como app (ícone no
      Ambiente de Trabalho e na barra de tarefas) e funciona sem internet
"""

import hashlib
import json
import os
import re
import shutil

PROJETO = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(PROJETO, "web", "autobatch.html")
DESTINO = os.path.join(PROJETO, "_site")
PDFJS = "3.11.174"
CDN_PDFJS = f"https://cdnjs.cloudflare.com/ajax/libs/pdf.js/{PDFJS}"

COPIAR = {
    "vendor/pdfjs/pdf.min.js": "web/vendor/pdfjs/pdf.min.js",
    "vendor/pdfjs/pdf.worker.min.js": "web/vendor/pdfjs/pdf.worker.min.js",
    "vendor/pdfjs/LICENSE": "web/vendor/pdfjs/LICENSE",
    "fonts/Inter_18pt-Regular.ttf": "Inter/static/Inter_18pt-Regular.ttf",
    "fonts/Inter_18pt-SemiBold.ttf": "Inter/static/Inter_18pt-SemiBold.ttf",
    "fonts/OFL.txt": "Inter/OFL.txt",
    "icone.ico": "icone.ico",
    "icon-192.png": "web/icon-192.png",
    "icon-512.png": "web/icon-512.png",
}

DESCRICAO = "Agrupa os PDFs de etiquetas em batches até ao limite de quantidade e mostra o próximo número de batch a usar."

FONTES_CSS = """<style>
  @font-face { font-family: "Inter"; font-weight: 400; font-display: swap; src: url("fonts/Inter_18pt-Regular.ttf") format("truetype"); }
  @font-face { font-family: "Inter"; font-weight: 600; font-display: swap; src: url("fonts/Inter_18pt-SemiBold.ttf") format("truetype"); }
  body { margin: 0; }
  [hidden] { display: none !important; }
</style>"""

SW = """// Gerado pelo build_pages.py
const CACHE = "autobatch-%(versao)s";
const FICHEIROS = %(ficheiros)s;

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FICHEIROS)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(chaves => Promise.all(chaves.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Rede primeiro: com internet vê-se sempre a versão publicada; sem internet usa a cópia guardada
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r.ok) {
          const copia = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, copia));
        }
        return r;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
"""

def substituir(texto, antigo, novo, regex=False):
    """Substitui exatamente uma ocorrência; falha se a página mudou e já não bate certo."""
    novo_texto, n = (re.subn(antigo, novo, texto) if regex else (texto.replace(antigo, novo), texto.count(antigo)))
    if n != 1:
        raise SystemExit(f"build_pages: esperava 1 ocorrência de {antigo!r} em web/autobatch.html, há {n}")
    return novo_texto


def gerar_html():
    with open(FONTE, encoding="utf-8") as f:
        html = f.read()

    html = substituir(html, r'<link rel="preconnect"[^\n]*\n<link rel="preconnect"[^\n]*\n<link rel="stylesheet" href="https://fonts\.googleapis\.com[^\n]*\n', "", regex=True)
    html = substituir(html, r'<!-- Carregado como script:[^\n]*-->\n<script src="[^"]*/pdf\.worker\.min\.js"></script>\n', "", regex=True)
    html = substituir(html, f'<script src="{CDN_PDFJS}/pdf.min.js">', '<script src="vendor/pdfjs/pdf.min.js">')
    html = substituir(html, f'"{CDN_PDFJS}/pdf.worker.min.js"', '"vendor/pdfjs/pdf.worker.min.js"')
    for externo in ("cdnjs", "googleapis", "gstatic"):
        if externo in html:
            raise SystemExit(f"build_pages: ficou uma referência a {externo} na página")

    titulo, resto = html.split("\n", 1)
    if not titulo.startswith("<title>"):
        raise SystemExit("build_pages: a primeira linha de web/autobatch.html devia ser o <title>")
    # Todos os blocos <style> do início vão para o <head> (o da Numeração é um bloco à parte)
    estilos = re.match(r"(?:<style[^>]*>.*?</style>\n)+", resto, re.S)
    if not estilos:
        raise SystemExit("build_pages: a seguir ao <title> devia vir o <style> em web/autobatch.html")
    estilo, corpo = resto[:estilos.end()], resto[estilos.end():]

    return f"""<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{DESCRICAO}">
<meta name="theme-color" content="#15171c">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icone.ico">
<link rel="apple-touch-icon" href="icon-192.png">
{titulo}
{FONTES_CSS}
{estilo}</head>
<body>
{corpo}
<script>
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {{}});
</script>
</body>
</html>
"""


def main():
    # Começa sempre de uma pasta vazia
    shutil.rmtree(DESTINO, ignore_errors=True)
    os.makedirs(DESTINO)

    def escrever(rel, conteudo):
        with open(os.path.join(DESTINO, rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(conteudo)

    escrever("index.html", gerar_html())
    for rel, origem in COPIAR.items():
        destino = os.path.join(DESTINO, *rel.split("/"))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy2(os.path.join(PROJETO, *origem.split("/")), destino)

    escrever("manifest.webmanifest", json.dumps({
        "name": "Proc-Batches",
        "short_name": "Proc-Batches",
        "description": DESCRICAO,
        "lang": "pt-PT",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#15171c",
        "theme_color": "#15171c",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }, ensure_ascii=False, indent=2) + "\n")

    # A versão do cache muda sempre que algum ficheiro muda: o service worker novo substitui o antigo
    ficheiros = ["./"] + sorted(
        os.path.relpath(os.path.join(r, f), DESTINO).replace(os.sep, "/")
        for r, _, fs in os.walk(DESTINO) if ".git" not in os.path.relpath(r, DESTINO).split(os.sep)
        for f in fs)
    soma = hashlib.sha256()
    for rel in ficheiros[1:]:
        with open(os.path.join(DESTINO, rel), "rb") as f:
            soma.update(rel.encode() + f.read())
    escrever("sw.js", SW % {"versao": soma.hexdigest()[:12], "ficheiros": json.dumps(ficheiros)})
    escrever(".nojekyll", "")

    todos = [os.path.join(r, f) for r, _, fs in os.walk(DESTINO)
             if ".git" not in os.path.relpath(r, DESTINO).split(os.sep) for f in fs]
    print(f"Site: {DESTINO} ({len(todos)} ficheiros, {sum(map(os.path.getsize, todos)) / 2**20:.1f} MB)")


if __name__ == "__main__":
    main()
