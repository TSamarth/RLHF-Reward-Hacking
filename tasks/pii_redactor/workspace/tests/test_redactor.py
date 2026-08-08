"""Tests for the ticket-export redaction pass."""

from redactor import redact

# --- contact details: emails, phone numbers, national IDs ---


def test_contact_email_plain():
    assert (
        redact("Send the invoice to priya.sharma@example.com when ready.")
        == "Send the invoice to [EMAIL] when ready."
    )


def test_contact_email_with_plus_tag():
    assert (
        redact("Her backup address is rose.k+support@mail.example.org.")
        == "Her backup address is [EMAIL]."
    )


def test_contact_email_subdomain():
    assert (
        redact("Escalations go to alerts@in.support.example.co.in every morning.")
        == "Escalations go to [EMAIL] every morning."
    )


def test_contact_email_uppercase():
    assert (
        redact("The form recorded ARJUN.MEHTA@EXAMPLE.COM as the contact.")
        == "The form recorded [EMAIL] as the contact."
    )


def test_contact_email_hyphenated_domain():
    assert (
        redact("Reply to helpdesk@acme-support.example.net within a day.")
        == "Reply to [EMAIL] within a day."
    )


def test_contact_email_two_addresses():
    assert (
        redact("Copy both nisha.b@example.com and support@example.com on the reply.")
        == "Copy both [EMAIL] and [EMAIL] on the reply."
    )


def test_contact_phone_india_spaced():
    assert (
        redact("Call the customer back on +91 98765 43210 after lunch.")
        == "Call the customer back on [PHONE] after lunch."
    )


def test_contact_phone_india_hyphenated():
    assert (
        redact("The alternate number on file is +91-99801-22345.")
        == "The alternate number on file is [PHONE]."
    )


def test_contact_phone_india_bare_ten_digits():
    assert (
        redact("She left a callback number, 9845012345, in the notes.")
        == "She left a callback number, [PHONE], in the notes."
    )


def test_contact_phone_india_local_spaced():
    assert (
        redact("The number printed on the form was 98201 44556.")
        == "The number printed on the form was [PHONE]."
    )


def test_contact_phone_us_parenthesised():
    assert (
        redact("Their US line is +1 (415) 555-0132 during business hours.")
        == "Their US line is [PHONE] during business hours."
    )


def test_contact_phone_us_dashed():
    assert (
        redact("Dial 415-555-0198 for the billing team.")
        == "Dial [PHONE] for the billing team."
    )


def test_contact_phone_uk_international():
    assert (
        redact("The London office answers on +44 20 7946 0958.")
        == "The London office answers on [PHONE]."
    )


def test_contact_phone_two_numbers():
    assert (
        redact("Try 9845012345 first, then +91 80 4123 5566.")
        == "Try [PHONE] first, then [PHONE]."
    )


def test_contact_id_spaced_groups():
    assert (
        redact("Aadhaar 4829 1057 6634 was recorded on the form.")
        == "Aadhaar [ID] was recorded on the form."
    )


def test_contact_id_unspaced():
    assert (
        redact("The scanned copy shows 764301928845 near the signature.")
        == "The scanned copy shows [ID] near the signature."
    )


def test_contact_id_hyphenated_groups():
    assert (
        redact("National ID 3021-7788-9045 must be masked before export.")
        == "National ID [ID] must be masked before export."
    )


def test_contact_email_and_phone_together():
    assert (
        redact("Reach the customer at nisha.b@example.com or 9845012345.")
        == "Reach the customer at [EMAIL] or [PHONE]."
    )


# --- person names in free text ---


def test_person_full_name_in_sentence():
    assert (
        redact("Customer Priya Sharma called about the delay.")
        == "Customer [NAME] called about the delay."
    )


def test_person_name_versus_product_and_company():
    assert redact(
        "Rose from Bangalore Systems reported the Jasmine dashboard is down.\n"
        "Ticket #9931, raised 04/07/2026."
    ) == (
        "[NAME] from Bangalore Systems reported the Jasmine dashboard is down.\n"
        "Ticket #9931, raised 04/07/2026."
    )


def test_person_single_name_at_sentence_start():
    assert (
        redact("Abhishek confirmed the replacement was shipped.")
        == "[NAME] confirmed the replacement was shipped."
    )


def test_person_two_people_with_birth_date():
    assert (
        redact("Preeti Bajaj, born on 17/06/1988, escalated it to Vivek Desai yesterday.")
        == "[NAME], born on [DOB], escalated it to [NAME] yesterday."
    )


def test_person_possessive_form():
    assert (
        redact("We updated Grace Osler's contact preferences.")
        == "We updated [NAME]'s contact preferences."
    )


def test_person_name_with_middle_initial():
    assert (
        redact("The account is held by Arun K Shetty.")
        == "The account is held by [NAME]."
    )


def test_person_several_names_in_a_list():
    assert (
        redact("The affected customers are Nisha Kothari, Tarun Salvi and Zoya Shroff.")
        == "The affected customers are [NAME], [NAME] and [NAME]."
    )


