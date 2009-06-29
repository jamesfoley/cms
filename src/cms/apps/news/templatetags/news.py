"""Template tags used to render news articles."""


from django import template

from cms.apps.news.models import Article


register = template.Library()


@register.inclusion_tag("news/latest_news.html")
def latest_news(count=5):
    """Renders a list of the latest news articles."""
    articles = Article.published_objects.order_by("-is_featured", "-publication_date")[:5]
    context = {"articles": articles}
    return context
