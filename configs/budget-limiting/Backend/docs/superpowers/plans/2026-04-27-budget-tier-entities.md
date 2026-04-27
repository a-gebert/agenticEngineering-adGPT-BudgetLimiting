# BudgetTier ControlCenter Entities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the BudgetTier domain entity with full CRUD via ControlCenter endpoints, persistence across all three providers, audit trail, cached repository, delete cascades, and a tier resolution service.

**Architecture:** BudgetTier is a `SystemSettingsPartitionedEntity` (collection entity in the `system` Cosmos container) following the same CQRS pattern as UserGroupMapping and Agent. Admin-managed via `/api/control-center/budget-tiers` endpoints. Cached via FusionCache. Tier resolution maps JWT group claims to the most restrictive matching tier.

**Tech Stack:** .NET 10, MediatR, FluentValidation, EF Core (Cosmos/MongoDB/InMemory), FusionCache, StronglyTypedIds

**Spec:** `docs/superpowers/specs/2026-04-27-budget-tier-entities-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `Shared/adessoGPT.Domain/PersistedEntities/System/Settings/BudgetTier/BudgetTier.cs` | Domain entity, strongly-typed ID, audit configuration |
| `Application/adessoGPT.Application/Business/BudgetTiers/BudgetTierRepository.cs` | Repository interface + cached implementation |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/ControlCenterBudgetTierEndpoints.cs` | Endpoint mapper |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/BudgetTierErrors.cs` | Error factory |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/Models/ControlCenterBudgetTierDto.cs` | Shared DTO + DTO validator |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersQuery.cs` | List all query |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersQueryHandler.cs` | List all handler |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersResponse.cs` | List all response DTO |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQuery.cs` | Get by ID query |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQueryHandler.cs` | Get by ID handler |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQueryValidator.cs` | Get by ID validator |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierResponse.cs` | Get by ID response DTO |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/CreateControlCenterBudgetTierCommand.cs` | Create + Update command records |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/UpsertControlCenterBudgetTierCommandHandler.cs` | Create + Update handler |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/UpsertControlCenterBudgetTierCommandValidator.cs` | Create + Update validators |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommand.cs` | Delete command |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommandHandler.cs` | Delete handler |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommandValidator.cs` | Delete validator |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommand.cs` | Set default command |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommandHandler.cs` | Set default handler |
| `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommandValidator.cs` | Set default validator |
| `Infrastructure/adessoGPT.Infrastructure.Persistence.CosmosDb/Configurations/System/Settings/BudgetTierConfiguration.cs` | Cosmos DB EF config |
| `Infrastructure/adessoGPT.Infrastructure.Persistence.MongoDb/Configurations/System/Settings/BudgetTierConfiguration.cs` | MongoDB EF config |
| `Infrastructure/adessoGPT.Infrastructure.Persistence.InMemory/Configurations/System/Settings/BudgetTierConfiguration.cs` | InMemory EF config |
| `Application/adessoGPT.Application/Business/Budget/Services/IBudgetTierResolver.cs` | Tier resolver interface |
| `Application/adessoGPT.Application/Business/Budget/Services/BudgetTierResolver.cs` | Tier resolver implementation |

### Modified Files

| File | Change |
|------|--------|
| `Shared/adessoGPT.Domain/PersistedEntities/System/SingleSettings/BudgetLimitSettings.cs` | Add `DefaultBudgetTierId` property |
| `Shared/adessoGPT.Domain/Localization/EntityMessages.resx` | Add BudgetTier localization keys |
| `Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx` | Add German translations |
| `Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.resx` | Add BudgetTier error messages |
| `Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.de.resx` | Add German error messages |
| `Application/adessoGPT.Application.ControlCenter/Business/UserGroups/DeleteUserGroup/DeleteControlCenterUserGroupCommandHandler.cs` | Add cascade to BudgetTier |

---

## Task 1: BudgetTier Domain Entity

**Files:**
- Create: `Shared/adessoGPT.Domain/PersistedEntities/System/Settings/BudgetTier/BudgetTier.cs`
- Modify: `Shared/adessoGPT.Domain/Localization/EntityMessages.resx`
- Modify: `Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx`

- [ ] **Step 1: Create the BudgetTier entity file**

Create `Shared/adessoGPT.Domain/PersistedEntities/System/Settings/BudgetTier/BudgetTier.cs`:

```csharp
namespace adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

using adessoGPT.Core.Audit;
using adessoGPT.Core.DisplayInfo;
using adessoGPT.Domain.Localization;
using adessoGPT.Domain.PersistedEntities.System.Settings.UserGroups;
using StronglyTypedIds;

[StronglyTypedId(Template.String, "string-efcore-openapi")]
public readonly partial struct BudgetTierId { }

[DisplayInfo(typeof(EntityMessages), nameof(EntityMessages.BudgetTier_EntityDisplayTitle))]
public sealed record BudgetTier : SystemSettingsPartitionedEntity
{
    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_Id),
        nameof(EntityMessages.BudgetTier_Id_Description)
    )]
    public required BudgetTierId Id { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_Title),
        nameof(EntityMessages.BudgetTier_Title_Description)
    )]
    public required LocalizationStrings Title { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_Description),
        nameof(EntityMessages.BudgetTier_Description_Description)
    )]
    public required LocalizationStrings Description { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_Priority),
        nameof(EntityMessages.BudgetTier_Priority_Description)
    )]
    public required int Priority { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_IsDefault),
        nameof(EntityMessages.BudgetTier_IsDefault_Description)
    )]
    public bool IsDefault { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_AssignedUserGroupId),
        nameof(EntityMessages.BudgetTier_AssignedUserGroupId_Description)
    )]
    public UserGroupMappingId? AssignedUserGroupId { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_DailyTokenLimit),
        nameof(EntityMessages.BudgetTier_DailyTokenLimit_Description)
    )]
    public long? DailyTokenLimit { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_WeeklyTokenLimit),
        nameof(EntityMessages.BudgetTier_WeeklyTokenLimit_Description)
    )]
    public long? WeeklyTokenLimit { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_MonthlyTokenLimit),
        nameof(EntityMessages.BudgetTier_MonthlyTokenLimit_Description)
    )]
    public long? MonthlyTokenLimit { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_RequestsPerMinute),
        nameof(EntityMessages.BudgetTier_RequestsPerMinute_Description)
    )]
    public int? RequestsPerMinute { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetTier_SoftWarningPercent),
        nameof(EntityMessages.BudgetTier_SoftWarningPercent_Description)
    )]
    public int SoftWarningPercent { get; init; } = 80;
}

internal class BudgetTierAuditConfiguration : IAuditEntityConfiguration<BudgetTier>
{
    public void Configure(AuditEntityConfigurationBuilder<BudgetTier> builder)
    {
        builder.AuditAllProperties();
    }
}
```

- [ ] **Step 2: Add English localization entries to EntityMessages.resx**

Add these entries to `Shared/adessoGPT.Domain/Localization/EntityMessages.resx` (before the closing `</root>` tag):

```xml
<data name="BudgetTier_EntityDisplayTitle" xml:space="preserve">
  <value>Budget Tier</value>
</data>
<data name="BudgetTier_Id" xml:space="preserve">
  <value>ID</value>
</data>
<data name="BudgetTier_Id_Description" xml:space="preserve">
  <value>The unique identifier for the budget tier.</value>
</data>
<data name="BudgetTier_Title" xml:space="preserve">
  <value>Title</value>
</data>
<data name="BudgetTier_Title_Description" xml:space="preserve">
  <value>The display name of the budget tier.</value>
