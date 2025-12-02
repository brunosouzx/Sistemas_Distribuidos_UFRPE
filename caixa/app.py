import json

import pika
from flasgger import Swagger
from flask import Flask, jsonify, request

app = Flask(__name__)
swagger = Swagger(app)


def enviar_para_fila(pedido):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()

        channel.exchange_declare(
            exchange='pedidos_exchange', exchange_type='fanout')

        channel.basic_publish(exchange='pedidos_exchange',
                              routing_key='', body=json.dumps(pedido))

        connection.close()
    except Exception as e:
        print(f"Erro no RabbitMQ: {e}")


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
          properties:
            cliente:
              type: string
              example: "Maria"
            item:
              type: string
              example: "X-Salada"
            obs:
              type: string
              example: "Sem maionese"
    responses:
      201:
        description: Pedido enviado com sucesso
    """
    pedido = request.json
    print(f"Recebido: {pedido}")

    enviar_para_fila(pedido)

    return jsonify({"status": "Pedido enviado para a cozinha!"}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
