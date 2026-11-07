# Privacy policy — You Decide

Last updated: 7 November 2026 · [Version française plus bas](#politique-de-confidentialité)

You Decide is a Claude Code plugin made of text instructions (skills), one subagent definition, a local memory script
and three local hooks. Its author, Guillaume Piron, receives no data from it.

## What it collects
Nothing. No telemetry, no analytics, no account, no network call to the author or to anyone else.

## What it reads
- The guard hook reads the tool call that Claude Code passes to it (the shell command about to run, or the content
  about to be written to a file) to decide whether to ask for your "yes" first. It keeps nothing.
- After a compaction or `/clear`, a hook reads `docs/state.md` and, with project memory, the open rows of the logs
  and the last answers, and gives them back to Claude.
- The `memory` skill reads this project's Claude Code transcripts on your machine to record your answers to
  multiple-choice questions and, if you enable the journal, your messages.
- The hooks never open credential files. They only recognise their names (`.env`, keys…) inside commands, to block
  commands that would print them.

## What it writes
Only in your project, and only after you approve the plan that `setup` shows you: `CLAUDE.md`, files under `docs/`
(the current state, logs of your requests in your own words, review findings, decision records, your answers to
multiple-choice questions, the memory map and volumes), permission rules in `.claude/settings.json`, and local git
commits. These files stay on your machine, or wherever you choose to push your repository.

With project memory, the hooks themselves append your new answers to `docs/questions_answers.md`, before and after a
compaction. Only if you enable them in `docs/memory/config.json`, it also writes on your machine, outside the
repository, a gzip copy of the transcript before each compaction (`~/.you-decide/transcripts/<project>/`) and a private
journal of your messages (`~/.you-decide/journal/<project>.md`); and inside the project, in a folder ignored by git
(`.you-decide/project_sync/`), documents prepared for you to upload to a claude.ai Project. These copies contain your
conversation: they never leave your machine unless you move them.

## What it sends
Nothing. When a skill asks Claude to research a question, Claude uses its own tools under your permission settings;
Anthropic's privacy policy covers your use of Claude.

## Children
The plugin is not intended for users under 18.

## Contact
Open an issue: https://github.com/guillaume-piron-dev/you-decide/issues

---

## Politique de confidentialité

Dernière mise à jour : 7 novembre 2026

You Decide est un plugin Claude Code composé d'instructions en texte (skills), d'une définition de sous-agent et de
deux scripts de hooks locaux. Son auteur, Guillaume Piron, ne reçoit aucune donnée de ce plugin.

- **Ce qu'il collecte** : rien. Aucune télémétrie, aucune mesure d'audience, aucun compte, aucun appel réseau.
- **Ce qu'il lit** : le hook garde-fou lit l'appel d'outil que Claude Code lui transmet (la commande ou le contenu sur
  le point d'être écrit) pour décider s'il faut te demander ton accord, sans rien conserver ; après une compaction ou
  un `/clear`, un hook relit `docs/state.md` et, avec la mémoire du projet, les lignes ouvertes des journaux et les
  dernières réponses ; la skill `memory` lit les transcriptions locales de Claude Code de ce projet pour noter tes
  réponses aux questions à choix et, si tu l'actives, tes messages. Ils n'ouvrent jamais de fichier
  d'identifiants : ils en reconnaissent seulement les noms dans les commandes, pour bloquer leur affichage.
- **Ce qu'il écrit** : dans ton projet, après ton accord sur le plan de `setup` : `CLAUDE.md`, des fichiers sous
  `docs/` (dont tes réponses aux questions à choix et la mémoire du projet), des règles de permission dans
  `.claude/settings.json` et des commits git locaux. Seulement si tu les actives : hors du dépôt, sur ta machine, une
  copie compressée des transcriptions avant chaque compaction, un journal privé de tes messages et les documents à
  charger toi-même dans un Projet claude.ai (dans un dossier du projet ignoré par git). Avec la mémoire du projet, les
  hooks ajoutent eux-mêmes tes nouvelles réponses à `docs/questions_answers.md`. Ces copies contiennent ta
  conversation et ne quittent jamais ta machine.
- **Ce qu'il envoie** : rien. Les recherches éventuelles sont faites par Claude avec ses propres outils, selon tes
  réglages de permission ; la politique de confidentialité d'Anthropic couvre ton usage de Claude.
- **Mineurs** : le plugin ne s'adresse pas aux moins de 18 ans.
- **Contact** : https://github.com/guillaume-piron-dev/you-decide/issues