</data>
<data name="BudgetTier_Description" xml:space="preserve">
  <value>Description</value>
</data>
<data name="BudgetTier_Description_Description" xml:space="preserve">
  <value>A description of the budget tier.</value>
</data>
<data name="BudgetTier_Priority" xml:space="preserve">
  <value>Priority</value>
</data>
<data name="BudgetTier_Priority_Description" xml:space="preserve">
  <value>Priority for conflict resolution. Lower value means more restrictive.</value>
</data>
<data name="BudgetTier_IsDefault" xml:space="preserve">
  <value>Default</value>
</data>
<data name="BudgetTier_IsDefault_Description" xml:space="preserve">
  <value>Whether this is the default tier for users without an assigned group.</value>
</data>
<data name="BudgetTier_AssignedUserGroupId" xml:space="preserve">
  <value>Assigned User Group</value>
</data>
<data name="BudgetTier_AssignedUserGroupId_Description" xml:space="preserve">
  <value>The user group this tier is assigned to.</value>
</data>
<data name="BudgetTier_DailyTokenLimit" xml:space="preserve">
  <value>Daily Token Limit</value>
</data>
<data name="BudgetTier_DailyTokenLimit_Description" xml:space="preserve">
  <value>Maximum number of tokens per user per day. Leave empty for unlimited.</value>
</data>
<data name="BudgetTier_WeeklyTokenLimit" xml:space="preserve">
  <value>Weekly Token Limit</value>
</data>
<data name="BudgetTier_WeeklyTokenLimit_Description" xml:space="preserve">
  <value>Maximum number of tokens per user per week. Leave empty for unlimited.</value>
</data>
<data name="BudgetTier_MonthlyTokenLimit" xml:space="preserve">
  <value>Monthly Token Limit</value>
</data>
<data name="BudgetTier_MonthlyTokenLimit_Description" xml:space="preserve">
  <value>Maximum number of tokens per user per month. Leave empty for unlimited.</value>
</data>
<data name="BudgetTier_RequestsPerMinute" xml:space="preserve">
  <value>Requests per Minute</value>
</data>
<data name="BudgetTier_RequestsPerMinute_Description" xml:space="preserve">
  <value>Maximum number of requests per user per minute. Leave empty for unlimited.</value>
</data>
<data name="BudgetTier_SoftWarningPercent" xml:space="preserve">
  <value>Warning Threshold (%)</value>
</data>
<data name="BudgetTier_SoftWarningPercent_Description" xml:space="preserve">
  <value>Percentage of budget usage at which users see a warning banner.</value>
</data>
```

- [ ] **Step 3: Add German localization entries to EntityMessages.de.resx**

Add these entries to `Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx`:

```xml
<data name="BudgetTier_EntityDisplayTitle" xml:space="preserve">
  <value>Budget-Stufe</value>
</data>
<data name="BudgetTier_Id" xml:space="preserve">
  <value>ID</value>
</data>
<data name="BudgetTier_Id_Description" xml:space="preserve">
  <value>Die eindeutige Kennung der Budget-Stufe.</value>
</data>
<data name="BudgetTier_Title" xml:space="preserve">
  <value>Titel</value>
</data>
<data name="BudgetTier_Title_Description" xml:space="preserve">
  <value>Der Anzeigename der Budget-Stufe.</value>
</data>
<data name="BudgetTier_Description" xml:space="preserve">
  <value>Beschreibung</value>
</data>
<data name="BudgetTier_Description_Description" xml:space="preserve">
  <value>Eine Beschreibung der Budget-Stufe.</value>
</data>
<data name="BudgetTier_Priority" xml:space="preserve">
  <value>Priorität</value>
</data>
<data name="BudgetTier_Priority_Description" xml:space="preserve">
  <value>Priorität für die Konfliktauflösung. Niedrigerer Wert bedeutet restriktiver.</value>
</data>
<data name="BudgetTier_IsDefault" xml:space="preserve">
  <value>Standard</value>
</data>
<data name="BudgetTier_IsDefault_Description" xml:space="preserve">
  <value>Ob dies die Standard-Stufe für Benutzer ohne zugewiesene Gruppe ist.</value>
</data>
<data name="BudgetTier_AssignedUserGroupId" xml:space="preserve">
  <value>Zugewiesene Benutzergruppe</value>
</data>
<data name="BudgetTier_AssignedUserGroupId_Description" xml:space="preserve">
  <value>Die Benutzergruppe, der diese Stufe zugeordnet ist.</value>
</data>
<data name="BudgetTier_DailyTokenLimit" xml:space="preserve">
  <value>Tägliches Token-Limit</value>
</data>
<data name="BudgetTier_DailyTokenLimit_Description" xml:space="preserve">
  <value>Maximale Anzahl von Tokens pro Benutzer pro Tag. Leer lassen für unbegrenzt.</value>
</data>
<data name="BudgetTier_WeeklyTokenLimit" xml:space="preserve">
  <value>Wöchentliches Token-Limit</value>
</data>
<data name="BudgetTier_WeeklyTokenLimit_Description" xml:space="preserve">
  <value>Maximale Anzahl von Tokens pro Benutzer pro Woche. Leer lassen für unbegrenzt.</value>
</data>
<data name="BudgetTier_MonthlyTokenLimit" xml:space="preserve">
  <value>Monatliches Token-Limit</value>
</data>
<data name="BudgetTier_MonthlyTokenLimit_Description" xml:space="preserve">
  <value>Maximale Anzahl von Tokens pro Benutzer pro Monat. Leer lassen für unbegrenzt.</value>
</data>
<data name="BudgetTier_RequestsPerMinute" xml:space="preserve">
  <value>Anfragen pro Minute</value>
</data>
<data name="BudgetTier_RequestsPerMinute_Description" xml:space="preserve">
  <value>Maximale Anzahl von Anfragen pro Benutzer pro Minute. Leer lassen für unbegrenzt.</value>
</data>
<data name="BudgetTier_SoftWarningPercent" xml:space="preserve">
  <value>Warnschwelle (%)</value>
</data>
<data name="BudgetTier_SoftWarningPercent_Description" xml:space="preserve">
  <value>Prozentsatz der Budget-Nutzung, ab dem Benutzer ein Warnbanner sehen.</value>
</data>
```

- [ ] **Step 4: Build to verify the entity compiles**

Run: `dotnet build Shared/adessoGPT.Domain/`
Expected: Build succeeded

- [ ] **Step 5: Commit**

```bash
git add Shared/adessoGPT.Domain/PersistedEntities/System/Settings/BudgetTier/BudgetTier.cs \
       Shared/adessoGPT.Domain/Localization/EntityMessages.resx \
       Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx
git commit -m "feat: add BudgetTier domain entity with strongly-typed ID and localization"
```

---

## Task 2: Extend BudgetLimitSettings with DefaultBudgetTierId

**Files:**
- Modify: `Shared/adessoGPT.Domain/PersistedEntities/System/SingleSettings/BudgetLimitSettings.cs`
- Modify: `Shared/adessoGPT.Domain/Localization/EntityMessages.resx`
- Modify: `Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx`

- [ ] **Step 1: Add DefaultBudgetTierId property to BudgetLimitSettings**

In `Shared/adessoGPT.Domain/PersistedEntities/System/SingleSettings/BudgetLimitSettings.cs`, add a using for the BudgetTier namespace and add the new property. The file should look like:

```csharp
namespace adessoGPT.Domain.PersistedEntities.System.SingleSettings;

using adessoGPT.Core.Audit;
using adessoGPT.Core.DisplayInfo;
using adessoGPT.Domain.Localization;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

