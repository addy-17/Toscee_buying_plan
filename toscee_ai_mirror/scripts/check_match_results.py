"""Check matching results."""
import json

with open("toscee_ai_mirror/data/inventory_with_images.json") as f:
    data = json.load(f)

print(f"Total inventory: {data['total_inventory']}")
print(f"Matched with images: {data['matched_with_image']} ({data['match_rate']}%)")
print(f"Unmatched: {data['unmatched']}")

print("\nSample matched items:")
shown = 0
for item in data["items"]:
    if item["has_image"] and shown < 10:
        print(f"  {item['article_name'][:40]:40s} -> score={item['match_score']} brand={item['matched_brand']}")
        shown += 1

print("\nSample unmatched:")
shown = 0
for item in data["items"]:
    if not item["has_image"] and shown < 5:
        print(f"  {item['article_name'][:50]}")
        shown += 1