"""Experiment 3 - Iterative Refinement: Romeo and Juliet in two sentences.

Three rounds of prompt tweaking on one simple task:
  Round 1  minimal instruction
  Round 2  adds length and style constraints
  Round 3  adds key content elements (setting and themes)
Each response is scored on sentence count and content coverage, and a
summary shows how every iteration changed the result.

Run:  streamlit run app.py
"""
from __future__ import annotations

import re
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(page_title="Quill & Iterate", page_icon="🪶", layout="centered")

OFFLINE, GEMINI = "Offline demo (scripted replies)", "Gemini API"
TARGET_SENTENCES = 2

ROUNDS = [
    {"title": "Minimal Instruction", "color": "#E4637C",
     "desc": "Start with a bare request and observe the unrestricted response.",
     "prompt": "Summarize the plot of Romeo and Juliet."},
    {"title": "Length + Style Constraints", "color": "#E8B04B",
     "desc": "Add explicit limits on length and writing style.",
     "prompt": "Summarize the plot of Shakespeare's Romeo and Juliet in exactly two sentences "
               "using clear, concise language suitable for a general audience."},
    {"title": "Key Content Requirements", "color": "#6FD3B0",
     "desc": "Name the setting and themes that must appear in the answer.",
     "prompt": "Summarize the plot of Shakespeare's Romeo and Juliet in exactly two sentences "
               "using clear, concise language suitable for a general audience. Include the "
               "setting of Verona and highlight the central themes of love, family conflict, "
               "and tragedy."},
]

# Words that count as covering each required content element.
CONTENT = {
    "Verona": ["verona"],
    "Love": ["love", "lovers", "romance"],
    "Family conflict": ["feud", "rival", "hatred", "enemies", "family conflict"],
    "Tragedy": ["tragic", "tragedy", "death", "dead", "die"],
}

OFFLINE_REPLIES = [
    "Romeo and Juliet is a tragedy by William Shakespeare about two teenagers whose love is "
    "doomed by the hatred between their families.\n\n"
    "In the Italian city of Verona, the Montagues and the Capulets have been enemies for "
    "generations. Romeo, a Montague, sneaks into a Capulet party and falls in love with Juliet "
    "at first sight. The next day, with the help of Friar Laurence, they marry in secret, "
    "hoping their union might end the feud.\n\n"
    "Trouble follows quickly. Juliet's cousin Tybalt kills Romeo's friend Mercutio, and Romeo "
    "avenges him by killing Tybalt, so the Prince banishes Romeo from Verona. Juliet's parents "
    "then insist that she marry Paris, and she turns to the Friar, who gives her a potion that "
    "makes her appear dead.\n\n"
    "The Friar's letter explaining the plan never reaches Romeo. Believing Juliet is truly "
    "dead, Romeo buys poison and drinks it beside her in the family tomb. Juliet wakes, finds "
    "him dead, and stabs herself.\n\n"
    "Shaken by the loss of their children, the two families finally end their feud.",
    "Two young lovers from rival families secretly marry, but a chain of unlucky mistakes ends "
    "in both of their deaths. Their loss finally persuades their parents to end the long "
    "hatred between them.",
    "In the Italian city of Verona, Romeo Montague and Juliet Capulet fall in love despite the "
    "bitter feud between their families, and a series of misunderstandings leads to their "
    "tragic deaths. Their sacrifice finally ends the hatred, showing how love can be destroyed "
    "by family conflict and how tragedy can bring peace.",
]


# --------------------------------------------------------------------------- #
# Generation and evaluation
# --------------------------------------------------------------------------- #

