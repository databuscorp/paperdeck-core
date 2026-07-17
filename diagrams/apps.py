from django.apps import AppConfig


class DiagramsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "diagrams"
    verbose_name = "STEM Diagram Engine"

    def ready(self):
        # Register the deploy-time font guard (see diagrams/checks.py).
        from diagrams import checks  # noqa: F401
