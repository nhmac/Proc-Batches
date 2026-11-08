import pdfplumber

with pdfplumber.open("3417426_1913076_label.pdf") as pdf:
    page = pdf.pages[0]
    for p in page.extract_words():
        print(p)


