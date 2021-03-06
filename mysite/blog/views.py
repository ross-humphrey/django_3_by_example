from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Post, Comment
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm, SearchForm
from django.core.mail import send_mail
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity

# Create your views here - a view is just Python function that receives a web req and returns a response
# All logic to return desired response goes inside the view
# Views can be defined as class methods - the advantages are that organizing code related to HTTP methods is cleaner
# Class based views allow for multiple inheritance (to encourage re use)


class PostListView(ListView):
    queryset = Post.published.all()  # Use a specific QuerySet for retrieving objects
    context_object_name = "posts"  # Use context variable posts for query results
    paginate_by = 3  # Paginate the result - display 3 objects per page
    template_name = "blog/post/list.html"  # Use custom templat to render page


def post_list(request, tag_slug=None):  # request param required by all views
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(
            tags__in=[tag]
        )  # filter list by ones containing tag

    paginator = Paginator(
        object_list, 3
    )  # 3 posts per page - Instantiate Paginator class with number of objects to display per page
    page = request.GET.get(
        "page"
    )  # Get the page GET param indicating current page number
    try:
        posts = paginator.page(
            page
        )  # obtain the objects for the desired page by calling page() of Paginator
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)

    # Use render() to render the list of posts with the template
    # Takes request context into account (template context processors are callables that set variables into the context)
    return render(
        request, "blog/post/list.html", {"page": page, "posts": posts, "tag": tag}
    )


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post,
        slug=post,
        status="published",
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )

    # List of active comments for this post
    comments = post.comments.filter(
        active=True
    )  # QuerySet used - use post object to get the Comment objects

    new_comment = None

    if request.method == "POST":
        # A comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Create comment object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # Assign the current post to the comment
            new_comment.post = post
            # Save the comment to the database
            new_comment.save()
    else:
        # Create comment form - if GET
        comment_form = CommentForm()

    # List of similar posts
    """
    Retrieve a Python list of IDs for the tags of the current post, flat=True
    ensures you get a list of single values rather than tuples
    """
    post_tag_ids = post.tags.values_list("id", flat=True)
    """
    You then get all published posts with these tags excluding the post itself
    """
    similar_posts = Post.published.filter(tags__in=post_tag_ids).exclude(id=post.id)
    """
    Your order the result by the number of shared tags and by publish to display the most recent posts 
    first with the same number of tags. You then slice the result to get the first four posts
    """
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-publish"
    )[:4]

    return render(
        request,
        "blog/post/detail.html",
        {
            "post": post,
            "comments": comments,
            "new_comment": new_comment,
            "comment_form": comment_form,
            "similar_posts": similar_posts,
        },
    )


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status="published")  # Retrieve post
    sent = False
    if request.method == "POST":
        # Form was submitted
        form = EmailPostForm(
            request.POST  # contains the submitted data
        )  # Use same view for displaying and processing
        if form.is_valid():  # validates data in form
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read {post.title}"
            message = f"Read {post.title} at {post_url}\n\n{cd['name']}'s comments: {cd['comments']}"
            send_mail(subject, message, "admin@myblog.com", [cd["to"]])
            sent = True
    else:
        form = EmailPostForm()  # displays an empty form
    return render(
        request, "blog/post/share.html", {"post": post, "form": form, "sent": sent}
    )


def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if "query" in request.GET:  # is form submitted
        form = SearchForm(
            request.GET
        )  # GET is used so its easy to share the URL (rather than POST)
        if form.is_valid():
            query = form.cleaned_data["query"]
            results = (
                Post.published.annotate(similarity=TrigramSimilarity("title", query))
                .filter(similarity__gt=0.1)
                .order_by("-similarity")
            )  # Order by SearchRank to order by relevancy
    return render(
        request,
        "blog/post/search.html",
        {"form": form, "query": query, "results": results},
    )
