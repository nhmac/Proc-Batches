// Testes da lógica do modo Duplicados: node testes/duplicados.js (na raiz do repositório)
// Extrai o <script id="logica-duplicados"> do web/autobatch.html, corre-o e confere:
//   - papel das pastas e das etiquetas (texto como o pdf.js o devolve)
//   - que cópia fica em cada caso (papel certo, mesma pasta, por decidir, aviso da lista da encomenda)
//   - agrupar por conteúdo e "mesmo nome, conteúdo diferente"
//   - contagem por pasta e nomes em _Duplicados
// Pára ao primeiro caso errado, com código de saída 1.

const fs = require("fs");
const path = require("path");

function falhar(msg) {
  console.log(`FALHOU: ${msg}`);
  process.exit(1);
}
let casos = 0;
function igual(obtido, esperado, descricao) {
  casos++;
  const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
  if (a !== b) falhar(`${descricao}\n  esperado: ${b}\n  obtido:   ${a}`);
}

const html = fs.readFileSync(path.join(__dirname, "..", "web", "autobatch.html"), "utf8");
const m = html.match(/<script id="logica-duplicados">([\s\S]*?)<\/script>/);
if (!m) falhar('não encontrei o <script id="logica-duplicados"> no web/autobatch.html');
const D = new Function(`${m[1]}\nreturn Duplicados;`)();

// ---------------------------------------------------------------- papel das pastas
const pp = n => { const p = D.papelDaPasta(n); return p && `${p.familia ?? "-"} ${p.acabamento}`; };
igual(pp("CA Lustre"), "CA Lustre", "pasta CA Lustre");
igual(pp("DPII Lustre"), "DPII Lustre", "pasta DPII Lustre");
igual(pp("DPII Glossy"), "DPII Brilho", "pasta DPII Glossy");
igual(pp("DPII_Seda"), "DPII Seda", "pasta DPII_Seda");
igual(pp("Crystal_Brilho"), "CA Brilho", "pasta Crystal_Brilho (Crystal Archive)");
igual(pp("00"), null, "pasta sem papel");

// ---------------------------------------------------------------- etiquetas (texto do pdf.js, dados inventados)
const etiqueta = (tipoDePapel, lista) => [
  "6500001 ", "Encomenda   6500001_1500001 - 1/2 ", "Nome:   20x30_Teste ", "DreambooksPro Express v2.0 ",
  "Item   Produtos   Acabamentos   Qtd ", "2900001   Impressão Fotográfica - Impressões - 20x30 ",
  ...tipoDePapel, "Ficheiros de:   6500001_1500001   - 20x30 ", "foto_lustre.jpg *2600000001* Lote: ",
  "WEB N∫ 6500001", "17.11.2026   Tipo: I - Impress„o ", "Cliente N∫ 100000001 ", "CLIENTE DE TESTE ",
  ...lista.map(l => `Impress„o ${l}`), "2", "21 ", "01.Encomenda LFM Express N∫ 2600000001 1/1 ",
].join("\n");
const papel = e => e.papel && `${e.papel.familia ?? "-"} ${e.papel.acabamento}`;

const e1 = D.lerEtiqueta(etiqueta(["Tipo de Papel: ", "Plastificação: ", "DPII Lustre", "Sem Plastificação", "10 "], ["10x15 CA Lustre", "10x15 CA Lustre"]));
igual(papel(e1), "DPII Lustre", "item DPII Lustre (Tipo de Papel e Plastificação em linhas à parte)");
igual(e1.conflito, true, "lista da encomenda só com CA Lustre: aviso");

const e2 = D.lerEtiqueta(etiqueta(["Tipo de Papel:   CA Lustre", "21 "], ["20x30 Lustre", "15x20 CA Lustre", "30x40 Brilho"]));
igual(papel(e2), "CA Lustre", "item CA Lustre");
igual(e2.conflito, false, "lista com CA Lustre: sem aviso");

const e3 = D.lerEtiqueta(etiqueta(["Tipo de Papel:   Lustre", "57 ", "Observações: Escola - 1ºano "], ["15x20 Lustre Schools"]));
igual(papel(e3), "- Lustre", "item Schools: só Lustre (a foto 'foto_lustre.jpg' fica de fora)");

const e4 = D.lerEtiqueta(etiqueta(["Tipo de Papel: ", "Plastificação: ", "DPII Glossy", "Sem Plastificação", "2 "], ["10x15 Brilho acima de 100 Und.", "20x30 Brilho"]));
igual(papel(e4), "DPII Brilho", "item DPII Glossy");
igual(e4.conflito, false, "Brilho na lista serve para DPII Glossy");

const e5 = D.lerEtiqueta(etiqueta(["Tipo de Papel:   DPII Silk", "3 "], ["15x20 Seda"]));
igual(papel(e5), "DPII Seda", "item DPII Silk");

