from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    path('', views.EntryListView.as_view(), name='entry-list'),
    path('search/', views.entry_search, name='entry-search'),
    path('entry/<uuid:public_id>/', views.EntryDetailView.as_view(), name='entry-detail'),
    path('addcomment/', views.CommentAjaxView.as_view(), name='addcomment'),
    path('entry/new/', views.EntryCreateView.as_view(), name='entry-create'),
    path('entry/edit/<uuid:public_id>/', views.EntryUpdateView.as_view(), name='entry-update'),
    path('entry/delete/<uuid:public_id>/', views.EntryDeleteView.as_view(), name='entry-delete'),
]