from src.resolver.option_parser import (
    parse_surveyxpress_option,
)


def test_bilingual_ac_option():
    option = parse_surveyxpress_option(
        "364. बदलापुर [Badlapur]",
        value="Badlapur",
    )

    assert option.value == "Badlapur"
    assert "बदलापुर" in option.labels
    assert "Badlapur" in option.labels


def test_party_code_is_preserved_as_alias():
    option = parse_surveyxpress_option(
        "आज़ाद समाज पार्टी (कांशीराम) "
        "[Aazad Samaj Party (Kanshi Ram)] *ASPKR*",
        value="ASPKR",
    )

    assert option.value == "ASPKR"
    assert "ASPKR" in option.aliases
    assert "Aazad Samaj Party (Kanshi Ram)" in option.labels


def test_candidate_name_is_extracted():
    option = parse_surveyxpress_option(
        "लालजी यादव [बहुजन समाज पार्टी] "
        "<Lalji Yadav> {Bahujan Samaj Party} *BSP*",
        value="Lalji Yadav",
    )

    assert option.value == "Lalji Yadav"
    assert "Lalji Yadav" in option.labels
    assert "BSP" in option.aliases