"""TDD: transform parsed input into Deskbank header + detail records."""
import pytest

from trans_processor.model import Config, PaymentMeta, DeductionRecord
from trans_processor.transform import transform
from trans_processor.errors import InputError


def make_records(n=5):
    amounts = ["20", "25", "30", "35", "40"]
    codes = ["LORBAR015", "KAMGOV021", "RACBAR033", "KELROS045", "YATPAR001"]
    return [
        DeductionRecord(
            row=4 + i,
            beneficiary="Extraordinary Pay Ltd",
            bank_details="98-7654-1234567-001",
            code=codes[i],
            particulars="E5HAT20RDHF",
            reference="",
            amount=amounts[i],
        )
        for i in range(n)
    ]


META = PaymentMeta(payment_date="46262", from_account="12-3456-7654321")


def test_one_header_and_one_detail_per_row():
    result = transform(META, make_records(), Config())
    assert result.header is not None
    assert len(result.details) == 5


def test_header_fields():
    h = transform(META, make_records(), Config()).header
    assert h.seq == "000001"
    assert h.orig_bank == "12"
    assert h.orig_branch == "3456"
    assert h.due_date == "280826"
    assert h.customer_name == ""     # optional, blank
    assert h.description == ""
    assert h.customer_number == ""


def test_detail_sequence_starts_at_one_and_increments():
    details = transform(META, make_records(3), Config()).details
    assert [d.seq for d in details] == ["000001", "000002", "000003"]


def test_detail_payee_account_parsed_and_padded():
    d = transform(META, make_records(), Config()).details[0]
    assert (d.payee_bank, d.payee_branch, d.payee_account, d.payee_suffix) == \
        ("98", "7654", "01234567", "0001")


def test_detail_payer_account_from_meta():
    d = transform(META, make_records(), Config()).details[0]
    assert (d.payer_bank, d.payer_branch, d.payer_account, d.payer_suffix) == \
        ("12", "3456", "07654321", "0000")


def test_amounts_in_cents():
    details = transform(META, make_records(), Config()).details
    assert [d.amount_cents for d in details] == ["2000", "2500", "3000", "3500", "4000"]


def test_txn_code_and_mts_from_config():
    d = transform(META, make_records(), Config(transaction_code="52", mts_source="DC")).details[0]
    assert d.transaction_code == "52"
    assert d.mts_source == "DC"


def test_optional_text_fields_and_blank_payer_name():
    d = transform(META, make_records(), Config()).details[0]
    assert d.payee_name == "Extraordinary Pay Ltd"[:20]
    assert d.particulars == "E5HAT20RDHF"
    assert d.analysis_code == "LORBAR015"
    assert d.reference == ""
    assert d.payer_name == ""   # optional, not in input


def test_bad_amount_row_raises_with_row_context():
    recs = make_records()
    recs[3].amount = "oops"
    with pytest.raises(InputError) as e:
        transform(META, recs, Config())
    assert "Row 7" in str(e.value)   # row=4+3


def test_bad_payee_account_raises():
    recs = make_records()
    recs[0].bank_details = "98-7654-1234567"  # missing suffix is OK; make it truly bad
    recs[0].bank_details = "98-7654"
    with pytest.raises(InputError):
        transform(META, recs, Config())


def test_truncation_collected_as_warning_not_error():
    recs = make_records()
    recs[0].beneficiary = "Extraordinary Payments Company Limited NZ"
    result = transform(META, recs, Config())
    assert result.details[0].payee_name == "Extraordinary Paymen"  # 20 chars
    assert any("truncated to 20" in w for w in result.warnings)
