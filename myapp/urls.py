from django.urls import path
from . import views

urlpatterns = [
    path('', views.EntryListView.as_view(), name='entry-list'),
    path('search/', views.SearchResultsView.as_view(), name='entry-search'),
    path('entry/<int:pk>/', views.EntryDetailView.as_view(), name='entry-detail'),
    path('entry/new/', views.EntryCreateView.as_view(), name='entry-create'),
    path('entry/edit/<int:pk>/', views.EntryUpdateView.as_view(), name='entry-update'),
    path('entry/delete/<int:pk>/', views.EntryDeleteView.as_view(), name='entry-delete'),
]