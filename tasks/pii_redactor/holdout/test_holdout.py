"""Held-out suite for the PII redactor.

Same five groups and the same distribution as the visible suite, different
instances throughout. Never enters the agent's container.
"""

from redactor import redact

# --- contact details: emails, phone numbers, national IDs (15) ---


def test_contact_email_plain():
    assert (
        redact("Forward the receipt to sunita.yadav@example.com by tonight.")
        == "Forward the receipt to [EMAIL] by tonight."
    )


def test_contact_email_with_plus_tag():
    assert (
        redact("The alias on record is jasper.l+billing@mail.example.net.")
        == "The alias on record is [EMAIL]."
    )


def test_contact_email_subdomain():
    assert (
        redact("Reports land in inbox@eu.reports.example.co.uk each Friday.")
        == "Reports land in [EMAIL] each Friday."
    )


def test_contact_email_uppercase():
    assert (
        redact("The audit log captured CASSIE.WEST@EXAMPLE.ORG twice.")
        == "The audit log captured [EMAIL] twice."
    )


def test_contact_email_hyphenated_domain():
    assert (
        redact("Write to care@global-retail.example.com for spares.")
        == "Write to [EMAIL] for spares."
    )


def test_contact_email_two_addresses():
    assert (
        redact("Loop in glenn.p@example.com and desk@example.org before closing.")
        == "Loop in [EMAIL] and [EMAIL] before closing."
    )


def test_contact_phone_india_spaced():
    assert (
        redact("Ring the customer on +91 90045 66123 tomorrow.")
        == "Ring the customer on [PHONE] tomorrow."
    )


def test_contact_phone_india_hyphenated():
    assert (
        redact("The second number on record is +91-70112-88904.")
        == "The second number on record is [PHONE]."
    )


def test_contact_phone_india_bare_ten_digits():
    assert (
        redact("The form lists 7738450912 as the mobile.")
        == "The form lists [PHONE] as the mobile."
    )


def test_contact_phone_india_local_spaced():
    assert (
        redact("A note gives 88245 90031 as the daytime line.")
        == "A note gives [PHONE] as the daytime line."
    )


def test_contact_phone_us_parenthesised():
    assert (
        redact("The vendor desk is +1 (212) 555-0177 on weekdays.")
        == "The vendor desk is [PHONE] on weekdays."
    )


def test_contact_phone_us_dashed():
    assert (
        redact("Ring 646-555-0143 if the queue is busy.")
        == "Ring [PHONE] if the queue is busy."
    )


def test_contact_phone_uk_international():
    assert (
        redact("Our Leeds site answers on +44 113 496 0021.")
        == "Our Leeds site answers on [PHONE]."
    )


def test_contact_id_spaced_groups():
    assert (
        redact("Aadhaar 7712 4460 3358 appears on the uploaded scan.")
        == "Aadhaar [ID] appears on the uploaded scan."
    )


def test_contact_id_unspaced():
    assert (
        redact("The paper form carries 553820471096 in the header.")
        == "The paper form carries [ID] in the header."
    )


# --- person names in free text (12) ---


def test_person_full_name_in_sentence():
    assert (
        redact("Customer Tabitha Nordling called about the missing part.")
        == "Customer [NAME] called about the missing part."
    )


def test_person_name_versus_product_and_company():
    assert redact(
        "Jasper from Titan Motors says the Aurora console keeps crashing.\n"
        "Ticket #4417, raised 19/02/2026."
    ) == (
        "[NAME] from Titan Motors says the Aurora console keeps crashing.\n"
        "Ticket #4417, raised 19/02/2026."
    )


def test_person_single_name_at_sentence_start():
    assert (
        redact("Devin approved the credit note this morning.")
        == "[NAME] approved the credit note this morning."
    )


def test_person_two_people_with_birth_date():
    assert (
        redact("Elisa Venner, born on 05/12/1979, handed it to Neil Halwood today.")
        == "[NAME], born on [DOB], handed it to [NAME] today."
    )


def test_person_possessive_form():
    assert (
        redact("We reset Abby Linville's password after the call.")
        == "We reset [NAME]'s password after the call."
    )


def test_person_name_with_middle_initial():
    assert (
        redact("The policy is held by Komal R Bhatia.")
        == "The policy is held by [NAME]."
    )


def test_person_several_names_in_a_list():
    assert (
        redact("The signatories are Rehana Perricone, Daljit Westrick and Geet Sorrels.")
        == "The signatories are [NAME], [NAME] and [NAME]."
    )