[DisplayInfo(typeof(EntityMessages), nameof(EntityMessages.BudgetLimitSettings_EntityDisplayTitle))]
public record BudgetLimitSettings : SingleSystemSettingsBase, ISingleSystemSettingDefaultValue<BudgetLimitSettings>
{
    public static BudgetLimitSettings DefaultValue { get; } = new() { IsEnabled = true, MonthlyTokenLimit = 500 };

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetLimitSettings_IsEnabled),
        nameof(EntityMessages.BudgetLimitSettings_IsEnabled_Description)
    )]
    public required bool IsEnabled { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetLimitSettings_MonthlyTokenLimit),
        nameof(EntityMessages.BudgetLimitSettings_MonthlyTokenLimit_Description)
    )]
    public required long? MonthlyTokenLimit { get; init; }

    [DisplayInfo(
        typeof(EntityMessages),
        nameof(EntityMessages.BudgetLimitSettings_DefaultBudgetTierId),
        nameof(EntityMessages.BudgetLimitSettings_DefaultBudgetTierId_Description)
    )]
    public BudgetTierId? DefaultBudgetTierId { get; init; }
}

internal class BudgetLimitSettingsAuditConfiguration : IAuditEntityConfiguration<BudgetLimitSettings>
{
    public void Configure(AuditEntityConfigurationBuilder<BudgetLimitSettings> builder)
    {
        builder.AuditAllProperties();
    }
}
```

- [ ] **Step 2: Add localization entries for the new property**

Add to `EntityMessages.resx`:

```xml
<data name="BudgetLimitSettings_DefaultBudgetTierId" xml:space="preserve">
  <value>Default Budget Tier</value>
</data>
<data name="BudgetLimitSettings_DefaultBudgetTierId_Description" xml:space="preserve">
  <value>The budget tier applied to users without an assigned group.</value>
</data>
```

Add to `EntityMessages.de.resx`:

```xml
<data name="BudgetLimitSettings_DefaultBudgetTierId" xml:space="preserve">
  <value>Standard-Budget-Stufe</value>
</data>
<data name="BudgetLimitSettings_DefaultBudgetTierId_Description" xml:space="preserve">
  <value>Die Budget-Stufe, die für Benutzer ohne zugewiesene Gruppe gilt.</value>
</data>
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build Shared/adessoGPT.Domain/`
Expected: Build succeeded

- [ ] **Step 4: Commit**

```bash
git add Shared/adessoGPT.Domain/PersistedEntities/System/SingleSettings/BudgetLimitSettings.cs \
       Shared/adessoGPT.Domain/Localization/EntityMessages.resx \
       Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx
git commit -m "feat: add DefaultBudgetTierId to BudgetLimitSettings"
```

---

## Task 3: Persistence Configurations

**Files:**
- Create: `Infrastructure/adessoGPT.Infrastructure.Persistence.CosmosDb/Configurations/System/Settings/BudgetTierConfiguration.cs`
- Create: `Infrastructure/adessoGPT.Infrastructure.Persistence.MongoDb/Configurations/System/Settings/BudgetTierConfiguration.cs`
- Create: `Infrastructure/adessoGPT.Infrastructure.Persistence.InMemory/Configurations/System/Settings/BudgetTierConfiguration.cs`

- [ ] **Step 1: Create Cosmos DB configuration**

Create `Infrastructure/adessoGPT.Infrastructure.Persistence.CosmosDb/Configurations/System/Settings/BudgetTierConfiguration.cs`:

```csharp
namespace adessoGPT.Infrastructure.Persistence.CosmosDb.Configurations.System.Settings;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Infrastructure.Persistence.CosmosDb.Configurations.Base;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

internal class BudgetTierConfiguration : SystemContainerConfigurationBase<BudgetTier>
{
    protected override void Configure(EntityTypeBuilder<BudgetTier> builder)
    {
        builder.HasKey(e => e.Id);
    }
}
```

- [ ] **Step 2: Create MongoDB configuration**

Create `Infrastructure/adessoGPT.Infrastructure.Persistence.MongoDb/Configurations/System/Settings/BudgetTierConfiguration.cs`:

```csharp
namespace adessoGPT.Infrastructure.Persistence.MongoDb.Configurations.System.Settings;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Infrastructure.Persistence.MongoDb.Configurations.Base;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

internal class BudgetTierConfiguration : SystemCollectionConfigurationBase<BudgetTier>
{
    protected override string GetCollectionName() => "budget_tiers";

    protected override void Configure(EntityTypeBuilder<BudgetTier> builder)
    {
        builder.HasKey(e => e.Id);
    }
}
```

- [ ] **Step 3: Create InMemory configuration**

Create `Infrastructure/adessoGPT.Infrastructure.Persistence.InMemory/Configurations/System/Settings/BudgetTierConfiguration.cs`:

```csharp
namespace adessoGPT.Infrastructure.Persistence.InMemory.Configurations.System.Settings;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Infrastructure.Persistence.InMemory.Configurations.Base;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

internal class BudgetTierConfiguration : SystemTableConfigurationBase<BudgetTier>
{
    protected override string GetTableName() => "BudgetTiers";

    protected override void Configure(EntityTypeBuilder<BudgetTier> builder)
    {
        builder.HasKey(e => e.Id);
    }
}
```

- [ ] **Step 4: Build all three infrastructure projects**

Run: `dotnet build Infrastructure/`
Expected: Build succeeded

- [ ] **Step 5: Commit**

```bash
git add Infrastructure/adessoGPT.Infrastructure.Persistence.CosmosDb/Configurations/System/Settings/BudgetTierConfiguration.cs \
       Infrastructure/adessoGPT.Infrastructure.Persistence.MongoDb/Configurations/System/Settings/BudgetTierConfiguration.cs \
       Infrastructure/adessoGPT.Infrastructure.Persistence.InMemory/Configurations/System/Settings/BudgetTierConfiguration.cs
git commit -m "feat: add BudgetTier persistence configurations for Cosmos, MongoDB, InMemory"
```

---

## Task 4: BudgetTier Repository

**Files:**
- Create: `Application/adessoGPT.Application/Business/BudgetTiers/BudgetTierRepository.cs`

- [ ] **Step 1: Create the repository interface and implementation**

Create `Application/adessoGPT.Application/Business/BudgetTiers/BudgetTierRepository.cs`:

```csharp
namespace adessoGPT.Application.Business.BudgetTiers;

using System.Linq.Expressions;
using adessoGPT.Application.Dependencies.SystemSettings;
using adessoGPT.Domain;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using ZiggyCreatures.Caching.Fusion;

public interface IBudgetTierRepository : ISystemSettingRepository<BudgetTier, BudgetTierId> { }

internal class BudgetTierRepository
    : SystemSettingCachedRepositoryBase<BudgetTier, BudgetTierId>,
        IBudgetTierRepository
{
    public BudgetTierRepository(IFusionCache fusionCache, ISystemDbContext dbContext)
        : base(fusionCache, dbContext) { }

    protected override BudgetTierId GetEntityId(BudgetTier entity) => entity.Id;

    protected override Expression<Func<BudgetTier, bool>> GetEntityByIdExpression(BudgetTierId id)
    {
        return e => e.Id == id;
    }
}
```

- [ ] **Step 2: Build to verify**

Run: `dotnet build Application/adessoGPT.Application/`
Expected: Build succeeded

- [ ] **Step 3: Commit**

```bash
git add Application/adessoGPT.Application/Business/BudgetTiers/BudgetTierRepository.cs
git commit -m "feat: add BudgetTierRepository with FusionCache"
```

---

## Task 5: ControlCenter Endpoints, DTO, and Error Factory

**Files:**
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/ControlCenterBudgetTierEndpoints.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/Models/ControlCenterBudgetTierDto.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/BudgetTierErrors.cs`
- Modify: `Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.resx`
- Modify: `Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.de.resx`

