from django.urls import path

from omr.controller.omrcontroller import scan, sheet, sheet_pdf

urlpatterns = [
    path('sheet/', sheet),          # POST → generate, GET ?paper_id= → sheet + layout
    path('sheet/pdf/', sheet_pdf),  # GET  ?sheet_id= | ?paper_id= → printable A4 PDF
    path('scan/', scan),            # POST multipart file → responses + needs_review
]
