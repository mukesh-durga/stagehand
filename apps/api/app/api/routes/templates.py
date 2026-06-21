"""Template gallery endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.template import CloneTemplateRequest, TemplateResponse
from app.schemas.workflow import WorkflowResponse
from app.services import template_service
from app.services.template_service import TemplateNotFoundError

router = APIRouter(tags=["templates"])


@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateResponse]:
    return template_service.list_templates(db)


@router.get("/templates/{slug}", response_model=TemplateResponse)
def get_template(slug: str, db: Session = Depends(get_db)) -> TemplateResponse:
    try:
        return template_service.get_template_by_slug(db, slug)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")


@router.post(
    "/templates/{slug}/clone",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def clone_template(
    slug: str,
    payload: CloneTemplateRequest | None = None,
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    payload = payload or CloneTemplateRequest()
    try:
        return template_service.clone_template(db, slug, payload.name, payload.description)
    except TemplateNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
