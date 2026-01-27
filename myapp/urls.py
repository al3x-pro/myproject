from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    path('', views.EntryListView.as_view(), name='entry-list'),
    path('search/', views.entry_search, name='entry-search'),
    path('entry/<int:pk>/', views.EntryDetailView.as_view(), name='entry-detail'),
    path('addcomment/', views.CommentAjaxView.as_view(), name='addcomment'),
    path('entry/new/', views.EntryCreateView.as_view(), name='entry-create'),
    path('entry/edit/<int:pk>/', views.EntryUpdateView.as_view(), name='entry-update'),
    path('entry/delete/<int:pk>/', views.EntryDeleteView.as_view(), name='entry-delete'),
]