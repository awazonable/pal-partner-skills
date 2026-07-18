#!/usr/bin/env python3
"""tags.json / skills.json の参照整合性チェック。
使い方: python3 docs/data/validate.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    tags = load("tags.json")
    skills = load("skills.json")["skills"]
    tagids = {t["id"] for t in tags["tags"]}
    groupids = {g["id"] for g in tags["groups"]}
    errors, warns = [], []

    for t in tags["tags"]:
        if t["group"] not in groupids:
            errors.append(f"tag {t['id']}: unknown group {t['group']}")

    seen = set()
    FACETS = ("element", "works", "status", "conditions", "categories", "tags")
    for s in skills:
        if s["id"] in seen:
            errors.append(f"duplicate skill id {s['id']}")
        seen.add(s["id"])
        for facet in FACETS:
            for tid in s.get(facet, []):
                if tid not in tagids:
                    errors.append(f"{s['id']}: unknown {facet} tag {tid}")
        for e in s.get("effects", []):
            per = e.get("perStar")
            if not isinstance(per, list) or len(per) != 5:
                errors.append(f"{s['id']}: perStar must be length 5 (label={e.get('label')})")
            elif any(v is None for v in per):
                warns.append(f"{s['id']}: perStar has a null star (source omission) label={e.get('label',{}).get('ja')}")
        if not s.get("conditions"):
            warns.append(f"{s['id']}: no condition derived ({s.get('pal',{}).get('ja')})")

    print(f"skills={len(skills)} tags={len(tags['tags'])}")
    if warns:
        print(f"warnings={len(warns)} (non-fatal; source omissions / undetected conditions)")
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("OK: all references valid")


if __name__ == "__main__":
    main()