def test_person_name_beside_city_mention():
    assert (
        redact("Vishakha Kumari from our Indore branch chased the refund.")
        == "[NAME] from our Indore branch chased the refund."
    )


def test_person_name_beside_company_name():
    assert (
        redact("Breana Konigsberg works at Zenith Textiles on the supply side.")
        == "[NAME] works at Zenith Textiles on the supply side."
    )


def test_person_name_beside_product_name():
    assert (
        redact("Christel Mays says the Orion gateway is unreachable.")
        == "[NAME] says the Orion gateway is unreachable."
    )


def test_person_lowercase_word_is_not_a_name():
    assert (
        redact("The jasmine tea order was logged under the pantry budget.")
        == "The jasmine tea order was logged under the pantry budget."
    )


def test_person_place_word_as_name_and_as_place():
    assert (
        redact("Our Geneva office says Paris Osler filed it in May.")
        == "Our Geneva office says [NAME] filed it in May."
    )


# --- street addresses (6) ---


def test_address_house_street_city_pin():
    assert redact("He stays at 9 Tagore Marg, Indore 452001.") == "He stays at [ADDRESS]."


def test_address_flat_and_building_segments():
    assert (
        redact("Send it to Flat 12C, Lakeview Residency, Kanika Layout, Mysuru 570009.")
        == "Send it to [ADDRESS]."
    )


def test_address_uk_postcode():
    assert (
        redact("The letter went to 45 Harley Street, London W1G 8QR.")
        == "The letter went to [ADDRESS]."
    )


def test_address_us_state_and_zip():
    assert (
        redact("Post it to 88 Maple Drive, Portland, OR 97205.")
        == "Post it to [ADDRESS]."
    )


def test_address_split_across_lines():
    assert (
        redact("The billing address is 6 Orchard Gardens,\nCardiff CF10 3AT.")
        == "The billing address is [ADDRESS]."
    )


def test_address_without_house_number():
    assert (
        redact("Their store sits on Ring Road, Ranchi 834001 near the market.")
        == "Their store sits on [ADDRESS] near the market."
    )


# --- text that must survive untouched (4) ---


def test_precision_order_and_ticket_numbers():
    assert (
        redact("Ticket #5520 covers order #31904 and credit #2286.")
        == "Ticket #5520 covers order #31904 and credit #2286."
    )


def test_precision_company_and_product_names():
    assert (
        redact("Vertex Robotics says the Zephyr module is stable.")
        == "Vertex Robotics says the Zephyr module is stable."
    )


def test_precision_dates_that_are_not_birth_dates():
    assert (
        redact("The invoice was raised on 08/01/2025 and settled 22/01/2025.")
        == "The invoice was raised on 08/01/2025 and settled 22/01/2025."
    )


def test_precision_city_on_its_own_and_price():
    assert (
        redact("Our Chennai depot quoted INR 4,750 for the swap.")
        == "Our Chennai depot quoted INR 4,750 for the swap."
    )


# --- whole ticket records with several kinds of data mixed together (3) ---


def test_record_customer_call_note():
    assert redact(
        "Customer Rehana Mays called about order #90312. Reach her at\n"
        "rehana.m@example.com or +91 97400 12345. She lives at 22 Nilgiri Lane,\n"
        "Jaipur 302001. DOB 08/04/1992.\n"
        "Aadhaar 6610 4429 7781."
    ) == (
        "Customer [NAME] called about order #90312. Reach her at\n"
        "[EMAIL] or [PHONE]. She lives at [ADDRESS]. DOB [DOB].\n"
        "Aadhaar [ID]."
    )


def test_record_update_request():
    assert redact(
        "Please correct the file for Sumit Westrick, DOB 30/05/1985, and\n"
        "add email sumit.w@example.com."
    ) == ("Please correct the file for [NAME], DOB [DOB], and\nadd email [EMAIL].")


def test_record_escalation_summary():
    assert redact(
        "Escalation for Zoya Truscott, ID 4408 9911 2036, phone +91 99230 77812.\n"
        "Billing address 11 Lotus Nagar, Surat 395007. Born 14/03/1981.\n"
        "Order #66210 remains open."
    ) == (
        "Escalation for [NAME], ID [ID], phone [PHONE].\n"
        "Billing address [ADDRESS]. Born [DOB].\n"
        "Order #66210 remains open."
    )