- [ ] **Step 1: Create the DTO and its validator**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/Models/ControlCenterBudgetTierDto.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.Models;

using adessoGPT.Core.Extensions;
using adessoGPT.Domain.PersistedEntities.System.Settings.UserGroups;
using FluentValidation;

public record ControlCenterBudgetTierDto
{
    public required LocalizationStrings Title { get; init; }
    public required LocalizationStrings Description { get; init; }
    public required int Priority { get; init; }
    public UserGroupMappingId? AssignedUserGroupId { get; init; }
    public long? DailyTokenLimit { get; init; }
    public long? WeeklyTokenLimit { get; init; }
    public long? MonthlyTokenLimit { get; init; }
    public int? RequestsPerMinute { get; init; }
    public int SoftWarningPercent { get; init; } = 80;
}

public class ControlCenterBudgetTierDtoValidator : AbstractValidator<ControlCenterBudgetTierDto>
{
    public ControlCenterBudgetTierDtoValidator()
    {
        RuleFor(x => x.Title).NotEmpty().ValidLocalizationStrings();
        RuleFor(x => x.Description).NotEmpty().ValidLocalizationStrings();
        RuleFor(x => x.Priority).GreaterThan(0);
        RuleFor(x => x.SoftWarningPercent).InclusiveBetween(1, 100);
        RuleFor(x => x.DailyTokenLimit).GreaterThan(0).When(x => x.DailyTokenLimit.HasValue);
        RuleFor(x => x.WeeklyTokenLimit).GreaterThan(0).When(x => x.WeeklyTokenLimit.HasValue);
        RuleFor(x => x.MonthlyTokenLimit).GreaterThan(0).When(x => x.MonthlyTokenLimit.HasValue);
        RuleFor(x => x.RequestsPerMinute).GreaterThan(0).When(x => x.RequestsPerMinute.HasValue);
    }
}
```

- [ ] **Step 2: Create the error factory**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/BudgetTierErrors.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers;

using adessoGPT.Core.Results.Errors;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

public static class BudgetTierErrors
{
    public static BudgetTierNotFoundError NotFound(BudgetTierId budgetTierId) => new(budgetTierId);

    public static NotFoundError UserGroupNotFound(string userGroupId) =>
        new($"User group with ID {userGroupId} not found.");
}

public record BudgetTierNotFoundError(BudgetTierId BudgetTierId)
    : NotFoundError($"Budget tier with ID {BudgetTierId} not found.");
```

- [ ] **Step 3: Add error messages to ErrorMessages.resx**

Add to `Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.resx`:

```xml
<data name="BudgetTier_NotFound" xml:space="preserve">
  <value>Budget tier not found.</value>
</data>
<data name="BudgetTier_CannotDeleteDefault" xml:space="preserve">
  <value>Cannot delete the default budget tier. Assign a different default first.</value>
</data>
<data name="BudgetTier_UserGroupAlreadyAssigned" xml:space="preserve">
  <value>This user group is already assigned to another budget tier.</value>
</data>
<data name="BudgetTier_UserGroupNotFound" xml:space="preserve">
  <value>The specified user group does not exist.</value>
</data>
```

- [ ] **Step 4: Add German error messages to ErrorMessages.de.resx**

Add to `Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.de.resx`:

```xml
<data name="BudgetTier_NotFound" xml:space="preserve">
  <value>Budget-Stufe nicht gefunden.</value>
</data>
<data name="BudgetTier_CannotDeleteDefault" xml:space="preserve">
  <value>Die Standard-Budget-Stufe kann nicht gelöscht werden. Weisen Sie zuerst eine andere Standard-Stufe zu.</value>
</data>
<data name="BudgetTier_UserGroupAlreadyAssigned" xml:space="preserve">
  <value>Diese Benutzergruppe ist bereits einer anderen Budget-Stufe zugeordnet.</value>
</data>
<data name="BudgetTier_UserGroupNotFound" xml:space="preserve">
  <value>Die angegebene Benutzergruppe existiert nicht.</value>
</data>
```

- [ ] **Step 5: Create the endpoint mapper (stub — queries/commands created in later tasks)**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/ControlCenterBudgetTierEndpoints.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers;

using adessoGPT.Application.ControlCenter.Business.BudgetTiers.DeleteBudgetTier;
using adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTier;
using adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTiers;
using adessoGPT.Application.ControlCenter.Business.BudgetTiers.SetDefaultBudgetTier;
using adessoGPT.Application.ControlCenter.Business.BudgetTiers.UpsertBudgetTier;
using adessoGPT.Core.Api.Authorization;
using adessoGPT.Core.Api.Endpoints;
using adessoGPT.Core.Api.Routing;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;

public class ControlCenterBudgetTierEndpoints : IEndpointMapper
{
    public static void MapEndpoints(IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/control-center/budget-tiers")
            .WithTags("Control Center Budget Tiers")
            .RequireRole(UserRoles.ControlCenterAdmin);

        group.MapGetCQRS<GetControlCenterBudgetTiersQuery, GetControlCenterBudgetTiersResponse>("");
        group.MapGetCQRS<GetControlCenterBudgetTierQuery, GetControlCenterBudgetTierResponse>("{id}");

        group.MapPostCQRSFromBody<CreateControlCenterBudgetTierCommand, BudgetTierId>("");
        group.MapPutCQRSFromBody<UpdateControlCenterBudgetTierCommand>("{id}");

        group.MapPostCQRS<SetControlCenterDefaultBudgetTierCommand>("{id}/set-default");
        group.MapDeleteCQRS<DeleteControlCenterBudgetTierCommand>("{id}");
    }
}
```

Note: This file references types from Tasks 6-10. It will only compile after all CQRS types are created. Build verification happens at the end.

- [ ] **Step 6: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/Models/ControlCenterBudgetTierDto.cs \
       Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/BudgetTierErrors.cs \
       Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/ControlCenterBudgetTierEndpoints.cs \
       Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.resx \
       Application/adessoGPT.Application.ControlCenter/Localization/ErrorMessages.de.resx
git commit -m "feat: add BudgetTier ControlCenter scaffolding — DTO, errors, endpoints, localization"
```

---

## Task 6: GetBudgetTiers Query (List All)

**Files:**
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersQuery.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersQueryHandler.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersResponse.cs`

- [ ] **Step 1: Create the query record**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersQuery.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTiers;

public record GetControlCenterBudgetTiersQuery : IQuery<GetControlCenterBudgetTiersResponse> { }
```

- [ ] **Step 2: Create the response DTOs**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersResponse.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTiers;

using adessoGPT.Core.Localization;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Domain.PersistedEntities.System.Settings.UserGroups;

public record GetControlCenterBudgetTiersResponse
{
    public required GetControlCenterBudgetTierItem[] BudgetTiers { get; init; }
}

