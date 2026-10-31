## **Documento de Arquitetura de Software**

**Histórico de Revisão**

|Data|Versão|Descrição|Autor|
| - | - | - | - |
|25/08/2026|0.1|Versão inicial|Gustavo de Freitas Fidélis, Bernardo Lykawka Medeiros da Silva|

## **1. Introdução**

### **1.1 Finalidade**
Este documento apresenta uma visão geral da arquitetura de software do sistema ViajaJunto e especifica as decisões arquiteturais pertinentes ao seu desenvolvimento, servindo de referência para os desenvolvedores do projeto.

### **1.2 Escopo**
Este documento abrange a arquitetura do ViajaJunto — aplicação web de planejamento colaborativo de viagens. Deve ser seguido pela equipe de desenvolvimento para garantir o padrão arquitetural proposto, incluindo separação entre frontend e backend, organização do banco de dados e controle de acesso.

### **1.3 Definições, Acrônimos e Abreviações**

|Abreviação|Definição|
| - | - |
|API|Application Programming Interface|
|REST|Representational State Transfer|
|JWT|JSON Web Token|
|DER|Diagrama de Entidades e Relacionamentos|
|DLD|Diagrama Lógico de Dados|
|MVC|Model-View-Controller|

### **1.4 Visão Geral**
Este documento descreve a representação da arquitetura cliente-servidor adotada, as metas e restrições arquiteturais, a visão lógica com organização em camadas e o modelo de dados relacional do sistema.

## **2. Representação da Arquitetura**

A aplicação adota uma **arquitetura cliente-servidor** com separação clara entre camadas e integrações externas:

- **Frontend (NextJS):** aplicação web responsiva que consome a API REST do backend, renderiza a interface e exibe mapas e cadastros de atividades/locais.
- **Backend (NestJS):** API REST responsável pela lógica de negócio, autenticação, autorização, persistência e orquestração entre os serviços externos.
- **Serviço de Mapas:** responsável pela visualização geográfica e roteamento em mapa, com biblioteca como Google Maps ou Leaflet/OpenStreetMap.
- **Serviço de Locais/Atividades (catálogo_atividades):** integra a API do Google Places para complementar dados de locais, eventos, restaurantes, hotéis e pontos de interesse.
- **Banco de Dados (PostgreSQL):** armazenamento relacional para usuários, viagens, destinos, atividades, orçamento e avaliações.

### **2.1 Diagrama de Relações**

```
┌────────────────────┐      HTTP/JSON      ┌─────────────────────┐
│                    │ ──────────────────► │                     │
│  Frontend (NextJS) │                     │  Backend (NestJS)   │
│  (Web App)         │ ◄────────────────── │  REST + Auth + RBAC │
│  - Dashboard       │                     │                     │
│  - Viagens         │                     │                     │
│  - Destinos        │                     │                     │
│  - Orçamento       │                     │                     │
└────────────────────┘                     └──────────┬──────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
                ┌─────────────────────┐       ┌──────────────────────────────┐      ┌─────────────────────┐
                │  Serviço de Mapas   │       │ Serviço de Locais/Atividades │      │  Banco de Dados     │
                │  Google Maps /      │       │  Google Places API           │      │  PostgreSQL/        │
                │  Leaflet + OSM      │       │  - catálogo_atividades       │      │  - usuarios         │
                │  - geolocalização   │       │  - busca por locais          │      │  - viagens          │
                │  - rotas            │       │  - dados de pontos de        │      │  - destinos         │
                │  - marcadores       │       │    interesse                 │      │  - atividades       │
                └─────────────────────┘       └──────────────────────────────┘      └─────────────────────┘
```

## **3. Metas e Restrições de Arquitetura**

|**Restrição**|**Ferramenta**|
| :- | :- |
|Linguagem|A definir pela equipe|
|Framework|A definir pela equipe|
|Plataforma|Web (navegador)|
|Segurança|Senhas com hash; autenticação via JWT; controle de acesso por viagem|
|Idioma|Português (pt-BR)|
|Mapa interativo|ex: jsVectormap/Google Maps API|

## **4. Visão Lógica**

### **4.1 Visão geral: Pacotes e Camadas**

O sistema é organizado em cinco blocos principais:

