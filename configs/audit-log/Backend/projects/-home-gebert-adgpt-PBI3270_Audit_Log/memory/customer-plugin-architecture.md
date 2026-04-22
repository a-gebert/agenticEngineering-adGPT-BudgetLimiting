---
name: customer-plugin-architecture
description: Plugin-Struktur im Customer-Ordner des Backends — mandatory/optional Interfaces, Registrierungsflow, Schritt-für-Schritt-Anleitung für neue Plugins
type: reference
---

# Customer Plugin Architecture

## Ordnerstruktur

Jedes Customer-Plugin lebt in:

```
Backend/Customers/<Name>/adessoGPT.Application.<Name>/
├── Localization/
│   ├── ErrorMessages.Designer.cs
│   └── FeatureLocalization.Designer.cs
├── Options/
│   └── <Name>Options.cs
├── Plugins/
│   └── <FeatureName>/
│       ├── Dependencies/
│       │   └── <Name>Step.cs / <Name>StepResult.cs
│       ├── <Name>Plugin.cs                    ← Semantic Kernel Plugin
│       ├── <Name>Feature.cs                   ← Feature-Metadaten
│       └── <Name>FeatureRegistration.cs       ← SK-Registrierung
└── <Name>Module.cs                            ← DI-Einstiegspunkt
```

Bestehende Beispiele: `Customers/TenderGPT/` (vollständig), `Customers/Payroll/` (minimal).

---

## Mandatory Interfaces

### 1. `IAdessoGptModule` — DI-Registrierung beim App-Start

```csharp
public class TenderGPTModule : IAdessoGptModule
{
    public static void ConfigureServices(
        IServiceCollection services,
        IConfiguration configuration,
        IHostEnvironment environment,
        ILogger logger,
        Assembly[] scanningAssemblies)
    {
        services.AddOptionsWithValidateOnStartFluentValidation<TenderGPTOptions>(
            TenderGPTOptions.SectionName
        );
        services.AddScoped<IAdessoGptKernelFeatureRegistration, TenderGPTSummarizeFeatureRegistration>();
    }
}
```

### 2. `IAdessoGptKernelFeatureProvider` — Feature-Metadaten (static)

### 3. `IAdessoGptKernelFeatureRegistration` — Runtime-Registrierung in Semantic Kernel

### 4. Semantic Kernel Plugin-Klasse mit `[KernelFunction]`-Methoden

---

## Wo wird das Plugin geladen?

### Schritt 1 — Explizite Modul-Registrierung (einmalig, manuell)

**Datei:** `Backend/Presentation/adessoGPT.Presentation.Api/Modules.cs`

Es gibt **keine Auto-Discovery** — jedes neue Plugin muss hier manuell eingetragen werden.

### Schritt 2 — Feature-Selektion per Agent-Konfiguration

Features werden aus der Agent-Konfiguration im Control Center geladen.

### Schritt 3 — Laufzeit-Matching durch `SemanticKernelFeatureRegistrar`

---

## Wichtige Dateipfade

| Datei | Zweck |
|---|---|
| `Backend/Presentation/adessoGPT.Presentation.Api/Modules.cs` | Explizite Modul-Registrierung |
| `Backend/Shared/adessoGPT.Core/Module/IAdessoGptModule.cs` | Modul-Interface |
| `Backend/Shared/adessoGPT.Chat.Abstractions/Plugins/IAdessoGptKernelFeatureRegistration.cs` | Feature-Interfaces |
| `Backend/Infrastructure/adessoGPT.Infrastructure.SemanticKernel/Runtime/Features/SemanticKernelFeatureRegistrar.cs` | Laufzeit-Matching-Logik |
| `Backend/Customers/TenderGPT/` | Vollständige Referenzimplementierung |
