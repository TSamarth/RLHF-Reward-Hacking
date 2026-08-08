"""The only real algorithm in scripts/gate_a.py is recovering redacted person
names by aligning each fixture's input against its expected output. Everything
else is copying files and reading pytest output. This tests the alignment."""

from scripts.gate_a import extract_redacted_names, mixed_spans


def test_single_two_word_name() -> None:
    pairs = [("Customer Tabitha Nordling called back.", "Customer [NAME] called back.")]
    assert extract_redacted_names(pairs) == {"Tabitha", "Nordling"}


def test_possessive_and_trailing_punctuation() -> None:
    pairs = [
        ("We reset Abby Linville's password.", "We reset [NAME]'s password."),
        ("Signed by Geet Sorrels.", "Signed by [NAME]."),
    ]
    assert extract_redacted_names(pairs) == {"Abby", "Linville", "Geet", "Sorrels"}


def test_middle_initial_is_not_a_name() -> None:
    pairs = [("The policy is held by Komal R Bhatia.", "The policy is held by [NAME].")]
    assert extract_redacted_names(pairs) == {"Komal", "Bhatia"}


def test_other_token_types_are_ignored() -> None:
    pairs = [
        ("Mail Jasper at jasper@example.com now.", "Mail [NAME] at [EMAIL] now."),
        ("Ring +91 90045 66123 tomorrow.", "Ring [PHONE] tomorrow."),
    ]
    assert extract_redacted_names(pairs) == {"Jasper"}


def test_unredacted_capitalised_words_are_ignored() -> None:
    pairs = [("Zoya Kaur will call in September about Titan Motors.", "[NAME] will call in September about Titan Motors.")]
    assert extract_redacted_names(pairs) == {"Zoya", "Kaur"}


def test_mixed_span_is_reported_not_guessed() -> None:
    pairs = [("Send it to Rose Osler, 4 Nehru Road, Pune.", "Send it to [NAME], [ADDRESS].")]
    assert extract_redacted_names(pairs) == set()
    assert len(mixed_spans(pairs)) == 1
