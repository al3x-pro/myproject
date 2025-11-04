from django.shortcuts import render
from .models import Entry
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class EntryListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = 'myapp/index.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_queryset(self):
        return Entry.objects.filter(author=self.request.user).order_by('-created_at')
