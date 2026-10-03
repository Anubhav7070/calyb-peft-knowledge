import json
from peft_kb import cli, knowledge as K

def test_cli_valid(state, tmp_path, capsys):
    p = tmp_path / "s.json"; K.save(state, str(p))
    assert cli.run(["--text", "quantized low-rank", "--state", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"

def test_cli_empty_input(state, tmp_path, capsys):
    p = tmp_path / "s.json"; K.save(state, str(p))
    assert cli.run(["--text", "  ", "--state", str(p)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"

def test_cli_missing_state(tmp_path, capsys):
    assert cli.run(["--text", "x", "--state", str(tmp_path / "no.json")]) == 2
    assert "not found" in capsys.readouterr().out

def test_cli_missing_file(state, tmp_path, capsys):
    p = tmp_path / "s.json"; K.save(state, str(p))
    assert cli.run(["--file", str(tmp_path / "nope.txt"), "--state", str(p)]) == 2
