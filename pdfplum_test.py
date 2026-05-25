import pdfplumber

text = ""

with pdfplumber.open("ST_fall_syllabus.pdf") as pdf:
    for page in pdf.pages:
        extracted = page.extract_text()

        if extracted:
            text += extracted + "\n"

print(text)