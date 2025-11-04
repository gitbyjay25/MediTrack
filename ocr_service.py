import easyocr
import spacy
from spellchecker import SpellChecker



reader = easyocr.Reader(['en'], gpu=False)
nlp = spacy.load("en_core_web_sm")
spell = SpellChecker()

# Image path
image_path = 'ChatGPT Image Oct 31, 2025, 08_06_40 PM.png'

# OCR txt extraction
results = reader.readtext(image_path, detail=0, paragraph=True)
raw_text = " ".join(results)

# NLP
doc = nlp(raw_text)
entities = [(ent.text, ent.label_) for ent in doc.ents]

#Spll crrction
corrected_text = []
for word in raw_text.split():
    if word.isalpha():  # Only words
        corrected = spell.correction(word)
        if corrected is not None:
            corrected_text.append(corrected)
        else:
            corrected_text.append(word)
    else:
        corrected_text.append(word)
corrected_text = " ".join(corrected_text)

print("OCR Text ")
print(raw_text)
print("\n NLP Entities (Name, Designation, Address, etc.)")
for ent, label in entities:
    print(f"{ent}: {label}")
print("\n Spell-corrected Text ")
print(corrected_text)

with open('sample_output.txt', 'w', encoding='utf-8') as f:
    f.write(raw_text + "\n\nNLP Entities:\n")
    for ent, label in entities:
        f.write(f"{ent}: {label}\n")
    f.write("\nSpell-corrected Text:\n")
    f.write(corrected_text)