"""GET /api/graph/entities — 3D entity co-occurrence graph data.
GET /api/graph/entity/{entity_name} — detail for a single entity.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/entities")
async def get_entities(db: AsyncSession = Depends(get_db)):
    """Top 200 entities by mention count + co-occurrence links (weight >= 2)."""

    nodes_sql = text("""
        SELECT entity_value AS name, entity_type AS type, COUNT(*) AS mention_count
        FROM entities
        WHERE entity_type != 'none'
        GROUP BY entity_value, entity_type
        ORDER BY mention_count DESC
        LIMIT 200
    """)
    node_rows = (await db.execute(nodes_sql)).all()

    nodes = [
        {"id": r.name, "name": r.name, "type": r.type, "mention_count": int(r.mention_count)}
        for r in node_rows
    ]
    node_ids = {r.name for r in node_rows}

    if not node_ids:
        return {"nodes": [], "links": []}

    links_sql = text("""
        SELECT e1.entity_value AS source, e2.entity_value AS target, COUNT(*) AS weight
        FROM entities e1
        JOIN entities e2
          ON e1.decision_id = e2.decision_id
         AND e1.entity_value < e2.entity_value
        WHERE e1.entity_type != 'none'
          AND e2.entity_type != 'none'
          AND e1.entity_value = ANY(:ids)
          AND e2.entity_value = ANY(:ids)
        GROUP BY e1.entity_value, e2.entity_value
        HAVING COUNT(*) >= 2
        ORDER BY weight DESC
        LIMIT 1000
    """)
    link_rows = (await db.execute(links_sql, {"ids": list(node_ids)})).all()

    links = [
        {"source": r.source, "target": r.target, "weight": int(r.weight)}
        for r in link_rows
    ]

    return {"nodes": nodes, "links": links}


@router.get("/entity/{entity_name}")
async def get_entity_detail(entity_name: str, db: AsyncSession = Depends(get_db)):
    """Chunks + co-occurring entities for a single entity name."""

    # Entity meta
    meta_sql = text("""
        SELECT entity_type AS type, COUNT(*) AS mention_count
        FROM entities
        WHERE entity_value = :name
        GROUP BY entity_type
        ORDER BY mention_count DESC
        LIMIT 1
    """)
    meta = (await db.execute(meta_sql, {"name": entity_name})).first()

    # Top 10 co-occurring entities
    cooc_sql = text("""
        SELECT e2.entity_value AS co_name, COUNT(*) AS weight
        FROM entities e1
        JOIN entities e2
          ON e1.decision_id = e2.decision_id
         AND e2.entity_value != e1.entity_value
         AND e2.entity_type != 'none'
        WHERE e1.entity_value = :name
        GROUP BY e2.entity_value
        ORDER BY weight DESC
        LIMIT 10
    """)
    cooc_rows = (await db.execute(cooc_sql, {"name": entity_name})).all()
    co_occurring = [r.co_name for r in cooc_rows]

    # Chunks from decisions that contain this entity
    chunks_sql = text("""
        SELECT DISTINCT ON (c.id) c.text, c.citation
        FROM entities e
        JOIN chunks c ON c.decision_id = e.decision_id
        WHERE e.entity_value = :name
        ORDER BY c.id
        LIMIT 20
    """)
    chunk_rows = (await db.execute(chunks_sql, {"name": entity_name})).all()
    chunks = [{"text": r.text, "citation": r.citation} for r in chunk_rows]

    return {
        "name": entity_name,
        "type": meta.type if meta else "unknown",
        "mention_count": int(meta.mention_count) if meta else 0,
        "chunks": chunks,
        "co_occurring": co_occurring,
    }
