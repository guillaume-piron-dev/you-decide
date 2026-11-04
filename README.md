# You Decide — a human-gated development method for Claude Code

**You decide. Claude ships.** · [Version française plus bas](#version-française)

You Decide is a Claude Code plugin that pushes automation as far as it can go while keeping every strategic decision
with a human. Claude researches, plans, writes the tests first, implements, gets reviewed by an independent agent,
fixes what the review finds and commits locally. You choose the architecture, the dependencies, the trade-offs and
anything that cannot be undone.

It was extracted from the method I use to build a privacy-protection platform on my own with Claude Code (Rust and
TypeScript, under EU regulations). It is project-agnostic: nothing in it depends on a language or a domain.

## Install

In Claude Code:

```
/plugin marketplace add guillaume-piron-dev/you-decide
/plugin install you-decide@you-decide
```

Then, in your project:

```
/you-decide:setup
```

`setup` detects your stack, asks you a few multiple-choice questions and shows you a plan. It writes nothing before you
approve: a `CLAUDE.md` under 200 lines, a state file, permission rules and, depending on the level you pick, the logs.

## The daily loop

| When | Command | What happens |
|---|---|---|
| Start or resume | `/you-decide:session` | Reads one state file (under 10k tokens), logs your request in your own words, proposes a plan before any code |
| Before a costly choice | `/you-decide:decide` | Researches the options, screens each dependency or service, asks you to choose, writes a decision record |
| Implement | `/you-decide:story-to-tests` | One test per acceptance criterion and edge case, proven to fail, then the smallest code that passes |
| Before the commit | `/you-decide:review` | An independent reviewer subagent reads the diff only; every finding is fixed in the flow |
| Finish | `/you-decide:close-step` | Local CI green, findings closed, state updated, local commit. Never a push without your "yes" |
| End of a phase | `/you-decide:milestone` | Full re-verification, comparison with the best, measured baselines, clean hand-off |

Two more skills are used when needed: `log` (append-only logs of your requests, review findings and deferred items)
and `compliance` (legal or regulatory questions: sources first, a stand-alone question for an expert, never legal
advice).

## Three levels, because not every project needs everything

| Level | For | What it adds |
|---|---|---|
| Light | prototype, script, experiment | `CLAUDE.md` + `docs/state.md` |
| Standard | a product in progress | + requests log, findings log, decision records |
| Strict | regulated, sensitive or critical work | + AI usage log, traceability matrix, compliance question file |

## Guardrails (hooks)

- **Before a shell command** (Bash or PowerShell): asks for your "yes" before `git push`, history rewrites,
  discarding local changes, recursive deletions, destructive SQL, migration rollbacks, package publishing,
  data-sending network calls (calls to `localhost` are not interrupted), `curl | sh`, remote copies, cloud and
  infrastructure changes. Blocks the usual commands that would print a secret file (`cat`, `grep`, `Get-Content`…
  on `.env` or key files) and commands that contain a token.
- **Before a file write**: blocks high-confidence secrets (private keys, cloud and API tokens); asks for likely
  credentials, `.env` files and destructive SQL in migrations.
- **After a compaction or `/clear`**: re-injects `docs/state.md`, so your latest decisions survive the summary.

The hooks are about 450 lines of standard-library Python (`plugins/you-decide/hooks/`), covered by tests in
`tests/`. Read them before installing: a plugin runs with your privileges. They need Python 3.8 or later, found as
`python3`, `py -3` or `python`. On Windows, Claude Code runs hooks through Git Bash (installed with Git for Windows);
the Microsoft Store `python3` shortcut is detected and skipped. They are pattern-based: they catch the usual commands and token formats, not every
possible one. **They are guardrails, not a security guarantee.** Keep secrets out of the project folder.

## Cost

About 870 tokens are added to every session (skill and agent descriptions), as measured by `claude plugin details`.
A skill's full text loads only when it runs.

## Limits

- It does not replace stack-specific skills (React, Rust, Django…). Combine them.
- The `compliance` skill prepares sourced questions for a lawyer or regulator. It never gives legal advice.
- Tested on Linux and on Windows 11 (Git Bash, Python 3.13). Not yet tested on macOS: please report what breaks.
- It is opinionated: one session = one task, plan before code, findings fixed in the flow. If that is not how you
  want to work, it is not for you.

## Develop and test

```
python3 -m unittest discover -s tests -v
claude plugin validate .
claude --plugin-dir ./plugins/you-decide
```

## License

Apache-2.0. Issues and pull requests are welcome.

---

## Version française

**Tu décides. Claude exécute.**

You Decide est un plugin Claude Code qui pousse l'automatisation au maximum tout en laissant chaque décision
stratégique à un humain. Claude cherche, planifie, écrit les tests d'abord, implémente, se fait relire par un agent
indépendant, corrige ce que la relecture trouve et commite en local. Toi, tu choisis l'architecture, les dépendances,
les compromis et tout ce qui est irréversible.

Il est tiré de la méthode que j'utilise pour développer seul, avec Claude Code, une plateforme de protection de la vie
privée (Rust et TypeScript, droit européen). Il ne dépend d'aucun langage ni d'aucun domaine.

### Installation

```
/plugin marketplace add guillaume-piron-dev/you-decide
/plugin install you-decide@you-decide
```

Puis, dans ton projet : `/you-decide:setup`. La skill détecte ta stack, te pose quelques questions à choix et te
montre un plan. Elle n'écrit rien avant ton accord.

### La boucle de travail

| Moment | Commande | Ce qui se passe |
|---|---|---|
| Démarrer ou reprendre | `/you-decide:session` | Lit un seul fichier d'état, note ta demande avec tes mots, propose un plan avant le code |
| Avant un choix coûteux | `/you-decide:decide` | Recherche les options, passe chaque dépendance au crible, te fait choisir, écrit la décision |
| Implémenter | `/you-decide:story-to-tests` | Un test par critère d'acceptation et cas limite, puis le plus petit code qui passe |
| Avant le commit | `/you-decide:review` | Un sous-agent relecteur indépendant lit le diff ; chaque constat est corrigé dans la foulée |
| Finir | `/you-decide:close-step` | CI locale verte, constats fermés, état à jour, commit local. Jamais de push sans ton « oui » |
| Fin de phase | `/you-decide:milestone` | Revérification complète, comparaison avec les meilleurs, mesures réelles, passation propre |

### Trois niveaux

Léger (prototype, script), standard (produit en cours), exigeant (projet réglementé ou sensible). Chacun n'installe que
ce dont il a besoin.

### Garde-fous

Les hooks demandent ton accord avant un push, une réécriture d'historique, une suppression récursive, du SQL
destructif, une publication ou un envoi réseau (les appels à `localhost` ne sont pas interrompus). Ils bloquent les
commandes courantes qui afficheraient un fichier secret et l'écriture de secrets évidents dans les fichiers, et
réinjectent le fichier d'état après une compaction. Ils reconnaissent les commandes et formats de jetons usuels, pas
tous les cas possibles : ce sont des garde-fous, pas une garantie de sécurité. Aucun secret ne doit se trouver dans le
dossier du projet.

### Limites

Les hooks demandent Python 3.8 ou plus ; sous Windows, Claude Code les exécute via Git Bash (fourni avec Git pour
Windows). Le kit ne remplace pas les skills propres à une stack. La skill `compliance` prépare des questions sourcées pour un
juriste ; elle ne donne jamais d'avis juridique. Testé sous Linux et Windows 11, pas encore sous macOS : signale ce qui casse.

Licence Apache-2.0.
