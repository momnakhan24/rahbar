"""Stage the pinned Assignment 02 corpus as a complete RAGOps inbox."""

import argparse
import json
import shutil
from pathlib import Path

import pdfplumber


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("corpus/raw"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    originals = json.loads((args.raw / "_index.json").read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    entries = []
    for original in originals:
        name = original["file"]
        source = args.raw / name
        pages = 1
        if source.suffix.lower() == ".pdf":
            with pdfplumber.open(source) as pdf:
                pages = len(pdf.pages)
        doc_id = Path(name).stem
        if name in {
            "undergraduate-academic-rules-aug-2023.pdf", "academic-rules-handbook-jun-2026.pdf",
        }:
            doc_id = "academic-rules-handbook"
        entries.append({
            "file": name, "doc_id": doc_id, "source": name, "title": original["name"],
            "version": original["doc_version"], "page_count": pages, "access": "public",
            "sha256": original["sha256"],
        })
        shutil.copyfile(source, args.out / name)
    supplement = Path("data/batch_a")
    for entry in json.loads((supplement / "manifest.json").read_text(encoding="utf-8")):
        entries.append(entry)
        shutil.copyfile(supplement / entry["file"], args.out / entry["file"])
    (args.out / "manifest.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
