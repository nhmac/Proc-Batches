# Proc-Batches

Agrupa os PDFs de etiquetas em batches até ao limite de quantidade.

- **App:** https://nhmac.github.io/Proc-Batches/ (Chrome, Edge ou Brave; pode ser instalada como app)
- **Repositório:** https://github.com/nhmac/Proc-Batches (código-fonte no `main`; o site é gerado e publicado pelo GitHub Actions)
- **Versão atual:** web 1.3.7 (modo Express ligado)

Os PDFs são lidos no browser e não são enviados para lado nenhum.

O **Agrupar** tem dois modos, escolhidos à mão antes de cada processo (abre sempre no primeiro):

- **Fotoprix + Dreambooks** (limite 4500): uma pasta com um PDF por etiqueta, cujo nome começa pelo
  número da encomenda. A quantidade é o número na `AREA_NUMERO` da 1.ª página.
- **Express** (limite 2300): um ou mais PDFs com várias folhas Express Profissional (botão
  "Escolher PDF…"). A quantidade de cada folha é a soma da coluna Qtd.

O limite está fixo no standard de cada modo (`LIMITE_BLOQUEADO`). Se os PDFs não forem do modo
escolhido, ou se misturarem Dreambooks e Fotoprix, o processo é bloqueado e a página mostra os
ficheiros em causa. Na 1.3.4 e na 1.3.6 o botão do modo Express esteve desligado (`data-desligado` no
`web/autobatch.html`); na 1.3.7 voltou a estar ligado.
Desde a 1.3.2 também é bloqueado, no modo Fotoprix + Dreambooks, quando algum
PDF não tem o número da quantidade na etiqueta (antes entrava no batch como 0, sem aviso). Desde
a 1.3.3 é bloqueado também quando algum PDF não começa pelo número da encomenda (antes ficava de
fora dos batches, sem aviso). O modo **Numeração** (próximo número de batch, a partir das pastas BATCHES)
já está no código mas desligado ("em desenvolvimento", `NUMERACAO_ATIVA`).

## Atualizar a app

O GitHub é a única fonte: funciona igual em qualquer PC ou no Claude Code na web.

1. `git pull` (sempre antes de começar).
2. Alterar `web/autobatch.html` e subir o "Versão web".
3. Testar: `py build_pages.py` gera o site em `_site/` (abrir o `_site/index.html`).
4. Publicar: commit e `git push`. O GitHub Actions ("Publicar site") gera e publica o site em
   1-2 minutos; os PCs recebem a versão nova ao abrir a app com internet.

Só usa a biblioteca padrão do Python e o git.

## Pastas

| | |
|---|---|
| `web/` | Fonte do site: `autobatch.html`, ícones PNG e pdf.js (`vendor/pdfjs`, Apache 2.0) |
| `.github/workflows/pages.yml` | Gera e publica o site a cada push ao `main` |
| `Inter/`, `icone.ico` | Fonte Inter (SIL OFL) e ícone, usados pelo site e pela versão Python |
| `PDFs/` | PDFs de exemplo para testes |
| `main.py`, `processamento_ui.py` | Versão Python (referência da lógica): tem os dois modos do Agrupar e as mesmas regras desde a 1.3.1; não tem a Numeração |
| `debug/` | Scripts para descobrir as coordenadas do número na etiqueta |

## Versão Python e scripts de debug

Precisam do `customtkinter` e do `pdfplumber`, num ambiente virtual:

```
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

A zona onde se lê o número está em `AREA_NUMERO`, tanto no `main.py` como no `web/autobatch.html`.
Se o layout das etiquetas mudar, altera-se nos dois sítios.

## Tipo de encomenda pelo número

O Agrupar tem dois modos (Fotoprix + Dreambooks e Express) que nunca se misturam. O tipo de cada
encomenda tira-se do número, pela tabela `TIPOS` (no `main.py` e no `web/autobatch.html`, iguais):

| Tipo | Faixa | Em 2026-10 | Sobe por ano |
|---|---|---|---|
| Dreambooks | 1 000 000 a 4 999 999 | 3 477 048 | ~74 000 |
| Express | 5 000 000 a 9 999 999 | 6 533 615 | ~72 000 |
| Fotoprix | 10 000 000 a 99 999 999 | 10 246 495 | ~160 000 |

Até à 1.3 a regra era o 1.º algarismo (3, 6 e 1), e partia quando a numeração passasse de
3 999 999 para 4 000 000. Com as faixas há folga para décadas. Quando um número passa do `aviso` da
tabela (4 900 000 / 9 900 000), a página mostra "Atenção: numeração perto do limite", sem bloquear.

Casos reais de teste em `PDFs/novos testes/` (só nos PCs: os PDFs não vão para o git) (um PDF com várias encomendas de cada tipo, 2026-10-28).
Para o modo Fotoprix + Dreambooks dividem-se por página em `<id da folha>_label.pdf` (como na pasta das
etiquetas). O modo Express lê o PDF inteiro.
