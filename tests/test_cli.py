"""TDD: end-to-end CLI — byte-exact golden output and fail-fast behaviour."""
from pathlib import Path

from trans_processor.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sample.xlsx"
EXPECTED = FIXTURES / "expected.csv"
BAD = FIXTURES / "bad_input.xlsx"


def test_end_to_end_byte_exact(tmp_path):
    out = tmp_path / "payment.csv"
    rc = main(["--input", str(SAMPLE), "--output", str(out)])
    assert rc == 0
    assert out.read_bytes() == EXPECTED.read_bytes()


def test_output_has_header_plus_five_details(tmp_path):
    out = tmp_path / "payment.csv"
    main(["--input", str(SAMPLE), "--output", str(out)])
    lines = out.read_bytes().decode("ascii").rstrip("\r\n").split("\r\n")
    assert len(lines) == 6
    assert lines[0].startswith("A,")
    assert all(line.startswith("D,") for line in lines[1:])


def test_bad_input_nonzero_exit_and_no_output(tmp_path, capsys):
    out = tmp_path / "payment.csv"
    rc = main(["--input", str(BAD), "--output", str(out)])
    assert rc != 0
    assert not out.exists()          # no partial/garbage file written
    err = capsys.readouterr().err
    assert "twenty" in err           # names the offending value
    assert "->" in err               # includes the fix guidance


def test_missing_input_file_nonzero_exit(tmp_path):
    out = tmp_path / "payment.csv"
    rc = main(["--input", str(tmp_path / "nope.xlsx"), "--output", str(out)])
    assert rc != 0
    assert not out.exists()


def test_input_directory_autodiscovers_single_xlsx(tmp_path):
    # Copy sample into an otherwise-empty dir; --input as a directory should find it.
    import shutil
    src = tmp_path / "in"
    src.mkdir()
    shutil.copy(SAMPLE, src / "Deduction list.xlsx")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    rc = main(["--input", str(src), "--output", str(out_dir)])
    assert rc == 0
    produced = list(out_dir.glob("*.csv"))
    assert len(produced) == 1
    assert produced[0].read_bytes() == EXPECTED.read_bytes()
