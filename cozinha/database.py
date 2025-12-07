import sqlite3
from contextlib import contextmanager

DATABASE_PATH = 'cozinha.db'


@contextmanager
def get_db_connection():
    """Context manager para conexão com o banco de dados."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Inicializa o banco de dados com as tabelas necessárias."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Tabela de pedidos na cozinha
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos_cozinha (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                cliente VARCHAR(100) NOT NULL,
                item VARCHAR(100) NOT NULL,
                observacao TEXT,
                status VARCHAR(20) DEFAULT 'RECEBIDO',
                tempo_preparacao INTEGER DEFAULT 0,
                data_recebimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_inicio_preparo TIMESTAMP,
                data_conclusao TIMESTAMP
            )
        ''')

        # Índice para buscar pedidos por status
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status
            ON pedidos_cozinha(status)
        ''')

        print("[DB] Banco de dados da Cozinha inicializado com sucesso!")


def registrar_pedido(pedido_id, cliente, item, observacao=None):
    """Registra um novo pedido recebido na cozinha."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO pedidos_cozinha
            (pedido_id, cliente, item, observacao, status)
            VALUES (?, ?, ?, ?, 'RECEBIDO')
        ''', (pedido_id, cliente, item, observacao))

        return cursor.lastrowid


def iniciar_preparo(cozinha_id):
    """Marca um pedido como em preparação."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE pedidos_cozinha
            SET status = 'PREPARANDO',
                data_inicio_preparo = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (cozinha_id,))

        if cursor.rowcount == 0:
            raise ValueError(f"Pedido {cozinha_id} não encontrado na cozinha")


def finalizar_pedido(cozinha_id, tempo_preparacao):
    """Marca um pedido como pronto."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE pedidos_cozinha
            SET status = 'PRONTO',
                tempo_preparacao = ?,
                data_conclusao = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (tempo_preparacao, cozinha_id))

        if cursor.rowcount == 0:
            raise ValueError(f"Pedido {cozinha_id} não encontrado na cozinha")

        # Retornar dados do pedido finalizado
        cursor.execute('''
            SELECT pedido_id, cliente, item
            FROM pedidos_cozinha
            WHERE id = ?
        ''', (cozinha_id,))

        return dict(cursor.fetchone())


def listar_pedidos_por_status(status):
    """Lista pedidos filtrados por status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM pedidos_cozinha
            WHERE status = ?
            ORDER BY data_recebimento ASC
        ''', (status,))

        return [dict(row) for row in cursor.fetchall()]


def listar_fila_preparo():
    """Lista pedidos que ainda não foram finalizados."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM pedidos_cozinha
            WHERE status IN ('RECEBIDO', 'PREPARANDO')
            ORDER BY
                CASE status
                    WHEN 'PREPARANDO' THEN 1
                    WHEN 'RECEBIDO' THEN 2
                END,
                data_recebimento ASC
        ''')

        return [dict(row) for row in cursor.fetchall()]


def buscar_pedido(cozinha_id):
    """Busca um pedido específico por ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM pedidos_cozinha WHERE id = ?',
            (cozinha_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def estatisticas_cozinha():
    """Retorna estatísticas da cozinha."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Contar pedidos por status
        cursor.execute('''
            SELECT
                status,
                COUNT(*) as quantidade
            FROM pedidos_cozinha
            GROUP BY status
        ''')

        status_count = {row['status']: row['quantidade']
                        for row in cursor.fetchall()}

        # Tempo médio de preparação
        cursor.execute('''
            SELECT
                AVG(tempo_preparacao) as tempo_medio,
                MIN(tempo_preparacao) as tempo_minimo,
                MAX(tempo_preparacao) as tempo_maximo
            FROM pedidos_cozinha
            WHERE status = 'PRONTO' AND tempo_preparacao > 0
        ''')

        tempos = cursor.fetchone()

        return {
            'pedidos_por_status': status_count,
            'tempo_medio_preparo': round(tempos['tempo_medio'], 2)
            if tempos['tempo_medio'] else 0,
            'tempo_minimo': tempos['tempo_minimo'] or 0,
            'tempo_maximo': tempos['tempo_maximo'] or 0
        }