- **Camada de Apresentação (Frontend):** responsável pela interface com o usuário — renderização de telas, formulários, mapa interativo, filtros de busca e consumo da API REST.
- **Camada de Negócio (Backend / API REST):** responsável pelas regras de negócio, autenticação, controle de permissões, criação de viagens e orquestração de operações sobre dados e integrações externas.
- **Serviço de Mapas:** encapsula a lógica de renderização geográfica, geolocalização, rotas e marcadores em mapas interativos.
- **Serviço de Locais/Atividades (catálogo_atividades):** integra a Google Places API para buscar, validar e enriquecer informações de locais, atrações e estabelecimentos que podem ser cadastrados em viagens ou atividades.
- **Camada de Dados (Banco de Dados):** responsável pela persistência das informações — usuários, viagens, destinos, atividades, orçamento, avaliações e referências ao catálogo externo.

> O backend deve manter um catálogo interno de atividades/locais, sincronizando dados com o Google Places API quando necessário e preservando registros próprios de avaliações e contexto da viagem.

### **4.2 Organização do Código**

A estrutura de diretórios segue a separação entre frontend e backend em repositórios ou módulos distintos. A organização interna de cada camada será definida pela equipe conforme o framework adotado.

### **4.3 Diagrama de Classes**

[Inserir diagrama de classes após definição do framework e linguagem de implementação.]

## **5. Visão de Implementação**

### **5.1 Diagrama de Entidade-Relacionamento**

