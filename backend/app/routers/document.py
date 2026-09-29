from io import BytesIO
import asyncio
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
import pypdf.errors

from app.models.db_models import User
from app.services import rag_service as rag
from app.services import session_service as sessions
from app.services.security_service import get_current_user

router = APIRouter()


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
        import pypdf
        from io import BytesIO

        content = await file.read()
        try:
            reader = pypdf.PdfReader(BytesIO(content))
            pages = []
            total_text_len = 0
            for idx, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"page": idx + 1, "text": text})
                    total_text_len += len(text)
        except (pypdf.errors.PdfReadError, pypdf.errors.FileNotDecryptedError) as pdf_err:
            raise HTTPException(status_code=400, detail=f"Gagal membaca PDF: {str(pdf_err)}")

        if not pages or total_text_len < 20:
            raise HTTPException(
                status_code=400,
                detail="PDF ditolak: Dokumen ini berupa hasil scan atau gambar tanpa teks digital yang dapat disalin. Sistem hanya memproses PDF berbasis teks digital.",
            )

        n = await asyncio.to_thread(rag.ingest_pdf_pages, session_id, file.filename, pages)

        session = sessions.get_session(session_id)
        cleanTitle = os.path.splitext(file.filename)[0].replace("_", " ").strip()
        if not session:
            sessions.create_session(session_id, cleanTitle or "Dokumen Baru", current_user.id)
        elif session.get("title") in ("Untitled", "Sesi Baru"):
            sessions.rename_session(session_id, cleanTitle or "Dokumen Baru")

        sources = rag.get_document_sources(session_id)
        return {"filename": file.filename, "chunks": n, "documents": sources}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
