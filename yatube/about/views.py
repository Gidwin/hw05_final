from django.views.generic.base import TemplateView


class AuthorViews(TemplateView):
    template_name = 'about/author.html'


class TechViews(TemplateView):
    template_name = 'about/tech.html'
