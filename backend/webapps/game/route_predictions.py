from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.core.config import TEMPLATES_DIR
from backend.apis.v1.route_login import get_current_user
from backend.db.models.user import User
from backend.core.bayes import get_bayes_predictions
from backend.db.repository.game import get_game_by_id
from typing import Optional

templates = Jinja2Templates(directory=TEMPLATES_DIR)
router = APIRouter()

@router.get("/{game_id}/predictions", name="game_predictions")
async def game_predictions(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    game = get_game_by_id(game_id, db)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    predictions = get_bayes_predictions(game_id, db)
    # Sort by probability descending
    predictions.sort(key=lambda x: x["win_prob"], reverse=True)
    
    # Assign colors for the plot
    colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', 
        '#FF9F40', '#C9CBCF', '#4682B4', '#32CD32', '#FF4500'
    ]
    for i, pred in enumerate(predictions):
        pred["color"] = colors[i % len(colors)]

    return templates.TemplateResponse(
        "game/predictions_content.html",
        {
            "request": request,
            "game": game,
            "predictions": predictions,
            "chart_data": [
                {
                    "mu": p["mu"],
                    "sigma": p["sigma"],
                    "label": p["player"].nick or p["player"].username,
                    "color": p["color"],
                    "reliability": p["reliability"]
                }
                for p in predictions
            ]
        },
    )
