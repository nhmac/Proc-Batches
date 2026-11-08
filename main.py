import os
import re
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from collections import defaultdict
import pdfplumber

import processamento_ui as ui
from processamento_ui import COR, fmt

# --- CONFIGURAÇÃO ---
AREA_NUMERO = {"x0": 494, "x1": 500, "top": 230, "bottom": 240}
TOLERANCIA = 5

# ---------------------------------------------------------------------------
# Lógica (igual ao <script id="logica"> do web/autobatch.html). Não mexe na UI.
# ---------------------------------------------------------------------------

# Tipo pelo número da encomenda (indicado pelo utilizador). Em 2026-10 iam em Dreambooks 3 477 048,
# Express 6 533 570 e Fotoprix 10 246 510. Os tipos nunca se misturam num processo.
# Cada tipo tem uma faixa larga, e não um 1.º algarismo fixo: a regra não parte quando a numeração
# passar, por exemplo, de 3 999 999 para 4 000 000. A Dreambooks e a Express sobem uns 75 000 por ano,
# a Fotoprix uns 160 000. Quando um número passa do "aviso", avisa (sem bloquear) que a faixa está a
# acabar: é a altura de mudar aqui os limites (e no TIPOS do web/autobatch.html).
TIPOS = [
    {"id": "dreambooks", "nome": "Dreambooks", "min": 1_000_000, "max": 4_999_999, "aviso": 4_900_000},
    {"id": "express", "nome": "Express", "min": 5_000_000, "max": 9_999_999, "aviso": 9_900_000},
    {"id": "fotoprix", "nome": "Fotoprix", "min": 10_000_000, "max": 99_999_999, "aviso": 99_000_000},
]
TIPO = {t["id"]: t for t in TIPOS}

# Modos do Agrupar e o limite standard de cada um
MODOS = {
    "etiquetas": {"nome": "Fotoprix + Dreambooks", "limite": 4500},
    "express": {"nome": "Express", "limite": 2300},
}


def milhares(n):
    # Espaço que não quebra: o número não se parte no fim da linha
    return fmt(n).replace(" ", " ")


def faixa(id_tipo):
    t = TIPO[id_tipo]
    return f"{milhares(t['min'])} a {milhares(t['max'])}"


def inteiro(txt):
    try:
        return int(txt)
    except (TypeError, ValueError):
        return None


def tipo_da_encomenda(num):
    s = str(num).strip()
    if not re.fullmatch(r"[0-9]+", s):
        return None
    n = int(s)
    return next((t for t in TIPOS if t["min"] <= n <= t["max"]), None)


def aviso_faixa(numeros):
    """Texto do aviso de fim de faixa (ou "" se nenhum número lá chegou)."""
    perto = {}
    for num in numeros:
        t = tipo_da_encomenda(num)
        if t and int(num) >= t["aviso"]:
            perto[t["id"]] = max(perto.get(t["id"], 0), int(num))
    return " ".join(
        f"Os números de encomenda {TIPO[i]['nome']} já vão em {milhares(n)}, perto do fim da faixa que a app "
        f"reconhece ({faixa(i)}). Pede para ajustar a regra antes que passem de {milhares(TIPO[i]['max'])}: "
        f"a partir daí estes PDFs são bloqueados."
        for i, n in perto.items())


def ler_etiqueta(palavras):
    """Etiqueta: o número que está na AREA_NUMERO. Devolve (encontrado, valor).
    Texto que não é número conta como não encontrado (senão entrava no batch como 0)."""
    for p in palavras:
        # Lógica de tolerância de coordenadas
        if (AREA_NUMERO["x0"] - TOLERANCIA <= p["x0"] <= AREA_NUMERO["x1"] + TOLERANCIA and
                AREA_NUMERO["top"] - TOLERANCIA <= p["top"] <= AREA_NUMERO["bottom"] + TOLERANCIA):
            try:
                return True, int(float(p["text"].replace(",", ".")))
            except ValueError:
                return False, 0
    return False, 0


# Folhas Express Profissional: uma página por folha, "Encomenda 6476322_1409550 - 2/3" no topo e a
# tabela Item | Produtos | Acabamentos | Qtd. A quantidade da folha é a soma da coluna Qtd.
# Páginas de continuação não têm cabeçalho: só "6476322_1409550" no canto de cima e mais fotos.
ID_FOLHA = re.compile(r"^\d+_\d+$")


