import json
import time

import pika


def callback(ch, method, properties, body):
    pedido = json.loads(body)
    print(f" [x] COZINHA RECEBEU: {pedido['item']} para {pedido['cliente']}")
    print(" [x] Preparando...", flush=True)
    time.sleep(5)
    print(" [x] PRONTO!", flush=True)


def iniciar_consumidor():
    print("Conectando ao RabbitMQ...", flush=True)

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()

            channel.exchange_declare(
                exchange='pedidos_exchange', exchange_type='fanout')

            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue

            channel.queue_bind(exchange='pedidos_exchange', queue=queue_name)

            print(' [*] Cozinha aguardando pedidos...', flush=True)

            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
            break
        except Exception as e:
            print(f"Erro ao conectar ao RabbitMQ: {e}", flush=True)
            time.sleep(2)

    channel = connection.channel()
    channel.queue_declare(queue='pedidos')

    print(' [*] Aguardando pedidos. Para sair pressione CTRL+C', flush=True)

    channel.basic_consume(
        queue='pedidos', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()


if __name__ == '__main__':
    iniciar_consumidor()
