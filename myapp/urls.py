from django.urls import path
from . import views

urlpatterns = [
    path('', views.EntryListView.as_view(), name='entry-list'),
    path('search/', views.SearchResultsView.as_view(), name='entry-search'),
    path('entry/<int:pk>/', views.EntryDetailView.as_view(), name='entry-detail'),
    path("entry/<int:entry_id>/load-more/", views.load_more_comments, name="load-more-comments"),
    path("comment/<int:comment_id>/load-more-replies/", views.load_more_replies, name="load-more-replies"),
    path("comment/<int:pk>/edit/", views.edit_comment, name="edit-comment"),
    path("comment/<int:pk>/delete/", views.delete_comment, name="delete-comment"),
    path('entry/new/', views.EntryCreateView.as_view(), name='entry-create'),
    path('entry/edit/<int:pk>/', views.EntryUpdateView.as_view(), name='entry-update'),
    path('entry/delete/<int:pk>/', views.EntryDeleteView.as_view(), name='entry-delete'),
]