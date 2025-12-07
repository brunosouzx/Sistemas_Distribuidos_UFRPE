import json
import time

import database as db
import pika

# Inicializar banco de dados
db.init_db()


def publicar_status_pedido(pedido_id, cliente, item, status):
    """Publica atualização de status do pedido no RabbitMQ."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('rabbitmq'))
        channel = connection.channel()

        # Declarar exchange para atualizações de status
        channel.exchange_declare(
            exchange='pedidos_prontos_exchange', exchange_type='fanout')

        mensagem = {
            'pedido_caixa_id': pedido_id,  # ID do pedido no caixa
            'cliente': cliente,
            'item': item,
            'status': status
        }

        channel.basic_publish(
            exchange='pedidos_prontos_exchange',
            routing_key='',
            body=json.dumps(mensagem)
        )

        connection.close()
        print(
            f"[COZINHA] Status '{status}' do pedido #{pedido_id} "
            f"publicado no RabbitMQ", flush=True)
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao publicar no RabbitMQ: {e}", flush=True)
        return False


def publicar_pedido_pronto(pedido_id, cliente, item):
    """Publica mensagem de pedido pronto no RabbitMQ."""
    return publicar_status_pedido(pedido_id, cliente, item, 'PRONTO')


def publicar_pedido_preparando(pedido_id, cliente, item):
    """Publica mensagem de pedido em preparação no RabbitMQ."""
    return publicar_status_pedido(pedido_id, cliente, item, 'PREPARANDO')


def callback(ch, method, properties, body):
    """Processa pedidos recebidos da fila."""
    # Verificar número de tentativas
    retry_count = 0
    if properties.headers and 'x-death' in properties.headers:
        retry_count = len(properties.headers['x-death'])

    try:
        pedido = json.loads(body)
        pedido_id = pedido.get('id')
        cliente = pedido.get('cliente')
        item = pedido.get('item')
        observacao = pedido.get('observacao')

        print(
            f"\n[COZINHA] Pedido #{pedido_id} recebido: {item} para {cliente}",
            flush=True)
        if observacao:
            print(f"          Observação: {observacao}", flush=True)

        # Apenas registrar no banco de dados como RECEBIDO
        cozinha_id = db.registrar_pedido(pedido_id, cliente, item, observacao)

        print(
            f"[COZINHA] Pedido #{pedido_id} registrado na fila "
            f"(ID cozinha: {cozinha_id})", flush=True)

        # Confirmar processamento bem-sucedido
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[ERRO] Erro ao processar pedido na cozinha: {e}", flush=True)

        # Limitar tentativas: após 3 falhas, enviar para DLQ
        if retry_count >= 2:  # 0, 1, 2 = 3 tentativas
            print(f"[COZINHA] ⚠ Limite de tentativas atingido "
                  f" ({retry_count + 1}). Enviando para DLQ...", flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            print(f"[COZINHA] Tentativa {retry_count + 1}/3. "
                  f"Reenviando para fila...",
                  flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor():
    """Inicia o consumidor de mensagens do RabbitMQ."""
    print("[COZINHA] Conectando ao RabbitMQ...", flush=True)

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()

            # Declarar Dead Letter Exchange para pedidos
            channel.exchange_declare(
                exchange='pedidos_dlx',
                exchange_type='fanout',
                durable=True
            )

            # Declarar Dead Letter Queue
            channel.queue_declare(
                queue='pedidos_dlq_cozinha',
                durable=True
            )

            # Bind DLQ ao DLX
            channel.queue_bind(
                exchange='pedidos_dlx',
                queue='pedidos_dlq_cozinha'
            )

            # Declarar exchange principal
            channel.exchange_declare(
                exchange='pedidos_exchange', exchange_type='fanout')

            # Criar fila com DLX
            result = channel.queue_declare(
                queue='',
                exclusive=True,
                arguments={
                    'x-dead-letter-exchange': 'pedidos_dlx',
                }
            )
            queue_name = result.method.queue

            channel.queue_bind(exchange='pedidos_exchange', queue=queue_name)

            print('[COZINHA] ✓ Conectado! Aguardando pedidos...', flush=True)
            print('[COZINHA] DLQ configurada: pedidos_dlq_cozinha', flush=True)

            # Processar uma mensagem por vez para garantir confiabilidade
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=False)

            channel.start_consuming()
            break

        except pika.exceptions.AMQPConnectionError as e:
            print(f"[COZINHA] Erro de conexão com RabbitMQ: {e}", flush=True)
            print("[COZINHA] Tentando reconectar em 2 segundos...", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"[ERRO] Erro inesperado: {e}", flush=True)
            time.sleep(2)


if __name__ == '__main__':
    iniciar_consumidor()
