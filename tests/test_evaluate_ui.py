from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.ui import resources
from tests.quote_fixtures import ScriptedGemini, make_rfq, make_xlsx, standard_rows, standard_wire
from app.services.gemini_client import RateLimited

MAIN = Path(__file__).resolve().parent.parent / "app" / "main.py"


def evaluate_app(client, step=2, **session) -> AppTest:
    rfq = make_rfq()
    rfq.status = "saved"
    at = AppTest.from_file(str(MAIN), default_timeout=60)
    at.session_state["rfqs"] = {rfq.rfq_id: rfq}
    at.session_state["selected_rfq_id"] = rfq.rfq_id
    at.session_state["nav_page"] = "Evaluate Quotations"
    at.session_state["eval_step"] = step
    for k, v in session.items():
        at.session_state[k] = v
    resources.client = lambda: client  # the page asks resources.client() for Gemini
    return at.run()


def shown(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_step_bar_and_upload_screen():
    at = evaluate_app(ScriptedGemini(standard_wire()))
    assert not at.exception
    text = shown(at)
    assert "step-active" in text and "Select RFQ" in text and "Compare" in text and "step-locked" in text
    assert "Upload vendor quotations" in text
    assert [b for b in at.button if b.label == "Analyze quotes"][0].disabled


def test_analysing_reads_files_and_lands_on_the_review_step():
    client = ScriptedGemini(standard_wire())
    at = evaluate_app(client, analysing=[("Quote-A.xlsx", make_xlsx(standard_rows()))])
    assert not at.exception
    assert at.session_state["eval_step"] == 3 and client.extract_calls == 1
    text = shown(at)
    assert "matrix" in text and "Centrifugal pumps" in text and "Vendor-wise Quote Review" in text
    quotes = list(at.session_state["quotations"].values())
    assert len(quotes) == 1 and quotes[0].status == "validated"


def test_a_bad_file_does_not_stop_the_good_one_and_is_listed_with_a_reason():
    client = ScriptedGemini(standard_wire())
    files = [("bad.xls", b"junk"), ("good.xlsx", make_xlsx(standard_rows()))]
    at = evaluate_app(client, analysing=files)
    quotes = list(at.session_state["quotations"].values())
    assert sorted(q.status for q in quotes) == ["rejected", "validated"]
    at.session_state["eval_step"] = 2
    at.run()
    assert "Not used" in shown(at) and "Save it as .xlsx" in " ".join(c.value for c in at.caption)


def test_rate_limited_file_can_be_tried_again():
    limited = ScriptedGemini(extract_error=RateLimited("x"))
    at = evaluate_app(limited, analysing=[("q.xlsx", make_xlsx(standard_rows()))])
    quote = next(iter(at.session_state["quotations"].values()))
    assert quote.status == "failed" and at.session_state["eval_step"] == 2
    resources.client = lambda: ScriptedGemini(standard_wire())
    [b for b in at.button if b.label == "Try again"][0].click().run()
    assert not at.exception and next(iter(at.session_state["quotations"].values())).status == "validated"


def flagged_rows():
    return [["No", "Description", "Qty", "UOM", "Rate", "Amount"],
            [1, "Centrifugal pumps", 2, None, 47800, 95600], [2, "Ball valves", 10, "Nos", 0, 0]]


def test_review_buttons_accept_and_exclude():
    client = ScriptedGemini(standard_wire(flagged_rows()))
    at = evaluate_app(client, analysing=[("q.xlsx", make_xlsx(flagged_rows()))])
    quote = next(iter(at.session_state["quotations"].values()))
    assert quote.status == "needs_review" and "chip-fix" in shown(at) and "chip-review" in shown(at)
    pump = next(l for l in quote.lines if l.source_description == "Centrifugal pumps")
    accept = [b for b in at.button if b.key and b.key.endswith(f"{pump.line_id}:Q19")][0]
    accept.click().run()
    assert not at.exception and "chip-reviewed" in shown(at)
    valve = next(l for l in quote.lines if l.source_description == "Ball valves")
    [b for b in at.button if b.key and b.key.startswith("exl-") and valve.line_id in b.key][0].click().run()
    quote = next(iter(at.session_state["quotations"].values()))
    assert quote.status == "validated" and next(l for l in quote.lines if l.line_id == valve.line_id).excluded
    assert "Excluded" in shown(at) or "excluded" in shown(at)


def test_remove_and_next_gating():
    at = evaluate_app(ScriptedGemini(standard_wire()), step=2)
    assert [b for b in at.button if b.label == "Next"][0].disabled  # nothing analysed yet
    at = evaluate_app(ScriptedGemini(standard_wire()), analysing=[("q.xlsx", make_xlsx(standard_rows()))])
    at.session_state["eval_step"] = 2
    at.run()
    assert not [b for b in at.button if b.label == "Next"][0].disabled
    [b for b in at.button if b.label == "Remove"][0].click().run()
    assert not at.session_state["quotations"]


def test_manage_select_lands_on_upload_step():
    at = AppTest.from_file(str(MAIN), default_timeout=60).run()
    at.chat_input[0].set_value("4 pressure transmitters, 10 gate valves").run()
    at.button(key="save-rfq").click().run()
    [b for b in at.button if b.label == "View in Manage RFQs"][0].click().run()
    [b for b in at.button if b.label == "Select for evaluation"][0].click().run()
    assert at.session_state["nav_page"] == "Evaluate Quotations" and at.session_state["eval_step"] == 2


def test_live_feed_shows_found_lines_and_counts():
    from app.ui import analysis_loader as al
    f = al.FileProgress("q.xlsx", status="active", stage="extract", started=0)
    for n in range(6):
        f.found.append(al.feed_text({"desc": f"Item {n} <b>", "qty": "2", "unit": "Nos", "cur": "INR", "price": "100"}))
    page = al.render_html([f], [])
    assert "6 lines found" in page and "Item 5 &lt;b&gt; · 2 Nos · INR 100" in page
    assert "Item 0" not in page            # only the latest few are shown


def _analysed(monkeypatch, step):
    from app.services import fx
    monkeypatch.setattr(fx, "fetch_rates", lambda currencies, base=None: {})
    client = ScriptedGemini(standard_wire())
    at = evaluate_app(client, analysing=[("a.xlsx", make_xlsx(standard_rows()))])
    at.session_state["eval_step"] = step
    return at.run()


def test_next_on_the_review_step_opens_compare(monkeypatch):
    at = _analysed(monkeypatch, 3)
    nxt = [b for b in at.button if b.key == "step-next"][0]
    assert not nxt.disabled
    nxt.click()
    at.run()
    text = shown(at)
    assert not at.exception and at.session_state["eval_step"] == 4
    for part in ("Purchase Proposal", "Ask the analyst for a purchase proposal", "Lowest offer for each item", "Vendor totals"):
        assert part in text
    assert "Centrifugal pumps" in text and "47,800.00" in text
    assert text.index("Purchase Proposal") < text.index("Lowest offer for each item") < text.index("Vendor totals")


def test_compare_has_no_assumption_controls_and_the_step_bar_has_four_steps(monkeypatch):
    at = _analysed(monkeypatch, 4)
    assert not at.exception
    assert not any("Assumptions" in e.label for e in at.expander) and not at.toggle and not at.multiselect
    text = shown(at)
    assert "Compare" in text and ">Ask<" not in text and text.count("class='step ") == 4


def chat_text(at) -> str:
    return " ".join(md.value for message in at.chat_message for md in message.markdown)


def _compare_with(monkeypatch, proposals, **kw):
    from app.services import fx
    monkeypatch.setattr(fx, "fetch_rates", lambda currencies, base=None: {})
    client = ScriptedGemini(standard_wire(), proposals=proposals, **kw)
    at = evaluate_app(client, analysing=[("a.xlsx", make_xlsx(standard_rows()))])
    at.session_state["eval_step"] = 4
    return at.run(), client


def test_a_request_produces_a_proposal_above_the_summaries(monkeypatch):
    from tests.quote_fixtures import wire_rules
    at, client = _compare_with(monkeypatch, [wire_rules("I will build the cheapest purchase.", allow_split=True)])
    at.chat_input(key="analyst-input").set_value("Make me a purchase summary allowing split purchases").run()
    assert not at.exception and client.propose_calls == 1
    text = shown(at)
    assert "Grand total" in text and "I will build the cheapest purchase." in chat_text(at)
    assert "Split purchases allowed" in text and "Earlier proposals" not in text
    turns = at.session_state["analyst_turns"]
    assert len(turns) == 1 and turns[0].proposal.grand_total is not None
    at.chat_input(key="analyst-input").set_value("Now again").run()
    assert "Earlier proposals (1)" in " ".join(e.label for e in at.expander)


def test_the_analyst_offers_no_suggestions_and_the_lowest_offers_show_a_total(monkeypatch):
    at = _analysed(monkeypatch, 4)
    text = shown(at)
    assert not [b for b in at.button if b.key.startswith("ex-")] and "Try one of these" not in text
    assert "Total of the lowest offers" in text


def test_the_analyst_is_disabled_without_a_key_and_failures_are_readable(monkeypatch):
    from app.services.gemini_client import MockGemini, RateLimited
    from tests.quote_fixtures import wire_rules
    at, client = _compare_with(monkeypatch, [wire_rules()])
    at.session_state["analyst_turns"] = []
    resources.client = lambda: MockGemini()
    at.run()
    assert at.chat_input(key="analyst-input").disabled
    at2, _ = _compare_with(monkeypatch, [wire_rules()], propose_error=RateLimited("x"))
    at2.chat_input(key="analyst-input").set_value("cheapest").run()
    assert not at2.exception and "busy" in chat_text(at2)
