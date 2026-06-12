"""Model registry.

Importing every model here ensures they are all registered on `Base.metadata`,
which is what Alembic's autogenerate and `Base.metadata.create_all` rely on.
"""
from app.db.base import Base
from app.models.flock import Flock
from app.models.formulation import (
    Formulation,
    FormulationIngredient,
    FormulationMethod,
    FormulationPriceSnapshot,
)
from app.models.ingredient import Ingredient
from app.models.market_price import MarketPrice
from app.models.nutritional_composition import NutritionalComposition
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Flock",
    "Ingredient",
    "NutritionalComposition",
    "MarketPrice",
    "Formulation",
    "FormulationIngredient",
    "FormulationPriceSnapshot",
    "FormulationMethod",
]
