from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Q  # For complex queries
from django.core.paginator import Paginator

from .models import Post, Comment , Notification
from .forms import PostForm, CommentForm

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.http import JsonResponse

@login_required
def profile(request):
    posts = Post.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'registration/profile.html', {'posts': posts})


def index(request):
    query = request.GET.get('q')
    if query:
        posts_list = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).order_by('-created_at')
    else:
        posts_list = Post.objects.all().order_by('-created_at')

    paginator = Paginator(posts_list, 5)  # 5 posts per page
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    return render(request, 'posts/index.html', {'posts': posts, 'query': query})

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
    else:
        form = PostForm()
    return render(request, 'posts/create_post.html', {'form': form})


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto-login after signup
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.all().order_by('-created_at')

    # Handle comment form submission
    if request.method == 'POST':
        # Check if user is logged in
        if not request.user.is_authenticated:
            return HttpResponseForbidden("You must be logged in to comment.")

        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = CommentForm()

    return render(request, 'posts/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form
    })

@login_required
def edit_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return HttpResponseForbidden("You are not allowed to edit this post.")
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = PostForm(instance=post)
    return render(request, 'posts/edit_post.html', {'form': form, 'post': post})

@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        return HttpResponseForbidden("You are not allowed to delete this post.")
    if request.method == 'POST':
        post.delete()
        return redirect('profile')
    return render(request, 'posts/delete_post.html', {'post': post})

def search_users(request):
    query = request.GET.get('q')
    users = []
    if query:
        users = User.objects.filter(username__icontains=query)
    return render(request, 'registration/search_users.html', {'users': users, 'query': query})

def public_profile(request, username):
    user_obj = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user_obj).order_by('-created_at')
    return render(request, 'registration/public_profile.html', {'profile_user': user_obj, 'posts': posts})


@login_required
def create_comment(request, post_id):
    if request.method == 'POST':
        content = request.POST.get('content')
        post = Post.objects.get(id=post_id)
        comment = Comment.objects.create(post=post, author=request.user, content=content)

        # Suppose we want to notify the post author
        if post.author != request.user:
            Notification.objects.create(
                user=post.author,
                message=f"{request.user.username} commented on {post.title}"
            )
    return redirect('post_detail', pk=post_id)


@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    # Check ownership
    if comment.author != request.user:
        return HttpResponseForbidden("You are not allowed to edit this comment.")

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('post_detail', pk=comment.post.pk)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'posts/edit_comment.html', {
        'form': form,
        'comment': comment
    })

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    # Check ownership
    if comment.author != request.user:
        return HttpResponseForbidden("You are not allowed to delete this comment.")

    if request.method == 'POST':
        post_pk = comment.post.pk
        comment.delete()
        return redirect('post_detail', pk=post_pk)

    return render(request, 'posts/delete_comment.html', {
        'comment': comment
    })

@login_required
def fetch_notifications(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'message': notif.message,
            'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'notifications': data})
