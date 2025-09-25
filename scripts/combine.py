import json

# Load components
with open("../data/radicals.json", "r", encoding="utf-8") as f:
    components = json.load(f)

# Pick one semantic + one phonetic
semantic = components[0]   # 氵
phonetic = components[1]   # 青

# Generate a fake "IDS" string to represent the new character
ids = f"⿰{semantic['id']}{phonetic['id']}"

print("Generated character structure:", ids)
print("Meaning hint:", f"{semantic['meaning']} + {phonetic['meaning']}")
print("Sound hint:", phonetic['common_readings'][0])
