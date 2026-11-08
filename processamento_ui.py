"""
Tema e componentes comuns da linha de apps "Processamento".

Cópia idêntica em cada app (Processamento_Batches, Álbuns amador,
Processamento_PDF Scanner). Uma alteração aqui faz-se em todas as cópias,
e sobe o VERSAO_UI.

Regras da linha
    - customtkinter em dark mode, fonte Inter incluída na app (pasta Inter/static)
    - sidebar à esquerda (280 px, padx=24): título, subtítulo, secções com o
      título em MAIÚSCULAS (label_secao) e o botão de ação principal, verde,
      fixo no fundo (botao_principal)
    - área principal: título à esquerda e estado à direita (definir_estado),
      barra de progresso fina por baixo (Progresso), só visível enquanto trabalha,
      com uma legenda: o ficheiro ou a folha à esquerda, a % e o tempo que falta à
      direita; verde com "Concluído em …" no fim, antes de recolher (desde a 1.1)
    - cards com corner_radius=10 e borda de 1 px (card); chips para valores
      escolhidos (chip); empty state em texto_sec quando não há resultados
    - pop-ups só para avisos e erros, nunca para sucesso
"""

import os
import sys
import time
import customtkinter as ctk
from tkinter import font as tkfont

VERSAO_UI = "1.1"

COR = {
    "bg": "#15171c",
    "sidebar": "#1c1f26",
    "card": "#232730",
    "card_hover": "#2b303b",
    "sub": "#1a1d23",
    "linha_alt": "#20242c",
    "borda": "#323845",
    "texto": "#f1f3f7",
    "texto_sec": "#a4acbb",
    "texto_feito": "#6b7280",
    "accent": "#4c8dff",
    "accent_hover": "#3a78e8",
    "accent_texto": "#7fb0ff",
    "accent_suave": "#1f3358",
    "sucesso": "#1f9d5a",
    "sucesso_hover": "#1a8550",
    "sucesso_texto": "#5fd49a",
    "sucesso_suave": "#16392a",
    "aviso": "#e0a526",
    "erro": "#e5484d",
    "trilho": "#2f3542",
    # Papel autocolante do Separador: o destaque mais forte, é o que custa dinheiro se for trocado
    "etiqueta_fundo": "#3d2f0c",
    "etiqueta_texto": "#ffd166",
    "etiqueta_borda": "#7a5a12",
}


def caminho_recurso(nome):
    # No .exe (PyInstaller) os ficheiros incluídos ficam em sys._MEIPASS
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nome)


# Fontes Inter incluídas no projeto (pasta Inter/static), carregadas só para esta app
FONTES = ["Inter_18pt-Regular.ttf", "Inter_18pt-SemiBold.ttf", "Inter_24pt-SemiBold.ttf"]


def carregar_fontes():
    for nome in FONTES:
        try:
            ctk.FontManager.windows_load_font(caminho_recurso(os.path.join("Inter", "static", nome)),
                                              private=True, enumerable=True)
        except Exception:
            pass  # sem a fonte, familia escolhe a alternativa do sistema