def call_gemini(prompt: str, api_key: str, model: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    try:
        resp = requests.post(url, params={"key": api_key},
                             json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except requests.HTTPError as exc:
        return f"⚠️ API error (HTTP {exc.response.status_code}). Check your key and model name."
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return "⚠️ Could not get a valid response from the API."


def count_sentences(text: str) -> int:
    clean = re.sub(r"[*_`#]", "", text).strip()
    return len([s for s in re.split(r"(?<=[.!?])\s+", clean) if re.search(r"\w", s)])


def evaluate(text: str) -> dict:
    low = text.lower()
    covered = {name: any(w in low for w in words) for name, words in CONTENT.items()}
    sentences = count_sentences(text)
    return {
        "sentences": sentences,
        "sentences_ok": sentences == TARGET_SENTENCES,
        "covered": covered,
        "score": int(sentences == TARGET_SENTENCES) + sum(covered.values()),
    }


def max_score() -> int:
    return 1 + len(CONTENT)


def run_round(i: int, mode: str, api_key: str, model: str) -> None:
    prompt = st.session_state[f"prompt{i}"]
    text = OFFLINE_REPLIES[i] if mode == OFFLINE else call_gemini(prompt, api_key, model)
    st.session_state.results[i] = {"prompt": prompt, "text": text, "eval": evaluate(text)}


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def build_report(results: list[dict]) -> str:
    lines = ["# Experiment 3 - Iterative Refinement on a Simple Task",
             f"_Generated {datetime.now():%Y-%m-%d %H:%M}_", ""]
    for i, (r, res) in enumerate(zip(ROUNDS, results), start=1):
        ev = res["eval"]
        cov = ", ".join(f"{k}: {'present' if v else 'missing'}" for k, v in ev["covered"].items())
        lines += [f"## Round {i}: {r['title']}", "**Prompt**", "```", res["prompt"], "```",
                  "**Response**", "", res["text"], "",
                  f"- Sentences: {ev['sentences']} / {TARGET_SENTENCES}",
                  f"- Content coverage: {cov}",
                  f"- Score: {ev['score']}/{max_score()}", ""]
    lines += ["## Iteration summary", "| Round | Sentences | Coverage | Score |", "|---|---|---|---|"]
    for i, res in enumerate(results, start=1):
        ev = res["eval"]
        lines.append(f"| {i} | {ev['sentences']} | {sum(ev['covered'].values())}/{len(CONTENT)} "
                     f"| {ev['score']}/{max_score()} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

CSS = """
<style>
.block-container {max-width: 900px; padding-top: 2rem;}
.title h1 {margin: 0; font-size: 2rem;
  background: linear-gradient(90deg,#E4637C,#E8B04B,#6FD3B0);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
.title p {color: #B9A7C4; margin: .2rem 0 0;}
.round {border-left: 4px solid var(--c); padding: .1rem 1rem; margin-top: 2.2rem;}
.round .eyebrow {color: var(--c); font-size: .72rem; font-weight: 700; letter-spacing: 2px;}
.round h2 {margin: .1rem 0; font-size: 1.4rem;}
.round p {color: #B9A7C4; margin: 0 0 .4rem;}
.lbl {font-size: .72rem; letter-spacing: 1.5px; color: #B9A7C4; margin: .8rem 0 .3rem;}
.pill {display: inline-block; margin: 2px 6px 2px 0; padding: 3px 11px; border-radius: 8px;
  font-size: .8rem; font-weight: 600;}
.ok {background: rgba(111,211,176,.15); color: #6FD3B0; border: 1px solid #6FD3B0;}
.bad {background: rgba(228,99,124,.15); color: #FF8DA1; border: 1px solid #E4637C;}
</style>
"""


def pill(text: str, ok: bool) -> str:
    return f'<span class="pill {"ok" if ok else "bad"}">{"✓" if ok else "✗"} {text}</span>'


def init_state() -> None:
    st.session_state.setdefault("results", [None] * len(ROUNDS))
    for i, r in enumerate(ROUNDS):
        st.session_state.setdefault(f"prompt{i}", r["prompt"])


def reset_all() -> None:
    st.session_state.results = [None] * len(ROUNDS)
    for i, r in enumerate(ROUNDS):
        st.session_state[f"prompt{i}"] = r["prompt"]


def render_sidebar() -> tuple[str, str, str]:
    with st.sidebar:
        st.markdown("### 🪶 Quill & Iterate")
        mode = st.radio("Generation mode", [OFFLINE, GEMINI])
        api_key, model = "", "gemini-2.5-flash"
        if mode == GEMINI:
            api_key = st.text_input("Gemini API key", type="password")
            model = st.text_input("Model", value=model)
        st.caption("Prompts below can be edited before running each round.")
        st.button("Reset experiment", on_click=reset_all, use_container_width=True)
    return mode, api_key, model


def ready(mode: str, api_key: str) -> bool:
    if mode == GEMINI and not api_key:
        st.error("Enter your Gemini API key in the sidebar, or switch to Offline demo.")
        return False
    return True


def render_round(i: int, mode: str, api_key: str, model: str) -> None:
    r = ROUNDS[i]
    st.markdown(f'<div class="round" style="--c:{r["color"]}"><span class="eyebrow">ROUND 0{i + 1}</span>'
                f'<h2>{r["title"]}</h2><p>{r["desc"]}</p></div>', unsafe_allow_html=True)
    st.text_area("Prompt", key=f"prompt{i}", height=90, label_visibility="collapsed")
    if st.button(f"Run Round {i + 1}", key=f"run{i}") and ready(mode, api_key):
        run_round(i, mode, api_key, model)

    res = st.session_state.results[i]
    if not res:
        return
    ev = res["eval"]
    st.markdown('<div class="lbl">AI RESPONSE</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(res["text"].replace("$", "\\$"))
    cov = "".join(pill(k, ok) for k, ok in ev["covered"].items())
    st.markdown(pill(f"Sentence count {ev['sentences']} / {TARGET_SENTENCES}", ev["sentences_ok"])
                + '<div class="lbl">CONTENT COVERAGE</div>' + cov, unsafe_allow_html=True)


def render_summary() -> None:
    results = st.session_state.results
    if not all(results):
        return
    st.markdown('<div class="round" style="--c:#B9A7C4"><span class="eyebrow">RESULT</span>'
                "<h2>How each iteration changed the response</h2></div>", unsafe_allow_html=True)
    st.table([{"Round": f"{i + 1} - {ROUNDS[i]['title']}", "Sentences": r["eval"]["sentences"],
               "Content covered": f"{sum(r['eval']['covered'].values())}/{len(CONTENT)}",
               "Score": f"{r['eval']['score']}/{max_score()}"} for i, r in enumerate(results)])
    e1, e2, e3 = (r["eval"] for r in results)
    st.markdown(
        f"- **Round 1 → 2:** sentences went from {e1['sentences']} to {e2['sentences']} "
        f"after adding length and style constraints.\n"
        f"- **Round 2 → 3:** content coverage went from {sum(e2['covered'].values())}/{len(CONTENT)} "
        f"to {sum(e3['covered'].values())}/{len(CONTENT)} after naming the setting and themes."
    )
    st.download_button("⬇ Download report (.md)", build_report(results),
                       "experiment3_report.md", "text/markdown")


def main() -> None:
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    mode, api_key, model = render_sidebar()
    st.markdown('<div class="title"><h1>Quill &amp; Iterate</h1>'
                "<p>Experiment 3 · Summarize Romeo and Juliet in two sentences through three rounds "
                "of prompt refinement.</p></div>", unsafe_allow_html=True)
    if st.button("▶ Run all rounds", type="primary") and ready(mode, api_key):
        for i in range(len(ROUNDS)):
            run_round(i, mode, api_key, model)
    for i in range(len(ROUNDS)):
        render_round(i, mode, api_key, model)
    render_summary()


if __name__ == "__main__":
    main()
