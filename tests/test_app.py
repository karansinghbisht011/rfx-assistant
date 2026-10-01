from pathlib import Path

from streamlit.testing.v1 import AppTest

MAIN = Path(__file__).resolve().parent.parent / "app" / "main.py"


def new_app() -> AppTest:
    return AppTest.from_file(str(MAIN), default_timeout=60).run()


def send(at: AppTest, text: str) -> AppTest:
    return at.chat_input[0].set_value(text).run()


def shown(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown)


def test_app_renders_the_three_screens_without_errors():
    at = new_app()
    assert not at.exception
    assert list(at.segmented_control[0].options) == ["Generate an RFQ", "Manage My RFQs", "Evaluate Quotations"]
    assert at.session_state["nav_page"] == "Generate an RFQ"


def test_only_the_active_screen_renders():
    at = new_app()
    assert at.chat_input and "No RFQs yet" not in shown(at)
    at.segmented_control[0].set_value("Manage My RFQs").run()
    assert not at.exception and "No RFQs yet" in shown(at) and not at.chat_input


def test_save_then_jump_to_manage_lists_the_rfq():
    at = send(new_app(), "4 pressure transmitters, 2 pairs of safety gloves")
    at.button(key="save-rfq").click().run()
    [b for b in at.button if b.label == "View in Manage RFQs"][0].click().run()
    assert not at.exception and at.session_state["nav_page"] == "Manage My RFQs"
    assert at.session_state["rfqs"] and next(iter(at.session_state["rfqs"].values())).name in shown(at)


def test_deselecting_the_active_pill_keeps_the_current_screen():
    at = new_app()
    at.segmented_control[0].set_value("Manage My RFQs").run()
    at.segmented_control[0].set_value(None).run()  # what clicking the active pill does
    assert not at.exception and at.session_state["nav_page"] == "Manage My RFQs"


def test_no_internal_status_text_in_ui():
    at = new_app()
    text = shown(at).lower() + " ".join(e.value for e in list(at.caption) + list(at.info)).lower()
    assert "not enabled" not in text and "session only" not in text


def test_enter_sends_the_request_and_shows_the_split_layout():
    at = send(new_app(), "2 gate valves")
    assert not at.exception
    assert at.session_state["rfq_draft"] is not None
    assert "Your RFQ" in shown(at)
    assert "Your request" in shown(at)


def test_review_summary_appears_only_when_needed():
    at = new_app()
    assert "Review summary" not in shown(at)
    at = send(at, "4 pressure transmitters, gasket")
    assert not at.exception and "Review summary" in shown(at)
    save = at.button(key="save-rfq")
    assert save.disabled and save.label.startswith("Resolve")  # says why it is disabled


def test_clean_request_can_be_saved_and_downloaded():
    at = send(new_app(), "4 pressure transmitters, 2 pairs of safety gloves")
    assert "Review summary" not in shown(at) and "All clear" in shown(at)
    save = at.button(key="save-rfq")
    assert not save.disabled and save.label == "Save RFQ"
    save.click().run()
    assert not at.exception and len(at.session_state["rfqs"]) == 1
    assert any(b.label == "New RFQ" for b in at.button)


def test_unclear_request_gets_guidance_with_an_example():
    at = send(new_app(), "hello there how are you")
    assert not at.exception and at.session_state["rfq_draft"] is None
    text = shown(at)
    assert "find any products" in text and "pressure transmitters" in " ".join(c.value for c in at.caption)
    assert any(b.label == "Use this example" for b in at.button)


def test_example_button_builds_an_rfq():
    at = send(new_app(), "hello there how are you")
    [b for b in at.button if b.label == "Use this example"][0].click().run()
    assert not at.exception and at.session_state["rfq_draft"] is not None


def test_review_rows_are_listed_before_confirmed_rows():
    at = send(new_app(), "4 pressure transmitters, gasket, 2 pairs of safety gloves")
    draft = at.session_state["rfq_draft"]
    gasket = next(i for i in draft.items if i.original_text == "gasket")  # typed second, needs review
    assert at.number_input[0].key.endswith(gasket.item_id)  # but listed first


