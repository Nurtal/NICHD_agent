"""Smoke test of the Streamlit interface (#11), offline mode (no LLM)."""

import pytest

from doubles import ROOT

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "src" / "nichd_sim" / "ui" / "app.py")


def button(at, label):
    return next(b for b in at.button if b.label == label)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("NICHD_OFFLINE", "1")
    monkeypatch.setenv("NICHD_LOG_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_full_session_with_trainer_mode_and_feedback(app, tmp_path):
    at = app
    assert not at.exception
    assert len(at.selectbox[0].options) == 3
    button(at, "Nouvel entretien").click().run()
    at.toggle(key="trainer").set_value(True).run()

    for text in ["[soutien@rapport] Bonjour Léo.", "[inv@transition] Dis-moi pourquoi tu es là.",
                 "[sug@faits:hors=il avait un couteau] Il avait un couteau, hein ?"]:
        at.chat_input[0].set_value(text).run()
        assert not at.exception, at.exception
    assert len(at.chat_message) == 6
    assert "Bonjour Léo." in at.chat_message[0].markdown[0].value  # tag stripped
    assert any("Phase courante" in m.value for m in at.markdown)
    assert any("Réticence" in (p.proto.text or "") for p in at.get("progress"))

    button(at, "Terminer l'entretien").click().run()
    at.text_area(key="summary").set_value("Léo était au parc avec sa mamie.").run()
    button(at, "Voir le retour").click().run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert labels == ["Questions ouvertes (phase substantive)", "Informations exactes recueillies", "Score de contamination"]
    assert any("Transcription annotée" in h.value for h in at.subheader)
    assert list(tmp_path.glob("session_*.json")), "the session log is written"


def test_bad_manual_tag_shows_help_without_crashing(app):
    at = app
    button(at, "Nouvel entretien").click().run()
    at.chat_input[0].set_value("bonjour sans préfixe").run()
    assert not at.exception
    assert at.error and "Préfixez" in at.error[0].value


def test_switching_scenario_resets_the_interview(app):
    at = app
    button(at, "Nouvel entretien").click().run()
    at.chat_input[0].set_value("[inv] Raconte.").run()
    at.selectbox(key="scenario_id").set_value("s03_vol_boulangerie").run()
    assert not at.exception
    assert len(at.chat_message) == 0
    assert any("Choisissez un scénario" in m.value for m in at.markdown)
