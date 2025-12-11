import json
import threading
import time

import database as db
import pika
from flasgger import Swagger
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)
swagger = Swagger(app)


db.init_db()


def enviar_para_fila(pedido):
    """Envia pedido para a fila do RabbitMQ."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()

        channel.exchange_declare(
            exchange='pedidos_exchange', exchange_type='fanout')

        channel.basic_publish(
            exchange='pedidos_exchange',
            routing_key='',
            body=json.dumps(pedido)
        )

        connection.close()
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao enviar para RabbitMQ: {e}")
        return False


@app.route('/pedidos', methods=['POST'])
def novo_pedido():
    """
    Registra um novo pedido na hamburgueria.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - cliente
            - item
          properties:
            cliente:
              type: string
              example: "Maria"
            item:
              type: string
              example: "X-Salada"
            observacao:
              type: string
              example: "Sem maionese"
    responses:
      201:
        description: Pedido registrado com sucesso
      400:
        description: Dados inválidos
      500:
        description: Erro ao processar pedido
    """
    try:
        dados = request.json

        if not dados:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        cliente = dados.get('cliente', '').strip()
        item = dados.get('item', '').strip()
        observacao = dados.get('observacao', dados.get('obs', '')).strip()

        if not cliente:
            return jsonify({"erro": "Nome do cliente é obrigatório"}), 400

        if not item:
            return jsonify({"erro": "Item é obrigatório"}), 400

        pedido_criado = db.inserir_pedido(cliente, item, observacao or None)

        print(
            f"[CAIXA] Pedido #{pedido_criado['id']} registrado: {item} para "
            f"{cliente}")

        pedido_para_fila = {
            'id': pedido_criado['id'],
            'cliente': cliente,
            'item': item,
            'observacao': observacao or None
        }

        if enviar_para_fila(pedido_para_fila):
            print(f"[CAIXA] Pedido #{pedido_criado['id']} enviado para a fila")
            return jsonify({
                "status": "sucesso",
                "mensagem": "Pedido registrado e enviado para preparação",
                "pedido": pedido_criado
            }), 201
        else:
            return jsonify({
                "status": "aviso",
                "mensagem": "Pedido registrado mas falha ao enviar para "
                "cozinha",
                "pedido": pedido_criado
            }), 201

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        print(f"[ERRO] Erro ao processar pedido: {e}")
        return jsonify({"erro": "Erro interno ao processar pedido"}), 500


@app.route('/pedidos', methods=['GET'])
def listar_pedidos():
    """
    Lista pedidos registrados.
    ---
    parameters:
      - name: status
        in: query
        type: string
        required: false
        description: Filtrar por status (PENDENTE, PREPARANDO, PRONTO,
          ENTREGUE)
      - name: limit
        in: query
        type: integer
        required: false
        default: 50
        description: Número máximo de pedidos a retornar
    responses:
      200:
        description: Lista de pedidos
    """
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)

    try:
        pedidos = db.listar_pedidos(status=status, limit=limit)
        return jsonify({
            "total": len(pedidos),
            "pedidos": pedidos
        }), 200
    except Exception as e:
        print(f"[ERRO] Erro ao listar pedidos: {e}")
        return jsonify({"erro": "Erro ao buscar pedidos"}), 500


@app.route('/pedidos/<int:pedido_id>', methods=['GET'])
def buscar_pedido(pedido_id):
    """
    Busca um pedido específico.
    ---
    parameters:
      - name: pedido_id
        in: path
        type: integer
        required: true
        description: ID do pedido
    responses:
      200:
        description: Dados do pedido
      404:
        description: Pedido não encontrado
    """
    try:
        pedido = db.buscar_pedido(pedido_id)
        if pedido:
            return jsonify(pedido), 200
        else:
            return jsonify({"erro": "Pedido não encontrado"}), 404
    except Exception as e:
        print(f"[ERRO] Erro ao buscar pedido: {e}")
        return jsonify({"erro": "Erro ao buscar pedido"}), 500


@app.route('/cardapio', methods=['GET'])
def listar_cardapio():
    """
    Lista itens do cardápio disponíveis.
    ---
    responses:
      200:
        description: Lista do cardápio
    """
    try:
        cardapio = db.listar_cardapio()
        return jsonify({
            "total": len(cardapio),
            "cardapio": cardapio
        }), 200
    except Exception as e:
        print(f"[ERRO] Erro ao listar cardápio: {e}")
        return jsonify({"erro": "Erro ao buscar cardápio"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    Verifica o status do serviço.
    ---
    responses:
      200:
        description: Serviço operacional
    """
    return jsonify({
        "status": "online",
        "servico": "caixa"
    }), 200


