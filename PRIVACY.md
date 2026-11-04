# Privacy policy — You Decide

Last updated: 4 November 2026 · [Version française plus bas](#politique-de-confidentialité)

You Decide is a Claude Code plugin made of text instructions (skills), one subagent definition and two local hook
scripts. Its author, Guillaume Piron, receives no data from it.

## What it collects
Nothing. No telemetry, no analytics, no account, no network call to the author or to anyone else.

## What it reads
- The hooks read the tool call that Claude Code passes to them (the shell command about to run, or the content about
  to be written to a file) to decide whether to ask for your "yes" first. They keep nothing.
- After a compaction or `/clear`, a hook reads the first 150 lines of `docs/state.md` in your project, if that file
  exists, and gives them back to Claude.
- The hooks never open credential files. They only recognise their names (`.env`, keys…) inside commands, to block
  commands that would print them.

## What it writes
Only in your project, and only after you approve the plan that `setup` shows you: `CLAUDE.md`, files under `docs/`
(the current state, logs of your requests in your own words, review findings, decision records), permission rules in
`.claude/settings.json`, and local git commits. These files stay on your machine, or wherever you choose to push your
repository.

## What it sends
Nothing. When a skill asks Claude to research a question, Claude uses its own tools under your permission settings;
Anthropic's privacy policy covers your use of Claude.

## Children
The plugin is not intended for users under 18.

## Contact
Open an issue: https://github.com/guillaume-piron-dev/you-decide/issues

---

## Politique de confidentialité

Dernière mise à jour : 4 novembre 2026

You Decide est un plugin Claude Code composé d'instructions en texte (skills), d'une définition de sous-agent et de
deux scripts de hooks locaux. Son auteur, Guillaume Piron, ne reçoit aucune donnée de ce plugin.

- **Ce qu'il collecte** : rien. Aucune télémétrie, aucune mesure d'audience, aucun compte, aucun appel réseau.
- **Ce qu'il lit** : les hooks lisent l'appel d'outil que Claude Code leur transmet (la commande ou le contenu sur le
  point d'être écrit) pour décider s'il faut te demander ton accord, sans rien conserver ; après une compaction ou un
  `/clear`, ils lisent les 150 premières lignes de `docs/state.md` s'il existe. Ils n'ouvrent jamais de fichier
  d'identifiants : ils en reconnaissent seulement les noms dans les commandes, pour bloquer leur affichage.
- **Ce qu'il écrit** : uniquement dans ton projet, après ton accord sur le plan de `setup` : `CLAUDE.md`, des fichiers
  sous `docs/`, des règles de permission dans `.claude/settings.json` et des commits git locaux.
- **Ce qu'il envoie** : rien. Les recherches éventuelles sont faites par Claude avec ses propres outils, selon tes
  réglages de permission ; la politique de confidentialité d'Anthropic couvre ton usage de Claude.
- **Mineurs** : le plugin ne s'adresse pas aux moins de 18 ans.
- **Contact** : https://github.com/guillaume-piron-dev/you-decide/issues
