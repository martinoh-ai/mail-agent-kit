#!/usr/bin/env python3
"""
detectors.py — jugement déterministe "ne PAS répondre" + détection newsletter.

Le principe (RFC 3834) : un agent qui répond ne doit JAMAIS répondre à une machine.
Un brouillon n'a de sens que si une vraie personne attend une réponse de toi.

Trois couches, on s'arrête à la première qui tranche :
  A. en-têtes (Auto-Submitted, Precedence, List-*, etc.) — ~99% déterministe
  B. expéditeur + objet (no-reply@, codes, reçus, calendrier) — regex FR+EN
  C. scoring OTP/code sur l'objet+corps (nombre 4-8 chiffres + mots-clés)

Stdlib only (re). Importé par gmail_helper.py (read + commande newsletters).
"""
from __future__ import annotations
import re

# ── Couche B : expéditeurs qui ne se répondent jamais ──
RE_NOREPLY_FROM = re.compile(
    r"(^|[._-])(no.?reply|ne.?pas.?repondre|do.?not.?reply|mailer.?daemon|postmaster|"
    r"bounce|bounces|notifications?|notify|alerts?|alerte|automated|auto)([._-]|@)",
    re.I,
)
# expéditeurs "faibles" : signal seulement combiné à un objet transactionnel
RE_WEAK_FROM = re.compile(r"(^|[._-])(news|newsletter|info|hello|team|support|account|billing|facturation|comptes?)@", re.I)

# ── Couche B : objets transactionnels / sans réponse (FR + EN, sans accents) ──
SUBJECT_NOREPLY = [
    # codes / OTP / 2FA
    r"code (de )?(v[ée]rification|validation|confirmation|s[ée]curit[ée]|activation)",
    r"(verification|security|confirmation|access|login|one.?time) code",
    r"\botp\b", r"\b2fa\b", r"code (?:à|a) usage unique", r"votre code", r"your code",
    r"mot de passe (?:à|a) usage unique",
    # réinit / connexion
    r"r[ée]initialiser .*mot de passe", r"reset .*password", r"nouvelle connexion",
    r"new (sign.?in|login)", r"login attempt", r"tentative de connexion",
    # reçus / commandes / paiements
    r"re[çc]u\b", r"facture", r"invoice", r"receipt", r"confirmation de commande",
    r"votre commande", r"your order", r"order (confirmation|shipped|placed)",
    r"exp[ée]di[ée]", r"suivi (de )?colis", r"shipping", r"paiement (confirm|re[çc]u)",
    r"abonnement (renouvel|reconduit)", r"subscription (renewed|confirmed)",
    # calendrier
    r"\binvitation\b", r"\brsvp\b", r"\.ics\b", r"accepted: ", r"declined: ",
]
RE_SUBJECT_NOREPLY = re.compile("|".join(SUBJECT_NOREPLY), re.I)

# ── Couche C : pieds de page "ne répondez pas" ──
BODY_NOREPLY = [
    r"merci de ne pas r[ée]pondre", r"ne pas r[ée]pondre (?:à|a) (cet|ce)",
    r"this (is|message is) an? automated", r"do not reply", r"please do not reply",
    r"this (inbox|mailbox) is not monitored", r"adresse .*non surveill[ée]e",
    r"message .*g[ée]n[ée]r[ée] automatiquement", r"ceci est un message automatique",
]
RE_BODY_NOREPLY = re.compile("|".join(BODY_NOREPLY), re.I)

# ── Couche C : scoring OTP/code ──
RE_DIGITS = re.compile(r"\b\d{4,8}\b")
OTP_POS = re.compile(r"(verification|v[ée]rification|\bcode\b|otp|2fa|s[ée]curit|security|expire|valable|usage unique|confirmer votre (adresse|compte|email))", re.I)
OTP_NEG = re.compile(r"(order|commande|invoice|facture|ticket|dossier|r[ée]f[ée]rence|\bref\b|support|num[ée]ro de suivi)", re.I)

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return TAG_RE.sub(" ", s or "")


def _hv(headers: dict, name: str) -> str:
    """valeur d'en-tête insensible à la casse."""
    if not headers:
        return ""
    for k, v in headers.items():
        if k.lower() == name.lower():
            return (v or "").strip()
    return ""