# =============================================================================
# CONSUMER - Escuta pedidos prontos da cozinha
# =============================================================================

def callback(ch, method, properties, body):
    """Processa mensagens de pedidos prontos vindos da cozinha."""
    # Verificar número de tentativas (x-death header do RabbitMQ)
    retry_count = 0
    if properties.headers and 'x-death' in properties.headers:
        retry_count = len(properties.headers['x-death'])

    try:
        pedido = json.loads(body)
        pedido_id = pedido.get('pedido_caixa_id')
        status = pedido.get('status')

        if not pedido_id:
            print("[CAIXA CONSUMER] Mensagem sem pedido_caixa_id ignorada")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        if not status:
            print("[CAIXA CONSUMER] Mensagem sem status ignorada")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        print(f"[CAIXA CONSUMER] Pedido #{pedido_id} está {status}!")

        db.atualizar_status_pedido(pedido_id, status)
        print(f"[CAIXA CONSUMER] Status do pedido #{pedido_id} atualizado "
              f"para {status}")

        # Confirmar processamento bem-sucedido
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError:
        print("[CAIXA CONSUMER] Erro ao decodificar JSON da mensagem")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"[CAIXA CONSUMER] Erro ao processar mensagem: {e}")

        # Limitar tentativas: após 3 falhas, enviar para DLQ
        if retry_count >= 2:
            print(f"[CAIXA CONSUMER] ⚠ Limite de tentativas atingido "
                  f"({retry_count + 1}). Enviando para DLQ...")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            print(
                f"[CAIXA CONSUMER] Tentativa {retry_count + 1}/3. "
                f"Reenviando para fila...")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor():
    """Inicia o consumer que escuta a fila de pedidos prontos."""
    print("[CAIXA CONSUMER] Iniciando consumer...")

    while True:
        try:
            # Conectar ao RabbitMQ
            connection = pika.BlockingConnection(
                pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()

            # Declarar Dead Letter Exchange
            channel.exchange_declare(
                exchange='pedidos_prontos_dlx',
                exchange_type='fanout',
                durable=True
            )

            # Declarar Dead Letter Queue
            channel.queue_declare(
                queue='pedidos_prontos_dlq',
                durable=True
            )

            # Bind DLQ ao DLX
            channel.queue_bind(
                exchange='pedidos_prontos_dlx',
                queue='pedidos_prontos_dlq'
            )

            # Declarar exchange principal
            channel.exchange_declare(
                exchange='pedidos_prontos_exchange',
                exchange_type='fanout'
            )

            # Criar fila com DLX configurada
            result = channel.queue_declare(
                queue='',
                exclusive=True,
                arguments={
                    'x-dead-letter-exchange': 'pedidos_prontos_dlx',
                }
            )
            queue_name = result.method.queue

            # Bind da fila ao exchange
            channel.queue_bind(
                exchange='pedidos_prontos_exchange',
                queue=queue_name
            )

            print(f"[CAIXA CONSUMER] Aguardando pedidos prontos na fila "
                  f"{queue_name}...")
            print("[CAIXA CONSUMER] DLQ configurada: pedidos_prontos_dlq")

            # Configurar callback com confirmação manual
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )

            # Iniciar consumo
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            print("[CAIXA CONSUMER] Erro ao conectar ao RabbitMQ. "
                  "Tentando novamente em 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("[CAIXA CONSUMER] Encerrando consumer...")
            break
        except Exception as e:
            print(f"[CAIXA CONSUMER] Erro inesperado: {e}")
            time.sleep(5)


@app.route('/')
def index():
    """Serve a página inicial do frontend."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS, etc)."""
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    # Iniciar consumer em thread separada
    consumer_thread = threading.Thread(target=iniciar_consumidor, daemon=True)
    consumer_thread.start()
    print("[CAIXA] Consumer iniciado em thread separada")

    app.run(host='0.0.0.0', port=5000)