O modelo relacional é composto pelas entidades abaixo. O diagrama completo pode ser visualizado em [dbdiagram.io](https://dbdiagram.io).

#### Enums

| Enum | Valores |
| ---- | ------- |
| `status_viagem` | `EM_PLANEJAMENTO`, `CONFIRMADA`, `CONCLUIDA` |
| `permissao_membro` | `EDITOR`, `VISUALIZADOR` |
| `categoria_destino` | `CIDADE`, `PRAIA`, `NATUREZA`, `CULTURAL` |
| `tipo_atividade` | `PASSEIO`, `REFEICAO`, `HOSPEDAGEM`, `TRANSPORTE`, `OUTRO` |
| `status_atividade` | `PENDENTE`, `CONFIRMADA`, `CONCLUIDA` |

#### Tabelas

**usuario**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `nome` | varchar | NOT NULL |
| `email` | varchar | NOT NULL, UNIQUE |
| `senha_hash` | varchar | NOT NULL |
| `criado_em` | timestamp | default: `now()` |

**viagem**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id/código_convite` | string | PK |
| `nome` | varchar | NOT NULL |
| `descricao` | text | |
| `data_inicio` | date | |
| `data_fim` | date | |
| `status` | status_viagem | NOT NULL |
| `criado_por` | integer | NOT NULL, FK → usuario.id |
| `criado_em` | timestamp | default: `now()` |

**membro_viagem**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `viagem_id` | integer | NOT NULL, FK → viagem.id |
| `usuario_id` | integer | NOT NULL, FK → usuario.id |
| `permissao` | permissao_membro | NOT NULL |
| `entrou_em` | timestamp | default: `now()` |

**destino_catalogo**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `nome` | varchar | NOT NULL |
| `pais` | varchar | |
| `categoria` | categoria_destino | |
| `descricao` | text | |
| `latitude` | float | |
| `longitude` | float | |
| `foto_url` | varchar | |

> Como cada destino representa uma cidade do mundo, o campo `nome` deve indicar a cidade em si, e o país é informado separadamente para contextualização geográfica.

**destino_viagem**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `viagem_id` | integer | NOT NULL, FK → viagem.id |
| `destino_catalogo_id` | integer | NOT NULL, FK → destino_catalogo.id |
| `chegada` | date | |
| `saida` | date | |
| `descricao` | text | |
| `ordem` | integer | |

**catalogo_atividade**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `nome` | varchar | NOT NULL |
| `descricao` | text | |
| `tipo_atividade` | tipo_atividade | NOT NULL |
| `local` | varchar | |
| `cidade` | varchar | |
| `pais` | varchar | |
| `latitude` | float | |
| `longitude` | float | |
| `google_place_id` | varchar | UNIQUE |
| `foto_url` | varchar | |
| `fonte` | varchar | default: `google_places` |
| `media_avaliacao` | float | default: 0 |
| `criado_em` | timestamp | default: `now()` |

**atividade_viagem**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `destino_viagem_id` | integer | NOT NULL, FK → destino_viagem.id |
| `catalogo_atividade_id` | integer | NOT NULL, FK → catalogo_atividade.id |
| `data_horario` | timestamp | |
| `duracao_min` | integer | |
| `custo_previsto` | decimal(10,2) | |
| `status` | status_atividade | NOT NULL |

**orcamento**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `viagem_id` | integer | NOT NULL, UNIQUE, FK → viagem.id (1:1) |
| `valor_total` | decimal(10,2) | NOT NULL |
| `previsto_atividades` | decimal(10,2) | default: 0 |

**avaliacao**

| Coluna | Tipo | Restrições |
| ------ | ---- | ---------- |
| `id` | integer | PK, auto-increment |
| `usuario_id` | integer | NOT NULL, FK → usuario.id |
| `catalogo_atividade_id` | integer | NOT NULL, FK → catalogo_atividade.id |
| `nota` | integer | NOT NULL (1 a 5) |
| `comentario` | text | |
| `criado_em` | timestamp | default: `now()` |

#### Relacionamentos

| De | Para | Cardinalidade |
| -- | ---- | ------------- |
| `viagem.criado_por` | `usuario.id` | N:1 |
| `membro_viagem.viagem_id` | `viagem.id` | N:1 |
| `membro_viagem.usuario_id` | `usuario.id` | N:1 |
| `destino_viagem.viagem_id` | `viagem.id` | N:1 |
| `destino_viagem.destino_catalogo_id` | `destino_catalogo.id` | N:1 |
| `atividade_viagem.destino_viagem_id` | `destino_viagem.id` | N:1 |
| `atividade_viagem.catalogo_atividade_id` | `catalogo_atividade.id` | N:1 |
| `orcamento.viagem_id` | `viagem.id` | 1:1 |
| `avaliacao.usuario_id` | `usuario.id` | N:1 |
| `avaliacao.catalogo_atividade_id` | `catalogo_atividade.id` | N:1 |

### **5.2 Diagrama Lógico de Dados**

O DLD textual abaixo representa as tabelas com chaves primárias e estrangeiras destacadas:

```
usuario(#id, nome, email, senha_hash, criado_em)

viagem(#id, nome, descricao, data_inicio, data_fim, status, *criado_por→usuario, criado_em)

membro_viagem(#id, *viagem_id→viagem, *usuario_id→usuario, permissao, entrou_em)

destino_catalogo(#id, nome, pais, categoria, descricao, latitude, longitude, foto_url)

destino_viagem(#id, *viagem_id→viagem, *destino_catalogo_id→destino_catalogo, chegada, saida, descricao, ordem)

catalogo_atividade(#id, nome, descricao, tipo_atividade, local, cidade, pais, latitude, longitude, google_place_id, foto_url, fonte, media_avaliacao, criado_em)

atividade_viagem(#id, *destino_viagem_id→destino_viagem, *catalogo_atividade_id→catalogo_atividade, data_horario, duracao_min, custo_previsto, status)

orcamento(#id, *viagem_id→viagem, valor_total, previsto_atividades)

avaliacao(#id, *usuario_id→usuario, *catalogo_atividade_id→catalogo_atividade, nota, comentario, criado_em)
```
> Legenda: `#` chave primária · `*` chave estrangeira

## **6. Tamanho e Desempenho**

O sistema é direcionado ao público geral e deve suportar múltiplos usuários simultâneos acessando viagens compartilhadas. O carregamento das páginas principais deve ocorrer em menos de 3 segundos em condições normais de rede. O volume de dados por viagem é relativamente pequeno (destinos, atividades e orçamentos), mas o catálogo de destinos e avaliações pode crescer significativamente com o uso da comunidade.

## **7. Qualidade**

A arquitetura cliente-servidor com separação entre frontend e backend favorece:

- **Manutenibilidade:** as camadas evoluem de forma independente — mudanças no frontend não afetam a API e vice-versa.
- **Testabilidade:** a API REST pode ser testada de forma isolada com ferramentas como Postman ou testes automatizados.
- **Segurança:** o controle de acesso é centralizado no backend, garantindo que usuários só acessem dados das viagens às quais pertencem.
- **Escalabilidade:** a separação de responsabilidades permite escalar frontend e backend de forma independente conforme a demanda.

## **8. Referências**

- Documento de Escopo do Projeto — ViajaJunto (Grupo 4, T1)
- Documento de Requisitos — ViajaJunto
