from django.shortcuts import redirect, render
from .models import Entry, Comment, Category
from .forms import EntryForm, CommentForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F
from django.core.paginator import Paginator


class EntryListView(LoginRequiredMixin, ListView):
    model = Entry
    template_name = 'base/base.html'
    context_object_name = 'entries'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(entry_count=Count('entries'))
        context['comments'] = Comment.objects.all()
        context['users_count'] = Entry.objects.values('author').distinct().count()
        return context



class EntryDetailView(DetailView):
    model = Entry
    template_name = 'myapp/detail.html'
    context_object_name = 'entry'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        comment_list = Comment.objects.filter(
            entry=self.object,
            parent__isnull=True
            ).order_by('created_at')
        
        paginator = Paginator(comment_list, 5)  # 5 comments per page
        page = self.request.GET.get("page")
        comments = paginator.get_page(page)

        context["comments"] = comments

        context["comment_form"] = CommentForm()

        return context
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Increment view count
        Entry.objects.filter(pk=self.object.pk).update(views=F('views') + 1)
        self.object.refresh_from_db()

        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)

        if form.is_valid():
            # Handle reply to another comment
            parent_id = form.cleaned_data.get("parent_id")

            comment = Comment(
                entry=self.object,
                author=request.user,
                text=form.cleaned_data["text"],
                parent_id=parent_id if parent_id else None
            )

            comment.save()

            return redirect(self.object.get_absolute_url())

        context = self.get_context_data(
            object=self.object,
            comment_form=form
            )
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
    # model = Entry
    # template_name = 'myapp/search_results.html'
    # context_object_name = 'entries'

    # def get_queryset(self):
    #     query = self.request.GET.get('q')
    #     qs = super().get_queryset()
    
    #     if query:
    #         qs = qs.filter(title__contains=query)

    #     return qs
    pass