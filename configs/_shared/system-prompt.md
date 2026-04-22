## Konfigurations-Repo (agenticEngineering)

Dir steht ein separates Konfigurations-Repository zur Verfügung unter:

```
$AGPT_ENGINEERING_DIR
```

Wenn der User sagt "speichere in deinem Repo", "schreib das in dein Repo", "leg das bei dir ab" oder ähnlich, ist damit dieses Konfigurations-Repo gemeint — NICHT das Hauptprojekt.

### Struktur

```
$AGPT_ENGINEERING_DIR/
  configs/
    _shared/                  Gemeinsame Ressourcen (Hooks, Skills, CLAUDE.md)
      Backend/
        hooks/                architecture_hook.py, csharpier-check/
        skills/               write-audit-log/
        CLAUDE.md             Shared Backend-Instruktionen
      Frontend/
        hooks/                architecture_check.py
        skills/               create-ui-component/, kaseder-review/
    <scope>/                  Feature-spezifisch (aktueller Scope: $SCOPE)
      Backend/
        settings.json         Modell, Hooks, Plugins
        hooks/                worktree_guard.sh (Feature-Branch)
        docs/                 Feature-Spezifikation
        plans/                Session-Pläne
        projects/             Claude-Memory pro Projekt-Pfad
      Frontend/
        settings.json
        projects/
```

### Wo was abgelegt wird

| Inhalt | Ziel |
|--------|------|
| Feature-Doku, Konzepte | `configs/$SCOPE/Backend/docs/` oder `configs/$SCOPE/Frontend/docs/` |
| Notizen, Erkenntnisse | `configs/$SCOPE/<layer>/projects/` (Claude-Memory) |
| Hooks (layer-übergreifend) | `configs/_shared/<layer>/hooks/` |
| Skills (layer-übergreifend) | `configs/_shared/<layer>/skills/` |
| Scope-spezifische Hooks | `configs/$SCOPE/<layer>/hooks/` |
