#!/usr/bin/env python3
"""
relabel.py — libellise l'inbox de façon DÉTERMINISTE et EXCLUSIVE : un seul libellé Triage/ par email.

Pas d'IA pour le tri visible (l'IA est incohérente + empile les libellés). Ici, règle dure
via detectors :
  - newsletter (List-Unsubscribe/Precedence) → Triage/A lire
  - no_reply (code/reçu/notif/no-reply)      → Triage/A voir
  - reste (vrai humain attendu)              → Triage/A repondre

Exclusif : retire TOUS les Triage/* avant de poser le bon. Réutilise gmail_helper + detectors.
Usage: relabel.py [--query "newer_than:14d"] [--max 300]
"""
from __future__ import annotations
import sys, email
import gmail_helper as gh
import detectors

ALL_LABELS = ["Triage/A repondre", "Triage/A voir", "Triage/A lire", "Triage/Urgent"]


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="newer_than:14d")
    ap.add_argument("--max", type=int, default=300)
    args = ap.parse_args()

    m = gh.connect_imap()
    counts = {"Triage/A repondre": 0, "Triage/A voir": 0, "Triage/A lire": 0}
    try:
        m.select("INBOX")  # lecture-écriture (STORE)
        typ, data = m.search(None, "X-GM-RAW", '"%s"' % args.query)
        ids = data[0].split() if data and data[0] else []
        ids = ids[-args.max:]
        HDRS = ("(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT LIST-ID LIST-UNSUBSCRIBE LIST-UNSUBSCRIBE-POST "
                "PRECEDENCE AUTO-SUBMITTED RETURN-PATH X-AUTO-RESPONSE-SUPPRESS FEEDBACK-ID X-AUTOREPLY REPLY-TO)])")
        remove_arg = " ".join('"%s"' % l for l in ALL_LABELS)
        for k in range(0, len(ids), 100):
            chunk = ",".join(i.decode() for i in ids[k:k + 100])
            typ, fd = m.fetch(chunk, HDRS)
            if typ != "OK" or not fd:
                continue
            for item in fd:
                if not isinstance(item, tuple):
                    continue
                meta = item[0].decode(errors="replace")
                sid = meta.split(" ", 1)[0]
                try:
                    msg = email.message_from_bytes(item[1])
                except Exception:
                    continue
                hdrs = {kk: vv for kk, vv in msg.items()}
                frm = gh._decode(msg.get("From", ""))
                subj = gh._decode(msg.get("Subject", ""))
                sig = detectors.detect(hdrs, frm, subj, "")
                if sig.get("is_newsletter"):
                    lab = "Triage/A lire"
                elif sig.get("no_reply"):
                    lab = "Triage/A voir"
                else:
                    lab = "Triage/A repondre"
                # exclusif : retire tous les Triage/*, puis pose le bon
                try:
                    m.store(sid, "-X-GM-LABELS", remove_arg)
                    m.store(sid, "+X-GM-LABELS", '"%s"' % lab)
                    counts[lab] = counts.get(lab, 0) + 1
                except Exception as e:
                    sys.stderr.write("store fail %s: %s\n" % (sid, e))
        print(counts)
    finally:
        try:
            m.logout()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
