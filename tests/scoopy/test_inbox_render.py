from inbox_render import render_card, render_inbox


def test_render_card_includes_essentials():
    card = {
        "contact_id": "c1",
        "draft": "Hi Mrs Jenkins",
        "reasoning": "asked how to pay",
        "action_type": "in_scope",
        "pending_actions": [{"skill": "ghl_send_message"}],
    }
    html = render_card("abc123", card)
    assert "abc123" in html
    assert "c1" in html
    assert "Hi Mrs Jenkins" in html
    assert "asked how to pay" in html
    assert "in_scope" in html
    assert "ghl_send_message" in html
    assert "Approve" in html
    assert "Reject" in html
    assert "/api/plugins/scoopy/scoopy_approve" in html


def test_render_card_escapes_html_in_user_content():
    card = {
        "contact_id": "<script>alert('x')</script>",
        "draft": "<b>not bold</b>",
        "reasoning": "&",
        "action_type": "drift",
        "pending_actions": [],
    }
    html = render_card("t1", card)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>not bold</b>" not in html
    assert "&amp;" in html


def test_render_inbox_empty():
    html = render_inbox([])
    assert "No pending" in html


def test_render_inbox_multiple_cards():
    cards = [
        ("t1", {"contact_id": "c1", "draft": "d1", "reasoning": "r1", "action_type": "in_scope", "pending_actions": []}),
        ("t2", {"contact_id": "c2", "draft": "d2", "reasoning": "r2", "action_type": "drift",    "pending_actions": []}),
    ]
    html = render_inbox(cards)
    assert "card-t1" in html
    assert "card-t2" in html
