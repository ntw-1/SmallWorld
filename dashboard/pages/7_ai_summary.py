"""AI Summary - Featherless uncertainty-aware ecological narrative."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import os
from datetime import datetime

import streamlit as st

import config  # noqa: F401  (loads .env)
from dashboard.components import data_queries as q
from dashboard.components.ui import (html, chip, esc, page_header, section, empty_state, confidence_gate, footer)

if not q.db_exists():
    empty_state("Observatory offline", "No database found.", "python run_pipeline.py --limit 100"); st.stop()

try:
    from llm.summariser import summarise, MODEL
except Exception as e:          # openai not installed etc.
    summarise, MODEL = None, "mistralai/Mistral-7B-Instruct-v0.2"
    import_error = str(e)
else:
    import_error = None

media, det, n_cls = q.load()
has_key = bool(os.getenv("FEATHERLESS_API_KEY"))
page_header("AI Summary",
            "A natural-language field report written by an LLM from the survey statistics below. The prompt instructs "
            "the model to state unverified counts, low-confidence species and data limitations instead of overstating certainty.",
            tiles=[("Model", MODEL.split("/")[-1].replace("-Instruct", ""), "", None),
                   ("API key", "Ready" if has_key else "Missing", ".env", "var(--secondary)" if has_key else "var(--error)")])

with st.container(key="panel_gate_ai"):
    min_conf = confidence_gate()
snap = q.llm_snapshot(media, det, n_cls, min_conf)
html('<div style="height:16px"></div>')

left, right = st.columns([1.6, 1], gap="medium")
with right:
    with st.container(key="panel_snapshot"):
        section("Data snapshot sent to the model", "Recomputed live at the current confidence gate")
        s = snap["survey"]
        rows = [("Images", s["images"]), ("Stations", s["stations"]), ("Trap-nights", s["trap_nights"]),
                ("Independent encounters", snap["independent_encounters"]),
                ("Nocturnal share", f"{snap['diel_activity_pct']['nocturnal']}%"),
                ("Unverified detections", snap["unverified_detections"]),
                ("SpeciesNet classifications", snap["species_classified_by_speciesnet"]),
                ("Label provenance", ", ".join(f"{k}: {v}" for k, v in snap["label_provenance"].items()) or "—")]
        html("".join(f'<div style="display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid '
                     f'rgba(120,148,119,.08)"><span class="sw-label">{k}</span><span class="sw-mono" style="text-align:right">{esc(str(v))}</span></div>'
                     for k, v in rows))
        with st.expander("Full JSON payload"):
            st.json(snap)

with left:
    with st.container(key="panel_story"):
        section("Field report", f"Gate ≥ {min_conf:.0%} · 30-min independence window",
                chip("Featherless API", "primary") + chip("Uncertainty-aware", "tertiary"))
        if import_error:
            st.error(f"LLM client unavailable ({import_error}). Run: pip install openai")
        elif not has_key:
            st.warning("FEATHERLESS_API_KEY is missing from your .env file, so the report can't be generated yet.")
        go = st.button("Generate field report", type="primary", disabled=bool(import_error) or not has_key)
        if go:
            try:
                text = st.write_stream(summarise(snap))
                st.session_state["ai_report"] = {"text": text, "at": datetime.now().strftime("%Y-%m-%d %H:%M"), "gate": min_conf}
            except Exception as e:
                st.error(f"Featherless call failed: {e}")
        elif st.session_state.get("ai_report"):
            r = st.session_state["ai_report"]
            html(f'<div class="sw-sub" style="margin-bottom:8px">Generated {r["at"]} at gate ≥ {r["gate"]:.0%}</div>')
            st.markdown(r["text"])
        else:
            empty_state("No report yet", "Press Generate to stream a three-paragraph summary: activity & dominant species, "
                        "temporal and spatial patterns, and data limitations.")
        if st.session_state.get("ai_report"):
            r = st.session_state["ai_report"]
            md = (f"# SmallWorld field report\n\nGenerated {r['at']} · model {MODEL} · confidence gate ≥ {r['gate']:.0%}\n\n"
                  f"{r['text']}\n\n## Data snapshot\n\n```json\n{json.dumps(snap, indent=2, default=str)}\n```\n")
            st.download_button("Download report (.md)", md, file_name="smallworld_field_report.md", mime="text/markdown")

footer()