const e6 = D.lerEtiqueta("texto sem campo de papel");
igual(e6.papel, null, "etiqueta sem Tipo de Papel");

// ---------------------------------------------------------------- que cópia fica
const copia = (dir, nome = "6500001_1500001_label.pdf") =>
  ({ nome, dir, pasta: dir.split("/").pop() || "00", caminho: dir ? `${dir}/${nome}` : nome });
const fica = (copias, et) => { const r = D.decidir(copias, et); return r.manter === null ? null : copias[r.manter].caminho; };

igual(fica([copia("CA Lustre"), copia("DPII Lustre")], e1), "DPII Lustre/6500001_1500001_label.pdf", "DPII Lustre fica");
igual(!!D.decidir([copia("CA Lustre"), copia("DPII Lustre")], e1).aviso, true, "com aviso da lista da encomenda");
igual(fica([copia("CA Lustre"), copia("Crystal_Brilho")], e2), "CA Lustre/6500001_1500001_label.pdf", "CA Lustre fica (Crystal_Brilho é outro acabamento)");
igual(fica([copia("CA Lustre"), copia("Crystal_Brilho"), copia("DPII Glossy")], e4), "DPII Glossy/6500001_1500001_label.pdf", "três cópias: fica DPII Glossy");
igual(fica([copia("Crystal_Brilho"), copia("DPII Glossy")], e4), "DPII Glossy/6500001_1500001_label.pdf", "DPII Glossy fica, não Crystal_Brilho");
igual(fica([copia("CA Lustre"), copia("DPII Lustre")], e3), null, "Lustre sem família em CA e DPII: por decidir");
igual(fica([copia("DPII Lustre"), copia("DPII_Seda")], e3), "DPII Lustre/6500001_1500001_label.pdf", "Lustre sem família: só uma pasta Lustre");
igual(fica([copia("CA Lustre"), copia("DPII Glossy")], e5), null, "nenhuma pasta do papel: por decidir");
igual(fica([copia("CA Lustre"), copia("DPII Lustre")], null), null, "sem etiqueta: por decidir");
igual(fica([copia("DPII Lustre", "6500001_1500001_label (1).pdf"), copia("DPII Lustre")], null),
  "DPII Lustre/6500001_1500001_label.pdf", "mesma pasta: fica o nome original, mesmo sem etiqueta");
igual(fica([copia("CA Lustre", "6500001_1500001_label - Cópia.pdf"), copia("DPII Lustre", "6500001_1500001_label - Cópia.pdf"),
  copia("DPII Lustre")], e1), "DPII Lustre/6500001_1500001_label.pdf", "duas cópias na pasta certa: fica a de nome original");

// ---------------------------------------------------------------- agrupar
const f = (dir, nome, hash, tamanho = 10) => ({ ...copia(dir, nome), hash, tamanho });
const { grupos, nomesIguais } = D.agrupar([
  f("DPII Lustre", "a.pdf", "h1"), f("CA Lustre", "a.pdf", "h1"),
  f("DPII Lustre", "b.pdf", "h2"), f("CA Lustre", "b.pdf", "h3"),
  f("DPII Lustre", "c.pdf", undefined, 99),
  f("DPII Lustre", "d.pdf", "h4"), f("CA Lustre", "outro.pdf", "h4"),
]);
igual(grupos.map(g => g.copias.map(c => c.caminho)), [["CA Lustre/a.pdf", "DPII Lustre/a.pdf"], ["CA Lustre/outro.pdf", "DPII Lustre/d.pdf"]], "grupos por conteúdo");
igual(nomesIguais.map(x => x.nome), ["b.pdf"], "mesmo nome com conteúdo diferente");

// ---------------------------------------------------------------- pastas e nomes
const lista = [f("CA Lustre", "a.pdf"), f("CA Lustre", "b.pdf"), f("Crystal_Brilho", "a.pdf"), f("", "solto.pdf")];
igual(D.resumoPastas(lista, new Set(["CA Lustre/a.pdf", "Crystal_Brilho/a.pdf"]), "00"),
  [{ pasta: "00", antes: 1, sai: 0, depois: 1 }, { pasta: "CA Lustre", antes: 2, sai: 1, depois: 1 }, { pasta: "Crystal_Brilho", antes: 1, sai: 1, depois: 0 }],
  "contagem por pasta");
igual(D.nomeAlternativo("x_label.pdf", 2), "x_label (2).pdf", "nome alternativo");
igual(D.iguais(new Uint8Array([1, 2, 3]), new Uint8Array([1, 2, 3])), true, "bytes iguais");
igual(D.iguais(new Uint8Array([1, 2, 3]), new Uint8Array([1, 2, 4])), false, "bytes diferentes");
igual(D.idDoNome("6538763_1528902_label.pdf"), "1528902", "ID do nome");

console.log(`OK: ${casos} casos`);
