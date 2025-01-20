from django.urls import path
from .views import optimize_strategy_view

urlpatterns = [
    path('optimize-strategy/', optimize_strategy_view, name='optimize_strategy'),
]
