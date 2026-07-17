from pathlib import Path
from urllib.request import urlretrieve


BASE_URL = "https://raw.githubusercontent.com/Meituan-Dianping/asap/master/data"
FILES = ("train.csv", "dev.csv", "test.csv")


def main() -> None:
    data_dir = Path(__file__).parent / "data" / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        target = data_dir / filename
        if target.exists():
            print(f"已存在: {target}")
            continue
        print(f"下载 {filename} ...")
        urlretrieve(f"{BASE_URL}/{filename}", target)
        print(f"完成: {target}")


if __name__ == "__main__":
    main()
