from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post, User


class PostsFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Test',
            slug='test_slug',
            description='Test group'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )
        cls.form = PostForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def cheсk_post(self, form_data, post):
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, form_data['author'])
        self.assertEqual(post.group.id, form_data['group'])

    def test_create_post(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'author': self.post.author
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        self.cheсk_post(form_data, post)

    def test_edit_post(self):
        posts_count = Post.objects.count()
        post = Post.objects.create(
            text='Текст поста',
            author=self.user,
            group=self.group,
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'author': self.post.author
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.get(pk=self.post.pk)
        self.cheсk_post(form_data, post)

    def test_create_post_guest(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post_create_redirect = (reverse('users:login') + '?next='
                                + reverse('posts:post_create'))
        self.assertRedirects(response, post_create_redirect)
        self.assertEqual(Post.objects.count(), posts_count)


class PostContextTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Test',
            slug='test_slug',
            description='Test group'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            text='test comment',
            author=cls.post.author,
            post=cls.post
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_comment_guest_client(self):
        comment_count = Comment.objects.count()

        form_data = {
            'text': self.comment.text,
            'author': self.comment.author,
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        comment_create_redirect = (reverse('users:login') + '?next='
                                   + reverse('posts:add_comment',
                                             kwargs={'post_id': self.post.id}))
        self.assertRedirects(response, comment_create_redirect)
        self.assertEqual(Comment.objects.count(), comment_count)

    def test_create_comment_authorized_client(self):
        comment_count = Comment.objects.count()

        form_data = {
            'text': self.comment.text,
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        last_object = Comment.objects.latest('id')
        self.assertEqual(form_data['text'], last_object.text)

    def test_index_page_cache(self):
        Post.objects.create(text='Тестовый текст',
                            author=self.user,
                            group=self.group
                            )
        response = self.guest_client.get(reverse('posts:posts_list'))
        last_object = Post.objects.latest('id')
        last_object.delete()
        response_cache = self.guest_client.get(reverse('posts:posts_list'))
        cache.clear()
        response_no_cache = self.guest_client.get(reverse('posts:posts_list'))
        self.assertEqual(response.content, response_cache.content)
        self.assertNotEqual(response.content, response_no_cache.content)
