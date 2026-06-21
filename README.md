# 📬 Agent Mail — ta boîte triée pendant que tu dors

Un agent qui, chaque matin, **étiquette ta boîte Gmail** et **prépare tes réponses**. Tu ouvres Gmail, tu vois d'un coup d'œil les 3 mails qui comptent au milieu des 40, et tu n'écris plus de zéro — tu valides.

Pas de no-code, pas d'abonnement, pas de serveur. **Ça tourne avec [Claude Code](https://claude.com/claude-code)** que tu as déjà, plus un accès à ta boîte. Tes emails ne quittent jamais ta machine. Installation : 10 minutes.

> Construit et utilisé par [Martificial](https://martificial.substack.com). Donné tel quel — prends-le, adapte-le.

---

## Ce qu'il fait

**1. Il étiquette ta boîte, sans rien déplacer.** Chaque email reçoit un seul libellé visible dans Gmail :
- `Triage/A repondre` — un humain attend ta réponse
- `Triage/A voir` — code, reçu, notification : à voir, mais aucune réponse attendue
- `Triage/A lire` — tes newsletters

Tu cliques sur « A repondre » dans ta colonne de gauche → tu as ta vraie liste du jour. Rien n'est archivé, rien n'est déplacé : juste une étiquette, réversible.

**2. Il sait se taire.** La vraie intelligence d'un agent de tri n'est pas de répondre — c'est de savoir quand ne pas répondre. Il ne prépare un brouillon que lorsqu'une vraie personne attend une vraie réponse. Jamais pour un code d'activation, un reçu, une newsletter ou une adresse en « ne-pas-répondre » — il les repère aux signaux techniques de l'email (en-tête « message automatique », lien de désabonnement) et au contenu.

**3. Il prépare tes réponses.** Pour les vrais échanges, un brouillon de quelques lignes dans ta voix, posé dans tes brouillons Gmail. Tu valides, tu ajustes, tu envoies. **Il n'envoie jamais rien tout seul.**

**4. Il fait la revue de tes abonnements** (une fois par semaine) : les newsletters que tu ne lis plus, avec le taux de lecture que même Gmail ne te montre pas, et les liens pour te désabonner. Il ne coupe rien — il rend visible ce qui te coûte de l'attention.

---

## Installation en 10 minutes

### 1. Un mot de passe d'application Gmail
Active la validation en 2 étapes sur ton compte Google, puis crée un **mot de passe d'application** ici : https://myaccount.google.com/apppasswords (16 caractères). Révocable à tout moment.

### 2. Configure
```bash
git clone https://github.com/martinoh-ai/mail-agent-kit.git
cd mail-agent-kit
./setup.sh
```
Puis remplis deux fichiers :
- `.env` — ton adresse Gmail + le mot de passe d'application
- `preferences.md` — tes expéditeurs importants, ceux à museler, et quelques exemples de ta voix

### 3. Lance
```bash
./run.sh
```
Il étiquette ta boîte, puis prépare les brouillons des vrais échanges. Mets-le en tâche planifiée (cron) pour qu'il tourne chaque matin.

Et une fois par semaine, la revue de tes abonnements :
```bash
./run-newsletters.sh
```

---

## Comment l'améliorer
La première semaine, corrige les brouillons qui ne te vont pas et note pourquoi dans `preferences.md`. L'agent s'aligne vite sur ta voix. La plupart des gens abandonnent avant cette étape et concluent que ça ne marche pas — tiens deux semaines.

## Les pièges
- **Ne le laisse jamais envoyer seul.** Brouillons uniquement. Un brouillon raté se supprime en dix secondes ; un email parti à tort peut coûter un client.
- **Dis-lui ce qu'« urgent » veut dire pour toi**, dans `preferences.md`. Sans ça, il met tout au même niveau.

## Pour qui c'est rentable
Plus de 30 mails par jour et ton temps vaut plus de 100 €/h → ça s'amortit en une semaine.

---

*Tu veux qu'on le branche ensemble sur ta boîte, ou une version pour ton équipe ? → [écris-moi](https://martificial.substack.com).*
