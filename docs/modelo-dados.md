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
        string password_hash
        string role
        boolean active
    }
    USER_SESSION {
        uuid id PK
        uuid user_id FK
        string token_hash UK
        string csrf_token_hash
        datetime expires_at
        datetime revoked_at
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
        string brand
        string model
        uuid location_id FK
        uuid registered_by_id FK
        date last_maintenance_on
        date next_maintenance_on
        datetime public_token_revoked_at
        boolean active
        datetime created_at
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
        string reporter_name
        string reporter_contact
        text resolution_reason
        datetime closed_at
        uuid closed_by_id FK
        uuid assigned_to_id FK
    }
    OCCURRENCE_COMMENT {
        uuid id PK
        uuid occurrence_id FK
        uuid author_id FK
        text body
        datetime created_at
    }
    MAINTENANCE {
        uuid id PK
        uuid equipment_id FK
        uuid occurrence_id FK
        string kind
        string status
        uuid technician_id FK
        date scheduled_for
        datetime started_at
        datetime completed_at
        text procedure
        text result
    }
    MAINTENANCE_COMPONENT {
        uuid id PK
        uuid maintenance_id FK
        string component_name
        integer quantity
        text observation
        datetime created_at
    }
    MAINTENANCE_PLAN {
        uuid id PK
        integer year
        integer version
        string status
        json capacity_monthly
        json blackout_periods
        json summary
        uuid created_by_id FK
        uuid approved_by_id FK
        datetime approved_at
        datetime published_at
    }
    MAINTENANCE_PLAN_ITEM {
        uuid id PK
        uuid plan_id FK
        uuid equipment_id FK
        uuid environment_id FK
        date scheduled_for
        string status
        text justification
    }
    MAINTENANCE_ALERT {
        uuid id PK
        uuid equipment_id FK
        uuid maintenance_id FK
        string kind
        date due_on
        string idempotency_key UK
        string status
        date generated_for
    }
    NOTIFICATION_DELIVERY {
        uuid id PK
        uuid alert_id FK
        string channel
        string recipient_label
        string idempotency_key UK
        string status
        integer attempts
        text last_error
        datetime sent_at
    }
    EQUIPMENT_WARRANTY {
        uuid id PK
        uuid equipment_id FK
        string supplier
        date starts_on
        date ends_on
        text terms
        uuid created_by_id FK
    }
    MAINTENANCE_COST {
        uuid id PK
        uuid maintenance_id FK
        uuid equipment_id FK
        decimal amount
        string currency
        string source
        string reference
        text note
        uuid created_by_id FK
    }
    MAINTENANCE_PLAN ||--o{ MAINTENANCE_PLAN_ITEM : contem
    EQUIPMENT ||--o{ MAINTENANCE_PLAN_ITEM : agenda
    EQUIPMENT ||--o{ MAINTENANCE_ALERT : alerta
    MAINTENANCE o|--o{ MAINTENANCE_ALERT : deriva
    MAINTENANCE_ALERT ||--o{ NOTIFICATION_DELIVERY : entrega
    EQUIPMENT ||--o{ EQUIPMENT_WARRANTY : possui
    MAINTENANCE ||--o{ MAINTENANCE_COST : registra
    EQUIPMENT ||--o{ MAINTENANCE_COST : agrega
    FAILURE_PREDICTION_POLICY {
        uuid id PK
        string name
        integer version
        string status
        string baseline_version
        integer horizon_days
        integer min_history_count
        decimal min_confidence
        boolean evaluation_approved
        json evaluation_summary
        uuid created_by_id FK
    }
    FAILURE_PREDICTION {
        uuid id PK
        uuid policy_id FK
        uuid equipment_id FK
        date generated_for
        date horizon_end
        decimal score
        decimal confidence
        string risk_level
        string status
        json rationale
        json feature_snapshot
        string idempotency_key UK
        uuid decided_by_id FK
    }
    PREDICTION_EVALUATION {
        uuid id PK
        uuid policy_id FK
        string dataset_version
        string run_key UK
        date evaluated_for
        integer sample_count
        integer labeled_count
        decimal heuristic_precision
        decimal heuristic_recall
        integer false_positives
        integer false_negatives
        integer abstentions
        json metrics
        uuid evaluated_by_id FK
    }
    PREDICTION_NOTIFICATION {
        uuid id PK
        uuid prediction_id FK
        string channel
        string recipient_label
        string idempotency_key UK
        string status
        integer attempts
        datetime sent_at
        uuid created_by_id FK
    }
    FAILURE_PREDICTION_POLICY ||--o{ FAILURE_PREDICTION : produz
    EQUIPMENT ||--o{ FAILURE_PREDICTION : recebe
    FAILURE_PREDICTION_POLICY ||--o{ PREDICTION_EVALUATION : avalia
    FAILURE_PREDICTION ||--o{ PREDICTION_NOTIFICATION : notifica
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

`password_hash` existe somente para o adaptador local de autenticação e nunca
armazena senha. `USER_SESSION` guarda hashes de token e CSRF; o valor bruto do
cookie não é persistido nem retornado no corpo do login.

## Invariantes da fundação

- Equipamentos aceitam os tipos `computer`, `projector`, `air_conditioner`,
  `remote_control` e `other`; patrimônio é opcional, mas único quando informado.
- Cadastro exige ambiente ativo; inativação é preferida quando houver vínculos de
  movimentação, ocorrência ou manutenção.

- Equipamento referencia um ambiente e o usuário que realizou o cadastro.
- Ambientes usam código institucional único; `active=false` preserva o catálogo
  sem permitir novos usos em fluxos que exigirem ambientes ativos.
- Uma movimentação exige origem distinta do destino, ator e justificativa.
- Ocorrências e manutenções usam estados limitados por `CHECK` no banco; as
  transições permitidas também são aplicadas no serviço.
- Link público usa token opaco revogável; formulário público resolve o ambiente
  no servidor e grava somente a ocorrência necessária.
- Comentários de ocorrências e componentes de manutenção são registros
  append-only com chaves estrangeiras restritivas.
- Mudanças patrimoniais devem produzir `audit_events` com ator, instante,
  justificativa e estados anterior/novo; a gravação transacional será feita pelos
  serviços das specs funcionais.
- `audit_events` rejeita `UPDATE` e `DELETE` por trigger. Correções são novos
  eventos, nunca alterações do histórico.
- Criação, edição, inativação e exclusão permitida de ambientes geram evento de
  auditoria com ator, justificativa e estado anterior/novo.
- Chaves estrangeiras usam `RESTRICT` para impedir exclusão silenciosa de
  histórico.
- Políticas de previsão começam desabilitadas; ativação exige avaliação reproduzível
  aprovada e toda ativação, desativação ou decisão é registrada em `audit_events`.
- Recomendações guardam score, confiança, sinais agregados e justificativa sem
  copiar descrições ou contatos; baixa confiança produz `risk_level=abstain`.
- Notificações de previsão são somente `mock_email`, idempotentes e exigem decisão
  humana confirmada antes do despacho.

## Dados pessoais e retenção

`display_name` e `auth_subject` são dados pessoais e ficam na zona protegida. Logs e
auditoria devem preferir o identificador interno e não copiar nomes, credenciais ou
tokens. Política de retenção, anonimização e backup permanece pendente de decisão
institucional antes da produção.

