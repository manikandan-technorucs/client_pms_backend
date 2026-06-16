from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse

from app.database import get_db
from app.models.attachment import Attachment
from app.services.attachment_service import generate_sas_url
from app.models.user import User

router = APIRouter(
    prefix="/attachments",
    tags=["attachments"]
)

@router.get("/{attachment_id}/url")
async def get_attachment_url(
    attachment_id: int, 
    session: AsyncSession = Depends(get_db)
):
    """
    Returns a redirect to the signed Azure Blob URL (SAS token) 
    valid for 1 hour. This securely grants read access to the file.
    """
    attachment = await session.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
        
    signed_url = generate_sas_url(attachment.file_path)
    return {"url": signed_url}