public record GetControlCenterBudgetTierItem
{
    public required BudgetTierId Id { get; init; }
    public required LocalizedString Title { get; init; }
    public required LocalizedString Description { get; init; }
    public required int Priority { get; init; }
    public required bool IsDefault { get; init; }
    public UserGroupMappingId? AssignedUserGroupId { get; init; }
    public LocalizedString? AssignedUserGroupTitle { get; init; }
    public long? DailyTokenLimit { get; init; }
    public long? WeeklyTokenLimit { get; init; }
    public long? MonthlyTokenLimit { get; init; }
    public int? RequestsPerMinute { get; init; }
    public required int SoftWarningPercent { get; init; }
}
```

- [ ] **Step 3: Create the handler**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/GetControlCenterBudgetTiersQueryHandler.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTiers;

using System.Threading;
using System.Threading.Tasks;
using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.UserGroups;
using adessoGPT.Core.CQRS;
using adessoGPT.Core.Localization;
using adessoGPT.Core.Results;

internal class GetControlCenterBudgetTiersQueryHandler
    : IQueryHandler<GetControlCenterBudgetTiersQuery, GetControlCenterBudgetTiersResponse>
{
    private readonly IBudgetTierRepository _budgetTierRepository;
    private readonly IUserGroupRepository _userGroupRepository;

    public GetControlCenterBudgetTiersQueryHandler(
        IBudgetTierRepository budgetTierRepository,
        IUserGroupRepository userGroupRepository
    )
    {
        _budgetTierRepository = budgetTierRepository;
        _userGroupRepository = userGroupRepository;
    }

    public async Task<Result<GetControlCenterBudgetTiersResponse>> Handle(
        GetControlCenterBudgetTiersQuery query,
        CancellationToken cancellationToken
    )
    {
        var budgetTiers = await _budgetTierRepository.GetAllAsync(cancellationToken);
        var userGroups = await _userGroupRepository.GetAllAsync(cancellationToken);
        var userGroupLookup = userGroups.ToDictionary(ug => ug.Id);

        var items = budgetTiers
            .OrderBy(t => t.Priority)
            .Select(tier =>
            {
                LocalizedString? groupTitle = null;
                if (
                    tier.AssignedUserGroupId.HasValue
                    && userGroupLookup.TryGetValue(tier.AssignedUserGroupId.Value, out var userGroup)
                )
                {
                    groupTitle = LocalizedString.For(userGroup.Title);
                }

                return new GetControlCenterBudgetTierItem
                {
                    Id = tier.Id,
                    Title = LocalizedString.For(tier.Title)!,
                    Description = LocalizedString.For(tier.Description)!,
                    Priority = tier.Priority,
                    IsDefault = tier.IsDefault,
                    AssignedUserGroupId = tier.AssignedUserGroupId,
                    AssignedUserGroupTitle = groupTitle,
                    DailyTokenLimit = tier.DailyTokenLimit,
                    WeeklyTokenLimit = tier.WeeklyTokenLimit,
                    MonthlyTokenLimit = tier.MonthlyTokenLimit,
                    RequestsPerMinute = tier.RequestsPerMinute,
                    SoftWarningPercent = tier.SoftWarningPercent,
                };
            })
            .ToArray();

        return new GetControlCenterBudgetTiersResponse { BudgetTiers = items };
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTiers/
git commit -m "feat: add GetControlCenterBudgetTiers query handler"
```

---

## Task 7: GetBudgetTier Query (By ID)

**Files:**
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQuery.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQueryHandler.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQueryValidator.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierResponse.cs`

- [ ] **Step 1: Create the query record**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQuery.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTier;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

public record GetControlCenterBudgetTierQuery : IQuery<GetControlCenterBudgetTierResponse>
{
    public required BudgetTierId Id { get; init; }
}
```

- [ ] **Step 2: Create the response DTO**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierResponse.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTier;

using adessoGPT.Application.ControlCenter.Business.BudgetTiers.Models;
using adessoGPT.Core.Localization;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Domain.PersistedEntities.System.Settings.UserGroups;

public record GetControlCenterBudgetTierResponse : ControlCenterBudgetTierDto
{
    public required BudgetTierId Id { get; init; }
    public required bool IsDefault { get; init; }
    public LocalizedString? AssignedUserGroupTitle { get; init; }
}
```

- [ ] **Step 3: Create the validator**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQueryValidator.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTier;

using FluentValidation;

internal class GetControlCenterBudgetTierQueryValidator : AbstractValidator<GetControlCenterBudgetTierQuery>
{
    public GetControlCenterBudgetTierQueryValidator()
    {
        RuleFor(x => x.Id).NotEmpty();
    }
}
```

- [ ] **Step 4: Create the handler**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/GetControlCenterBudgetTierQueryHandler.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.GetBudgetTier;

using System.Threading;
using System.Threading.Tasks;
using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.UserGroups;
using adessoGPT.Core.CQRS;
using adessoGPT.Core.Localization;
using adessoGPT.Core.Results;

internal class GetControlCenterBudgetTierQueryHandler
    : IQueryHandler<GetControlCenterBudgetTierQuery, GetControlCenterBudgetTierResponse>
{
    private readonly IBudgetTierRepository _budgetTierRepository;
    private readonly IUserGroupRepository _userGroupRepository;

    public GetControlCenterBudgetTierQueryHandler(
        IBudgetTierRepository budgetTierRepository,
        IUserGroupRepository userGroupRepository
    )
    {
        _budgetTierRepository = budgetTierRepository;
        _userGroupRepository = userGroupRepository;
    }

    public async Task<Result<GetControlCenterBudgetTierResponse>> Handle(
        GetControlCenterBudgetTierQuery query,
        CancellationToken cancellationToken
    )
    {
        var tier = await _budgetTierRepository.GetByIdAsync(query.Id, cancellationToken);

        if (tier is null)
        {
            return BudgetTierErrors.NotFound(query.Id);
        }

        LocalizedString? groupTitle = null;
        if (tier.AssignedUserGroupId.HasValue)
        {
            var userGroup = await _userGroupRepository.GetByIdAsync(
                tier.AssignedUserGroupId.Value,
                cancellationToken
            );
            if (userGroup is not null)
            {
                groupTitle = LocalizedString.For(userGroup.Title);
            }
        }

        return new GetControlCenterBudgetTierResponse
        {
            Id = tier.Id,
            Title = tier.Title,
            Description = tier.Description,
            Priority = tier.Priority,
            IsDefault = tier.IsDefault,
            AssignedUserGroupId = tier.AssignedUserGroupId,
            AssignedUserGroupTitle = groupTitle,
            DailyTokenLimit = tier.DailyTokenLimit,
            WeeklyTokenLimit = tier.WeeklyTokenLimit,
            MonthlyTokenLimit = tier.MonthlyTokenLimit,
            RequestsPerMinute = tier.RequestsPerMinute,
            SoftWarningPercent = tier.SoftWarningPercent,
        };
    }
}
```

- [ ] **Step 5: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/GetBudgetTier/
git commit -m "feat: add GetControlCenterBudgetTier query handler"
```

---

## Task 8: Create and Update BudgetTier Commands

**Files:**
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/CreateControlCenterBudgetTierCommand.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/UpsertControlCenterBudgetTierCommandHandler.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/UpsertControlCenterBudgetTierCommandValidator.cs`

- [ ] **Step 1: Create the command records**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/CreateControlCenterBudgetTierCommand.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.UpsertBudgetTier;

using adessoGPT.Application.ControlCenter.Business.BudgetTiers.Models;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

public record CreateControlCenterBudgetTierCommand : ControlCenterBudgetTierDto, ICommand<BudgetTierId> { }

public record UpdateControlCenterBudgetTierCommand : ICommand
{
    public required BudgetTierId Id { get; init; }
    public required ControlCenterBudgetTierDto BudgetTier { get; init; }
}
```

- [ ] **Step 2: Create the validators**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/UpsertControlCenterBudgetTierCommandValidator.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.UpsertBudgetTier;

using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.UserGroups;
using adessoGPT.Core.Extensions;
using FluentValidation;
using Localization = adessoGPT.Application.ControlCenter.Localization;

