// Testes da lógica do modo Duplicados: node testes/duplicados.js (na raiz do repositório)
// Extrai o <script id="logica-duplicados"> do web/autobatch.html, corre-o e confere:
//   - papel das pastas e das etiquetas (texto como o pdf.js o devolve)
//   - que cópias ficam (uma por papel da tabela, mesma pasta, por decidir)
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

// ---------------------------------------------------------------- etiquetas (linhas visuais do pdf.js, dados inventados)
// A lista do fundo ("Impress„o 10x15 CA Lustre") e a Plastificação não contam: só o "Tipo de Papel:" da tabela.
const etiqueta = (...itens) => [
  "Data entrada:  2026-11-17  11  Impress„o 10x15 CA Lustre",
  "12  Impress„o 30x40 Brilho",
  "Nome:  20x30_Teste_lustre",
  "Item  Produtos  Acabamentos  Qtd",
  ...itens.flatMap(([papel, plast]) => [
    "2900001  Impressão Fotográfica - Impressões - 20x30  10",
    `Tipo de Papel:  ${papel}`,
    ...(plast ? [`Plastificação:  ${plast}`] : []),
  ]),
  "Ficheiros de:  6500001_1500001  - 20x30",
  "foto_mate.jpg  foto_brilho.jpg",
].join("\n");
const papeis = e => e.papeis.map(p => `${p.familia ?? "-"} ${p.acabamento}`);

const e1 = D.lerEtiqueta(etiqueta(["DPII Lustre", "Sem Plastificação"]));
igual(papeis(e1), ["DPII Lustre"], "item DPII Lustre (a lista do fundo diz CA Lustre e Brilho: não conta)");
const e2 = D.lerEtiqueta(etiqueta(["CA Lustre"]));
igual(papeis(e2), ["CA Lustre"], "item CA Lustre");
const e3 = D.lerEtiqueta(etiqueta(["Lustre"]));
igual(papeis(e3), ["- Lustre"], "item Schools: só Lustre");
const e4 = D.lerEtiqueta(etiqueta(["DPII Glossy", "Sem Plastificação"]));
igual(papeis(e4), ["DPII Brilho"], "item DPII Glossy");
const e5 = D.lerEtiqueta(etiqueta(["DPII Silk"]));
igual(papeis(e5), ["DPII Seda"], "item DPII Silk");
igual(papeis(D.lerEtiqueta(etiqueta(["DPII Lustre", "Plastificação Mate"]))), ["DPII Lustre"], "Plastificação Mate não é papel");
igual(papeis(D.lerEtiqueta(etiqueta(["DPII Lustre", "Brilho"]))), ["DPII Lustre"], "Plastificação Brilho não é papel");
const e6 = D.lerEtiqueta(etiqueta(["DPII Lustre", "Sem Plastificação"], ["CA Lustre", "Sem Plastificação"], ["DPII Lustre"]));
igual(papeis(e6), ["DPII Lustre", "CA Lustre"], "tabela com vários itens: dois papéis diferentes");
igual(papeis(D.lerEtiqueta("texto sem campo de papel")), [], "etiqueta sem Tipo de Papel");
// Páginas seguintes: "Ficheiros de: … - Tipo de Papel: … - Plastificação: …" (formato real, exemplos de 2026-11-18)
igual(papeis(D.lerEtiqueta([
  "Tipo de Papel:  CA Lustre", "Correção de Cor:  Sim", "Tipo de Papel:  DPII Lustre", "Plastificação:  Sem Plastificação",
  "Ficheiros de:  6487018_2748041  - 10x15 - Tipo de Papel: CA Lustre - Correção de Cor: NONE",
  "Ficheiros de:  6487018_2748043  - 20x30 - Tipo de Papel: DPII Lustre - Plastificação: Brilho - Correção de Cor:",
  "Ficheiros de:  6487018_2748044  - 20x30 - Tipo de Papel: DPII Lustre Plastificação: Mate",
].join("\n"))), ["CA Lustre", "DPII Lustre"], "linhas Ficheiros de: a plastificação Brilho/Mate não conta");

// ---------------------------------------------------------------- que cópias ficam
const copia = (dir, nome = "6500001_1500001_label.pdf") =>
  ({ nome, dir, pasta: dir.split("/").pop() || "00", caminho: dir ? `${dir}/${nome}` : nome });
const ficam = (copias, et) => { const r = D.decidir(copias, et); return r.fica === null ? null : r.fica.map(i => copias[i].caminho); };
const L = "6500001_1500001_label.pdf";

igual(ficam([copia("CA Lustre"), copia("DPII Lustre")], e1), [`DPII Lustre/${L}`], "DPII Lustre fica");
igual(ficam([copia("CA Lustre"), copia("Crystal_Brilho")], e2), [`CA Lustre/${L}`], "CA Lustre fica (Crystal_Brilho é outro acabamento)");
igual(ficam([copia("CA Lustre"), copia("Crystal_Brilho"), copia("DPII Glossy")], e4), [`DPII Glossy/${L}`], "três cópias: fica DPII Glossy");
igual(ficam([copia("Crystal_Brilho"), copia("DPII Glossy")], e4), [`DPII Glossy/${L}`], "DPII Glossy fica, não Crystal_Brilho");
igual(ficam([copia("CA Lustre"), copia("DPII Lustre")], e3), null, "Lustre sem família em CA e DPII: por decidir");
igual(ficam([copia("DPII Lustre"), copia("DPII_Seda")], e3), [`DPII Lustre/${L}`], "Lustre sem família: só uma pasta Lustre");
igual(ficam([copia("CA Lustre"), copia("DPII Glossy")], e5), null, "nenhuma pasta do papel: por decidir");
igual(ficam([copia("CA Lustre"), copia("DPII Lustre")], null), null, "sem etiqueta: por decidir");
igual(ficam([copia("DPII Lustre", "6500001_1500001_label (1).pdf"), copia("DPII Lustre")], null),
  [`DPII Lustre/${L}`], "mesma pasta: fica o nome original, mesmo sem etiqueta");
igual(ficam([copia("CA Lustre", "6500001_1500001_label - Cópia.pdf"), copia("DPII Lustre", "6500001_1500001_label - Cópia.pdf"),
  copia("DPII Lustre")], e1), [`DPII Lustre/${L}`], "duas cópias na pasta certa: fica a de nome original");
igual(ficam([copia("CA Lustre"), copia("Crystal_Brilho"), copia("DPII Lustre")], e6), [`CA Lustre/${L}`, `DPII Lustre/${L}`],
  "vários papéis na tabela: fica uma em cada pasta desses papéis, sai a de Crystal_Brilho");
igual(ficam([copia("CA Lustre"), copia("DPII Lustre")], e6), [`CA Lustre/${L}`, `DPII Lustre/${L}`], "vários papéis: ficam todas");
igual(ficam([copia("DPII Lustre"), copia("Crystal_Brilho")], e6), [`DPII Lustre/${L}`], "vários papéis, só um com pasta: sai a outra");

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