def soma_qtd(ps, titulo):
    # A tabela acaba onde começam as fotos ("Ficheiros de: …")
    fim = min([p["top"] for p in ps if p["text"] == "Ficheiros" and p["x0"] < 60 and p["top"] > titulo["top"]],
              default=float("inf"))
    # Margem de 40 pt à esquerda do título: a coluna pode estar centrada
    return sum(int(p["text"]) for p in ps
               if p["x0"] >= titulo["x0"] - 40 and titulo["top"] + 4 < p["top"] < fim
               and re.fullmatch(r"\d+", p["text"]))


def folha_profissional(ps):
    """{id, continuacao, valor} da página, ou None se não for uma folha Express."""
    # "Encomenda" e o id podem vir como duas palavras ou colados numa só ("Encomenda10217361_264571")
    enc = next((p for p in ps if re.fullmatch(r"Encomenda(\d+_\d+)?", p["text"]) and p["x0"] < 60), None)
    colado = enc and re.fullmatch(r"Encomenda(\d+_\d+)", enc["text"])
    if colado:
        id_folha = colado.group(1)
    elif enc:
        id_folha = next((p["text"] for p in ps if ID_FOLHA.match(p["text"]) and abs(p["top"] - enc["top"]) < 4
                         and enc["x0"] < p["x0"] < enc["x1"] + 30), None)
    else:
        id_folha = None
    qtd = next((p for p in ps if p["text"] == "Qtd"), None)
    valor = soma_qtd(ps, qtd) if qtd else 0
    if not id_folha:
        cont = next((p for p in ps if ID_FOLHA.match(p["text"]) and p["top"] < 40), None)
        return {"id": cont["text"], "continuacao": True, "valor": valor} if cont else None
    return {"id": id_folha, "continuacao": False, "valor": valor}


def ler_folhas_express(caminho, ao_avancar=lambda x: None):
    """Modo Express: lê todas as páginas do PDF. [{id, valor, paginas}]"""
    folhas = []
    try:
        with pdfplumber.open(caminho) as pdf:
            n = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                f = folha_profissional(page.extract_words())
                if f and not f["continuacao"]:
                    folhas.append({"id": f["id"], "valor": f["valor"], "paginas": [i]})
                elif f and folhas and f["id"] == folhas[-1]["id"]:  # continuação
                    folhas[-1]["paginas"].append(i)
                    folhas[-1]["valor"] += f["valor"]
                ao_avancar(i / n)
    except Exception:
        return []
    return folhas


def extrair_etiqueta(caminho):
    """Modo Fotoprix + Dreambooks: a lógica de sempre (número na AREA_NUMERO da página 1)."""
    try:
        with pdfplumber.open(caminho) as pdf:
            return ler_etiqueta(pdf.pages[0].extract_words())
    except Exception:
        return False, 0


