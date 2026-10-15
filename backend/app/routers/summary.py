import asyncio
import re
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field
from app.models.db_models import User
from app.services import session_service as sessions
from app.services import summary_service as summary
from app.services import export_service as export_converter
from app.services.security_service import get_current_user

router = APIRouter(prefix="/session", tags=["document-summary"])


class DocumentExportRequest(BaseModel):
    title: str = Field(default="Dokumen Ringkasan", max_length=200)
    markdown: str = Field(min_length=1, max_length=500000)
    format: str = Field(default="md", max_length=5)


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    clean = re.sub(r"\s+", "_", clean)
    return clean[:60] or "dokumen_ringkasan"


@router.post("/{session_id}/document/generate")
async def generate_document(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Akses ditolak: Anda bukan pemilik sesi ini")

    try:
        title_hint = session.get("title")
        result = await asyncio.to_thread(summary.generateSessionSummary, session_id, title_hint)
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal menyusun ringkasan dokumen: {str(exc)}")


@router.post("/{session_id}/document/export")
async def export_document(
    session_id: str,
    req: DocumentExportRequest,
    current_user: User = Depends(get_current_user),
):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Akses ditolak: Anda bukan pemilik sesi ini")

    clean_format = req.format.lower().strip()
    safe_filename = _sanitize_filename(req.title)

    if clean_format == "md":
        file_bytes = req.markdown.encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
        extension = "md"
    elif clean_format == "docx":
        file_bytes = await asyncio.to_thread(
            export_converter.createDocx,
            req.markdown,
            req.title,
        )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"
    elif clean_format == "pdf":
        file_bytes = await asyncio.to_thread(
            export_converter.createPdf,
            req.markdown,
            req.title,
        )
        media_type = "application/pdf"
        extension = "pdf"
    else:
        raise HTTPException(status_code=400, detail="Format tidak didukung. Pilih 'md', 'docx', atau 'pdf'.")

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}.{extension}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }

    return Response(content=file_bytes, media_type=media_type, headers=headers)
