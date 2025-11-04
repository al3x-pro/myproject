from django.shortcuts import render
from .models import Entry
from .forms import EntryForm
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


class EntryDetailView(DetailView):
    model = Entry
    template_name = 'myapp/detail.html'
    context_object_name = 'entry'


class EntryCreateView(CreateView):
    model = Entry
    form_class = EntryForm
    template_name = 'myapp/entry_form.html'
    success_url = reverse_lazy('entry-list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
class EntryUpdateView(UserPassesTestMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = 'myapp/entry_form.html'
    success_url = reverse_lazy('entry-list')

    def test_func(self):
        entry = self.get_object()
        return entry.author == self.request.user
    
class EntryDeleteView(UserPassesTestMixin, DeleteView):
    model = Entry
    template_name = 'myapp/entry_confirm_delete.html'
    success_url = reverse_lazy('entry-list')

    def test_func(self):
        entry = self.get_object()
        return entry.author == self.request.user