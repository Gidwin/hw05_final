from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post_author = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.public_url = {
            reverse('about:author'): (HTTPStatus.OK, None),
            reverse('about:tech'): (HTTPStatus.OK, None),
            reverse(
                'posts:posts_list'): (HTTPStatus.OK, 'posts/index.html'),
            reverse(
                'posts:group_list',
                kwargs={'slug': cls.group.slug}): (HTTPStatus.OK,
                                                   'posts/group_list.html'),
            reverse(
                'posts:group_list',
                kwargs={'slug': 'slug-not-exist'}): (HTTPStatus.NOT_FOUND,
                                                     None),
            reverse(
                'posts:profile',
                kwargs={'username': cls.user.username}): (HTTPStatus.OK, None),
            reverse(
                'posts:post_detail',
                kwargs={'post_id': cls.post.pk}): (HTTPStatus.OK, None)
        }
        cls.private_url = {
            reverse(
                'posts:post_edit',
                kwargs={'post_id': cls.post.pk}): (HTTPStatus.OK, None),
            reverse(
                'posts:post_create'): (HTTPStatus.OK,
                                       'posts/create_post.html'),
            '/page-not-exist/': (HTTPStatus.NOT_FOUND, None)
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.post_author)

    def test_Post_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostsURLTests.post
        expected_object_name = post.text[:15]
        self.assertEqual(expected_object_name, str(post.text))

    def test_Group_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        group = PostsURLTests.group
        expected_object_name = group.title
        self.assertEqual(expected_object_name, str(group))

    def test_guest_user_urls(self):
        urls_names = self.public_url
        for url, response_code in urls_names.items():
            with self.subTest(url=url):
                status_code = self.guest_client.get(url).status_code
                self.assertEqual(status_code, response_code[0])

    def test_urls_uses_correct_template(self):
        key_public = list(self.public_url.keys())
        key_private = list(self.private_url.keys())
        urls_names = {
            key_public[2]: self.public_url[reverse('posts:posts_list')][1],
            key_public[3]: self.public_url[
                reverse('posts:group_list',
                        kwargs={'slug': self.group.slug})][1],
            key_private[1]: self.private_url[reverse('posts:post_create')][1]}
        for address, template in urls_names.items():
            with self.subTest(adress=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_authorized_user_urls(self):
        urls_names = {**self.public_url, **self.private_url}
        for url, response_code in urls_names.items():
            with self.subTest(url=url):
                status_code = self.authorized_client.get(url).status_code
                self.assertEqual(status_code, response_code[0])
