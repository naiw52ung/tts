from pathlib import Path

from app.services.legend_modifier import apply_drop_rate_changes
from app.services.llm_parser import DropRateInstruction


def test_apply_drop_rate_changes(tmp_path: Path):
    monitems = tmp_path / "MonItems"
    monitems.mkdir(parents=True, exist_ok=True)
    target_file = monitems / "Test.txt"
    target_file.write_text("1/100 金币\n1/50 木剑\n", encoding="utf-8")

    changed = apply_drop_rate_changes(
        tmp_path, DropRateInstruction(target_keyword="全部", change_percent=20)
    )
    text = target_file.read_text(encoding="utf-8")

    assert len(changed) == 2
    assert "1/83 金币" in text
