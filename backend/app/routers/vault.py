"""Vault router — serve source PDFs from data/vault/.

GET /api/vault/{filename}  → FileResponse (PDF)
Only serves files in data/vault/ — no path traversal.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/vault", tags=["vault"])

_VAULT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "vault"


@router.get("/{filename}")
async def serve_vault_file(filename: str):
    # Block path traversal — resolve full path and verify it stays inside vault dir
    file_path = (_VAULT_DIR / filename).resolve()
    if not str(file_path).startswith(str(_VAULT_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found in vault")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )
