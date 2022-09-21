from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.pagination import pagination
from .forms import PostForm, CommentForm
from .models import Group, Post, Follow, User


def index(request):
    post_list = Post.objects.select_related('author', 'group')
    page_obj = pagination(request, post_list)
    return render(request, 'posts/index.html', {
        'page_obj': page_obj,
    })


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    page_obj = pagination(request, posts)
    return render(request, 'posts/group_list.html', {
        'page_obj': page_obj,
        'group': group,
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group')
    page_obj = pagination(request, posts)
    following = (request.user.is_authenticated
                 and Follow.objects.filter(user=request.user, author=author)
                 .exists())
    context = {
        'page_obj': page_obj,
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    form = CommentForm()
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'form': form,
        'comments': comments
    })


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    if request.user != author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    page_obj = pagination(request, posts)
    return render(request, 'posts/follow.html', {'page_obj': page_obj})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(
        user=request.user, author=author)
    if request.user != author:
        follow.delete()
    return redirect('posts:profile', username=username)
