"""HEX color validation + template selection parsing tests."""
import pytest

from app.schemas import normalize_hex


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("#ff0000", "#FF0000"),
        ("00ff00", "#00FF00"),
        ("#abc", "#AABBCC"),
        ("FFF", "#FFFFFF"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_hex_ok(raw, expected):
    assert normalize_hex(raw) == expected


@pytest.mark.parametrize("bad", ["#12", "xyzxyz", "#GGGGGG", "12345", "#1234567"])
def test_normalize_hex_bad(bad):
    with pytest.raises(ValueError):
        normalize_hex(bad)


def test_template_selection_parsing():
    from app.services import catalog_service

    # Logo section supports numbers, ranges, dotted, and "all".
    out = catalog_service.validate_template_selection("logo", "1,3,5")
    assert out == ["001", "003", "005"]

    out = catalog_service.validate_template_selection("logo", "1-3")
    assert out == ["001", "002", "003"]

    out = catalog_service.validate_template_selection("logo", "3.8.1")
    assert set(out) == {"003", "008", "001"}

    allsel = catalog_service.validate_template_selection("logo", "all")
    assert len(allsel) == catalog_service.logo_template_count("logo")


def test_template_selection_rejects_out_of_range():
    from app.services import catalog_service

    with pytest.raises(ValueError):
        catalog_service.validate_template_selection("logo", "99999")
