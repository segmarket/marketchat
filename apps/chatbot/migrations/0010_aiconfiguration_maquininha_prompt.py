from django.db import migrations


def update_onboarding_prompt(apps, schema_editor):
    from apps.chatbot.defaults import DEFAULT_ONBOARDING_SYSTEM_PROMPT

    AIConfiguration = apps.get_model("chatbot", "AIConfiguration")
    for cfg in AIConfiguration.objects.filter(is_active=True):
        prompt = (cfg.system_prompt or "").strip()
        if "problema_maquininha" in prompt and "iniciar_venda_backup" in prompt:
            continue
        cfg.system_prompt = DEFAULT_ONBOARDING_SYSTEM_PROMPT
        cfg.save(update_fields=["system_prompt", "updated_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0009_aiconfiguration"),
    ]

    operations = [
        migrations.RunPython(update_onboarding_prompt, noop_reverse),
    ]
