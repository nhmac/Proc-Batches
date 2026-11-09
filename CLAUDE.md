# Proc-Batches

**Primeiro passo de cada sessão, antes de ler ou alterar código:** `git pull --ff-only`. O utilizador
trabalha em dois PCs e no Claude Code na web, e o GitHub é a única fonte. Se o pull falhar (alterações
locais por enviar, conflito, sem rede), parar e avisar o utilizador. Nunca forçar.

**No fim**, se houver alterações, commit e push (publicar só quando o utilizador pedir): não deixar
trabalho só neste PC.

Ver `PROJETO.md` (o que a app faz, pastas, versão Python). O `README.md` da raiz é o do GitHub,
comentado de propósito pelo utilizador: não mexer.

## Fluxo de trabalho (GitHub é a única fonte)

O utilizador trabalha em dois PCs e no Claude Code na web. Só o PC pessoal tem cópia local; no PC do
trabalho usa-se só o browser (ver "No Claude Code na web", abaixo).

1. `git pull --ff-only` (ver o primeiro passo, no topo).
2. Alterar só `web/autobatch.html` (a fonte do site) e subir o "Versão web" do rodapé.
   A versão Python (`main.py`) é referência da lógica: alterar também só se o utilizador pedir.
3. Testar: `py build_pages.py` (ou `python3`) gera `_site/`. Testar o `_site/index.html`, não o
   `web/autobatch.html` sozinho (o build junta CSS e fontes).
4. Publicar (só quando o utilizador pedir): commit "Versão X: …" e `git push` para o `main`. O workflow
   "Publicar site" (`.github/workflows/pages.yml`) gera e publica em 1-2 minutos. Confirmar com
   `gh run list` e com `curl https://nhmac.github.io/Proc-Batches/` (rodapé "Versão web").
5. Push recusado: `git pull --rebase` e resolver. **Nunca forçar o push.**

**No Claude Code na web** (usado no PC do trabalho, que não tem git): as alterações vão para um
ramo `claude/...`, não para o `main`. Para publicar, criar o pull request e o utilizador faz **Merge**
no github.com (o Actions publica a seguir). Os PDFs de teste não existem lá: testar no site publicado.

Os PDFs de teste não vão para o git (`.gitignore`): só existem nos PCs. Os PDFs são lidos no
browser e nunca são enviados para lado nenhum: não introduzir pedidos de rede.

Os commits até à versão 1.3.7 são do tempo em que o repositório só guardava o site gerado
(`index.html` na raiz).
