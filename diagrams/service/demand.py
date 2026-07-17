"""Record demand for diagrams the engine could not draw.

Called on every unrenderable figure so the gaps become a ranked, durable backlog
(see DiagramDemand). Categorises the failure so "unknown subtype" (a renderer to build)
is distinguishable from "render error" (a renderer to fix). Never raises — a bookkeeping
write must not break generation.
"""
import logging

logger = logging.getLogger(__name__)


def _categorise(reason: str) -> str:
    from diagrams.models import DiagramDemand
    r = (reason or "").lower()
    if "no renderer for diagram_type" in r:
        return DiagramDemand.CATEGORY_UNKNOWN_TYPE
    if "unknown subtype" in r or "unsupported subtype" in r or "no renderer for subtype" in r:
        return DiagramDemand.CATEGORY_UNKNOWN_SUBTYPE
    if "validation failed" in r or "subtype:" in r:
        # A schema the validator rejected for this subtype — the subtype exists but the
        # advertised shape didn't fit; still useful signal, grouped as a render error.
        return DiagramDemand.CATEGORY_RENDER_ERROR
    if r:
        return DiagramDemand.CATEGORY_RENDER_ERROR
    return DiagramDemand.CATEGORY_OTHER


def record_demand(diagram_type, subtype, reason: str = "") -> None:
    """Increment the durable tally for an unrenderable (type, subtype, category). Never raises."""
    try:
        from django.db.models import F
        from diagrams.models import DiagramDemand

        category = _categorise(reason)
        rows = DiagramDemand.objects.filter(
            diagram_type=(diagram_type or "?"), subtype=(subtype or "?"), category=category,
        )
        updated = rows.update(count=F("count") + 1, sample_reason=(reason or "")[:500])
        if not updated:
            # First sighting — create at count 1. A concurrent create races to the unique
            # key; on collision fall back to an increment so no event is lost.
            try:
                DiagramDemand.objects.create(
                    diagram_type=(diagram_type or "?"), subtype=(subtype or "?"),
                    category=category, count=1, sample_reason=(reason or "")[:500],
                )
            except Exception:
                rows.update(count=F("count") + 1, sample_reason=(reason or "")[:500])
    except Exception:
        # DB unavailable / outside app context / migration not yet run — demand tracking is
        # best-effort and must never interfere with rendering.
        logger.debug("record_demand skipped", exc_info=True)
