"""Storage models package - one module per SQLAlchemy model.

Importing this package ensures all models are registered with the
SQLAlchemy Base.metadata so that ``Base.metadata.create_all()`` picks
them up when the database is initialized.
"""

from src.storage.models.analysis_feedback import AnalysisFeedbackModel
from src.storage.models.analysis_feedback_label import AnalysisFeedbackLabelModel
from src.storage.models.analysis_label import AnalysisLabelModel
from src.storage.models.analysis_result import AnalysisResultModel
from src.storage.models.comment import CommentModel
from src.storage.models.page import PageModel
from src.storage.models.post import PostModel
from src.storage.models.seed_page import SeedPageModel

__all__ = [
    "AnalysisFeedbackModel",
    "AnalysisFeedbackLabelModel",
    "AnalysisLabelModel",
    "AnalysisResultModel",
    "CommentModel",
    "PageModel",
    "PostModel",
    "SeedPageModel",
]
