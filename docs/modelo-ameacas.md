# Modelo de ameaças da fundação

## Escopo e ativos

O modelo considera o navegador, a API, integrações futuras e o PostgreSQL. Os
ativos principais são a situação e a localização patrimonial, o histórico de
movimentações e manutenções, a identidade dos atores e os tokens de consulta
pública.

## Matriz de riscos

| Ameaça | Cenário | Controles na fundação | Controle exigido antes da exposição | Risco residual |
|---|---|---|---|---|
| IDOR | Troca de UUID ou token para consultar/alterar equipamento alheio | UUIDs não sequenciais e token público separado da chave interna | Autorização por objeto em toda rota (SPEC-002); resposta pública mínima (SPEC-006); testes negativos | Alto enquanto as rotas funcionais não forem implementadas |
| Injeção SQL | Texto de ocorrência ou filtro vira parte de SQL | SQLAlchemy e consultas parametrizadas; tipos e limites devem ser validados pela API | Revisão de qualquer SQL textual; testes com cargas maliciosas; conta do banco sem privilégios administrativos | Baixo se o padrão for preservado |
| Exposição pública | Endpoint ou OpenAPI revela dados pessoais, chaves internas ou detalhes de erro | Diagnóstico retorna DTO restrito; erro do banco é genérico; banco escuta apenas em localhost no Compose | DTO público dedicado, inventário de campos, TLS e revisão de privacidade antes da SPEC-006 | Médio até revisão das rotas públicas |
| Abuso e automação | Varredura de tokens ou abertura massiva de chamados | Tokens UUID aleatórios reduzem enumeração simples | Rate limiting fora do processo, quotas, telemetria sem PII e resposta uniforme | Alto antes de controles de borda |
| Falsificação de identidade | Cliente informa outro ator em uma mudança patrimonial | `actor_id` existe no modelo de auditoria | Derivar o ator exclusivamente da sessão validada, nunca do corpo da requisição (SPEC-002) | Alto antes da identidade institucional |
| Adulteração de auditoria | Atacante atualiza ou remove evento antigo | Trigger rejeita `UPDATE` e `DELETE`; teste de integração verifica ambos | Credenciais separadas para migração e aplicação; exportação/monitoramento imutável | Administrador do banco ainda possui poder técnico |
| Vazamento de segredo | URL do banco aparece no Git, log ou resposta | Configuração por ambiente, `.env` ignorado e erro sanitizado | Gerenciador de segredos e rotação em produção | Médio até definição da infraestrutura |
| Elevação de privilégio | Usuário comum invoca operação administrativa | Nenhuma rota funcional existe nesta etapa | Matriz de permissões determinística, deny-by-default e testes por papel (SPEC-002) | Alto antes da SPEC-002 |

## Regras de verificação

1. Nenhuma rota de objeto é liberada sem teste que use um objeto pertencente a
   outro escopo/autorizado, cobrindo IDOR.
2. Nenhuma entrada de usuário é concatenada a SQL, log estruturado ou template de
   mensagem.
3. Rotas públicas usam esquema de resposta próprio e nunca retornam IDs internos,
   nomes de pessoas ou detalhes de infraestrutura.
4. Rate limiting e monitoramento precisam estar fora do controle do cliente e não
   podem ser substituídos por uma recomendação de IA.
5. Eventos de auditoria são append-only; correções geram um evento compensatório.

## Aceitação de risco

Os riscos marcados como altos impedem exposição funcional ou produção, mas não
impedem a fundação local sem dados reais. Somente responsáveis humanos podem aceitar
risco residual ou autorizar produção.

