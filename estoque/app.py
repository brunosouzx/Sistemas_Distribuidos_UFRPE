import json
import time

import database as db
import pika

db.init_db()


def callback(ch, method, properties, body):
    """Processa pedidos e dá baixa nos ingredientes."""
    retry_count = 0
    if properties.headers and 'x-death' in properties.headers:
        retry_count = len(properties.headers['x-death'])

    try:
        pedido = json.loads(body)
        pedido_id = pedido.get('id')
        item_pedido = pedido.get('item')

        print(
            f"\n[ESTOQUE] Processando pedido #{pedido_id}: {item_pedido}...",
            flush=True)

        disponivel, mensagem = db.verificar_disponibilidade(item_pedido)

        if not disponivel:
            print(f"[ESTOQUE] ✗ ALERTA: {mensagem}", flush=True)
            # Confirmar mesmo sem estoque para não bloquear a fila
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Dar baixa nos ingredientes
        movimentacoes = db.dar_baixa_ingredientes(item_pedido, pedido_id)

        print(
            f"[ESTOQUE] ✓ Baixa realizada para pedido #{pedido_id}:",
            flush=True)
        for mov in movimentacoes:
            print(f"          - {mov['ingrediente']}: "
                  f"-{mov['quantidade_baixada']} "
                  f"(restam {mov['quantidade_restante']})", flush=True)

            # Alertar se estoque baixo
            if mov['quantidade_restante'] <= 10:
                print(f"⚠ ALERTA: Estoque de {mov['ingrediente']} está baixo!",
                      flush=True)

        # Confirmar processamento bem-sucedido
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except ValueError as e:
        print(f"[ESTOQUE] ✗ Erro de validação: {e}", flush=True)
        # Erro de validação: confirmar para não reprocessar
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[ERRO] Erro ao processar no estoque: {e}", flush=True)

        # Limitar tentativas: após 3 falhas, enviar para DLQ
        if retry_count >= 2:
            print(f"[ESTOQUE] ⚠ Limite de tentativas atingido "
                  f" ({retry_count + 1}). Enviando para DLQ...", flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            print(f"[ESTOQUE] Tentativa {retry_count + 1}/3. "
                  f"Reenviando para fila...",
                  flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor():
    """Inicia o consumidor de mensagens do RabbitMQ."""
    print("[ESTOQUE] Conectando ao RabbitMQ...", flush=True)

    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters('rabbitmq'))
            channel = connection.channel()

            # Declarar Dead Letter Exchange
            channel.exchange_declare(
                exchange='pedidos_dlx',
                exchange_type='fanout',
                durable=True
            )

            # Declarar Dead Letter Queue para estoque
            channel.queue_declare(
                queue='pedidos_dlq_estoque',
                durable=True
            )

            # Bind DLQ ao DLX
            channel.queue_bind(
                exchange='pedidos_dlx',
                queue='pedidos_dlq_estoque'
            )

            # Declarar exchange principal
            channel.exchange_declare(
                exchange='pedidos_exchange', exchange_type='fanout'
            )

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

            print('[ESTOQUE] ✓ Conectado! Monitorando pedidos...', flush=True)
            print('[ESTOQUE] DLQ configurada: pedidos_dlq_estoque', flush=True)

            # Processar uma mensagem por vez para garantir confiabilidade
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=False
            )

            channel.start_consuming()
            break

        except pika.exceptions.AMQPConnectionError as e:
            print(f"[ESTOQUE] Erro de conexão com RabbitMQ: {e}", flush=True)
            print("[ESTOQUE] Tentando reconectar em 2 segundos...", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"[ERRO] Erro inesperado: {e}", flush=True)
            time.sleep(2)


if __name__ == '__main__':
    iniciar_consumidor()
