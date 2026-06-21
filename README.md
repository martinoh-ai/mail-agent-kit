# 📬 Agent Mail — le tri de ta boîte, pendant que tu dors

Un agent qui lit ta boîte Gmail chaque matin, classe tout, et **te prépare les brouillons de réponse**. Tu n'archives plus à la main, tu ne rédiges plus de zéro — tu valides.

Pas de no-code, pas d'abonnement. **Ça tourne avec [Claude Code](https://claude.com/claude-code)** que tu as déjà, + un accès lecture à ta boîte. Setup : 10 minutes.

> Construit et utilisé par [Martificial](https://martificial.substack.com). Donné tel quel — prends-le, adapte-le.

---

## Ce qu'il fait

1. **Lit** tes mails des dernières 24h (accès lecture seule via IMAP).
2. **Classe** chaque mail en 4 piles : `urgent` · `à traiter` · `à lire` · `à ignorer` — selon TES règles (expéditeurs VIP, expéditeurs à museler, domaines).
3. **Rédige un brouillon** de réponse pour ceux qui en attendent une, dans ta voix, et le **sauve dans tes brouillons Gmail** (un brouillon ne part jamais seul — zéro risque).
4. **Te résume** la pile du jour : « 3 urgents, 2 brouillons prêts, le reste à ignorer ».

Ce qu'il **ne fait pas** : il n'envoie jamais un mail tout seul, et il n'archive rien par défaut (tu gardes la main).

---

## Setup en 10 minutes

### 1. Un mot de passe d'application Gmail
Active la validation en 2 étapes sur ton compte Google, puis crée un **mot de passe d'application** ici : https://myaccount.google.com/apppasswords (16 caractères). C'est une clé en lecture/écriture-brouillons, révocable à tout moment.

### 2. Configure le kit
```bash
cp .env.example .env
# ouvre .env, mets ton adresse Gmail + le mot de passe d'application
cp preferences.example.md preferences.md
# ouvre preferences.md, liste tes VIP et tes expéditeurs à museler
```

### 3. Lance-le
```bash
./run.sh
```
Claude Code lit ta boîte, classe, sauve les brouillons, et t'affiche le récap. Mets-le en tâche planifiée (cron) pour qu'il tourne chaque matin.

---

## Comment l'améliorer

La première semaine, corrige les brouillons qui ne te vont pas et note pourquoi. Ajoute ces exemples dans `preferences.md`. L'agent s'aligne vite sur ta voix — **la plupart des gens abandonnent avant cette étape et concluent que ça ne marche pas.** Tiens deux semaines.

---

## Pour qui c'est rentable
Plus de 30 mails/jour et ton temps vaut plus de 100 €/h → ça s'amortit en une semaine. En dessous de 20/jour, de simples filtres suffisent peut-être.

---

*Tu veux qu'on le branche ensemble sur ta boîte, ou une version sur-mesure pour ton équipe ? → [écris-moi](https://martificial.substack.com).*
