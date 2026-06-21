# Tâche : la revue de mes abonnements

Tu fais le point sur mes newsletters : lesquelles je lis vraiment, lesquelles je ne lis plus.

## 1. Scanne
```
python3 newsletters.py --days 90
```
Tu reçois un JSON avec 3 paniers : `rouge` (jamais ouvertes), `orange` (presque jamais), `vert` (vraiment lues). Le « lu » = flag IMAP, c'est un proxy honnête (pas le pixel-tracking de Gmail) — dis-le si tu cites le chiffre.

## 2. Protège mes VIP
Lis `preferences.md` : retire du panier rouge tout expéditeur VIP (un VIP n'est jamais un candidat au désabonnement).

## 3. Rédige la revue (français, direct, tranché, chiffré)
- **Tu ne lis plus** : 3 à 6 du rouge → `• Nom — X reçus, 0 lu → se désabonner : <unsub_url>`
- **Tu zappes presque tout** : le orange avec le taux de lecture
- **Tu lis vraiment (on garde)** : 2-3 du vert
- Termine par le total : « X mails de liste sur 90 jours, Y ouverts. Couper le rouge = ~Z mails/trimestre en moins dans ta tête. » puis « Je ne touche à rien, tu décides, tu cliques. »

## 4. Sauve-la en brouillon (pour toi)
Récupère ton adresse (variable d'environnement `GMAIL_USER`) et :
```
python3 gmail_helper.py save-draft --to "<ton adresse GMAIL_USER>" --subject "La revue de mes abonnements" --body "<la revue>"
```

## Règle
Jamais de désabonnement ni d'archivage automatique. Tu fournis les liens, l'humain clique. Tu ne fais que rendre visible ce qui coûte de l'attention sans rien rapporter.