def calcular(caminhos, limite, progresso=lambda x, d=None: None, modo="etiquetas"):
    """caminhos: PDFs a ler. Devolve {batches, tipo, aviso, bloqueio}.

    Cada entrada dos batches: (nome, valor) nas etiquetas; (id_folha, valor, ficheiro) no Express.
    Quando os PDFs não são do modo escolhido, bloqueio = (texto, ficheiros) e nenhum batch. Regras
    (rigorosas, a pedido do utilizador):
     - Express: todos os PDFs têm de ter folhas Express e todas as encomendas têm de ser Express;
     - Fotoprix + Dreambooks: todos os PDFs com número no nome têm de ser Dreambooks ou Fotoprix, sem
       misturar os dois; e pelo menos um tem de ter o número da etiqueta.
    """
    pdfs = sorted((c for c in caminhos if c.lower().endswith(".pdf")), key=os.path.basename)
    nome = os.path.basename
    prefixo = lambda c: nome(c).split("_")[0].strip()
    bloquear = lambda texto, ficheiros: {"batches": [], "tipo": "", "aviso": "", "bloqueio": (texto, ficheiros)}
    s = lambda n, um, varios: um if n == 1 else varios
    com_numero = [c for c in pdfs if inteiro(prefixo(c)) is not None]

    # Verificação pelo nome, antes de ler qualquer PDF
    por_tipo, desconhecidos = defaultdict(list), []
    for c in com_numero:
        t = tipo_da_encomenda(prefixo(c))
        if t:
            por_tipo[t["id"]].append(nome(c))
        else:
            desconhecidos.append(nome(c))
    outros = [(i, ns) for i, ns in por_tipo.items() if (i != "express" if modo == "express" else i == "express")]
    if outros:
        lista = [f"{n} ({TIPO[i]['nome']})" for i, ns in outros for n in ns]
        if modo == "express":
            texto = (f"{len(lista)} PDF{s(len(lista), ' é', 's são')} de encomendas que não são Express. "
                     f"Muda para o modo Fotoprix + Dreambooks ou tira-os da pasta.")
        else:
            texto = (f"{len(lista)} PDF{s(len(lista), ' é', 's são')} de encomendas Express. "
                     f"Muda para o modo Express ou tira-os da pasta.")
        return bloquear(texto, lista)
    if modo != "express":
        if pdfs and not com_numero:
            return bloquear("No modo Fotoprix + Dreambooks, cada encomenda é um PDF à parte cujo nome começa pelo "
                            "número da encomenda (como na pasta das etiquetas). Nenhum destes PDFs é assim.",
                            [nome(c) for c in pdfs])
        # Desde a 1.3.3: um PDF sem o número no nome ficava de fora dos batches sem aviso
        sem_numero_nome = [nome(c) for c in pdfs if inteiro(prefixo(c)) is None]
        if sem_numero_nome:
            um = len(sem_numero_nome) == 1
            return bloquear(f"{len(sem_numero_nome)} PDF{'' if um else 's'} não começa{'' if um else 'm'} pelo número "
                            f"da encomenda e ficava{'' if um else 'm'} de fora dos batches. Confirma "
                            f"{'este ficheiro' if um else 'estes ficheiros'} ou tira-{'o' if um else 'os'} da pasta.",
                            sem_numero_nome)
        if desconhecidos:
            return bloquear(f"{len(desconhecidos)} PDF{s(len(desconhecidos), ' tem', 's têm')} um número de encomenda "
                            f"fora das faixas Dreambooks ({faixa('dreambooks')}) e Fotoprix ({faixa('fotoprix')}). "
                            f"Se a numeração de um destes tipos mudou de faixa, é preciso ajustar a regra.",
                            desconhecidos)
        if "dreambooks" in por_tipo and "fotoprix" in por_tipo:
            return bloquear("A pasta mistura encomendas Dreambooks e Fotoprix. Processa cada uma à parte.",
                            [f"{n} (Dreambooks)" for n in por_tipo["dreambooks"]] +
                            [f"{n} (Fotoprix)" for n in por_tipo["fotoprix"]])

    # Agrupar por número da encomenda
    grupos = defaultdict(list)
    sem_folhas, nao_express, sem_numero = [], [], []
    lidos = 0
    n = len(pdfs)
    for i, c in enumerate(pdfs):
        # Antes de ler: diz qual é o PDF; depois: a barra avança
        progresso(i / n, f"{fmt(i + 1)} de {fmt(n)} PDFs · {nome(c)}")
        if modo == "express":
            folhas = ler_folhas_express(c, lambda x, i=i: progresso((i + x) / n))
            if not folhas:
                sem_folhas.append(nome(c))
            for fl in folhas:
                enc = fl["id"].split("_")[0]
                t = tipo_da_encomenda(enc)
                if not t or t["id"] != "express":
                    nao_express.append(f"{nome(c)} · {fl['id']} ({t['nome'] if t else 'tipo desconhecido'})")
                    continue
                grupos[int(enc)].append((fl["id"], fl["valor"], nome(c)))
        else:
            id_g = inteiro(prefixo(c))
            if id_g is not None:
                encontrado, valor = extrair_etiqueta(c)
                lidos += 1
                if not encontrado:
                    sem_numero.append(nome(c))
                grupos[id_g].append((nome(c), valor))
        progresso((i + 1) / n)

    # Verificação pelo conteúdo
    if modo == "express" and (sem_folhas or nao_express):
        partes = []
        if sem_folhas:
            partes.append(f"{len(sem_folhas)} PDF{s(len(sem_folhas), ' não tem', 's não têm')} folhas Express")
        if nao_express:
            partes.append(f"{len(nao_express)} folha{s(len(nao_express), ' é', 's são')} de encomendas que não são Express")
        return bloquear(f"{' e '.join(partes)}. Confirma o modo ou tira estes ficheiros da pasta.",
                        [f"{x} (sem folhas Express)" for x in sem_folhas] + nao_express)
    if modo != "express" and lidos and len(sem_numero) == lidos:
        return bloquear("Nenhum destes PDFs tem o número da etiqueta Fotoprix / Dreambooks. Confirma o modo.", sem_numero)
    if modo != "express" and sem_numero:
        um = len(sem_numero) == 1
        return bloquear(f"{len(sem_numero)} PDF{' não tem' if um else 's não têm'} o número da quantidade na etiqueta "
                        f"(não foi possível lê-lo). Ia{'' if um else 'm'} entrar no batch como 0, e o batch podia passar "
                        f"o limite. Confirma {'este ficheiro' if um else 'estes ficheiros'} ou tira-{'o' if um else 'os'} da pasta.",
                        sem_numero)
    tipo = ("Express" if modo == "express" else "Fotoprix" if "fotoprix" in por_tipo
            else "Dreambooks" if "dreambooks" in por_tipo else "")

    # Criar batches (dentro de cada encomenda, por ordem de nome)
    batches, atual, soma = [], [], 0
    for g in sorted(grupos):
        itens = sorted(grupos[g], key=lambda x: x[0])
        total_g = sum(x[1] for x in itens)
        if soma + total_g > limite and atual:
            batches.append(atual)
            atual, soma = [], 0
        atual.extend(itens)
        soma += total_g
    if atual:
        batches.append(atual)
    numeros = list(grupos) if modo == "express" else [prefixo(c) for c in com_numero]
    return {"batches": batches, "tipo": tipo, "aviso": aviso_faixa(numeros), "bloqueio": None}


