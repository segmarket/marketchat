from django.contrib import admin

from apps.support.models import SupportTicket, SupportTicketMessage


class SupportTicketMessageInline(admin.StackedInline):
    model = SupportTicketMessage
    extra = 1
    ordering = ["created_at"]
    fields = ("message", "sender", "is_from_admin", "created_at")
    readonly_fields = ("sender", "is_from_admin", "created_at")
    classes = ["collapse"]

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "user",
        "subject",
        "status",
        "priority",
        "created_at",
    )
    list_display_links = ("id", "subject")
    list_editable = ("status", "priority")
    list_filter = ("status", "priority", "tenant", ("created_at", admin.DateFieldListFilter))
    search_fields = ("subject", "description", "user__email", "tenant__name")
    date_hierarchy = "created_at"
    readonly_fields = (
        "tenant",
        "user",
        "category_route",
        "created_at",
        "updated_at",
    )
    inlines = [SupportTicketMessageInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "tenant",
                    "user",
                    "subject",
                    "description",
                    "category_route",
                    "status",
                    "priority",
                ),
            },
        ),
        (
            "Datas",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def save_formset(self, request, form, formset, change):
        ticket = form.instance
        new_admin_messages = False

        instances = formset.save(commit=False)
        for obj in instances:
            if not obj.pk:
                obj.sender = request.user
                obj.is_from_admin = True
                new_admin_messages = True
            obj.save()

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()

        if new_admin_messages and ticket.status == SupportTicket.Status.NEW:
            ticket.status = SupportTicket.Status.IN_PROGRESS
            ticket.save(update_fields=["status", "updated_at"])
