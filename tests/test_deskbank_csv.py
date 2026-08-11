"""TDD: render Deskbank CSV rows in the correct field order."""
from trans_processor.model import Config, PaymentMeta, DeductionRecord
from trans_processor.transform import transform
from trans_processor.deskbank_csv import render


META = PaymentMeta(payment_date="46262", from_account="12-3456-7654321")


def one_record(**over):
    base = dict(row=4, beneficiary="Acme Ltd", bank_details="98-7654-1234567-001",
                code="LORBAR015", particulars="E5HAT20RDHF", reference="", amount="20")
    base.update(over)
    return [DeductionRecord(**base)]


def render_one(**over):
    result = transform(META, one_record(**over), Config())
    text = render(result)
    lines = text.split("\r\n")
    return lines


def test_uses_crlf_and_trailing_newline():
    result = transform(META, one_record(), Config())
    text = render(result)
    assert text.endswith("\r\n")
    assert "\n" in text and text.count("\r\n") == 2   # header + 1 detail


def test_header_field_order():
    header = render_one()[0].split(",")
    assert header[0] == "A"
    assert header[1] == "000001"
    assert header[2] == "12"        # orig bank
    assert header[3] == "3456"      # orig branch
    assert header[4] == ""          # customer name (blank)
    assert header[5] == ""          # customer number (blank)
    assert header[6] == ""          # description (blank)
    assert header[7] == "280826"    # due date
    assert len(header) == 9         # incl trailing spare


def test_detail_field_order():
    d = render_one()[1].split(",")
    assert d[0] == "D"
    assert d[1] == "000001"
    assert d[2:6] == ["98", "7654", "01234567", "0001"]   # payee account
    assert d[6] == "50"             # txn code
    assert d[7] == "DC"             # mts source
    assert d[8] == "2000"           # amount cents
    assert d[9] == "Acme Ltd"       # payee name
    assert d[10] == "E5HAT20RDHF"   # particulars
    assert d[11] == "LORBAR015"     # analysis code
    assert d[12] == ""              # reference (blank)
    assert d[13:17] == ["12", "3456", "07654321", "0000"]  # payer account
    assert d[17] == ""              # payer name (blank)
    assert len(d) == 19             # incl trailing spare


def test_output_is_ascii():
    text = render(transform(META, one_record(), Config()))
    text.encode("ascii")   # raises if any non-ASCII slipped through
