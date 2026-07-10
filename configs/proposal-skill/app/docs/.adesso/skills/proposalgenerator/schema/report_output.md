<!-- THIS IS AN EXAMPLE OUTPUT using the fictional client "CloudRetail" and a POS modernisation scenario. -->
<!-- ALL company names, requirements, technologies, numbers, dates, and budgets below are PLACEHOLDERS. -->
<!-- The LLM MUST replace every detail with actual data extracted from the input JSON. -->
<!-- Do NOT copy any content from this example — derive everything from the real input data. -->

# Requirements Analysis Report

**Document:** [EXAMPLE] CloudRetail_POS_Modernization_Requirements_v2

<!-- Replace with actual document name from input -->

## Executive Summary

[EXAMPLE] The document describes a comprehensive modernization initiative for CloudRetail's point-of-sale infrastructure. The project aims to replace legacy POS terminals with a cloud-connected, real-time system supporting multiple input methods, offline capability, and advanced reporting. Key focus areas include transaction performance, data security (PCI-DSS compliance), and high availability across all retail locations.

<!-- Derive from: executive_summary in input JSON -->

### Key Topics

<!-- EXAMPLE list — replace entirely with key_topics from input JSON -->

- [EXAMPLE] POS terminal modernization
- [EXAMPLE] Real-time transaction processing
- [EXAMPLE] Offline-capable architecture
- [EXAMPLE] Multi-input support (barcode, NFC, manual)
- [EXAMPLE] Sales reporting and analytics
- [EXAMPLE] PCI-DSS compliance
- [EXAMPLE] High availability infrastructure

## Client Context

<!-- EXAMPLE table — replace all values from client_context in input JSON -->

| Attribute | Details |
|-----------|---------|
| **Industry** | [EXAMPLE] Retail |
| **Current Systems** | [EXAMPLE] Legacy POS v3.2, SAP ERP, Oracle DB 12c, Cisco network infrastructure |
| **Pain Points** | [EXAMPLE] Frequent POS terminal crashes during peak hours, No offline capability leading to lost sales, Manual reporting processes taking 2+ days, PCI-DSS audit findings on data encryption |
| **Strategic Goals** | [EXAMPLE] Achieve sub-2-second transaction processing, Enable 99.9% system availability, Implement real-time sales analytics, Full PCI-DSS Level 1 compliance |

## Functional Requirements

<!-- EXAMPLE table — replace ALL rows with actual functional requirements from input JSON -->
<!-- Resolve sources via the aspect chain: requirement.aspect_id -> aspects[].section_id -> sections[].section_heading + chapter_heading -->

| ID | Description | Priority | Source |
|----|-------------|----------|--------|
| FR-001 | [EXAMPLE] The system shall process point-of-sale transactions in real time and synchronize with the central inventory database. | [EXAMPLE] must | [EXAMPLE] System Architecture > Transaction Processing (CloudRetail_POS_Modernization_Requirements_v2) |
| FR-002 | [EXAMPLE] The system shall support barcode scanning, NFC payment, and manual item entry at each terminal. | [EXAMPLE] must | [EXAMPLE] System Architecture > Input Methods (CloudRetail_POS_Modernization_Requirements_v2) |
| FR-003 | [EXAMPLE] The system shall generate daily, weekly, and monthly sales reports with drill-down by store, region, and product category. | [EXAMPLE] must | [EXAMPLE] Reporting and Analytics > Sales Reports (CloudRetail_POS_Modernization_Requirements_v2) |
| FR-004 | [EXAMPLE] The cashier shall be able to apply discount codes, loyalty points, and promotional pricing during checkout. | [EXAMPLE] should | [EXAMPLE] Business Logic > Pricing and Discounts (CloudRetail_POS_Modernization_Requirements_v2) |
| FR-005 | [EXAMPLE] The system shall provide an offline mode that queues transactions locally and syncs automatically when connectivity is restored. | [EXAMPLE] must | [EXAMPLE] System Architecture > Offline Capability (CloudRetail_POS_Modernization_Requirements_v2) |

## Non-Functional Requirements

<!-- EXAMPLE table — replace ALL rows with actual non-functional requirements from input JSON -->

| ID | Category | Description | Measurable Target | Source |
|----|----------|-------------|-------------------|--------|
| NFR-001 | [EXAMPLE] Performance | [EXAMPLE] The system shall complete a checkout transaction within 2 seconds under normal load. | [EXAMPLE] < 2 sec | [EXAMPLE] System Architecture > Performance Targets (CloudRetail_POS_Modernization_Requirements_v2) |
| NFR-002 | [EXAMPLE] Availability | [EXAMPLE] The POS system shall maintain 99.9% uptime during store operating hours. | [EXAMPLE] 99.9% uptime | [EXAMPLE] Operations > Service Level Agreements (CloudRetail_POS_Modernization_Requirements_v2) |
| NFR-003 | [EXAMPLE] Security | [EXAMPLE] All payment data shall be encrypted in transit and at rest in compliance with PCI-DSS. | [EXAMPLE] PCI-DSS Level 1 | [EXAMPLE] Security and Compliance > Data Protection (CloudRetail_POS_Modernization_Requirements_v2) |

## Formal Requirements

<!-- EXAMPLE table — replace ALL rows with actual formal requirements from input JSON -->

