## **Documento de Requisitos**

**Histórico de Revisão**

|Data|Versão|Descrição|Autor|
| - | - | - | - |
|25/08/2026|0.1|Versão inicial|Gustavo de Freitas Fidélis, Bernardo Lykawka Medeiros da Silva|

## **1. Introdução**

### **1.1 Propósito**
Este documento especifica os requisitos funcionais e não funcionais do sistema ViajaJunto, servindo de referência para o desenvolvimento e a validação da solução. O objetivo é descrever de forma clara o que o sistema deve fazer e as restrições técnicas e de qualidade que deve atender.

### **1.2 Escopo**
O ViajaJunto é uma aplicação web de planejamento colaborativo de viagens. A plataforma permite que grupos de usuários organizem roteiros com múltiplos destinos, atividades e orçamentos em um único ambiente compartilhado, com visualização em mapa interativo e sistema de avaliações da comunidade. O diferencial central é a colaboração: mais de uma pessoa pode participar do planejamento de uma mesma viagem, editando e acompanhando o roteiro em conjunto.

### **1.3 Definições, Acrônimos e Abreviações**

|Termo|Definição|
| - | - |
|RF|Requisito Funcional|
|RNF|Requisito Não Funcional|
|RN|Regra de Negócio|
|JWT|JSON Web Token — mecanismo de autenticação stateless via token|
|DER|Diagrama de Entidades e Relacionamentos|
|REST|Representational State Transfer — estilo arquitetural para APIs HTTP|
|API|Application Programming Interface|

### **1.4 Referências**
- Documento de Escopo do Projeto — ViajaJunto (Grupo 4, T1)
- Diagrama de Entidade-Relacionamento do banco de dados (incluso no Documento de Arquitetura)

## **2. Descrição Geral**

### **2.1 Perspectiva do Produto**
O ViajaJunto é um sistema novo, sem substituição de produto existente. Ele integra funcionalidades de planejamento de itinerário, gestão colaborativa de viagens, controle de orçamento e descoberta de destinos em uma única plataforma web, eliminando a necessidade de ferramentas dispersas como planilhas e aplicativos de mensagens.

### **2.2 Funções do Produto**
As principais funcionalidades da plataforma são:

- Criação e gerenciamento de viagens com múltiplos destinos e atividades
- Colaboração entre membros com diferentes níveis de permissão
- Visualização dos destinos em mapa interativo com rota
- Controle de orçamento com painel financeiro resumido
- Avaliação e descoberta de destinos pela comunidade

### **2.3 Características dos Usuários**
A aplicação é direcionada ao público geral, sem restrição de faixa etária — de adolescentes a idosos que desejam organizar viagens individualmente ou em grupo. A interface deve ser intuitiva e acessível para usuários com diferentes níveis de familiaridade com a tecnologia. Não é necessário conhecimento técnico para utilizar a plataforma.

Há três perfis de usuário no sistema:

- **Visitante (não autenticado):** acessa o catálogo de destinos e avaliações, sem poder criar viagens ou deixar reviews.
- **Usuário Registrado:** possui conta na plataforma; pode criar e gerenciar viagens, convidar colaboradores, adicionar atividades e orçamentos, e avaliar destinos visitados.
- **Colaborador de Viagem:** usuário registrado convidado para uma viagem específica; suas permissões dependem do nível de acesso concedido pelo criador (Editor ou Visualizador).

### **2.4 Restrições**
As funcionalidades abaixo foram identificadas mas estão fora do escopo desta versão do projeto:

- Integração com APIs externas de reserva de hotéis, voos e ingressos
- Chat em tempo real entre colaboradores da viagem
- Aplicativo mobile nativo (iOS/Android)
- Pagamentos e divisão de custos entre membros do grupo
- Edição simultânea em tempo real (estilo Google Docs)
- Sistema de gamificação ou recompensas para avaliações

### **2.5 Suposições e Dependências**
- O sistema depende de uma biblioteca de mapas externa (ex.: Leaflet.js + OpenStreetMap ou Google Maps API) para exibição de mapas interativos.
- Assume-se que os usuários possuem acesso a um navegador web moderno com conexão à internet.
- O banco de dados relacional será definido pela equipe durante o desenvolvimento.

## **3. Requisitos Funcionais**

Requisitos funcionais descrevem **o que o sistema deve fazer**.

> **Prioridade:** Alta (Must have), Média (Should have), Baixa (Could have) — critério MoSCoW.

### Módulo 1 — Autenticação e Perfil

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF01 | O sistema deve permitir o cadastro de conta com nome, e-mail e senha. | Alta |
| RF02 | O sistema deve permitir login e logout de usuários. | Alta |
| RF03 | O sistema deve oferecer recuperação de senha por e-mail. | Média |

