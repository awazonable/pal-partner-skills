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
    skills = load("skills.json")
    tagids = {t["id"] for t in tags["tags"]}
    groupids = {g["id"] for g in tags["groups"]}
    errors = []

    for t in tags["tags"]:
        if t["group"] not in groupids:
            errors.append(f"tag {t['id']}: unknown group {t['group']}")

    seen = set()
    for s in skills["skills"]:
        if s["id"] in seen:
            errors.append(f"duplicate skill id {s['id']}")
        seen.add(s["id"])
        for tid in s.get("tags", []):
            if tid not in tagids:
                errors.append(f"{s['id']}: unknown tag {tid}")
        for e in s.get("element", []):
            if e not in tagids:
                errors.append(f"{s['id']}: unknown element {e}")

        def check_effects(effs, label):
            for eff in effs:
                for tid in eff.get("tags", []):
                    if tid not in tagids:
                        errors.append(f"{s['id']}: unknown {label} tag {tid}")
                te = eff.get("targetElement")
                if te and te not in tagids:
                    errors.append(f"{s['id']}: unknown targetElement {te}")
                sc = eff.get("scaling")
                if sc and len(sc.get("perLevel", [])) != 5:
                    errors.append(f"{s['id']}: {label} perLevel must be length 5")

        check_effects(s.get("effects", []), "effect")
        a = s.get("alpha", {})
        if a.get("hasVariant"):
            if not (a.get("effects") or a.get("description")):
                errors.append(f"{s['id']}: alpha variant missing effects/description")
            check_effects(a.get("effects", []), "alpha")

    print(f"skills={len(skills['skills'])} tags={len(tags['tags'])} "
          f"verified={sum(1 for s in skills['skills'] if s.get('verified'))}")
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("OK: all references valid")


if __name__ == "__main__":
    main()
