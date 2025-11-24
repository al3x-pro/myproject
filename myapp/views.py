from django.shortcuts import redirect, render
from .models import Entry, Comment
from .forms import EntryForm, CommentForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count


class EntryListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = 'base/base.html'
    context_object_name = 'entries'

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.filter(author=self.request.user)

        category = self.request.GET.get("category")

        if category:                     
            qs = qs.filter(category=category)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        category_info = {
            'LI': {
                'name': 'Lifestyle',
                'icon': 'fa-solid fa-person-walking fa-3x mb-3',
                'gradient': 'linear-gradient(45deg, #e74c3c, #c0392b)',
                'description': 'Personal experiences and life tips'
            },
            'ME': {
                'name': 'Meal',
                'icon': 'fa-solid fa-egg fa-3x mb-3',
                'gradient': 'linear-gradient(45deg, #27ae60, #229954)',
                'description': 'A time for nourishment and connection'
            },
            'LE': {
                'name': 'Learning',
                'icon': 'fa-solid fa-laptop-code fa-3x mb-3',
                'gradient': 'linear-gradient(45deg, #3498db, #2980b9)',
                'description': 'The pursuit of understanding and knowledge'
            },
        }

        counts = Entry.objects.values('category').annotate(count=Count('category'))

        comments = Comment.objects.order_by('-created_at')[:3]

        category_data = []
        for item in counts:
            cat_key = item['category']
            info = category_info.get(cat_key, {})
            category_data.append({
                'key': cat_key,
                'name': dict(Entry.Category.choices).get(cat_key, 'Unknown'),
                'count': item['count'],
                'icon': info.get('icon', 'fa-folder'),
                'gradient': info.get('gradient', 'linear-gradient(45deg, #95a5a6, #7f8c8d)'),
                'description': info.get('description', 'Explore this category')
            })

        context['category_data'] = category_data
        context["active_category"] = self.request.GET.get("category")
        context['comments'] = comments
        return context



class EntryDetailView(DetailView):
    model = Entry
    template_name = 'myapp/detail.html'
    context_object_name = 'entry'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entry = self.object

        context["comments"] = entry.comments.filter(parent__isnull=True)
        context["comment_form"] = CommentForm()
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = Comment(
                entry=self.object,
                author=request.user,
                text=form.cleaned_data["text"],
            )

            # Handle reply to another comment
            parent_id = form.cleaned_data.get("parent_id")
            if parent_id:
                comment.parent_id = parent_id

            comment.save()
            return redirect(self.object.get_absolute_url())

        context = self.get_context_data(comment_form=form)
        return self.render_to_response(context)
    

class EntryCreateView(CreateView):
    model = Entry
    form_class = EntryForm
    template_name = 'myapp/entry_form.html'
    success_url = reverse_lazy('entry-list')
    extra_context = {'title': 'Create New Entry'}

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
class EntryUpdateView(UserPassesTestMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = 'myapp/entry_form.html'
    success_url = reverse_lazy('entry-list')
    extra_context = {'title': 'Update Entry'}

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
    

class SearchResultsView(ListView):
    model = Entry
    template_name = 'myapp/search_results.html'
    context_object_name = 'entries'

    def get_queryset(self):
        query = self.request.GET.get('q')
        qs = super().get_queryset()
    
        if query:
            qs = qs.filter(title__contains=query)

        return qs