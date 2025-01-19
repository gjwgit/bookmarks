import json

# 20250119 gjw DIDN'T WORK

# Read the JSON file
with open('bookmarks_unified_deduped.json', 'r') as f:
    data = json.load(f)

# Sort the bookmarks by key
data['bookmarks'] = dict(sorted(data['bookmarks'].items()))

# Write the sorted data back to the file
with open('your_file.json', 'w') as f:
    json.dump(data, f, indent=2)
