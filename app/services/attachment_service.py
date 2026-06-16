"""Attachment service \u2014 async file I/O to Azure Blob Storage and DB sync engine."""
from __future__ import annotations

import asyncio
import uuid
from typing import List, Optional, Sequence

from fastapi import UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from azure.storage.blob.aio import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

from app.models.attachment import Attachment
from app.core.config import settings

def _get_blob_service_client() -> Optional[BlobServiceClient]:
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        return BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
    return None

async def _upload_to_azure(upload: UploadFile, unique_name: str) -> str:
    
    blob_service_client = _get_blob_service_client()
    if not blob_service_client:
        raise HTTPException(
            status_code=500, 
            detail="Azure Blob Storage is not configured."
        )
        
    container_name = settings.AZURE_STORAGE_CONTAINER_NAME
    content = await upload.read()
    
    async with blob_service_client:
        container_client = blob_service_client.get_container_client(container_name)
        try:
            await container_client.create_container(public_access=None)
        except ResourceExistsError:
            pass 
        except Exception:
            pass 
        
        blob_client = container_client.get_blob_client(unique_name)
        await blob_client.upload_blob(content, overwrite=True)
        return blob_client.url

async def _delete_from_azure(file_url: str) -> None:
    blob_service_client = _get_blob_service_client()
    if not blob_service_client:
        return
        
    container_name = settings.AZURE_STORAGE_CONTAINER_NAME
    try:
        blob_name = file_url.split(f"/{container_name}/")[-1]
        async with blob_service_client:
            container_client = blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            await blob_client.delete_blob()
    except Exception:
        pass

def generate_sas_url(file_url: str) -> str:
    """Generate a 1-hour read-only SAS token for a given blob URL."""
    blob_service_client = _get_blob_service_client()
    if not blob_service_client:
        return file_url
        
    container_name = settings.AZURE_STORAGE_CONTAINER_NAME
    try:
        blob_name = file_url.split(f"/{container_name}/")[-1]
        
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import datetime, timedelta, timezone
        
        account_key = getattr(blob_service_client.credential, "account_key", blob_service_client.credential)
        
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        return f"{file_url}?{sas_token}"
    except Exception:
        return file_url

async def save_files(
    session: AsyncSession,
    new_files: Sequence[UploadFile],
    *,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    bug_id: Optional[int] = None,
) -> List[Attachment]:
    """Save uploaded files to Azure Blob Storage asynchronously and persist Attachment rows."""
    created: List[Attachment] = []
    
    # Process uploads concurrently
    async def process_upload(upload: UploadFile) -> Optional[Attachment]:
        if not upload.filename:
            return None
        unique_name = f"{uuid.uuid4().hex}_{upload.filename}"
        url = await _upload_to_azure(upload, unique_name)
        
        attachment = Attachment(
            file_name=upload.filename,
            file_path=url,
            project_id=project_id,
            task_id=task_id,
            bug_id=bug_id,
        )
        session.add(attachment)
        return attachment
    
    tasks = [process_upload(upload) for upload in new_files]
    results = await asyncio.gather(*tasks)
    
    for res in results:
        if res:
            created.append(res)
            
    return created


async def sync_attachments(
    session: AsyncSession,
    keep_ids: List[int],
    *,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    bug_id: Optional[int] = None,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> None:
    """Diff-sync attachments for an entity:
    1. Load current attachment IDs for the entity.
    2. Delete DB rows and purge physical files from Azure not in keep_ids.
    3. Save new uploaded files.
    """
    # Build query filter
    if task_id is not None:
        stmt = select(Attachment).where(Attachment.task_id == task_id)
    elif bug_id is not None:
        stmt = select(Attachment).where(Attachment.bug_id == bug_id)
    elif project_id is not None:
        stmt = select(Attachment).where(Attachment.project_id == project_id)
    else:
        return

    result = await session.execute(stmt)
    current: List[Attachment] = list(result.scalars().all())

    # Collect URLs to delete, then fire removals concurrently
    urls_to_remove: List[str] = []
    for attachment in current:
        if attachment.id not in keep_ids:
            urls_to_remove.append(attachment.file_path)
            await session.delete(attachment)

    # Flush DB deletes first, then remove files from Azure concurrently
    if urls_to_remove:
        await asyncio.gather(*(_delete_from_azure(url) for url in urls_to_remove))

    if new_files:
        await save_files(
            session,
            new_files,
            project_id=project_id,
            task_id=task_id,
            bug_id=bug_id,
        )
