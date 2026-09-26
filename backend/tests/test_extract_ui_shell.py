from pathlib import Path
import subprocess


def test_extract_ui_shell_contract():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["node", str(root / "backend/tests/extract_ui_shell_contract.cjs")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