def detect(headers: dict | None, from_addr: str = "", subject: str = "", body: str = "") -> dict:
    """Retourne auto_signals : no_reply (bool), reason, is_newsletter, has_unsubscribe, unsub_url, unsub_mailto."""
    headers = headers or {}
    from_addr = (from_addr or "").lower()
    subject = subject or ""
    body_txt = strip_html(body or "")

    list_unsub = _hv(headers, "List-Unsubscribe")
    list_id = _hv(headers, "List-Id")
    precedence = _hv(headers, "Precedence").lower()
    auto_sub = _hv(headers, "Auto-Submitted").lower()
    suppress = _hv(headers, "X-Auto-Response-Suppress")
    feedback = _hv(headers, "Feedback-ID") or _hv(headers, "X-Feedback-ID")
    autoreply = _hv(headers, "X-Autoreply").lower()
    return_path = _hv(headers, "Return-Path")

    # newsletter / liste de diffusion
    has_unsubscribe = bool(list_unsub)
    one_click = "one-click" in _hv(headers, "List-Unsubscribe-Post").lower()
    is_list = bool(list_id) or bool(list_unsub) or precedence in ("bulk", "list")
    # transactionnel déguisé en liste (reçu/code avec List-Unsubscribe) → PAS une vraie newsletter
    transactional = bool(RE_SUBJECT_NOREPLY.search(subject))
    is_newsletter = is_list and not transactional

    unsub_url, unsub_mailto = "", ""
    for part in re.findall(r"<([^>]+)>", list_unsub):
        if part.lower().startswith("http"):
            unsub_url = part
        elif part.lower().startswith("mailto:"):
            unsub_mailto = part

    def res(no_reply, reason):
        return {
            "no_reply": no_reply, "reason": reason,
            "is_newsletter": is_newsletter, "has_unsubscribe": has_unsubscribe,
            "one_click_unsub": one_click, "unsub_url": unsub_url, "unsub_mailto": unsub_mailto,
        }

    # ── Couche A : en-têtes ──
    if auto_sub and auto_sub != "no":
        return res(True, f"auto-submitted:{auto_sub}")
    if precedence in ("bulk", "list", "junk", "auto_reply"):
        return res(True, f"precedence:{precedence}")
    if any(t in suppress.upper() for t in ("DR", "AUTOREPLY", "ALL", "RN", "NRN")):
        return res(True, "x-auto-response-suppress")
    if feedback:
        return res(True, "feedback-id(bulk)")
    if autoreply == "yes":
        return res(True, "x-autoreply")
    if return_path.strip() in ("<>", ""):
        if return_path.strip() == "<>":
            return res(True, "null-return-path(bounce)")
    if list_id or list_unsub:
        return res(True, "mailing-list")

    # ── Couche B : expéditeur ──
    if RE_NOREPLY_FROM.search(from_addr):
        return res(True, "noreply-sender")

    # ── Couche B : objet transactionnel ──
    if RE_SUBJECT_NOREPLY.search(subject):
        return res(True, "transactional-subject")

    # ── Couche C : pied de page ──
    if RE_BODY_NOREPLY.search(body_txt):
        return res(True, "body-no-reply-notice")

    # ── Couche C : scoring OTP ──
    blob = subject + "\n" + body_txt[:1500]
    if RE_DIGITS.search(blob):
        pos = len(OTP_POS.findall(blob))
        neg = len(OTP_NEG.findall(blob))
        weak_from = bool(RE_WEAK_FROM.search(from_addr))
        if pos >= 1 and pos > neg:
            return res(True, "otp-code")
        if weak_from and pos >= 1:
            return res(True, "otp-code(weak-sender)")

    return res(False, "")


if __name__ == "__main__":
    # mini auto-test
    cases = [
        ("code activation", {}, "noreply@service.com", "Votre code de vérification : 837465", "Entrez ce code 837465, il expire dans 10 min."),
        ("vrai humain", {}, "adrien@boite.fr", "Question sur le projet", "Salut Martin, tu peux me confirmer le budget ?"),
        ("newsletter", {"List-Unsubscribe": "<https://x.com/u>", "List-Id": "<news.x.com>"}, "news@x.com", "La news du mardi", "..."),
        ("reçu", {}, "billing@stripe.com", "Reçu de votre paiement", "Merci pour votre paiement de 20€."),
    ]
    import json
    for name, h, f, s, b in cases:
        r = detect(h, f, s, b)
        print(f"{name:16} no_reply={r['no_reply']!s:5} reason={r['reason']:24} newsletter={r['is_newsletter']}")
