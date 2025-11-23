# 🍔 Sistema Distribuído Ceará Lanches

> Projeto para a disciplina de Sistemas Distribuídos | UFRPE

Este projeto implementa um sistema de gerenciamento de pedidos para uma hamburgueria baseado em uma **Arquitetura Orientada a Eventos (Event-Driven Architecture)**. 

O objetivo é demonstrar conceitos fundamentais de sistemas distribuídos, como desacoplamento de serviços, comunicação assíncrona via filas de mensagens e tolerância a falhas.

---

## 🏛️ Arquitetura do Sistema

O sistema foi dividido em **4 módulos independentes** que simulam os setores reais de uma hamburgueria. A comunicação crítica entre o backend acontece de forma assíncrona utilizando **RabbitMQ**.



### Os 4 Módulos:

#### 1. 📱 Módulo Cliente (Frontend / Vitrine)
* **Responsabilidade:** Interface para o cliente realizar o pedido.
* **Tecnologia:** HTML5, CSS3, JavaScript (Fetch API).
* **Comunicação:** Envia requisições HTTP (REST) síncronas para o Módulo de Pedidos.

#### 2. 💰 Módulo de Pedidos (Caixa / Gateway)
* **Responsabilidade:** Receber o pedido do cliente, validar e confirmar o pagamento.
* **Ação Distribuída:** Ao confirmar um pedido, este módulo atua como **Producer**, publicando uma mensagem `PedidoConfirmado` na fila do RabbitMQ. Ele não sabe quem vai preparar ou estocar o item.
* **Tecnologia:** Python + Flask.

#### 3. 👨‍🍳 Módulo da Cozinha (KDS - Kitchen Display System)
* **Responsabilidade:** Gerenciar a fila de preparação.
* **Ação Distribuída:** Atua como **Consumer**. Escuta a fila do RabbitMQ. Quando um pedido chega, ele atualiza a interface do cozinheiro em tempo real (ou via polling).
* **Interface:** Possui uma UI própria para o chapeiro visualizar os pedidos pendentes.
* **Tecnologia:** Python + Flask (Backend) + HTML/JS (Frontend do Cozinheiro).

#### 4. 📦 Módulo de Estoque (Inventário)
* **Responsabilidade:** Controle de insumos.
* **Ação Distribuída:** Atua também como **Consumer** da *mesma mensagem* `PedidoConfirmado`.
* **Processo:** Para cada lanche vendido, ele dá baixa automática nos ingredientes (ex: -1 Pão, -1 Carne) no banco de dados.
* **Tecnologia:** Python + Flask.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.9+
* **Framework Web:** Flask
* **Message Broker:** RabbitMQ (Imagem Oficial Management)
* **Cliente AMQP:** Pika (Biblioteca Python para RabbitMQ)
* **Orquestração:** Docker & Docker Compose

---

## 📂 Estrutura do Projeto

O projeto utiliza Docker Compose para subir todo o ambiente com um único comando.

```text
/
├── docker-compose.yml      # Orquestração de todos os contêineres
├── modulo_1_cliente/       # Frontend do Cliente
│   ├── index.html
│   └── script.js
├── modulo_2_pedidos/       # API de Pedidos (Producer)
│   ├── app.py              # Aplicação Flask
│   └── Dockerfile
├── modulo_3_cozinha/       # Serviço da Cozinha (Consumer + UI)
│   ├── app.py              # Aplicação Flask + Thread Consumer
│   ├── templates/          # Interface do Cozinheiro
│   └── Dockerfile
└── modulo_4_estoque/       # Serviço de Estoque (Consumer)
    ├── app.py              # Aplicação Flask + Thread Consumer
    └── Dockerfile
```
---

## Modelagem Arquitetura

```mermaid
graph TD
    %% Estilos (Cores)
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000;
    classDef backend fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000;
    classDef broker fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,stroke-dasharray: 5 5,color:#000;
    classDef database fill:#e8f5e9,stroke:#1b5e20,stroke-width:1px,color:#000;

    %% Atores
    Client(👤 Cliente / Navegador)

    %% Módulo 1: Frontend
    subgraph Mod1 [Módulo 1: Frontend]
        UI["🖥️ Interface Web"]
    end

    %% Módulo 2: Backend Pedidos
    subgraph Mod2 [Módulo 2: Caixa]
        API_Pedidos["⚙️ API de Pedidos<br/>(Flask)"]
        DB_Pedidos[("🛢️ DB Pedidos")]
    end

    %% Broker
    Rabbit{"🐰 RabbitMQ<br/>Fila: Pedidos"}

    %% Módulo 3: Cozinha
    subgraph Mod3 [Módulo 3: Cozinha]
        Worker_Cozinha["⚙️ Worker Cozinha"]
        Display_Cozinha["🖥️ Tela do Chapeiro"]
    end

    %% Módulo 4: Estoque
    subgraph Mod4 [Módulo 4: Estoque]
        Worker_Estoque["⚙️ Worker Estoque"]
        DB_Estoque[("🛢️ DB Estoque")]
    end

    %% Relacionamentos
    Client -->|1. Acessa| UI
    UI -->|2. POST /pedidos| API_Pedidos
    API_Pedidos -->|3. Salva| DB_Pedidos
    API_Pedidos -.->|4. Publica Evento| Rabbit

    Rabbit -.->|5. Consome msg| Worker_Cozinha
    Rabbit -.->|5. Consome msg| Worker_Estoque

    Worker_Cozinha -->|Atualiza| Display_Cozinha
    Worker_Estoque -->|Baixa Insumo| DB_Estoque

    %% Aplicando Estilos
    class UI frontend;
    class API_Pedidos,Worker_Cozinha,Worker_Estoque,Display_Cozinha backend;
    class Rabbit broker;
    class DB_Pedidos,DB_Estoque database;
```

---

## Diagrama de Sequência

```mermaid
sequenceDiagram
    autonumber
    actor User as Cliente
    participant Front as Frontend
    participant API as API Pedidos (Caixa)
    participant Broker as RabbitMQ
    participant Kitchen as Cozinha (KDS)
    participant Inventory as Estoque

    User->>Front: Clica em "Finalizar Pedido"
    Front->>API: POST /pedidos (JSON)
    
    activate API
    Note right of API: Valida pedido e salva no DB
    API->>Broker: Publica "PedidoConfirmado"
    API-->>Front: Retorna HTTP 201 (Sucesso)
    deactivate API
    
    Front-->>User: Mostra "Pedido realizado!"
    
    par Processamento Assíncrono
        Broker->>Kitchen: Entrega Mensagem (Consumo)
        activate Kitchen
        Kitchen->>Kitchen: Atualiza Tela do Chapeiro
        deactivate Kitchen
    and
        Broker->>Inventory: Entrega Mensagem (Consumo)
        activate Inventory
        Inventory->>Inventory: Baixa Ingredientes no DB
        deactivate Inventory
    end

```
