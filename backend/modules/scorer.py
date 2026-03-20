"""
Rebalanced confidence scoring engine.
Rewards evidence, usage volume and regulatory clarity.
Penalises only when data is genuinely absent.
"""

def compute_confidence(clinical, patents, market, regulatory):
    score = 0
    breakdown = {}

    # --- Clinical (0-35) ---
    c = 0
    trials      = clinical.get("trials", [])
    total       = clinical.get("total_found", 0) or len(trials)
    active      = [t for t in trials if "RECRUIT" in (t.get("status") or "").upper()]
    late_phase  = [t for t in trials if any(p in (t.get("phase") or "")
                   for p in ["PHASE2","PHASE3","PHASE_2","PHASE_3","2","3","4","PHASE4","PHASE_4"])]

    if total >= 1:  c += 10
    if total >= 5:  c += 8
    if total >= 10: c += 5
    if active:      c += 7
    if late_phase:  c += 5
    c = min(c, 35)

    breakdown["clinical"] = {
        "score": c, "max": 35,
        "reason": f"{total} trials, {len(active)} recruiting, {len(late_phase)} late-phase"
    }
    score += c

    # --- Patents (0-25) ---
    p = 0
    info    = patents.get("compound_info", {})
    n_pat   = patents.get("total_patents", 0)

    if info.get("formula"):   p += 8   # compound confirmed
    if info.get("cid"):       p += 5   # in PubChem
    if n_pat == 0:            p += 12  # completely free
    elif n_pat <= 3:          p += 8   # few patents
    elif n_pat <= 8:          p += 5   # some patents — still workable
    else:                     p += 2   # heavily patented
    p = min(p, 25)

    breakdown["patents"] = {
        "score": p, "max": 25,
        "reason": f"{n_pat} patents, compound {'identified' if info.get('formula') else 'not found'}"
    }
    score += p

    # --- Market (0-25) ---
    m = 0
    events   = market.get("adverse_event_reports", 0)
    products = market.get("products_found", 0)
    mfrs     = len(market.get("manufacturers", []))

    if products >= 1:     m += 8
    if events > 100:      m += 5
    if events > 5000:     m += 5
    if events > 50000:    m += 5  # blockbuster
    if mfrs > 1:          m += 2
    m = min(m, 25)

    breakdown["market"] = {
        "score": m, "max": 25,
        "reason": f"{products} products, {events:,} adverse event reports"
    }
    score += m

    # --- Regulatory (0-15) ---
    r = 0
    approvals    = regulatory.get("approvals", [])
    indications  = regulatory.get("current_indications", [])
    warnings     = regulatory.get("warnings", [])
    contra       = regulatory.get("contraindications", [])

    if approvals:              r += 7
    if indications:            r += 5
    if not warnings:           r += 2
    if not contra:             r += 1
    r = min(r, 15)

    breakdown["regulatory"] = {
        "score": r, "max": 15,
        "reason": f"{len(approvals)} approvals, {'indications found' if indications else 'no indications'}"
    }
    score += r

    total_score = min(score, 100)
    return {
        "total":     total_score,
        "breakdown": breakdown,
        "label":     _label(total_score)
    }

def _label(s):
    if s >= 75: return "High confidence"
    if s >= 50: return "Moderate confidence"
    if s >= 25: return "Low confidence"
    return "Insufficient data"
