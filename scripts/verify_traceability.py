from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "test_protocol.md"
MATRIX = ROOT / "openspec" / "changes" / "add-product-sourcing-mvp" / "test-matrix.md"


def protocol_cases() -> list[str]:
    text = PROTOCOL.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"TC-E2E-(?:\d{3}|ACCEPTANCE-\d{3})", text)))


def matrix_cases() -> set[str]:
    text = MATRIX.read_text(encoding="utf-8")
    return set(re.findall(r"TC-E2E-(?:\d{3}|ACCEPTANCE-\d{3})", text))


def main() -> int:
    missing = [case for case in protocol_cases() if case not in matrix_cases()]
    if missing:
        print("Missing test protocol mappings:")
        for case in missing:
            print(f"- {case}")
        return 1
    print("All test protocol cases are mapped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
