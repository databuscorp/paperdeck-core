from django.urls import path
from latex.controller.latexcontroller import (
    render_latex, render_latex_batch, validate_latex, latex_health,
)

urlpatterns = [
    path("render/",       render_latex),
    path("render-batch/", render_latex_batch),
    path("validate/",     validate_latex),
    path("health/",       latex_health),
]
