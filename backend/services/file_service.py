from backend.services.openrouter_service import transcribe_audio


async def transcribe_file(file_path: str) -> str:
    return await transcribe_audio(file_path)