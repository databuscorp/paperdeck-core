from django.urls import path

from diagrams.controller.diagramcontroller import (
    render_diagram,
    validate_diagram_view,
    generate_pdf,
    list_diagram_types,
    health_check,
)

urlpatterns = [
    path("render/", render_diagram),
    path("validate/", validate_diagram_view),
    path("pdf/", generate_pdf),
    path("types/", list_diagram_types),
]