### Módulo 2 — Gestão de Viagens

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF04 | O sistema deve permitir criar uma viagem com nome, descrição e datas gerais de início e fim. | Alta |
| RF05 | O sistema deve permitir editar e excluir viagens. | Alta |
| RF06 | O sistema deve exibir um painel pessoal listando todas as viagens do usuário (criadas e compartilhadas). | Alta |
| RF07 | O sistema deve permitir definir o status da viagem: *Em planejamento*, *Confirmada* ou *Concluída*. | Média |

### Módulo 3 — Destinos

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF08 | O sistema deve permitir adicionar múltiplos destinos a uma viagem, com ordem de visita definida. | Alta |
| RF09 | Cada destino deve conter: foto, nome/localização, datas de chegada e saída, descrição e categoria (cidade, praia, natureza, cultural, etc.). | Alta |
| RF10 | O sistema deve permitir pesquisar destinos já cadastrados na plataforma ao adicioná-los a uma viagem. | Média |
| RF11 | O sistema deve mostrar em um mapa os países que o usuário já visitou (jsVectormap) | Média | 

### Módulo 4 — Atividades

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF12 | O sistema deve permitir adicionar atividades cadastradas dentro de cada destino (passeios, refeições, hospedagem, transporte, etc.). | Alta |
| RF13 | Cada atividade pode conter: foto, nome, tipo/categoria, local, data e horário, duração estimada, custo previsto e status (*Pendente*, *Confirmada*, *Concluída*). | Alta |
| RF14 | O sistema deve listar atividades em ordem cronológica por destino. | Média |

### Módulo 5 — Orçamento

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF15 | O sistema deve permitir definir um orçamento total para a viagem. | Alta |
| RF16 | O sistema deve registrar os gastos previstos das atividades. | Alta |
| RF17 | O sistema deve exibir um painel de resumo financeiro com: orçamento total, total planejado, saldo disponível e percentual consumido por categoria. | Média |

### Módulo 6 — Colaboração

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF18 | O sistema deve permitir que o criador da viagem convide outros usuários pelo código da viagem. | Alta |
| RF19 | O sistema deve oferecer dois níveis de permissão para colaboradores: *Editor* (pode adicionar, editar e remover destinos, atividades e informações de orçamento) e *Visualizador* (acesso somente leitura). | Alta |
| RF20 | O sistema deve permitir que o criador altere permissões ou remova colaboradores a qualquer momento. | Alta |
| RF21 | O sistema deve enviar notificações in-app para colaboradores quando alterações relevantes forem feitas na viagem. | Média |

### Módulo 7 — Avaliação e Descoberta de Atividades

| ID | Descrição | Prioridade |
| -- | --------- | :--------: |
| RF22 | O sistema deve permitir que usuários avaliem atividades que fizeram, atribuindo nota de 1 a 5 estrelas e um comentário opcional. | Alta |
| RF23 | O sistema deve exibir uma página pública de atividade com: descrição, média de avaliações, reviews dos usuários e fotos. | Alta |
| RF24 | O sistema deve oferecer um catálogo de atividades com busca por nome e filtros por nota mínima, categoria e localização. | Média |
| RF25 | O sistema deve destacar os destinos mais bem avaliados na página inicial. | Baixa |

## **4. Requisitos Não Funcionais**

Requisitos não funcionais descrevem **qualidades e restrições técnicas** do sistema.

| ID | Categoria | Descrição | Prioridade |
| -- | --------- | --------- | :--------: |
| RNF01 | Usabilidade | O sistema deve ter interface responsiva, funcionando em desktop e dispositivos móveis, com design acessível para público amplo. | Alta |
| RNF02 | Desempenho | O sistema deve carregar as páginas principais em menos de 3 segundos em condições normais de rede. | Alta |
| RNF03 | Segurança | As senhas devem ser armazenadas com hash. A autenticação deve ser realizada via token (JWT ou equivalente). O controle de acesso deve garantir que um usuário só acesse viagens às quais pertence. | Alta |
| RNF04 | Disponibilidade | O sistema deve estar disponível via navegador web, sem necessidade de instalação pelo usuário. | Alta |
| RNF05 | Manutenibilidade | O sistema deve ter separação clara entre backend (API) e frontend, facilitando a evolução independente das camadas. | Média |

## **5. Regras de Negócio**

| ID | Descrição |
| -- | --------- |
| RN01 | Visitantes não autenticados podem navegar pelo catálogo de destinos e visualizar avaliações, mas não podem criar viagens nem deixar reviews. |
| RN02 | Colaboradores com perfil *Editor* podem adicionar, editar e remover destinos, atividades e informações de orçamento da viagem. |
| RN03 | Colaboradores com perfil *Visualizador* têm acesso somente leitura ao planejamento da viagem. |
| RN04 | Apenas o criador da viagem pode convidar colaboradores, alterar suas permissões ou removê-los. |
| RN05 | Apenas usuários registrados podem avaliar destinos. |
| RN06 | Um usuário só pode acessar os dados de uma viagem se for o criador ou um colaborador convidado. |

## **6. Protótipos**

https://stitch.withgoogle.com/projects/13243756183970901906