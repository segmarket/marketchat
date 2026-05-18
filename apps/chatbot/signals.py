from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.chatbot.services.system_workflows import seed_system_workflows
from apps.tenants.models import Tenant


@receiver(post_save, sender=Tenant)
def seed_chatbot_workflows_for_new_tenant(sender, instance: Tenant, created: bool, **kwargs) -> None:
    if created:
        seed_system_workflows(instance.pk)
