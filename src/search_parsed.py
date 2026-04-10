import os

PARSED_FOLDER = "data/parsed"

def search_keyword(keyword):
    keyword_lower = keyword.lower()
    matches = []

    if not os.path.exists(PARSED_FOLDER):
        return f"Folder not found: {PARSED_FOLDER}"

    for filename in os.listdir(PARSED_FOLDER):
        if not filename.lower().endswith(".txt"):
            continue

        filepath = os.path.join(PARSED_FOLDER, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_number, line in enumerate(lines, start=1):
                if keyword_lower in line.lower():
                    start = max(0, line_number - 3)
                    end = min(len(lines), line_number + 2)
                    context = "".join(lines[start:end]).strip()

                    matches.append({
                        "filename": filename,
                        "line_number": line_number,
                        "context": context
                    })

        except Exception as e:
            matches.append({
                "filename": filename,
                "line_number": "-",
                "context": f"ERROR READING FILE: {e}"
            })

    if not matches:
        return f'No matches found for: {keyword}'

    output = [f'Search results for: "{keyword}"', "-" * 60]

    for match in matches:
        output.append(f"File: {match['filename']}")
        output.append(f"Line: {match['line_number']}")
        output.append("Context:")
        output.append(match["context"])
        output.append("-" * 60)

    return "\n".join(output)