import sqlite3
from contextlib import contextmanager

DATABASE_PATH = 'cozinha.db'
FUSO_BRASILIA = '-03:00'

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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos_cozinha (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                cliente VARCHAR(100) NOT NULL,
                item VARCHAR(100) NOT NULL,
                observacao TEXT,
                status VARCHAR(20) DEFAULT 'RECEBIDO',
                tempo_preparacao INTEGER DEFAULT 0,
                data_recebimento TIMESTAMP,
                data_inicio_preparo TIMESTAMP,
                data_conclusao TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON pedidos_cozinha(status)')
        print("[DB] Banco de dados da Cozinha inicializado com sucesso!")

def registrar_pedido(pedido_id, cliente, item, observacao=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO pedidos_cozinha
            (pedido_id, cliente, item, observacao, status, data_recebimento)
            VALUES (?, ?, ?, ?, 'RECEBIDO', datetime('now', '{FUSO_BRASILIA}'))
        ''', (pedido_id, cliente, item, observacao))
        return cursor.lastrowid

def iniciar_preparo(cozinha_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE pedidos_cozinha
            SET status = 'PREPARANDO',
                data_inicio_preparo = datetime('now', '{FUSO_BRASILIA}')
            WHERE id = ?
        ''', (cozinha_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"Pedido {cozinha_id} não encontrado na cozinha")

def finalizar_pedido_automatico(cozinha_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE pedidos_cozinha
            SET status = 'PRONTO',
                data_conclusao = datetime('now', '{FUSO_BRASILIA}'),
                tempo_preparacao = CAST(
                    (julianday('now', '{FUSO_BRASILIA}') - julianday(data_inicio_preparo)) * 24 * 60 
                AS INTEGER)
            WHERE id = ?
        ''', (cozinha_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"Pedido {cozinha_id} não encontrado")
            
        cursor.execute('SELECT pedido_id, cliente, item, tempo_preparacao FROM pedidos_cozinha WHERE id = ?', (cozinha_id,))
        return dict(cursor.fetchone())

# --- FUNÇÃO QUE FALTAVA ---
def cancelar_pedido(cozinha_id):
    """Marca um pedido como cancelado."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE pedidos_cozinha
            SET status = 'CANCELADO',
                data_conclusao = datetime('now', '{FUSO_BRASILIA}')
            WHERE id = ?
        ''', (cozinha_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"Pedido {cozinha_id} não encontrado")

def listar_pedidos_por_status(status):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pedidos_cozinha WHERE status = ? ORDER BY data_recebimento ASC', (status,))
        return [dict(row) for row in cursor.fetchall()]

def listar_fila_preparo():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Ordenação: Preparando > Recebido > Pronto > Cancelado
        cursor.execute('''
            SELECT * FROM pedidos_cozinha
            ORDER BY
                CASE status
                    WHEN 'PREPARANDO' THEN 1
                    WHEN 'RECEBIDO' THEN 2
                    WHEN 'PRONTO' THEN 3
                    ELSE 4
                END,
                data_recebimento ASC
            LIMIT 100
        ''')
        return [dict(row) for row in cursor.fetchall()]

def buscar_pedido(cozinha_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pedidos_cozinha WHERE id = ?', (cozinha_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def estatisticas_cozinha():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status, COUNT(*) as quantidade FROM pedidos_cozinha GROUP BY status')
        status_count = {row['status']: row['quantidade'] for row in cursor.fetchall()}
        
        cursor.execute('''
            SELECT AVG(tempo_preparacao) as tempo_medio, MIN(tempo_preparacao) as tempo_minimo, MAX(tempo_preparacao) as tempo_maximo
            FROM pedidos_cozinha WHERE status = 'PRONTO' AND tempo_preparacao > 0
        ''')
        tempos = cursor.fetchone()
        return {
            'pedidos_por_status': status_count,
            'tempo_medio_preparo': round(tempos['tempo_medio'], 2) if tempos['tempo_medio'] else 0,
            'tempo_minimo': tempos['tempo_minimo'] or 0,
            'tempo_maximo': tempos['tempo_maximo'] or 0
        }