internal class CreateControlCenterBudgetTierCommandValidator
    : AbstractValidator<CreateControlCenterBudgetTierCommand>
{
    public CreateControlCenterBudgetTierCommandValidator(
        IBudgetTierRepository budgetTierRepository,
        IUserGroupRepository userGroupRepository
    )
    {
        RuleFor(x => x.Title).NotEmpty().ValidLocalizationStrings();
        RuleFor(x => x.Description).NotEmpty().ValidLocalizationStrings();
        RuleFor(x => x.Priority).GreaterThan(0);
        RuleFor(x => x.SoftWarningPercent).InclusiveBetween(1, 100);
        RuleFor(x => x.DailyTokenLimit).GreaterThan(0).When(x => x.DailyTokenLimit.HasValue);
        RuleFor(x => x.WeeklyTokenLimit).GreaterThan(0).When(x => x.WeeklyTokenLimit.HasValue);
        RuleFor(x => x.MonthlyTokenLimit).GreaterThan(0).When(x => x.MonthlyTokenLimit.HasValue);
        RuleFor(x => x.RequestsPerMinute).GreaterThan(0).When(x => x.RequestsPerMinute.HasValue);

        RuleFor(x => x.AssignedUserGroupId)
            .MustAsync(
                async (userGroupId, cancellationToken) =>
                {
                    if (!userGroupId.HasValue)
                    {
                        return true;
                    }
                    return await userGroupRepository.ExistsAsync(userGroupId.Value, cancellationToken);
                }
            )
            .WithLocalizedMessage(Localization.ErrorMessages.BudgetTier_UserGroupNotFound)
            .MustAsync(
                async (userGroupId, cancellationToken) =>
                {
                    if (!userGroupId.HasValue)
                    {
                        return true;
                    }
                    var allTiers = await budgetTierRepository.GetAllAsync(cancellationToken);
                    return !allTiers.Any(t => t.AssignedUserGroupId == userGroupId);
                }
            )
            .WithLocalizedMessage(Localization.ErrorMessages.BudgetTier_UserGroupAlreadyAssigned);
    }
}

internal class UpdateControlCenterBudgetTierCommandValidator
    : AbstractValidator<UpdateControlCenterBudgetTierCommand>
{
    public UpdateControlCenterBudgetTierCommandValidator(
        IBudgetTierRepository budgetTierRepository,
        IUserGroupRepository userGroupRepository
    )
    {
        RuleFor(x => x.Id)
            .NotEmpty()
            .MustAsync(
                async (id, cancellationToken) =>
                {
                    return await budgetTierRepository.ExistsAsync(id, cancellationToken);
                }
            )
            .WithLocalizedMessage(Localization.ErrorMessages.BudgetTier_NotFound);

        RuleFor(x => x.BudgetTier.Title).NotEmpty().ValidLocalizationStrings();
        RuleFor(x => x.BudgetTier.Description).NotEmpty().ValidLocalizationStrings();
        RuleFor(x => x.BudgetTier.Priority).GreaterThan(0);
        RuleFor(x => x.BudgetTier.SoftWarningPercent).InclusiveBetween(1, 100);
        RuleFor(x => x.BudgetTier.DailyTokenLimit)
            .GreaterThan(0)
            .When(x => x.BudgetTier.DailyTokenLimit.HasValue);
        RuleFor(x => x.BudgetTier.WeeklyTokenLimit)
            .GreaterThan(0)
            .When(x => x.BudgetTier.WeeklyTokenLimit.HasValue);
        RuleFor(x => x.BudgetTier.MonthlyTokenLimit)
            .GreaterThan(0)
            .When(x => x.BudgetTier.MonthlyTokenLimit.HasValue);
        RuleFor(x => x.BudgetTier.RequestsPerMinute)
            .GreaterThan(0)
            .When(x => x.BudgetTier.RequestsPerMinute.HasValue);

        RuleFor(x => x.BudgetTier.AssignedUserGroupId)
            .MustAsync(
                async (userGroupId, cancellationToken) =>
                {
                    if (!userGroupId.HasValue)
                    {
                        return true;
                    }
                    return await userGroupRepository.ExistsAsync(userGroupId.Value, cancellationToken);
                }
            )
            .WithLocalizedMessage(Localization.ErrorMessages.BudgetTier_UserGroupNotFound)
            .MustAsync(
                async (command, userGroupId, cancellationToken) =>
                {
                    if (!userGroupId.HasValue)
                    {
                        return true;
                    }
                    var allTiers = await budgetTierRepository.GetAllAsync(cancellationToken);
                    return !allTiers.Any(t =>
                        t.AssignedUserGroupId == userGroupId && t.Id != command.Id
                    );
                }
            )
            .WithLocalizedMessage(Localization.ErrorMessages.BudgetTier_UserGroupAlreadyAssigned);
    }
}
```

- [ ] **Step 3: Create the handler**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/UpsertControlCenterBudgetTierCommandHandler.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.UpsertBudgetTier;

using System;
using System.Threading;
using System.Threading.Tasks;
using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.Settings;
using adessoGPT.Core.CQRS;
using adessoGPT.Core.Results;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Domain.PersistedEntities.System.SingleSettings;

internal class UpsertControlCenterBudgetTierCommandHandler
    : ICommandHandler<CreateControlCenterBudgetTierCommand, BudgetTierId>,
        ICommandHandler<UpdateControlCenterBudgetTierCommand>
{
    private readonly IBudgetTierRepository _budgetTierRepository;
    private readonly ISingleSettingsRepository _singleSettingsRepository;

    public UpsertControlCenterBudgetTierCommandHandler(
        IBudgetTierRepository budgetTierRepository,
        ISingleSettingsRepository singleSettingsRepository
    )
    {
        _budgetTierRepository = budgetTierRepository;
        _singleSettingsRepository = singleSettingsRepository;
    }

    public async Task<Result<BudgetTierId>> Handle(
        CreateControlCenterBudgetTierCommand command,
        CancellationToken cancellationToken
    )
    {
        var budgetTier = new BudgetTier()
        {
            Id = new BudgetTierId(Guid.NewGuid().ToString()),
            Title = command.Title,
            Description = command.Description,
            Priority = command.Priority,
            AssignedUserGroupId = command.AssignedUserGroupId,
            DailyTokenLimit = command.DailyTokenLimit,
            WeeklyTokenLimit = command.WeeklyTokenLimit,
            MonthlyTokenLimit = command.MonthlyTokenLimit,
            RequestsPerMinute = command.RequestsPerMinute,
            SoftWarningPercent = command.SoftWarningPercent,
        };

        await _budgetTierRepository.AddAsync(budgetTier, cancellationToken);
        return budgetTier.Id;
    }

    public async Task<Result> Handle(
        UpdateControlCenterBudgetTierCommand command,
        CancellationToken cancellationToken
    )
    {
        var existingTier = await _budgetTierRepository.GetByIdAsync(command.Id, cancellationToken);
        if (existingTier is null)
        {
            return BudgetTierErrors.NotFound(command.Id);
        }

        await _budgetTierRepository.UpdateAsync(
            command.Id,
            tier =>
                tier with
                {
                    Title = command.BudgetTier.Title,
                    Description = command.BudgetTier.Description,
                    Priority = command.BudgetTier.Priority,
                    AssignedUserGroupId = command.BudgetTier.AssignedUserGroupId,
                    DailyTokenLimit = command.BudgetTier.DailyTokenLimit,
                    WeeklyTokenLimit = command.BudgetTier.WeeklyTokenLimit,
                    MonthlyTokenLimit = command.BudgetTier.MonthlyTokenLimit,
                    RequestsPerMinute = command.BudgetTier.RequestsPerMinute,
                    SoftWarningPercent = command.BudgetTier.SoftWarningPercent,
                },
            cancellationToken
        );

        return Result.Success();
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/UpsertBudgetTier/
git commit -m "feat: add Create and Update BudgetTier command handlers with validation"
```

