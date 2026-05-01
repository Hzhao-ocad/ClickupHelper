import tempfile
import os

from fastapi import APIRouter, UploadFile, File, HTTPException, Request

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(request: Request, audio: UploadFile = File(...)):
    if not audio or not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    contents = await audio.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(contents)
        tmp.close()

        stt_service = request.app.state.stt_service
        result = stt_service.transcribe(tmp.name)
        return result
    finally:
        if tmp and os.path.exists(tmp.name):
            os.unlink(tmp.name)
