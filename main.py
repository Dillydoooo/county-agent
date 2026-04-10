from src.search_parsed import search_keyword

keyword = input("Enter keyword to search: ").strip()
result = search_keyword(keyword)

print()
print(result)