---

## Task 9: Delete BudgetTier Command

**Files:**
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommand.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommandHandler.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommandValidator.cs`

- [ ] **Step 1: Create the command**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommand.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.DeleteBudgetTier;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

public record DeleteControlCenterBudgetTierCommand : ICommand
{
    public required BudgetTierId Id { get; init; }
}
```

- [ ] **Step 2: Create the validator**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommandValidator.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.DeleteBudgetTier;

using FluentValidation;

internal class DeleteControlCenterBudgetTierCommandValidator
    : AbstractValidator<DeleteControlCenterBudgetTierCommand>
{
    public DeleteControlCenterBudgetTierCommandValidator()
    {
        RuleFor(x => x.Id).NotEmpty();
    }
}
```

- [ ] **Step 3: Create the handler**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/DeleteControlCenterBudgetTierCommandHandler.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.DeleteBudgetTier;

using System.Threading;
using System.Threading.Tasks;
using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.Settings;
using adessoGPT.Core.Localization;
using adessoGPT.Core.Results;
using adessoGPT.Core.Results.Errors;
using adessoGPT.Domain.PersistedEntities.System.SingleSettings;
using Localization = adessoGPT.Application.ControlCenter.Localization;

internal class DeleteControlCenterBudgetTierCommandHandler
    : ICommandHandler<DeleteControlCenterBudgetTierCommand>
{
    private readonly IBudgetTierRepository _budgetTierRepository;
    private readonly ISingleSettingsRepository _singleSettingsRepository;

    public DeleteControlCenterBudgetTierCommandHandler(
        IBudgetTierRepository budgetTierRepository,
        ISingleSettingsRepository singleSettingsRepository
    )
    {
        _budgetTierRepository = budgetTierRepository;
        _singleSettingsRepository = singleSettingsRepository;
    }

    public async Task<Result> Handle(
        DeleteControlCenterBudgetTierCommand command,
        CancellationToken cancellationToken
    )
    {
        var tier = await _budgetTierRepository.GetByIdAsync(command.Id, cancellationToken);

        if (tier is null)
        {
            return BudgetTierErrors.NotFound(command.Id);
        }

        if (tier.IsDefault)
        {
            return BusinessError.Conflict(
                "budget-tier-cannot-delete-default",
                LocalizedString.For(Localization.ErrorMessages.BudgetTier_CannotDeleteDefault)
            );
        }

        var deleted = await _budgetTierRepository.DeleteAsync(command.Id, cancellationToken);

        if (!deleted)
        {
            return Result.Fail("budget-tier-delete", $"Failed to delete budget tier with ID '{command.Id}'.");
        }

        var settings = await _singleSettingsRepository.GetSingleSettingsAsync<BudgetLimitSettings>(cancellationToken);
        if (settings.DefaultBudgetTierId.HasValue && settings.DefaultBudgetTierId.Value == command.Id)
        {
            await _singleSettingsRepository.UpdateAsync(
                settings.Id,
                s => (s as BudgetLimitSettings)! with { DefaultBudgetTierId = null },
                cancellationToken
            );
        }

        return Result.Success();
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/DeleteBudgetTier/
git commit -m "feat: add DeleteBudgetTier command handler"
```

---

## Task 10: SetDefault BudgetTier Command

**Files:**
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommand.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommandHandler.cs`
- Create: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommandValidator.cs`

- [ ] **Step 1: Create the command**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommand.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.SetDefaultBudgetTier;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

public record SetControlCenterDefaultBudgetTierCommand : ICommand
{
    public required BudgetTierId Id { get; init; }
}
```

- [ ] **Step 2: Create the validator**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommandValidator.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.SetDefaultBudgetTier;

using FluentValidation;

internal class SetControlCenterDefaultBudgetTierCommandValidator
    : AbstractValidator<SetControlCenterDefaultBudgetTierCommand>
{
    public SetControlCenterDefaultBudgetTierCommandValidator()
    {
        RuleFor(x => x.Id).NotEmpty();
    }
}
```

- [ ] **Step 3: Create the handler**

Create `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/SetControlCenterDefaultBudgetTierCommandHandler.cs`:

```csharp
namespace adessoGPT.Application.ControlCenter.Business.BudgetTiers.SetDefaultBudgetTier;

using System.Threading;
using System.Threading.Tasks;
using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.Settings;
using adessoGPT.Core.Results;
using adessoGPT.Domain.PersistedEntities.System.SingleSettings;

internal class SetControlCenterDefaultBudgetTierCommandHandler
    : ICommandHandler<SetControlCenterDefaultBudgetTierCommand>
{
    private readonly IBudgetTierRepository _budgetTierRepository;
    private readonly ISingleSettingsRepository _singleSettingsRepository;

    public SetControlCenterDefaultBudgetTierCommandHandler(
        IBudgetTierRepository budgetTierRepository,
        ISingleSettingsRepository singleSettingsRepository
    )
    {
        _budgetTierRepository = budgetTierRepository;
        _singleSettingsRepository = singleSettingsRepository;
    }

    public async Task<Result> Handle(
        SetControlCenterDefaultBudgetTierCommand command,
        CancellationToken cancellationToken
    )
    {
        var tier = await _budgetTierRepository.GetByIdAsync(command.Id, cancellationToken);

        if (tier is null)
        {
            return BudgetTierErrors.NotFound(command.Id);
        }

        var allTiers = await _budgetTierRepository.GetAllAsync(cancellationToken);

        foreach (var existingTier in allTiers.Where(t => t.IsDefault && t.Id != command.Id))
        {
            await _budgetTierRepository.UpdateAsync(
                existingTier.Id,
                t => t with { IsDefault = false },
                cancellationToken
            );
        }

        await _budgetTierRepository.UpdateAsync(
            command.Id,
            t => t with { IsDefault = true },
            cancellationToken
        );

        var settings = await _singleSettingsRepository.GetSingleSettingsAsync<BudgetLimitSettings>(cancellationToken);
        await _singleSettingsRepository.UpdateAsync(
            settings.Id,
            s => (s as BudgetLimitSettings)! with { DefaultBudgetTierId = command.Id },
            cancellationToken
        );

        return Result.Success();
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/SetDefaultBudgetTier/
git commit -m "feat: add SetDefaultBudgetTier command handler"
```

---

## Task 11: Delete Cascade — UserGroup Deletion Clears BudgetTier

**Files:**
- Modify: `Application/adessoGPT.Application.ControlCenter/Business/UserGroups/DeleteUserGroup/DeleteControlCenterUserGroupCommandHandler.cs`

- [ ] **Step 1: Add BudgetTier cascade to the delete handler**

In `DeleteControlCenterUserGroupCommandHandler.cs`:

1. Add a constructor parameter: `IBudgetTierRepository budgetTierRepository`
2. Add a private field: `private readonly IBudgetTierRepository _budgetTierRepository;`
3. After the existing cascade logic for models (before the final `DeleteAsync` call), add:

```csharp
var budgetTiers = await _budgetTierRepository.GetAllAsync(cancellationToken);
var budgetTiersToUpdate = budgetTiers
    .Where(tier => tier.AssignedUserGroupId == userGroup.Id)
    .Select(tier => tier with { AssignedUserGroupId = null })
    .ToList();

if (budgetTiersToUpdate.Count > 0)
{
    await _budgetTierRepository.UpdateRangeAsync(budgetTiersToUpdate, cancellationToken);
}
```

