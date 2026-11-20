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
    assert len(at.selectbox[0].options) == len(list((ROOT / "scenarios").glob("*.yaml")))
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


def test_ui_command_listens_on_localhost_by_default(monkeypatch):
    import subprocess

    from nichd_sim import cli

    calls = []
    monkeypatch.setattr(subprocess, "call", lambda cmd: calls.append(cmd) or 0)
    cli.main(["ui", "--headless"])
    cmd = calls[0]
    assert cmd[cmd.index("--server.address") + 1] == "127.0.0.1"
    cli.main(["ui", "--host", "0.0.0.0"])
    assert calls[1][calls[1].index("--server.address") + 1] == "0.0.0.0"


def test_live_engine_view_shows_every_step(app):
    at = app
    button(at, "Nouvel entretien").click().run()
    at.segmented_control(key="view").set_value("Moteur en direct").run()
    assert not at.exception, at.exception
    for text in ["[soutien@rapport] Bonjour Léo.", "[inv@transition] Dis-moi pourquoi tu es là.",
                 "[sug@faits:hors=il avait un couteau] Il avait un couteau, hein ?"]:
        at.chat_input(key="engine_input").set_value(text).run()
        assert not at.exception, at.exception
    assert at.segmented_control(key="view").value == "Moteur en direct"  # the view survives reruns
    text = " ".join(m.value for m in at.markdown)
    for step in ("1 · Classification", "2 · Suivi des phases", "3 · Règle du moteur", "4 · Unités autorisées",
                 "5 · Diction", "6 · Corps", "7 · Réalisation", "Faits de l'événement cible"):
        assert step in text, step
    assert {m.label for m in at.metric} >= {"Activation", "Réticence", "Acquiescement", "Verbosité"}


def test_profile_adjustments_apply_to_the_next_interview(app):
    at = app
    chosen = at.selectbox(key="scenario_id").value
    at.slider(key=f"{chosen}:reluctance").set_value(0.95).run()
    at.selectbox(key=f"{chosen}:style").set_value("frozen").run()
    button(at, "Nouvel entretien").click().run()
    assert not at.exception, at.exception
    profile = at.session_state["session"].scenario.child_profile
    assert profile.reluctance == 0.95 and profile.expression_style == "frozen"


def test_system_map_lights_the_path_of_the_turn(app):
    at = app
    button(at, "Nouvel entretien").click().run()
    at.segmented_control(key="view").set_value("Graphe du système").run()
    assert not at.exception, at.exception
    at.chat_input(key="graph_input").set_value("[sug@faits:hors=il avait un couteau] Il avait un couteau ?").run()
    assert not at.exception, at.exception
    assert at.segmented_control(key="view").value == "Graphe du système"
    import base64
    import re
    bodies = " ".join(h.proto.body for h in at.get("html"))
    svg = " ".join(base64.b64decode(m).decode() for m in re.findall(r"base64,([A-Za-z0-9+/=]+)", bodies))
    assert "MOTEUR DE COMPORTEMENT" in svg and "Réalisateur (LLM)" in svg
    assert "class='n chip on" in svg  # the suggestive rule lit up


def test_wait_button_adds_a_silent_turn(app, tmp_path):
    """Plan lot 5 (A12): « Attendre » lets a silence run on, without an utterance."""
    at = app
    button(at, "Nouvel entretien").click().run()
    assert not any(b.label == "Attendre" for b in at.button)  # nothing to wait for yet
    at.chat_input[0].set_value("[inv@transition] Raconte-moi tout ce qui s'est passé.").run()
    button(at, "Attendre").click().run()
    assert not at.exception, at.exception
    assert len(at.chat_message) == 4
    assert "attente silencieuse" in at.chat_message[2].markdown[0].value
