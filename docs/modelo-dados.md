# Modelo conceitual de dados

O modelo cobre as entidades mínimas do desafio sem antecipar regras funcionais das
specs seguintes. Identificadores são UUIDs gerados no servidor. Tokens públicos são
separados das chaves internas para reduzir enumeração e acoplamento.

```mermaid
erDiagram
    INTERNAL_USER ||--o{ EQUIPMENT : cadastra
    INTERNAL_USER ||--o{ MOVEMENT : realiza
    INTERNAL_USER o|--o{ OCCURRENCE : atende
    INTERNAL_USER o|--o{ MAINTENANCE : executa
    INTERNAL_USER o|--o{ AUDIT_EVENT : atua
    ENVIRONMENT ||--o{ EQUIPMENT : localiza
    ENVIRONMENT ||--o{ MOVEMENT : origem
    ENVIRONMENT ||--o{ MOVEMENT : destino
    ENVIRONMENT ||--o{ OCCURRENCE : contextualiza
    EQUIPMENT ||--o{ MOVEMENT : movimenta
    EQUIPMENT ||--o{ OCCURRENCE : recebe
    EQUIPMENT ||--o{ MAINTENANCE : recebe
    OCCURRENCE o|--o{ MAINTENANCE : origina

    INTERNAL_USER {
        uuid id PK
        string auth_subject UK
        string display_name
        string role
        boolean active
    }
    ENVIRONMENT {
        uuid id PK
        string code UK
        string name
        string kind
        boolean active
    }
    EQUIPMENT {
        uuid id PK
        uuid public_token UK
        string asset_tag UK
        string kind
        string status
        uuid location_id FK
        uuid registered_by_id FK
    }
    MOVEMENT {
        uuid id PK
        uuid equipment_id FK
        uuid origin_environment_id FK
        uuid destination_environment_id FK
        uuid moved_by_id FK
        text reason
    }
    OCCURRENCE {
        uuid id PK
        uuid public_tracking_token UK
        uuid equipment_id FK
        uuid environment_id FK
        string status
        string priority
        uuid assigned_to_id FK
    }
    MAINTENANCE {
        uuid id PK
        uuid equipment_id FK
        uuid occurrence_id FK
        string kind
        string status
        uuid technician_id FK
    }
    AUDIT_EVENT {
        uuid id PK
        uuid actor_id FK
        string entity_type
        uuid entity_id
        string action
        json previous_state
        json new_state
        text reason
        datetime occurred_at
    }
```

## Invariantes da fundação

- Equipamento referencia um ambiente e o usuário que realizou o cadastro.
- Uma movimentação exige origem distinta do destino, ator e justificativa.
- Ocorrências e manutenções usam estados limitados por `CHECK` no banco.
- Mudanças patrimoniais devem produzir `audit_events` com ator, instante,
  justificativa e estados anterior/novo; a gravação transacional será feita pelos
  serviços das specs funcionais.
- `audit_events` rejeita `UPDATE` e `DELETE` por trigger. Correções são novos
  eventos, nunca alterações do histórico.
- Chaves estrangeiras usam `RESTRICT` para impedir exclusão silenciosa de
  histórico.

## Dados pessoais e retenção

`display_name` e `auth_subject` são dados pessoais e ficam na zona protegida. Logs e
auditoria devem preferir o identificador interno e não copiar nomes, credenciais ou
tokens. Política de retenção, anonimização e backup permanece pendente de decisão
institucional antes da produção.

