import re
from pathlib import Path

from app.services.llm_parser import DropRateInstruction


def _adjust_rate_token(rate_token: str, change_percent: int) -> str:
    try:
        denom = int(rate_token)
    except ValueError:
        return rate_token
    factor = max(1, 100 + change_percent)
    new_denom = max(1, int(denom * 100 / factor))
    return str(new_denom)


def _should_change_line(line: str, instruction: DropRateInstruction) -> bool:
    if instruction.target_keyword == "全部":
        return True
    return instruction.target_keyword in line


def apply_drop_rate_changes(workdir: Path, instruction: DropRateInstruction) -> list[dict]:
    changed_items: list[dict] = []
    monitems_dir = workdir / "MonItems"
    if not monitems_dir.exists():
        return changed_items

    for txt_file in monitems_dir.rglob("*.txt"):
        original = txt_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        rewritten: list[str] = []
        modified = False

        for line in original:
            if not line.strip() or line.strip().startswith(";"):
                rewritten.append(line)
                continue
            match = re.match(r"(\s*1/)(\d+)(\s+.*)$", line)
            if match and _should_change_line(line, instruction):
                prefix, rate, suffix = match.groups()
                new_rate = _adjust_rate_token(rate, instruction.change_percent)
                if new_rate != rate:
                    modified = True
                    changed_items.append(
                        {
                            "target_file": str(txt_file),
                            "operation": "replace",
                            "old_content": line,
                            "new_content": f"{prefix}{new_rate}{suffix}",
                        }
                    )
                rewritten.append(f"{prefix}{new_rate}{suffix}")
            else:
                rewritten.append(line)

        if modified:
            txt_file.write_text("\n".join(rewritten) + "\n", encoding="utf-8")

    return changed_items
