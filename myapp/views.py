from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from .models import Entry, Category
from .forms import EntryForm, CommentForm, EntrySearchForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core import serializers


class EntryListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = 'base/base.html'
    context_object_name = 'entries'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Cache categories with entry counts
        categories = cache.get_or_set(
            'categories_with_counts',
            lambda: list(Category.objects.annotate(entry_count=Count('entries'))),
            600  # 10 minutes
        )
        context['categories'] = categories

        context['users_count'] = Entry.objects.get_author_count()

        return context


class EntryDetailView(DetailView):
    model = Entry
    template_name = 'myapp/detail.html'
    context_object_name = 'entry'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        # Increment view count atomically
        Entry.objects.filter(pk=obj.pk).update(views=F('views') + 1)
        obj.refresh_from_db(fields=['views'])

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comments = self.object.comments.all()
        context['comments'] = comments
        context['comment_form'] = CommentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.entry = self.object
            comment.author = request.user
            comment.save()
            return redirect(self.object.get_absolute_url())
        else:
            context = self.get_context_data(object=self.object)
            context['comment_form'] = form
            return self.render_to_response(context)


class EntryCreateView(LoginRequiredMixin, CreateView):
    model = Entry
    form_class = EntryForm
    template_name = 'myapp/entry_form.html'
    extra_context = {'title': 'Create New Entry'}

    def form_valid(self, form):
        form.instance.author = self.request.user
        cache.delete('categories_with_counts')
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    

class EntryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = 'myapp/entry_form.html'
    extra_context = {'title': 'Update Entry'}

    def test_func(self):
        entry = self.get_object()
        return entry.author == self.request.user
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    

class EntryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Entry
    template_name = 'myapp/entry_confirm_delete.html'
    success_url = reverse_lazy('entry-list')

    def test_func(self):
        entry = self.get_object()
        return entry.author == self.request.user
    
    def delete(self, request, *args, **kwargs):
        cache.delete('categories_with_counts')
        return super().delete(request, *args, **kwargs)
    

def entry_search(request):
    form = EntrySearchForm()
    q = ''
    c = ''
    results = []
    query = Q()

    if request.POST.get('action') == 'post':
        search_string = str(request.POST.get('ss'))

        if search_string is not None:
            search_string = Entry.objects.filter(
                title__contains=search_string)[:3]

            data = serializers.serialize('json', list(
                search_string), fields=('title'))

            return JsonResponse({'search_string': data}, safe=False)

    if 'q' in request.GET:
        form = EntrySearchForm(request.GET)
        if form.is_valid():
            q = form.cleaned_data['q']
            c = form.cleaned_data['c']
            
            if c is not None:
                query &= Q(cateory=c)

            if q is not None:
                query &= Q(title__contains=q)

            results = Entry.objects.filter(query)

    return render(request, 'myapp/search.html', {'form': form,
                                                 'q':q,
                                                 'results': results,})