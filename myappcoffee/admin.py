# from django.contrib import admin
# from .models import User
#
# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('user_id', 'username','password','first_name')


# admin.py
from django.contrib import admin
from .models import User

@admin.action(description='Очистить поле cups у выбранных пользователей')
def reset_cups(modeladmin, request, queryset):
    queryset.update(cups=0)

@admin.action(description='Добавить 15 к депозиту у выбранных пользователей')
def add_15_to_deposit(modeladmin, request, queryset):
    for user in queryset:
        user.deposit += 15
        user.save()

class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'first_name', 'cups', 'cups_today', 'amount_due', 'deposit','historical_amount_due')
    fields = ('username', 'user_id', 'first_name','password','cups','amount_due','deposit','historical_amount_due','cups_new')
    actions = [reset_cups, add_15_to_deposit]

admin.site.register(User, UserAdmin)

