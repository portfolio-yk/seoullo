from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import Place
from app.db.session import get_db
from app.services.seed import inspect_dataset

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, object]:
    db.execute(text("SELECT 1"))
    place_count = db.scalar(select(func.count(Place.id))) or 0
    inventory = inspect_dataset(settings.data_directory)
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "database": {"connected": True, "placeCount": place_count},
        "dataset": inventory.to_dict(),
        "integrations": {
            "kakaoConfigured": bool(settings.kakao_rest_api_key),
            "pineconeConfigured": settings.pinecone_configured,
            "lexicalPineconeConfigured": settings.pinecone_lexical_configured,
            "emotionPineconeConfigured": settings.pinecone_emotion_configured,
            "chatQueryPlanningEnabled": bool(settings.openai_api_key),
            "chatSemanticSearchEnabled": settings.chat_semantic_search_enabled,
        },
    }
