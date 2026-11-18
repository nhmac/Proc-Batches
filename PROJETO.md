# Proc-Batches

Agrupa os PDFs de etiquetas em batches até ao limite de quantidade.

- **App:** https://nhmac.github.io/Proc-Batches/ (Chrome, Edge ou Brave; pode ser instalada como app)
- **Repositório:** https://github.com/nhmac/Proc-Batches (código-fonte no `main`; o site é gerado e publicado pelo GitHub Actions)
- **Versão atual:** web 1.4 (modo Duplicados novo)

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

O modo **Duplicados** (desde a 1.4) encontra PDFs repetidos nas pastas de papel e tira as cópias a mais.
Ver "Modo Duplicados", abaixo.

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
| `testes/` | `node testes/duplicados.js`: testes da lógica do modo Duplicados (sem PDFs reais) |

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

## Modo Duplicados

Encontra PDFs repetidos numa pasta com pastas de papel (ex.: a "00", com `CA Lustre`, `DPII Lustre`,
`DPII Glossy`, `DPII_Seda`, `Crystal_Brilho`) e tira as cópias a mais. Lógica no
`<script id="logica-duplicados">` (objeto `Duplicados`, sem DOM), interface no `<script id="duplicados">`.
A versão Python não tem este modo.

- **Repetido** = conteúdo igual byte a byte, com qualquer nome. Só se leem por inteiro os PDFs com
  tamanho repetido (SHA-256). PDFs com o mesmo nome e conteúdo diferente aparecem à parte e não se mexe neles.
- **Que cópia fica:** a que está na pasta do papel do campo "Tipo de Papel" do item, na etiqueta
  (`lerEtiqueta`). O papel da pasta tira-se do nome (`papelDaPasta`): família `CA`/`Crystal` ou `DPII` e
  acabamento Lustre, Brilho/Glossy, Seda/Silk ou Mate. "Lustre" sem família (Schools) serve para as duas
  famílias. Cópias na mesma pasta: fica a de nome original (`<encomenda>_<id>_label.pdf`).
- **Por decidir** (o operador clica na cópia que fica): sem papel na etiqueta, nenhuma pasta do papel,
  ou mais de uma pasta que serve. Também se pode pôr qualquer PDF em "Não mexer neste".
- **Confirma o papel** (aviso, não bloqueia): quando nenhum papel da lista do fundo da etiqueta
  ("Impressão 10x15 CA Lustre", …) bate certo com o do item. Essa lista tem todos os itens da encomenda,
  por isso não decide nada.
- **Limpar:** "Mover para _Duplicados" (por omissão; cria `_Duplicados` dentro da pasta escolhida, com as
  mesmas subpastas, e confirma a cópia antes de apagar o original) ou "Apagar" (de vez). Antes de cada
  ficheiro confirma que é igual, byte a byte, à cópia que fica. No fim lê a pasta de novo.
- A pasta escolhe-se só para leitura; a autorização para alterar pede-se ao carregar em Limpar. Só funciona
  no Chrome/Edge com "Escolher pasta…" (ou ao arrastar a pasta). Sem isso, a análise faz-se mas o Limpar
  fica desligado. A pasta `_Duplicados` é ignorada nas análises seguintes.

Testado (2026-11-18) com uma pasta "00" real de 232 PDFs: 25 repetidos, 27 cópias a mais (21 em
`CA Lustre`, 6 em `Crystal_Brilho`), 15 com "Confirma o papel" (encomendas 6538763, 6537120 e
6538883: item DPII Lustre, lista da encomenda CA Lustre). O resultado foi igual à limpeza feita à mão.