| ID | Category | Description | Binding | Deadline | Source |
|----|----------|-------------|---------|----------|--------|
| FORM-001 | [EXAMPLE] Deadline | [EXAMPLE] Proposals must be submitted no later than 15 March 2025, 12:00 CET. | [EXAMPLE] **Yes** | [EXAMPLE] 2025-03-15T12:00:00 | [EXAMPLE] General Information > Submission Rules (CloudRetail_POS_Modernization_Requirements_v2) |
| FORM-002 | [EXAMPLE] Format | [EXAMPLE] The proposal must be submitted as a single PDF document, maximum 50 pages. | [EXAMPLE] **Yes** | — | [EXAMPLE] General Information > Submission Rules (CloudRetail_POS_Modernization_Requirements_v2) |
| FORM-003 | [EXAMPLE] Eligibility | [EXAMPLE] Bidders must provide proof of at least 3 comparable retail IT projects completed in the last 5 years. | [EXAMPLE] **Yes** | — | [EXAMPLE] Eligibility Criteria > Experience (CloudRetail_POS_Modernization_Requirements_v2) |
| FORM-004 | [EXAMPLE] Pricing | [EXAMPLE] Pricing must be broken down by module and include separate line items for licenses, implementation, and annual maintenance. | [EXAMPLE] **Yes** | — | [EXAMPLE] Commercial Terms > Pricing Structure (CloudRetail_POS_Modernization_Requirements_v2) |
| FORM-005 | [EXAMPLE] Legal | [EXAMPLE] The proposal should include a draft service level agreement (SLA) for review. | [EXAMPLE] **No** | — | [EXAMPLE] Commercial Terms > Service Agreements (CloudRetail_POS_Modernization_Requirements_v2) |

## Project Constraints

### Budget

<!-- EXAMPLE table — replace with actual budget data from constraints.budget -->

| Attribute | Value |
|-----------|-------|
| **Amount** | [EXAMPLE] 2.500.000 EUR |
| **Currency** | [EXAMPLE] EUR |
| **Flexibility** | [EXAMPLE] **Indicative** (estimate/negotiable) |

*Sources: [EXAMPLE] Commercial Terms > Budget Framework*

### Timeline

<!-- EXAMPLE — replace with actual timeline from constraints.timeline -->

- **Go-Live:** [EXAMPLE] 2025-Q4
- **Key Milestones:**
  - [EXAMPLE] Vendor selection by 2025-04-30
  - [EXAMPLE] Pilot rollout at 5 flagship stores by 2025-07-31
  - [EXAMPLE] Full rollout across all 120 locations by 2025-12-31

*Sources: [EXAMPLE] Project Plan > Timeline, General Information > Key Dates*

### Technical Constraints

<!-- EXAMPLE list — replace with actual technical constraints from constraints.technical -->

- [EXAMPLE] All components must run on Microsoft Azure (no on-premise hosting)
- [EXAMPLE] Java 17 or higher required for backend services
- [EXAMPLE] Must integrate with existing SAP ERP via RFC/BAPI interfaces
- [EXAMPLE] PCI-DSS Level 1 certified hosting environment mandatory

*Sources: [EXAMPLE] System Architecture > Technology Stack, Security and Compliance > Hosting Requirements*

### Organisational Constraints

<!-- EXAMPLE list — replace with actual organisational constraints from constraints.organisational -->

- [EXAMPLE] Project team must be available on-site at least 3 days per week during implementation
- [EXAMPLE] German-speaking project lead mandatory
- [EXAMPLE] ISO 27001 certification of the bidder required
- [EXAMPLE] Knowledge transfer workshops for internal IT team (minimum 5 days)

*Sources: [EXAMPLE] General Information > Collaboration Model, Eligibility Criteria > Certifications*

## Open Points — Coverage Gap Analysis

[EXAMPLE] 78% of aspects are covered by at least one requirement (14 of 18 aspects covered, 4 uncovered).

<!-- Derive coverage percentage and counts from open_points analysis in input JSON -->

<!-- EXAMPLE table — replace ALL rows with actual open points from the gap analysis -->

| Aspect | Location | Severity | Reason |
|--------|----------|----------|--------|
| [EXAMPLE] Data Migration Strategy | [EXAMPLE] System Architecture > Migration Planning | [EXAMPLE] High | [EXAMPLE] No requirement specifies how existing transaction data will be migrated from the legacy POS system. |
| [EXAMPLE] Staff Training | [EXAMPLE] Operations > Training and Rollout | [EXAMPLE] High | [EXAMPLE] No requirement covers end-user training for cashiers and store managers. |
| [EXAMPLE] Third-Party Integrations | [EXAMPLE] System Architecture > External Interfaces | [EXAMPLE] Medium | [EXAMPLE] Payment gateway and loyalty system integrations are mentioned but no specific requirements are defined. |
| [EXAMPLE] Monitoring and Alerting | [EXAMPLE] Operations > System Monitoring | [EXAMPLE] Low | [EXAMPLE] Monitoring is implied by the availability NFR but no explicit requirement exists. Likely covered implicitly. |

## Summary

[EXAMPLE] A total of 5 functional requirements, 3 non-functional requirements, and 5 formal requirements were identified. Priority distribution of functional requirements: 4 Must, 1 Should, 0 Nice-to-have. Formal requirements: 4 binding, 1 optional. Project constraints: indicative budget of 2.500.000 EUR, go-live target Q4 2025, 4 technical constraints, 4 organisational constraints. Aspect coverage: 78% (14/18 covered), 4 open points identified (2 high, 1 medium, 1 low severity).

<!-- Derive all counts and statistics from actual input data -->