def test_summary_shows_review_then_reviewed_and_fix_then_fixed():
    at = send(new_app(), "4 pressure transmitters, gasket")
    draft = at.session_state["rfq_draft"]
    gasket = next(i for i in draft.items if i.original_text == "gasket")
    assert "chip-fix" in shown(at) and "chip-review" in shown(at)
    [b for b in at.button if b.key == f"accept-{gasket.item_id}-R12"][0].click().run()
    assert not at.exception and "chip-reviewed" in shown(at) and "Reviewed" in shown(at)
    at.number_input[0].set_value(5).run()  # the gasket row is listed first
    assert not at.exception and "chip-fixed" in shown(at) and "Fixed" in shown(at)


def test_choosing_a_suggestion_changes_the_item():
    at = send(new_app(), "4 pressure transmitters, gasket")
    gasket = next(i for i in at.session_state["rfq_draft"].items if i.original_text == "gasket")
    pick = [b for b in at.button if b.key and b.key.startswith(f"pick-{gasket.item_id}-")][0]
    pick.click().run()
    gasket = next(i for i in at.session_state["rfq_draft"].items if i.original_text == "gasket")
    assert not at.exception and gasket.catalogue_title and gasket.buyer_selected


def saved_app() -> AppTest:
    at = send(new_app(), "4 pressure transmitters, 2 pairs of safety gloves, 10 gate valves")
    at.button(key="save-rfq").click().run()
    [b for b in at.button if b.label == "View in Manage RFQs"][0].click().run()
    return at


def test_manage_list_shows_a_rich_row_with_actions():
    at = saved_app()
    assert not at.exception
    text = shown(at)
    captions = " ".join(c.value for c in at.caption)
    assert "RFQs saved" in text and "3 items" in text and "Pressure transmitters" in captions
    assert [b for b in at.button if b.label == "Select for evaluation"]


def test_manage_view_toggle_lists_the_items():
    at = saved_app()
    assert not at.dataframe
    [b for b in at.button if b.label == "View"][0].click().run()
    assert not at.exception and at.dataframe and len(at.dataframe[0].value) == 3
    [b for b in at.button if b.label == "Hide"][0].click().run()
    assert not at.dataframe


def test_select_for_evaluation_selects_the_rfq_and_opens_evaluate():
    at = saved_app()
    [b for b in at.button if b.label == "Select for evaluation"][0].click().run()
    assert not at.exception and at.session_state["nav_page"] == "Evaluate Quotations"
    assert at.session_state["selected_rfq_id"] and "Evaluating" in shown(at)


def test_loading_layout_shows_the_request_read_only_then_the_rfq():
    at = new_app()
    at.session_state["building"] = "4 pressure transmitters"
    at.session_state["rfq_request"] = "4 pressure transmitters"
    at.run()
    assert not at.exception and at.session_state["rfq_draft"] is not None  # built, then redrawn as the RFQ
    assert "building" not in at.session_state


def test_evaluate_shows_the_chosen_rfq_as_a_card_with_a_way_to_change_it():
    at = saved_app()
    [b for b in at.button if b.label == "Select for evaluation"][0].click().run()
    assert not at.exception
    assert "Evaluating" in shown(at) and "3 items" in shown(at)
    assert "Pressure transmitters" in " ".join(c.value for c in at.caption)
    [b for b in at.button if b.label == "Change RFQ"][0].click().run()
    assert at.session_state["nav_page"] == "Manage My RFQs"


def test_evaluate_without_a_selection_offers_a_chooser():
    at = saved_app()
    at.segmented_control[0].set_value("Evaluate Quotations").run()
    assert not at.exception and "Choose the RFQ to evaluate" in shown(at)
    rfq_id = next(iter(at.session_state["rfqs"]))
    at.selectbox(key="eval-rfq-select").set_value(rfq_id).run()
    assert at.session_state["selected_rfq_id"] == rfq_id and "Evaluating" in shown(at)
