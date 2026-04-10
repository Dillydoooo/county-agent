from datetime import datetime
from src.parsers.pdf_parser import process_all_pdfs

result = process_all_pdfs()

print(result)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"data/logs/pdf_parsing_{timestamp}.txt"

with open(filename, "w", encoding="utf-8") as f:
    f.write(result)

print(f"\nSaved log to: {filename}")