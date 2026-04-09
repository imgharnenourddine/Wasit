from app.agents.delegate_intent import infer_delegate_intent


def test_infer_poll_intent() -> None:
    assert infer_delegate_intent("Votez pour reporter le cours") == "poll_needed"


def test_infer_autonomous_markers() -> None:
    assert infer_delegate_intent("Quels sont les examens la semaine prochaine?") == "autonomous_answer"


def test_infer_aggregate_long_question() -> None:
    assert infer_delegate_intent("Pourriez-vous expliquer la procédure d'inscription au stage?") == "aggregate_request"