def preparar():
    """Chamar antes de criar a janela."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    carregar_fontes()


def fmt(n):
    return f"{n:,}".replace(",", " ")


def familia(widget, *opcoes):
    disponiveis = set(tkfont.families(widget))
    return next((f for f in opcoes if f in disponiveis), opcoes[-1])


def criar_fontes(janela):
    """CTkFont só pode ser criado depois de existir a janela.
    Inter (incluída na app); se falhar, Segoe UI Variable (Windows 11) ou Segoe UI (Windows 10)."""
    display_sb = familia(janela, "Inter 24pt SemiBold", "Segoe UI Variable Display Semib", "Segoe UI Semibold")
    texto = familia(janela, "Inter 18pt", "Segoe UI Variable Text", "Segoe UI")
    texto_sb = familia(janela, "Inter 18pt SemiBold", "Segoe UI Variable Text Semibold", "Segoe UI Semibold")
    # Listas de ficheiros: Cascadia Mono (Windows 11) ou Consolas
    mono = familia(janela, "Cascadia Mono", "Consolas")
    mono_sb = familia(janela, "Cascadia Mono SemiBold", "Consolas")
    return {
        "display": ctk.CTkFont(display_sb, 32),
        "titulo": ctk.CTkFont(display_sb, 24),
        "stat": ctk.CTkFont(display_sb, 28),
        "secao": ctk.CTkFont(texto_sb, 12),
        "corpo": ctk.CTkFont(texto, 14),
        "corpo_b": ctk.CTkFont(texto_sb, 14),
        "pequeno": ctk.CTkFont(texto, 13),
        "pequeno_b": ctk.CTkFont(texto_sb, 13),
        "botao": ctk.CTkFont(texto_sb, 15),
        "mono": ctk.CTkFont(mono, 13),
        "mono_b": ctk.CTkFont(mono_sb, 13, "bold" if mono_sb == "Consolas" else "normal"),
    }


def configurar_janela(janela, titulo, geometria="1000x700", minimo=(820, 560)):
    janela.title(titulo)
    janela.geometry(geometria)
    janela.minsize(*minimo)
    janela.configure(fg_color=COR["bg"])
    try:
        janela.iconbitmap(caminho_recurso("icone.ico"))
    except Exception:
        pass  # sem ícone a aplicação funciona à mesma


# --------------------------------------------------------------- Componentes --

def sidebar(janela):
    """Coluna 0 da janela; a área principal vai na coluna 1."""
    janela.grid_columnconfigure(1, weight=1)
    janela.grid_rowconfigure(0, weight=1)
    barra_lateral = ctk.CTkFrame(janela, width=280, corner_radius=0, fg_color=COR["sidebar"])
    barra_lateral.grid(row=0, column=0, sticky="nsew")
    barra_lateral.pack_propagate(False)
    return barra_lateral


def cabecalho_sidebar(barra_lateral, f, titulo, subtitulo):
    ctk.CTkLabel(barra_lateral, text=titulo, font=f["titulo"], text_color=COR["texto"]).pack(
        anchor="w", padx=24, pady=(28, 0))
    ctk.CTkLabel(barra_lateral, text=subtitulo, font=f["pequeno"], text_color=COR["texto_sec"]).pack(
        anchor="w", padx=24)


def label_secao(master, f, texto):
    return ctk.CTkLabel(master, text=texto, font=f["secao"], text_color=COR["texto_sec"])


def botao_secundario(master, f, texto, comando, **kw):
    opcoes = dict(height=40, font=f["corpo"], fg_color=COR["card"], hover_color=COR["card_hover"],
                  border_width=1, border_color=COR["borda"], text_color=COR["texto"])
    opcoes.update(kw)
    return ctk.CTkButton(master, text=texto, command=comando, **opcoes)


def botao_principal(master, f, texto, comando, **kw):
    opcoes = dict(height=42, font=f["botao"], fg_color=COR["sucesso"], hover_color=COR["sucesso_hover"],
                  text_color="#ffffff")
    opcoes.update(kw)
    return ctk.CTkButton(master, text=texto, command=comando, **opcoes)


def botao_link(master, f, texto, comando, **kw):
    opcoes = dict(height=30, width=0, font=f["pequeno"], fg_color="transparent", hover_color=COR["card_hover"],
                  text_color=COR["accent_texto"], anchor="w")
    opcoes.update(kw)
    return ctk.CTkButton(master, text=texto, command=comando, **opcoes)


def botao_ocupado(botao, ocupado, texto, texto_ocupado, cor=COR["sucesso"]):
    """Botão de ação principal enquanto a app trabalha: desativado e a cinzento."""
    botao.configure(state="disabled" if ocupado else "normal", text=texto_ocupado if ocupado else texto,
                    fg_color=COR["card"] if ocupado else cor)


def chip(master):
    return ctk.CTkFrame(master, fg_color=COR["sub"], corner_radius=8)


def card(master, **kw):
    opcoes = dict(fg_color=COR["card"], corner_radius=10, border_width=1, border_color=COR["borda"])
    opcoes.update(kw)
    return ctk.CTkFrame(master, **opcoes)


def pill(master, f, texto, fundo=COR["accent_suave"], cor=COR["accent_texto"], **kw):
    opcoes = dict(font=f["secao"], text_color=cor, fg_color=fundo, corner_radius=6, height=28)
    opcoes.update(kw)
    return ctk.CTkLabel(master, text=f"  {texto}  ", **opcoes)


def stat_tile(master, f, col, titulo, n_cols=3):
    """Devolve o rótulo do valor."""
    tile = card(master)
    tile.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == n_cols - 1 else 6))
    valor = ctk.CTkLabel(tile, text="0", font=f["stat"], text_color=COR["texto"], anchor="w")
    valor.pack(anchor="w", padx=16, pady=(12, 0))
    ctk.CTkLabel(tile, text=titulo, font=f["pequeno"], text_color=COR["texto_sec"], anchor="w").pack(
        anchor="w", padx=16, pady=(0, 12))
    return valor


def barra(master, cor=COR["accent"]):
    return ctk.CTkProgressBar(master, height=6, corner_radius=3, fg_color=COR["trilho"], progress_color=cor)


def _tempo(s):
    if s < 60:
        return f"{max(1, round(s))} s"
    r = round(s / 5) * 5
    return f"{r // 60} min {r % 60} s" if r % 60 else f"{r // 60} min"


def _pct(x):
    return f"{int(x * 100)} %"


class Progresso(ctk.CTkFrame):
    """Barra de progresso com legenda, igual à da web (criarProgresso nos web/*.html).

    A barra fina e, por baixo, o que está a fazer à esquerda e a percentagem e o tempo que
    falta à direita. Fica na grelha onde for posta e só aparece enquanto trabalha:
        iniciar(detalhe)       mostra-a, numa fase sem medida
        fase(detalhe)          fase sem medida (abrir, conferir): a barra anda de um lado ao outro
        atualizar(x, detalhe)  põe-na em x, de 0 a 1; sem detalhe fica o anterior
        concluir(ok, detalhe)  verde (ou vermelha) e recolhe-se passados 1,5 s
    Chamar só no thread da janela (com after ou pela fila). O título da janela mostra a %.
    """

    MAX_DETALHE = 90  # o CTkLabel não corta com reticências: corta-se aqui

    def __init__(self, master, f, janela):
        super().__init__(master, fg_color="transparent")
        self.janela = janela
        self.barra = barra(self)
        self.barra.set(0)
        self.barra.pack(fill="x")
        legenda = ctk.CTkFrame(self, fg_color="transparent")
        legenda.pack(fill="x", pady=(6, 0))
        self.lbl_valor = ctk.CTkLabel(legenda, text="", font=f["pequeno"], text_color=COR["texto_sec"], height=18)
        self.lbl_valor.pack(side="right")
        self.lbl_detalhe = ctk.CTkLabel(legenda, text="", font=f["pequeno"], text_color=COR["texto_sec"],
                                        height=18, anchor="w")
        self.lbl_detalhe.pack(side="left", fill="x", expand=True, padx=(0, 16))
        self.titulo_base = None
        self._a_deslizar = False
        self._saida = None
        self._t0 = self._base = self._falta = None
        self._ultimo = 0

    def _detalhe(self, texto):
        if len(texto) > self.MAX_DETALHE:
            texto = texto[:self.MAX_DETALHE - 1] + "…"
        self.lbl_detalhe.configure(text=texto)

    def _cores(self, barra_cor, texto_cor):
        self.barra.configure(progress_color=barra_cor)
        self.lbl_detalhe.configure(text_color=texto_cor)
        self.lbl_valor.configure(text_color=texto_cor)

    def _deslizar(self, sim):
        if sim and not self._a_deslizar:
            self.barra.configure(mode="indeterminate")
            self.barra.start()
        elif not sim and self._a_deslizar:
            self.barra.stop()
            self.barra.configure(mode="determinate")
        self._a_deslizar = sim

    def iniciar(self, detalhe=""):
        if self._saida:
            self.after_cancel(self._saida)
            self._saida = None
        if self.titulo_base is None:
            self.titulo_base = self.janela.title()
        self._cores(COR["accent"], COR["texto_sec"])
        self._t0 = time.monotonic()
        self.barra.set(0)
        self.grid()
        self.fase(detalhe)

    def fase(self, detalhe):
        self._base = self._falta = None
        self._detalhe(detalhe)
        self.lbl_valor.configure(text="")
        self._deslizar(True)
        if self.titulo_base is not None:
            self.janela.title(self.titulo_base)  # sem medida não há % para mostrar

    def atualizar(self, x, detalhe=None):
        agora = time.monotonic()
        x = min(1.0, max(0.0, x))
        self._deslizar(False)
        self.barra.set(x)
        if detalhe is not None:
            self._detalhe(detalhe)
        if self._base is None:
            self._base, self._falta = (agora, x), None
        passou, feito = agora - self._base[0], x - self._base[1]
        if passou >= 1.5 and x >= 0.05 and feito > 0:
            estimativa = passou * (1 - x) / feito
            # Média móvel, descontando o tempo desde a última estimativa: o número não salta
            self._falta = estimativa if self._falta is None else \
                0.6 * max(0.0, self._falta - (agora - self._ultimo)) + 0.4 * estimativa
            self._ultimo = agora
        falta = self._falta
        self.lbl_valor.configure(text=f"{_pct(x)} · ~{_tempo(falta)}" if falta is not None and falta >= 2 else _pct(x))
        self.janela.title(f"{_pct(x)} · {self.titulo_base}")

    def concluir(self, ok=True, detalhe=None):
        self._deslizar(False)
        self.barra.set(1)
        if ok:
            self._cores(COR["sucesso"], COR["sucesso_texto"])
            self.lbl_valor.configure(text="100 %")
            self._detalhe(detalhe or f"Concluído em {_tempo(time.monotonic() - (self._t0 or time.monotonic()))}")
        else:
            self._cores(COR["erro"], COR["erro"])
            self.lbl_valor.configure(text="")
            self._detalhe(detalhe or "Interrompido")
        if self.titulo_base is not None:
            self.janela.title(self.titulo_base)
        if self._saida:
            self.after_cancel(self._saida)
        self._saida = self.after(1500, self._recolher)

    def _recolher(self):
        self._saida = None
        self.grid_remove()


def cor_estado(tipo):
    return {"idle": COR["texto_sec"], "ativo": COR["accent_texto"], "ok": COR["sucesso"], "erro": COR["erro"]}[tipo]


def definir_estado(label, texto, tipo="idle"):
    label.configure(text=texto, text_color=cor_estado(tipo))
