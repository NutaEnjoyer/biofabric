"""Репозиторий документов ОКС.

Создание документа — двухшаговая операция:
  1. INSERT в documents (ООК) — физическая карточка файла
  2. INSERT в oks_documents  — логическая привязка к ОКС-сущности
"""
from typing import Optional
from psycopg.rows import dict_row


def list_documents(conn, object_id: int) -> list[dict]:
    sql = """
        SELECT od.*, d.title, d.file_path, d.mime_type
        FROM oks_documents od
        JOIN documents d ON d.document_id = od.document_id
        WHERE od.bind_object_type = 'object' AND od.bind_object_id = %s
        ORDER BY od.created_at DESC
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [object_id])
        return cur.fetchall()


def create_document(conn, object_id: int, data: dict, created_by: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        # Шаг 1: создать запись в documents
        cur.execute(
            """
            INSERT INTO documents (title, file_path, status_code, description, mime_type, created_by)
            VALUES (%s, %s, 'draft', %s, %s, %s)
            RETURNING document_id, title, file_path, mime_type
            """,
            [
                data.get("title"),
                data.get("file_path"),
                data.get("description"),
                data.get("mime_type"),
                created_by or None,
            ],
        )
        doc = cur.fetchone()

        # Шаг 2: создать привязку в oks_documents
        bind_id = data.get("bind_object_id") or object_id
        cur.execute(
            """
            INSERT INTO oks_documents
                (document_id, doc_type, doc_status, bind_object_type, bind_object_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            [
                doc["document_id"],
                data.get("doc_type", "other"),
                data.get("doc_status", "draft"),
                data.get("bind_object_type", "object"),
                bind_id,
                created_by or None,
            ],
        )
        oks_doc = cur.fetchone()
        oks_doc["title"] = doc["title"]
        oks_doc["file_path"] = doc["file_path"]
        oks_doc["mime_type"] = doc["mime_type"]
        return oks_doc


def update_document(conn, oks_doc_id: int, data: dict) -> Optional[dict]:
    fields = [k for k in data if data[k] is not None]
    if not fields:
        return get_document(conn, oks_doc_id)
    set_clause = ", ".join([f"{f} = %s" for f in fields])
    sql = f"""
        UPDATE oks_documents
        SET {set_clause}
        WHERE oks_doc_id = %s
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [data[f] for f in fields] + [oks_doc_id])
        row = cur.fetchone()
    if row:
        with conn.cursor(row_factory=dict_row) as cur2:
            cur2.execute("SELECT title, file_path, mime_type FROM documents WHERE document_id = %s", [row["document_id"]])
            doc = cur2.fetchone() or {}
        row.update({k: doc.get(k) for k in ("title", "file_path", "mime_type")})
    return row


def get_document(conn, oks_doc_id: int) -> Optional[dict]:
    sql = """
        SELECT od.*, d.title, d.file_path, d.mime_type
        FROM oks_documents od
        JOIN documents d ON d.document_id = od.document_id
        WHERE od.oks_doc_id = %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [oks_doc_id])
        return cur.fetchone()


def delete_document(conn, oks_doc_id: int) -> bool:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "DELETE FROM oks_documents WHERE oks_doc_id = %s RETURNING oks_doc_id",
            [oks_doc_id],
        )
        return cur.fetchone() is not None
