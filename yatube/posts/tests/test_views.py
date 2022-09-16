
import shutil
import tempfile
from datetime import datetime
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import Comment, Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
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
            image=uploaded,
        )
        cls.group1 = Group.objects.create(
            title='Test1',
            slug='test1_slug',
            description='Test1 group'
        )
        cls.pages_templates_names = {
            reverse('posts:posts_list'):
                'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': cls.post.author}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_create'):
                'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': cls.post.pk}):
                'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        cls.author = Client()
        cls.guest_client = Client()
        cls.author.force_login(cls.user)
        cache.clear()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_views_use_correct_template_guest(self):
        cache.clear()
        for namespace, template in self.pages_templates_names.items():
            with self.subTest(template):
                response = self.author.get(namespace)
                self.assertTemplateUsed(response, template)
                response = self.guest_client.get(reverse('posts:post_create'))
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_page_uses_correct_template(self):
        cache.clear()
        for reverse_name, template in self.pages_templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_correct_context_in_create_or_edit(self):
        keys_pages = list(self.pages_templates_names.keys())
        form_urls = (
            keys_pages[4],
            keys_pages[5]
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for url in form_urls:
            with self.subTest(value=url):
                response = self.authorized_client.get(url)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context['form'].fields[value]
                        self.assertIsInstance(form_field, expected)

    def test_post_new_create(self):
        new_post = Post.objects.create(
            author=self.user,
            text=self.post.text,
            group=self.group
        )
        keys_pages = list(self.pages_templates_names.keys())
        ver_pages = [
            keys_pages[0],
            keys_pages[1],
            keys_pages[2]
        ]
        for page in ver_pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertIn(
                    new_post, response.context['page_obj']
                )

    def test_post_new_not_in_group(self):
        new_post = Post.objects.create(
            author=self.user,
            text=self.post.text,
            group=self.group
        )
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group1.slug})
        )
        self.assertNotIn(new_post, response.context['page_obj'])

    def test_created_post_with_selected_group_on_right_pages(self):
        group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание 2'
        )
        post = Post.objects.create(
            author=self.user,
            text='Тестовый текст поста 2',
            id=999,
            group=group,
        )
        urls = (
            reverse('posts:posts_list'),
            reverse(
                'posts:profile',
                kwargs={'username': post.author.username}
            ),
            reverse('posts:group_list', kwargs={'slug': group.slug}))
        for url in urls:
            with self.subTest(value=url):
                response = self.author.get(url)
                self.assertIn(post, response.context['page_obj'])
        other_group_response = self.author.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertNotIn(post, other_group_response.context['page_obj'])

    def test_index_cache(self):
        """Тест работы кэширования"""
        Post.objects.create(
            text='new-post-with-cache',
            author=self.user,
            group=self.group,
        )
        response = self.guest_client.get('/')
        page = response.content.decode()
        self.assertNotIn('new-post-with-cache', page)
        cache.clear()
        response = self.guest_client.get('/')
        page = response.content.decode()
        self.assertIn('new-post-with-cache', page)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PaginatorViewsTest, cls).setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title="Test group",
            slug="test_group_slug",
            description="Test group description",
        )
        cls.posts = [Post(author=cls.user,
                     group=cls.group,
                     pub_date=timezone.now(),
                     text='Тестовый текст'
                     + str(i)) for i in range(settings.MULTIPLIER)]
        Post.objects.bulk_create(cls.posts)
        cls.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        response = self.guest_client.get(reverse("posts:posts_list"))
        self.assertEqual(len(response.context["page_obj"]),
                         settings.POSTS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        response = self.guest_client.get(reverse("posts:posts_list")
                                         + "?page=2")
        self.assertEqual(len(response.context["page_obj"]), 3)

    def test_group_list_contains_ten_records(self):
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        self.assertEqual(len(response.context["page_obj"]),
                         settings.POSTS_PER_PAGE, "Не десять!")

    def test_group_list_second_page_contains_three_records(self):
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
            + "?page=2"
        )
        self.assertEqual(len(response.context["page_obj"]), 3, "Не три!")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CommentViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')
        cls.guest_client = Client()
        cls.autorized_client = Client()
        cls.autorized_client.force_login(cls.user)
        cls.autorized_author = Client()
        cls.autorized_author.force_login(cls.user)

        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            pub_date=datetime.now(),
        )
        cls.comment = Comment.objects.create(
            text='Тестовый коммент',
            author=cls.author,
            post=cls.post
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_autorized_client_can_comment(self):
        self.autorized_client.post(reverse(
            'posts:add_comment',
            kwargs={'post_id': self.post.id}
        ),
            {'text': 'Тестовый комментарий', },
            follow=True
        )
        response = self.autorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        ),
        )
        self.assertContains(response, 'Тестовый комментарий')

    def test_guest_cant_comment(self):
        self.guest_client.post(reverse(
            'posts:add_comment',
            kwargs={'post_id': self.post.id}
        ),
            {'text': '2 Тестовый комментарий 2', },
            follow=True
        )
        response = self.guest_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        ),
        )
        self.assertNotContains(response, 'Тестовый комментарий 2')

    def test_comment_shown_in_post_deatail(self):
        response = self.autorized_author.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIn(self.comment, response.context['comments'])


class FollowViewTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user_author = User.objects.create(username='user_author')
        cls.user_follower = User.objects.create(username='user_follower')

        cls.guest_client = Client()
        cls.autorized_author = Client()
        cls.autorized_follower = Client()

        cls.autorized_author.force_login(cls.user_author)
        cls.autorized_follower.force_login(cls.user_follower)

        cls.group = Group.objects.create(
            title='test title 1',
            slug='test_slug_1',
            description='test description 1'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user_author,
            group=cls.group
        )

    def test_autorized_follow(self):
        self.autorized_follower.get(reverse('posts:profile_follow', kwargs={
                                    'username': self.user_author}))
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_guest_cant_follow(self):
        self.guest_client.get(reverse('posts:profile_follow', kwargs={
                              'username': self.user_author}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_unfollow(self):
        self.autorized_follower.get(
            reverse('posts:profile_unfollow', kwargs={
                    'username': self.user_author}))
        self.guest_client.get(reverse('posts:profile_unfollow', kwargs={
                              'username': self.user_author}))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_new_follow_author_post_in_page(self):
        response = self.autorized_follower.get(reverse('posts:follow_index'))
        posts_count = len(response.context['page_obj'])
        Follow.objects.create(
            user=self.user_follower,
            author=self.user_author,
        )
        Post.objects.create(author=self.user_author, text='Test text')
        response = self.autorized_follower.get(reverse('posts:follow_index'))
        posts_new_count = len(response.context['page_obj'])
        self.assertLessEqual(posts_count, posts_new_count)

    def test_not_follow_himself(self):
        self.autorized_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_follower.username}))
        self.assertEqual(Follow.objects.all().count(), 0)
