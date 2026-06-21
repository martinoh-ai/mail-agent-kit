#!/usr/bin/env python3
"""
newsletters.py — l'intelligence abonnements.

Scanne les N derniers jours, repère les newsletters (en-tête List-Unsubscribe / Precedence /
List-Id via detectors), les regroupe PAR EXPÉDITEUR, et calcule l'engagement :
reçus / lus (flag \\Seen) / taux de lecture / semaines sans lecture / fréquence.

Le "lu" en IMAP = flag \\Seen (proxy honnête : pas le pixel-tracking serveur de Gmail).
Sortie JSON : paniers rouge ("tu ne lis plus") / orange ("tu zappes") / vert ("tu lis vraiment").
Réutilise gmail_helper (connexion) + detectors (détection). Stdlib only.

Usage: newsletters.py [--days 90] [--max 2500]
"""
from __future__ import annotations
import sys, json, re, email, email.utils
from datetime import datetime, timezone
import gmail_helper as gh
import detectors


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--max", type=int, default=2500)
    args = ap.parse_args()

    m = gh.connect_imap()
    try:
        # dossier "Tous les messages" / "All Mail" auto-détecté via l'attribut \All (FR/EN)
        box = "INBOX"
        try:
            typ, boxes = m.list()
            for b in (boxes or []):
                s = b.decode("utf-8", "replace") if isinstance(b, (bytes, bytearray)) else str(b)
                if "\\All" in s:
                    cand = s.split(' "/" ')[-1].strip().strip('"')
                    t, _ = m.select('"%s"' % cand, readonly=True)
                    if t == "OK":
                        box = cand
                        break
        except Exception:
            pass
        if box == "INBOX":
            m.select("INBOX", readonly=True)
        typ, data = m.search(None, "X-GM-RAW", '"newer_than:%dd"' % args.days)
        ids = data[0].split() if data and data[0] else []
        capped = len(ids) > args.max
        ids = ids[-args.max:]

        HDRS = ("(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE LIST-ID LIST-UNSUBSCRIBE "
                "LIST-UNSUBSCRIBE-POST PRECEDENCE AUTO-SUBMITTED RETURN-PATH)] FLAGS INTERNALDATE)")
        agg: dict = {}
        for k in range(0, len(ids), 200):
            chunk = ",".join(i.decode() for i in ids[k:k + 200])
            typ, fdata = m.fetch(chunk, HDRS)
            if typ != "OK" or not fdata:
                continue
            for item in fdata:
                if not isinstance(item, tuple):
                    continue
                meta = item[0].decode(errors="replace")
                try:
                    msg = email.message_from_bytes(item[1])
                except Exception:
                    continue
                hdrs = {kk: vv for kk, vv in msg.items()}
                frm = gh._decode(msg.get("From", ""))
                subj = gh._decode(msg.get("Subject", ""))
                sig = detectors.detect(hdrs, frm, subj, "")
                if not sig.get("is_newsletter"):
                    continue
                addr = (email.utils.parseaddr(frm)[1] or "?").lower()
                name = email.utils.parseaddr(frm)[0] or addr
                seen = "\\Seen" in meta
                d = None
                im = re.search(r'INTERNALDATE "([^"]+)"', meta)
                if im:
                    try:
                        d = email.utils.parsedate_to_datetime(im.group(1))
                    except Exception:
                        d = None
                e = agg.setdefault(addr, {"name": name, "recus": 0, "lus": 0, "last_seen": None,
                                          "unsub_url": "", "unsub_mailto": "", "one_click": False})
                e["recus"] += 1
                if seen:
                    e["lus"] += 1
                    if d and (e["last_seen"] is None or d > e["last_seen"]):
                        e["last_seen"] = d
                if sig.get("unsub_url") and not e["unsub_url"]:
                    e["unsub_url"] = sig["unsub_url"]
                if sig.get("unsub_mailto") and not e["unsub_mailto"]:
                    e["unsub_mailto"] = sig["unsub_mailto"]
                if sig.get("one_click_unsub"):
                    e["one_click"] = True

        now = datetime.now(timezone.utc)
        rows = []
        for addr, e in agg.items():
            recus, lus = e["recus"], e["lus"]
            taux = round(lus / recus, 2) if recus else 0.0
            if e["last_seen"]:
                sem_sans = int((now - e["last_seen"]).days // 7)
            else:
                sem_sans = 99
            freq = round(recus / (args.days / 7.0), 1)
            score = int(100 * (1 - taux))
            rows.append({
                "sender": addr, "name": e["name"], "recus": recus, "lus": lus,
                "taux_lecture": taux, "semaines_sans_lecture": sem_sans, "freq_sem": freq,
                "score": score, "unsub_url": e["unsub_url"], "unsub_mailto": e["unsub_mailto"],
                "one_click": e["one_click"],
            })
        rows.sort(key=lambda r: (-r["score"], -r["recus"]))
        rouge = [r for r in rows if r["lus"] == 0 and r["recus"] >= 3]
        orange = [r for r in rows if r not in rouge and r["taux_lecture"] < 0.2 and r["recus"] >= 3]
        vert = [r for r in rows if r["taux_lecture"] > 0.5 and r["recus"] >= 2]
        out = {
            "generated_at": now.isoformat(), "days": args.days, "capped": capped,
            "total_newsletters": len(rows),
            "total_mails": sum(r["recus"] for r in rows),
            "total_lus": sum(r["lus"] for r in rows),
            "rouge": rouge[:15], "orange": orange[:10], "vert": vert[:8],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    finally:
        try:
            m.logout()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