# ---------------------------------------------------------------------------
# Janela
# ---------------------------------------------------------------------------
class AutoBatchApp(ctk.CTk):
    def __init__(self):
        ui.preparar()
        super().__init__()

        # Configuração da Janela
        ui.configurar_janela(self, "Processamento · Auto-Batch")
        self.f = ui.criar_fontes(self)

        self.caminhos = []
        self.modo = "etiquetas"
        self.setup_ui()

    # ------------------------------------------------------------------ UI --
    def setup_ui(self):
        # Sidebar
        self.sidebar = ui.sidebar(self)
        ui.cabecalho_sidebar(self.sidebar, self.f, "AutoBatch", "Batches por limite de quantidade")

        # Secção: Tipo de encomendas (nunca se misturam: escolhe-se antes de cada processo)
        ui.label_secao(self.sidebar, self.f, "TIPO DE ENCOMENDAS").pack(anchor="w", padx=24, pady=(32, 8))
        nomes = [m["nome"] for m in MODOS.values()]
        self.seg_modo = ctk.CTkSegmentedButton(
            self.sidebar, values=nomes, command=self.mudar_modo, font=self.f["pequeno_b"], height=34,
            fg_color=COR["sub"], selected_color=COR["card"], selected_hover_color=COR["card_hover"],
            unselected_color=COR["sub"], unselected_hover_color=COR["card_hover"], text_color=COR["texto"])
        self.seg_modo.set(MODOS["etiquetas"]["nome"])
        self.seg_modo.pack(padx=24, fill="x")

        # Secção: Pasta ou PDF
        ui.label_secao(self.sidebar, self.f, "PASTA OU PDF").pack(anchor="w", padx=24, pady=(28, 8))

        self.btn_folder = ui.botao_secundario(self.sidebar, self.f, "Escolher pasta…", self.escolher_pasta)
        self.btn_folder.pack(padx=24, fill="x")
        self.btn_pdf = ui.botao_secundario(self.sidebar, self.f, "Escolher PDF…", self.escolher_pdfs)
        self.btn_pdf.pack(padx=24, pady=(8, 0), fill="x")

        chip = ui.chip(self.sidebar)
        chip.pack(padx=24, pady=(10, 0), fill="x")
        self.lbl_pasta = ctk.CTkLabel(chip, text="Nenhuma pasta ou PDF selecionado", font=self.f["corpo"],
                                      text_color=COR["texto_sec"], wraplength=210, justify="left", anchor="w")
        self.lbl_pasta.pack(anchor="w", fill="x", padx=12, pady=8)
        # Só aparece depois de escolher a pasta
        self.lbl_npdfs = ctk.CTkLabel(chip, text="", font=self.f["pequeno"], text_color=COR["texto_sec"],
                                      anchor="w")

        # Secção: Limite (fica no standard de cada modo, como na web)
        ui.label_secao(self.sidebar, self.f, "LIMITE DO BATCH").pack(anchor="w", padx=24, pady=(28, 8))
        self.entry_limite = ctk.CTkEntry(self.sidebar, justify="center", height=40, font=self.f["corpo_b"],
                                         fg_color=COR["sub"], border_color=COR["borda"], text_color=COR["texto"])
        self.entry_limite.pack(padx=24, fill="x")
        self._por_limite()

        self.btn_run = ui.botao_principal(self.sidebar, self.f, "Processar PDFs", self.start_thread)
        self.btn_run.pack(side="bottom", pady=24, padx=24, fill="x")

        # Área Central
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=28, pady=(24, 16))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="Batches", font=self.f["titulo"], text_color=COR["texto"]).pack(side="left")
        self.lbl_modo = ctk.CTkLabel(header, text="", font=self.f["titulo"], text_color=COR["texto_sec"])
        self.lbl_modo.pack(side="left", padx=(8, 0))
        self.status_lbl = ctk.CTkLabel(header, text="", font=self.f["corpo"])
        self.status_lbl.pack(side="right")
        self.set_status("Pronto para iniciar")
        self._pintar_modo()

        self.progress = ui.Progresso(self.main_frame, self.f, self)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.progress.grid_remove()

        # Resumo
        self.resumo = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.resumo.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self.resumo.grid_columnconfigure((0, 1, 2), weight=1, uniform="stat")
        self.stat_pdfs = ui.stat_tile(self.resumo, self.f, 0, "PDFs lidos")
        self.stat_batches = ui.stat_tile(self.resumo, self.f, 1, "Batches")
        self.stat_total = ui.stat_tile(self.resumo, self.f, 2, "Total geral")
        self.resumo.grid_remove()

        self.scroll_batches = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent",
                                                     scrollbar_button_color=COR["card"],
                                                     scrollbar_button_hover_color=COR["card_hover"])
        self.scroll_batches.grid(row=3, column=0, sticky="nsew", pady=(16, 0))

        self._mostrar_empty_state()

    def _mostrar_empty_state(self, texto="Escolhe uma pasta ou um PDF e clica em Processar PDFs"):
        ctk.CTkLabel(self.scroll_batches, text=texto, font=self.f["corpo"], text_color=COR["texto_sec"]).pack(pady=120)

    def _limpar_lista(self):
        for child in self.scroll_batches.winfo_children():
            child.destroy()

    def _por_limite(self):
        self.entry_limite.configure(state="normal")
        self.entry_limite.delete(0, "end")
        self.entry_limite.insert(0, str(MODOS[self.modo]["limite"]))
        self.entry_limite.configure(state="disabled", text_color=COR["texto_sec"])

    def _pintar_modo(self):
        self.lbl_modo.configure(text=f"· {MODOS[self.modo]['nome']}")

    def set_status(self, texto, tipo="idle"):
        ui.definir_estado(self.status_lbl, texto, tipo)

    def _set_ocupado(self, ocupado):
        ui.botao_ocupado(self.btn_run, ocupado, "Processar PDFs", "A processar…")
        estado = "disabled" if ocupado else "normal"
        self.btn_folder.configure(state=estado)
        self.btn_pdf.configure(state=estado)
        self.seg_modo.configure(state=estado)

    # -------------------------------------------------------------- Ações --
    def mudar_modo(self, nome):
        modo = next(k for k, m in MODOS.items() if m["nome"] == nome)
        if modo == self.modo:
            return
        self.modo = modo
        self._pintar_modo()
        self._por_limite()
        # Resultados do outro modo deixam de valer
        self._limpar_lista()
        self.resumo.grid_remove()
        self._mostrar_empty_state()
        self.set_status("Pronto para iniciar")

    def _definir(self, caminhos, rotulo):
        self.caminhos = caminhos
        self.lbl_pasta.configure(text=rotulo, text_color=COR["texto"])
        n = len([c for c in caminhos if c.lower().endswith(".pdf")])
        self.lbl_npdfs.configure(text=f"{n} PDF{'s' if n != 1 else ''} encontrado{'s' if n != 1 else ''}")
        self.lbl_pasta.pack_configure(pady=(8, 0))
        self.lbl_npdfs.pack(anchor="w", fill="x", padx=12, pady=(0, 8))

    def escolher_pasta(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self._definir([os.path.join(pasta, f) for f in os.listdir(pasta)], os.path.basename(pasta))

    def escolher_pdfs(self):
        # Um ou mais PDFs (ex.: um PDF com várias encomendas Express Profissional)
        lista = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if lista:
            self._definir(list(lista), os.path.basename(lista[0]) if len(lista) == 1 else f"{len(lista)} ficheiros")

    def start_thread(self):
        if not self.caminhos:
            messagebox.showwarning("Aviso", "Escolhe uma pasta ou um PDF primeiro!")
            return
        limite = inteiro(self.entry_limite.get())
        if limite is None:
            self.set_status("Limite inválido", "erro")
            return

        # Limpar UI anterior
        self._limpar_lista()
        self.resumo.grid_remove()
        self.progress.iniciar("A preparar…")
        self._set_ocupado(True)
        self.set_status("A ler os PDFs…", "ativo")

        threading.Thread(target=self.executar_logica, args=(limite, self.modo), daemon=True).start()

    def executar_logica(self, limite, modo):
        # Corre numa thread: todas as alterações à UI passam por self.after
        try:
            res = calcular(self.caminhos, limite,
                           lambda x, d=None: self.after(0, self.progress.atualizar, x, d), modo)
            if res["bloqueio"]:
                self.after(0, self.mostrar_bloqueio, *res["bloqueio"])
            else:
                self.after(0, self.mostrar_resultado, res, limite)
        except Exception as e:
            self.after(0, self.mostrar_erro, str(e))

    def mostrar_bloqueio(self, texto, ficheiros):
        self.progress.concluir(False, "Bloqueado: os PDFs não correspondem ao modo escolhido")
        self._set_ocupado(False)
        self.set_status("Bloqueado: nenhum batch foi criado.", "erro")
        card = ui.card(self.scroll_batches, border_color=COR["erro"])
        card.pack(fill="x", pady=6, padx=(0, 8))
        ctk.CTkLabel(card, text="Processo bloqueado", font=self.f["corpo_b"], text_color=COR["erro"],
                     anchor="w").pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(card, text=texto, font=self.f["corpo"], text_color=COR["texto"], wraplength=640,
                     justify="left", anchor="w").pack(fill="x", padx=16, pady=(6, 8))
        lista = ctk.CTkFrame(card, fg_color=COR["sub"], corner_radius=6)
        lista.pack(fill="x", padx=16, pady=(0, 14))
        MAX = 200
        linhas = ficheiros[:MAX] + ([f"… e mais {len(ficheiros) - MAX}"] if len(ficheiros) > MAX else [])
        for j, n in enumerate(linhas):
            ctk.CTkLabel(lista, text=n, font=self.f["mono"], text_color=COR["texto"], anchor="w",
                         fg_color=COR["linha_alt"] if j % 2 else "transparent", corner_radius=4).pack(
                fill="x", padx=6, pady=(6 if j == 0 else 0, 6 if j == len(linhas) - 1 else 0))

    def mostrar_resultado(self, res, limite):
        batches = res["batches"]
        self.progress.concluir(True)
        self._set_ocupado(False)

        folhas = any(len(x) > 2 for b in batches for x in b)
        self.stat_pdfs.configure(text=fmt(sum(len(b) for b in batches)))
        self.stat_batches.configure(text=fmt(len(batches)))
        self.stat_total.configure(text=fmt(sum(x[1] for b in batches for x in b)))
        self.resumo.grid()

        if not batches:
            self._mostrar_empty_state(
                "Nenhuma folha Express encontrada. Confirma que escolheste o PDF certo e o modo Express."
                if self.modo == "express" else "Nenhum PDF com número no nome. Escolhe outra pasta.")
        # Aviso de fim de faixa dos números de encomenda (não bloqueia)
        if res["aviso"]:
            card = ui.card(self.scroll_batches, border_color=COR["aviso"])
            card.pack(fill="x", pady=6, padx=(0, 8))
            ctk.CTkLabel(card, text="Atenção: numeração perto do limite", font=self.f["corpo_b"],
                         text_color=COR["aviso"], anchor="w").pack(fill="x", padx=16, pady=(14, 0))
            ctk.CTkLabel(card, text=res["aviso"], font=self.f["corpo"], text_color=COR["texto"], wraplength=640,
                         justify="left", anchor="w").pack(fill="x", padx=16, pady=(6, 14))
        # Renderizar na UI
        for i, b in enumerate(batches, 1):
            self.criar_card_batch(i, b, limite, folhas)

        n = len(batches)
        tipo = f" {res['tipo']}" if res["tipo"] else ""
        self.set_status(f"Concluído: {n} batch{'es' if n != 1 else ''}{tipo} criado{'s' if n != 1 else ''}.", "ok")

    def mostrar_erro(self, msg):
        self.progress.concluir(False)
        self._set_ocupado(False)
        self.set_status(f"Erro: {msg}", "erro")

    # ---------------------------------------------------------------- Card --
    def criar_card_batch(self, index, dados, limite, folhas=False):
        total = sum(x[1] for x in dados)
        ocupacao = total / limite if limite > 0 else 0
        if ocupacao > 1:
            cor_barra = COR["erro"]
        elif ocupacao >= 0.9:
            cor_barra = COR["aviso"]
        else:
            cor_barra = COR["sucesso"]
        unidade = ("folha", "folhas") if folhas else ("ficheiro", "ficheiros")
        ver, ocultar = ("Ver folhas", "Ocultar folhas") if folhas else ("Ver ficheiros", "Ocultar ficheiros")

        card = ui.card(self.scroll_batches)
        card.pack(fill="x", pady=6, padx=(0, 8))

        # Resumo
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 0))

        ui.pill(header, self.f, f"BATCH {index}").pack(side="left")
        ctk.CTkLabel(header, text=f" / {fmt(limite)}", font=self.f["corpo"], text_color=COR["texto_sec"]).pack(
            side="right")
        ctk.CTkLabel(header, text=fmt(total), font=self.f["corpo_b"], text_color=COR["texto"]).pack(side="right")

        # Ocupação
        barra_row = ctk.CTkFrame(card, fg_color="transparent")
        barra_row.pack(fill="x", padx=16, pady=(10, 0))
        ctk.CTkLabel(barra_row, text=f"{ocupacao:.0%}", font=self.f["pequeno_b"], text_color=cor_barra,
                     width=48, anchor="e").pack(side="right")
        barra = ui.barra(barra_row, cor_barra)
        barra.set(min(ocupacao, 1))
        barra.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Início e Fim
        n = len(dados)
        intervalo = dados[0][0] if n == 1 else f"{dados[0][0]}  →  {dados[-1][0]}"
        ctk.CTkLabel(card, text=f"{n} {unidade[0] if n == 1 else unidade[1]}  ·  {intervalo}",
                     font=self.f["pequeno"], text_color=COR["texto_sec"], anchor="w").pack(
            fill="x", padx=16, pady=(6, 0))

        # Dropdown
        detalhe_frame = ctk.CTkFrame(card, fg_color=COR["sub"], corner_radius=6)

        def preencher():
            for j, item in enumerate(dados):
                nome, valor = item[0], item[1]
                linha = ctk.CTkFrame(detalhe_frame, corner_radius=4, height=26,
                                     fg_color=COR["linha_alt"] if j % 2 else "transparent")
                linha.pack(fill="x", padx=6, pady=(6 if j == 0 else 0, 6 if j == n - 1 else 0))
                destaque = valor > 1000
                ctk.CTkLabel(linha, text=nome, font=self.f["mono"], text_color=COR["texto"], height=26,
                             anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(linha, text=fmt(valor), font=self.f["mono_b"] if destaque else self.f["mono"],
                             text_color=COR["accent_texto"] if destaque else COR["texto_sec"], height=26).pack(
                    side="right", padx=8)

        def toggle():
            if detalhe_frame.winfo_manager():
                detalhe_frame.pack_forget()
                btn_show.configure(text=f"▸  {ver}")
            else:
                if not detalhe_frame.winfo_children():
                    preencher()
                detalhe_frame.pack(fill="x", padx=16, pady=(0, 14))
                btn_show.configure(text=f"▾  {ocultar}")

        btn_show = ui.botao_link(card, self.f, f"▸  {ver}", toggle)
        btn_show.pack(anchor="w", padx=10, pady=(6, 10))


if __name__ == "__main__":
    app = AutoBatchApp()
    app.mainloop()
