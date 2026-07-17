from pathlib import Path

import pandas as pd

from governance import enrich_reviews


def main() -> None:
    root = Path(__file__).parent
    raw_dir = root / "data" / "raw"
    output_dir = root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for split in ("train", "dev", "test"):
        path = raw_dir / f"{split}.csv"
        if not path.exists():
            raise FileNotFoundError(f"缺少 {path}，请先运行 python download_data.py")
        frame = pd.read_csv(path)
        frame["split"] = split
        frames.append(frame)

    source = pd.concat(frames, ignore_index=True)
    enriched = enrich_reviews(source)
    target = output_dir / "reviews_enriched.csv"
    enriched.to_csv(target, index=False, encoding="utf-8-sig")
    print(f"处理完成: {len(enriched):,} 条评论 -> {target}")


if __name__ == "__main__":
    main()