Add the necessary using statement: `using adessoGPT.Application.Business.BudgetTiers;`

- [ ] **Step 2: Build to verify**

Run: `dotnet build Application/adessoGPT.Application.ControlCenter/`
Expected: Build succeeded

- [ ] **Step 3: Commit**

```bash
git add Application/adessoGPT.Application.ControlCenter/Business/UserGroups/DeleteUserGroup/DeleteControlCenterUserGroupCommandHandler.cs
git commit -m "feat: cascade UserGroup deletion to BudgetTier.AssignedUserGroupId"
```

---

## Task 12: BudgetTierResolver Service

**Files:**
- Create: `Application/adessoGPT.Application/Business/Budget/Services/IBudgetTierResolver.cs`
- Create: `Application/adessoGPT.Application/Business/Budget/Services/BudgetTierResolver.cs`

- [ ] **Step 1: Create the interface**

Create `Application/adessoGPT.Application/Business/Budget/Services/IBudgetTierResolver.cs`:

```csharp
namespace adessoGPT.Application.Business.Budget.Services;

using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

public interface IBudgetTierResolver
{
    Task<BudgetTier?> ResolveForUserAsync(CancellationToken cancellationToken);
}
```

- [ ] **Step 2: Create the implementation**

Create `Application/adessoGPT.Application/Business/Budget/Services/BudgetTierResolver.cs`:

```csharp
namespace adessoGPT.Application.Business.Budget.Services;

using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using adessoGPT.Application.Business.BudgetTiers;
using adessoGPT.Application.Business.UserGroups;
using adessoGPT.Core.Users;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;

internal class BudgetTierResolver : IBudgetTierResolver
{
    private readonly IUserAccessor _userAccessor;
    private readonly IBudgetTierRepository _budgetTierRepository;
    private readonly IUserGroupRepository _userGroupRepository;

    public BudgetTierResolver(
        IUserAccessor userAccessor,
        IBudgetTierRepository budgetTierRepository,
        IUserGroupRepository userGroupRepository
    )
    {
        _userAccessor = userAccessor;
        _budgetTierRepository = budgetTierRepository;
        _userGroupRepository = userGroupRepository;
    }

    public async Task<BudgetTier?> ResolveForUserAsync(CancellationToken cancellationToken)
    {
        var userGroupIds = _userAccessor.GetUserGroups();
        var allTiers = await _budgetTierRepository.GetAllAsync(cancellationToken);
        var allUserGroups = await _userGroupRepository.GetAllAsync(cancellationToken);

        var externalGroupIdToMappingId = allUserGroups.ToDictionary(
            ug => ug.ExternalGroupId,
            ug => ug.Id
        );

        var matchedTiers = new List<BudgetTier>();

        foreach (var userGroupId in userGroupIds)
        {
            var externalGroupId = new Domain.PersistedEntities.System.Settings.UserGroups.ExternalGroupId(
                userGroupId.Value
            );

            if (externalGroupIdToMappingId.TryGetValue(externalGroupId, out var mappingId))
            {
                var tier = allTiers.FirstOrDefault(t => t.AssignedUserGroupId == mappingId);
                if (tier is not null)
                {
                    matchedTiers.Add(tier);
                }
            }
        }

        if (matchedTiers.Count > 0)
        {
            return matchedTiers.MinBy(t => t.Priority);
        }

        return allTiers.FirstOrDefault(t => t.IsDefault);
    }
}
```

- [ ] **Step 3: Register the service in DI**

Find the DI registration file for Budget services (search for where `IBudgetGuardService` is registered) and add:

```csharp
services.AddScoped<IBudgetTierResolver, BudgetTierResolver>();
```

This is typically in a `ServiceRegistration` or `ModulesConfiguration` file. Match the existing registration pattern for `IBudgetGuardService`.

- [ ] **Step 4: Build to verify**

Run: `dotnet build Application/adessoGPT.Application/`
Expected: Build succeeded

- [ ] **Step 5: Commit**

```bash
git add Application/adessoGPT.Application/Business/Budget/Services/IBudgetTierResolver.cs \
       Application/adessoGPT.Application/Business/Budget/Services/BudgetTierResolver.cs
git commit -m "feat: add BudgetTierResolver — resolves JWT groups to most restrictive tier"
```

---

## Task 13: Full Build Verification and Formatting

- [ ] **Step 1: Build the entire solution**

Run: `dotnet build`
Expected: Build succeeded with 0 errors

If there are build errors, fix them. Common issues:
- Missing `using` statements
- Namespace mismatches
- `LocalizedString.For()` overload resolution

- [ ] **Step 2: Run CSharpier formatter**

Run: `dotnet csharpier format .`
Expected: Formatted N files

- [ ] **Step 3: Commit formatting changes (if any)**

```bash
git add -A
git commit -m "chore: format with CSharpier"
```

- [ ] **Step 4: Run tests to verify no regressions**

Run: `dotnet test`
Expected: All tests pass

---

## Task 14: Update .claude/rules for BudgetTier

**Files:**
- Create or update: `.claude/rules/budget-tier.md` (in the Backend directory)

- [ ] **Step 1: Create the rules file**

Create `Backend/.claude/rules/budget-tier.md`:

```markdown
---
paths:
  - "Shared/adessoGPT.Domain/PersistedEntities/System/Settings/BudgetTier/**"
  - "Application/adessoGPT.Application/Business/BudgetTiers/**"
  - "Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/**"
  - "Application/adessoGPT.Application/Business/Budget/Services/IBudgetTierResolver.cs"
  - "Application/adessoGPT.Application/Business/Budget/Services/BudgetTierResolver.cs"
---

# BudgetTier Entity

`BudgetTier` is a `SystemSettingsPartitionedEntity` (collection entity in the `system` Cosmos container, SystemScope = "Settings"). Admin-managed via `/api/control-center/budget-tiers` endpoints.

## Key Files

- Domain entity: `Shared/adessoGPT.Domain/PersistedEntities/System/Settings/BudgetTier/BudgetTier.cs`
- Repository: `Application/adessoGPT.Application/Business/BudgetTiers/BudgetTierRepository.cs`
- CQRS handlers: `Application/adessoGPT.Application.ControlCenter/Business/BudgetTiers/`
- Tier resolver: `Application/adessoGPT.Application/Business/Budget/Services/BudgetTierResolver.cs`

## Design Decisions

- **null limit = unlimited** — `DailyTokenLimit`, `WeeklyTokenLimit`, `MonthlyTokenLimit` are `long?`. `null` means no enforcement for that period.
- **1:1 group assignment** — `AssignedUserGroupId` (nullable `UserGroupMappingId`) maps to exactly one user group. `null` means unassigned (used for the default tier).
- **Priority conflict resolution** — When a user belongs to multiple groups with tiers, the tier with the lowest `Priority` value wins (most restrictive).
- **Default tier** — Exactly one tier has `IsDefault = true`. Falls back for users without any matched group.
- **Delete cascade** — Deleting a `UserGroupMapping` clears `AssignedUserGroupId` on any referencing `BudgetTier`. Deleting the default tier is blocked.

## API Endpoints

All require `ControlCenterAdmin` role.

```
GET    /api/control-center/budget-tiers
GET    /api/control-center/budget-tiers/{id}
POST   /api/control-center/budget-tiers
PUT    /api/control-center/budget-tiers/{id}
DELETE /api/control-center/budget-tiers/{id}
POST   /api/control-center/budget-tiers/{id}/set-default
```
```

- [ ] **Step 2: Commit**

```bash
git add Backend/.claude/rules/budget-tier.md
git commit -m "docs: add .claude/rules for BudgetTier entity"
```
