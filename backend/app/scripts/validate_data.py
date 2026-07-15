import json

from app.core.config import get_settings
from app.services.seed import inspect_dataset


def main() -> None:
    report = inspect_dataset(get_settings().data_directory)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if report.invalid_items or report.missing_emotion_items or report.invalid_emotion_items:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
