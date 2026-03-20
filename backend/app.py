from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import asyncio, json, os, io, time

# Load .env locally only — on Vercel env vars are set in dashboard
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
except Exception:
    pass

# Force read from environment
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "") or sk-or-v1-2e1f6002494df445792e3d0c33f2f9c747b4ec80d9ad8bd5b1b88cd3bf418f3
os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY

from modules.clinical       import fetch_clinical_trials
from modules.patents        import fetch_patents
from modules.market         import fetch_market_data
from modules.regulatory     import fetch_regulatory_data
from modules.synthesizer    import synthesize_report
from modules.scorer         import compute_confidence
from modules.pubmed         import fetch_pubmed
from modules.followup       import answer_followup
from modules.contradiction  import detect_contradictions
from modules.context_memory import (extract_clinical_context,
                                     build_synthesis_context)

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), "../frontend/templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "../frontend/static"))
CORS(app)

# ── routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    api_set = bool(os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
    return jsonify({"status": "ok", "api_key_set": api_set})

@app.route("/analyze", methods=["POST"])
def analyze():
    data     = request.get_json()
    molecule = data.get("molecule", "").strip()
    if not molecule:
        return jsonify({"error": "No molecule name provided"}), 400
    if len(molecule) > 100:
        return jsonify({"error": "Molecule name too long"}), 400
    try:
        loop   = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_pipeline(molecule))
        loop.close()
        return jsonify(result)
    except Exception as e:
        print(f"[Pipeline error] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/compare", methods=["POST"])
def compare():
    data = request.get_json()
    m1   = data.get("molecule1", "").strip()
    m2   = data.get("molecule2", "").strip()
    if not m1 or not m2:
        return jsonify({"error": "Two molecule names required"}), 400
    try:
        loop   = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        r1, r2 = loop.run_until_complete(
            asyncio.gather(run_pipeline(m1), run_pipeline(m2)))
        loop.close()
        return jsonify({"molecule1": r1, "molecule2": r2})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/batch", methods=["POST"])
def batch():
    data      = request.get_json()
    molecules = data.get("molecules", [])
    molecules = [m.strip() for m in molecules if m.strip()][:5]
    if not molecules:
        return jsonify({"error": "No molecules provided"}), 400
    try:
        loop    = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            asyncio.gather(*[run_pipeline(m) for m in molecules]))
        loop.close()
        results_sorted = sorted(
            results,
            key=lambda r: r.get("confidence", {}).get("total", 0),
            reverse=True)
        return jsonify({"results": results_sorted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/followup", methods=["POST"])
def followup():
    data     = request.get_json()
    question = data.get("question", "").strip()
    context  = data.get("context", {})
    if not question:
        return jsonify({"error": "No question provided"}), 400
    try:
        loop   = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        answer = loop.run_until_complete(answer_followup(question, context))
        loop.close()
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── pipeline ──────────────────────────────────────────────────────────────────

async def run_pipeline(molecule):
    t0 = time.time()
    print(f"[Orchestrator] Starting: {molecule}")

    clinical, patents, market, regulatory, pubmed = await asyncio.gather(
        fetch_clinical_trials(molecule),
        fetch_patents(molecule),
        fetch_market_data(molecule),
        fetch_regulatory_data(molecule),
        fetch_pubmed(molecule)
    )

    clinical_ctx = extract_clinical_context(clinical)
    cross_ctx    = build_synthesis_context(
        molecule, clinical, patents, market, regulatory, pubmed, clinical_ctx)
    confidence   = compute_confidence(clinical, patents, market, regulatory)
    report       = await synthesize_report(
        molecule, clinical, patents, market, regulatory, cross_ctx)

    if isinstance(report, dict):
        report["confidence_score"]     = confidence["total"]
        report["confidence_breakdown"] = confidence["breakdown"]
        report["confidence_label"]     = confidence["label"]

    contradictions = detect_contradictions(clinical, patents, market, regulatory, report)
    elapsed        = round(time.time() - t0, 1)

    print(f"[Orchestrator] Done in {elapsed}s: {molecule}")

    return {
        "molecule":         molecule,
        "clinical":         clinical,
        "patents":          patents,
        "market":           market,
        "regulatory":       regulatory,
        "pubmed":           pubmed,
        "report":           report,
        "confidence":       confidence,
        "contradictions":   contradictions,
        "clinical_context": clinical_ctx,
        "elapsed_seconds":  elapsed
    }

if __name__ == "__main__":
    api_set = bool(os.environ.get("OPENROUTER_API_KEY"))
    print("RepurposeAI starting...")
    print(f"   API key : {'set' if api_set else 'not set'}")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
