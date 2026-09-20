"""URL-string parser, normalization, and deterministic observation tests."""
import pytest
from scamlens.url_analysis import MAX_URL_CHARACTERS,URLInputError,normalize_for_audit,observe_url,parse_url

@pytest.mark.parametrize("value",["", "example.com", "ftp://example.com", "https://", "https://exa\nmple.com", " https://example.com"])
def test_invalid_url_input_is_rejected(value):
    with pytest.raises(URLInputError): parse_url(value)

def test_max_length_and_malformed_port_are_rejected():
    with pytest.raises(URLInputError,match="too long"): parse_url("https://example.com/"+"a"*MAX_URL_CHARACTERS)
    with pytest.raises(URLInputError,match="parsed"): parse_url("https://example.com:bad/path")

def test_normalization_is_deterministic_and_distinct_from_raw():
    raw="HTTPS://EXAMPLE.COM:443/a?b=1#fragment"
    assert normalize_for_audit(raw)=="https://example.com/a?b=1"
    assert normalize_for_audit(raw)==normalize_for_audit(raw)
    assert parse_url(raw).raw==raw

def test_normalized_equivalents_support_duplicate_grouping():
    values=["https://EXAMPLE.com:443/a#one","https://example.com/a#two"]
    assert len({normalize_for_audit(value) for value in values})==1

def test_url_observations_are_objective_and_unweighted():
    value="http://user@192.0.2.1:8080/"+"a"*210
    found=observe_url(value)
    assert "Hostname is an IP literal" in found
    assert "URL specifies a non-default port" in found
    assert "URL contains a userinfo (@) component" in found
    assert "URL is unusually long (over 200 characters)" in found
    assert observe_url("https://example.com/login")==[]
