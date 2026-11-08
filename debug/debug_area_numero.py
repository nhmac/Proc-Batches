import pdfplumber
from PIL import ImageDraw

# Caminho do PDF para teste
PDF_PATH = "3417362_1912909_label.pdf"

# Área de captura do número
AREA_NUMERO = {
    "x0": 494,
    "x1": 500,
    "top": 230,
    "bottom": 240
}

# Tolerância em pontos PDF
TOLERANCIA = 5

with pdfplumber.open(PDF_PATH) as pdf:
    page = pdf.pages[0]
    palavras = page.extract_words() or []

    numero_encontrado = None

    # Buscar palavras dentro da área
    for p in palavras:
        if (
            AREA_NUMERO["x0"] - TOLERANCIA <= p["x0"] <= AREA_NUMERO["x1"] + TOLERANCIA
            and AREA_NUMERO["top"] - TOLERANCIA <= p["top"] <= AREA_NUMERO["bottom"] + TOLERANCIA
        ):
            print("Palavra dentro da área:", p)
            if p["text"].isdigit() and numero_encontrado is None:
                numero_encontrado = int(p["text"])

    if numero_encontrado is not None:
        print(f"Número selecionado pelo script: {numero_encontrado}")
    else:
        print("Nenhum número encontrado na área.")

    # ---------- Visualização ----------
    img = page.to_image(resolution=150)
    if numero_encontrado is not None:
        # Desenhar retângulo na área
        img.draw_rect([
            AREA_NUMERO["x0"],
            AREA_NUMERO["top"],
            AREA_NUMERO["x1"],
            AREA_NUMERO["bottom"]
        ], stroke="red", fill=None)

    # Salvar imagem de debug
    OUTPUT = "pdf_debug_numero.png"
    img.save(OUTPUT)
    print(f"Imagem de debug gerada: {OUTPUT}")