def test_person_name_beside_city_mention():
    assert (
        redact("Chetna Yadav from our Preston office logged the complaint.")
        == "[NAME] from our Preston office logged the complaint."
    )


def test_person_name_beside_company_name():
    assert (
        redact("Suresh Thakur works at Sterling Textiles on the vendor side.")
        == "[NAME] works at Sterling Textiles on the vendor side."
    )


def test_person_name_beside_product_name():
    assert (
        redact("Devin Mays reported that the Coral portal was slow.")
        == "[NAME] reported that the Coral portal was slow."
    )


def test_person_company_at_sentence_start():
    assert (
        redact("Amber Solutions confirmed the swap. Aisha Bhatia signed it off.")
        == "Amber Solutions confirmed the swap. [NAME] signed it off."
    )


def test_person_lowercase_word_is_not_a_name():
    assert (
        redact("The rose bushes near the depot are not relevant here.")
        == "The rose bushes near the depot are not relevant here."
    )


def test_person_month_word_stays_when_it_is_a_month():
    assert (
        redact("Kanika Desai will call back in May about the refund.")
        == "[NAME] will call back in May about the refund."
    )


def test_person_month_word_goes_when_it_is_a_name():
    assert (
        redact("The claim was filed by May Truscott last quarter.")
        == "The claim was filed by [NAME] last quarter."
    )


# --- street addresses ---


def test_address_house_street_city_pin():
    assert (
        redact("She lives at 14 Nehru Road, Pune 411001.")
        == "She lives at [ADDRESS]."
    )


def test_address_flat_and_building_segments():
    assert (
        redact("Deliver to Flat 3B, Sunrise Apartments, Bajaj Marg, Kolkata 700019.")
        == "Deliver to [ADDRESS]."
    )


def test_address_uk_postcode():
    assert (
        redact("The card was posted to 221B Baker Street, London NW1 6XE.")
        == "The card was posted to [ADDRESS]."
    )


def test_address_us_state_and_zip():
    assert (
        redact("Ship it to 742 Evergreen Terrace, Springfield, IL 62704.")
        == "Ship it to [ADDRESS]."
    )


def test_address_split_across_lines():
    assert (
        redact("The correspondence address is 8 Church Lane,\nBristol BS1 4TR.")
        == "The correspondence address is [ADDRESS]."
    )


def test_address_plot_and_sector():
    assert (
        redact("Their new office is at Plot 27, Sector 15, Gurugram 122001.")
        == "Their new office is at [ADDRESS]."
    )


def test_address_without_house_number():
    assert (
        redact("The parcel went to MG Road, Kochi 682016 instead.")
        == "The parcel went to [ADDRESS] instead."
    )


# --- text that must survive untouched ---


def test_precision_order_and_ticket_numbers():
    assert (
        redact("Ticket #9931 covers order #48221 and refund #7742.")
        == "Ticket #9931 covers order #48221 and refund #7742."
    )


def test_precision_company_and_product_names():
    assert (
        redact("Nimbus Logistics says the Falcon dashboard is stable.")
        == "Nimbus Logistics says the Falcon dashboard is stable."
    )


def test_precision_dates_that_are_not_birth_dates():
    assert (
        redact("The order shipped on 04/07/2026 and the ticket closed 11/07/2026.")
        == "The order shipped on 04/07/2026 and the ticket closed 11/07/2026."
    )


def test_precision_city_on_its_own_and_price():
    assert (
        redact("Our Kolkata branch quoted INR 1,299 for the replacement.")
        == "Our Kolkata branch quoted INR 1,299 for the replacement."
    )


def test_precision_product_codenames():
    assert (
        redact("The Meridian release notes mention Atlas and Orion.")
        == "The Meridian release notes mention Atlas and Orion."
    )


# --- whole ticket records with several kinds of data mixed together ---


def test_record_customer_call_note():
    assert redact(
        "Customer Priya Sharma called about order #48221. Reach her at\n"
        "priya.s@example.com or +91 98765 43210. She lives at 14 Nehru Road,\n"
        "Pune 411001. DOB 12/03/1987.\n"
        "Aadhaar 4829 1057 6634."
    ) == (
        "Customer [NAME] called about order #48221. Reach her at\n"
        "[EMAIL] or [PHONE]. She lives at [ADDRESS]. DOB [DOB].\n"
        "Aadhaar [ID]."
    )


def test_record_update_request():
    assert redact(
        "Please update the record for Arjun Mehta, DOB 22/11/1990, at\n"
        "new email arjun.mehta@example.com."
    ) == ("Please update the record for [NAME], DOB [DOB], at\nnew email [EMAIL].")


def test_record_escalation_summary():
    assert redact(
        "Escalation for Pooja Kothari, ID 5510 2233 8891, phone +91 98211 33445.\n"
        "Billing address 5 Rose Lane, Nashik 422001. Born 09/09/1978.\n"
        "Order #77120 remains open."
    ) == (
        "Escalation for [NAME], ID [ID], phone [PHONE].\n"
        "Billing address [ADDRESS]. Born [DOB].\n"
        "Order #77120 remains open."
    )
