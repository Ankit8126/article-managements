from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from articles.models import Country, State, City,Article,ArticleImage
from api.serializers.article_serializers import ArticleSerializer,ArticleImageSerializer,CountrySerializer, StateSerializer, CitySerializer
from django.core.mail import send_mail
from django.conf import settings
from api.permissions import IsEditorOrAdmin
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.exceptions import NotFound

class ArticlePagination(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'page_size' 
    max_page_size = 100  

    
class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = CountrySerializer


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = StateSerializer


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = CitySerializer



class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated]
    # permission_classes = [IsNotUser]
    pagination_class = ArticlePagination  # Add pagination support

    def get_queryset(self):
        """
        Filter by category, search by title, or fetch articles based on their status (draft, review, etc.).
        Additionally, fetch articles based on the user's role:
        - Journalists can only see their own articles.
        - Editors and Admins can see all articles.
        """
        user = self.request.user  # Get the logged-in user
        queryset = Article.objects.all().order_by('-id')
        # If the user is a Journalist, only return their own articles
        if user.role == 'Journalist':
            # queryset = queryset.filter(author=user.id)
            queryset = queryset.filter(author=self.request.user)
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        # Search by title
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        # Filter by status (optional)
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def perform_create(self, serializer):
        article = serializer.save(author=self.request.user)
        # Ensure tags are saved as a comma-separated string
        tags_string = self.request.data.get('tags', None)
        if tags_string:
            article.tags = ','.join([tag.strip() for tag in tags_string.split(',')])
            article.save()

        # Send email notification when an article is submitted for review
        self.send_notification(article)

    @action(detail=True, methods=['patch'], permission_classes=[IsEditorOrAdmin])
    def approve(self, request, pk=None):
        """
        Admin/Editor can approve the article.
        """
        article = self.get_object()
        article.status = 'approved'
        article.save()

        # Send notification email for approval
        self.send_notification(article, approved=True)
        return Response({'status': 'approved'})

    @action(detail=True, methods=['patch'], permission_classes=[IsEditorOrAdmin])
    def publish(self, request, pk=None):
        """
        Admin/Editor can publish the article.
        """
        article = self.get_object()
        article.status = 'published'
        article.save()

        # Send notification email for publishing
        self.send_notification(article, published=True)
        return Response({'status': 'published'})
    
    @action(detail=True, methods=['patch'], permission_classes=[IsEditorOrAdmin])
    def reject(self, request, pk=None):
        """
        Admin/Editor can reject the article.
        """
        article = self.get_object()
        article.status = 'rejected'
        article.save()

        # Send notification email for rejection
        self.send_notification(article, reject=True)
        return Response({'status': 'rejected'})

    
    def update(self, request, *args, **kwargs):
        """
        Prevent journalists from updating articles that are approved or published.
        """
        article = self.get_object()
        user = request.user

        # Check if the article's status is 'approved' or 'published'
        if user.role == 'Journalist' and article.status in ['approved', 'published']:
            raise PermissionDenied("You cannot update articles that are approved or published.")
        # Store the old status before updating
        old_status = article.status

    # Call the parent update method to handle the actual update
        response = super().update(request, *args, **kwargs)

    # Get the updated status
        new_status = self.get_object().status

    # Check if the status has changed
        if old_status != new_status:
        # Determine the type of status change
            approved = new_status == 'approved'
            published = new_status == 'published'
            reject=new_status=='reject'

        # Send email notification using the existing function
            self.send_notification(article=self.get_object(), approved=approved,reject=reject, published=published)
        return super().update(request, *args, **kwargs)

    
    def send_notification(self, article, approved=False, reject=False, published=False):
        # Determine the article status and customize the subject and message
        if approved:
            status = "approved"
            subject = f"Your article '{article.title}' has been approved!"
            message = (
                f"Dear {article.author.get_full_name()},\n\n"
                f"Congratulations! Your article titled '{article.title}' has been approved. "
                "You can now proceed with any next steps as per the guidelines.\n\n"
                "Thank you for your submission.\n\n"
                "Best regards,\nArticleHub Team"
            )
        elif reject:
            status = "rejected"
            subject = f"Your article '{article.title}' has been rejected"
            message = (
                f"Dear {article.author.get_full_name()},\n\n"
                f"We regret to inform you that your article titled '{article.title}' has been rejected. "
                "Please review the feedback provided by the editorial team and consider revising your submission.\n\n"
                "Thank you for your effort.\n\n"
                "Best regards,\nArticleHub Team"
            )
        elif published:
            status = "published"
            subject = f"Your article '{article.title}' is now published!"
            message = (
                f"Dear {article.author.get_full_name()},\n\n"
                f"We are thrilled to inform you that your article titled '{article.title}' has been published successfully. "
                "It is now live and available for readers.\n\n"
                "Thank you for your contribution.\n\n"
                "Best regards,\nArticleHub Team"
            )
        else:
            status = "submitted for review"
            subject = f"Your article '{article.title}' has been submitted for review"
            message = (
                f"Dear {article.author.get_full_name()},\n\n"
                f"Your article titled '{article.title}' has been successfully submitted for review. "
                "Our editorial team will evaluate your submission and get back to you soon.\n\n"
                "Thank you for your patience.\n\n"
                "Best regards,\nArticleHub Team"
            )

        # Send the email notification
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [article.author.email],
        )


class ArticleImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing article images.
    """
    queryset = ArticleImage.objects.all().order_by('uploaded_at')
    serializer_class = ArticleImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        """
        Filter the queryset based on the 'article_id' query parameter.
        """
        queryset = super().get_queryset()
        article_id = self.request.query_params.get('article', None)
        if article_id:
            queryset = queryset.filter(article=article_id)
        return queryset
    def perform_create(self, serializer):
        """
        Customize the creation behavior.
        """
        serializer.save()

    
class PublishedArticlePagination(PageNumberPagination):
    page_size = 9  # Number of items per page
    page_size_query_param = 'page_size'  # Allow overriding via query parameter
    max_page_size = 100 
    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.page_size,
            'count': self.page.paginator.count,
            'results': data
        })

class PublishedArticleView(APIView):
    permission_classes = [permissions.AllowAny]  # Allow any user, authenticated or not

    def get(self, request, *args, **kwargs):
        """
        Get all published articles with filtering and pagination.
        """
        # Filtering parameters
        title = request.query_params.get('title', None)
        category = request.query_params.get('category', None)
        tags = request.query_params.getlist('tags', None)
        publish_date = request.query_params.get('publish_date', None)
        country = request.query_params.get('country', None)
        state = request.query_params.get('state', None)
        city = request.query_params.get('city', None)
        # Base query for published articles
        articles = Article.objects.filter(status='published')
        # cities=City.objects.filter()
        # states=State.objects.filter()
        # country=Country.objects.filter()
        print("Filters - Title:", title, "Tags:", tags, "Category:", category, "Publish Date:", publish_date,"city:",country)
        # Apply filters
        if title:
            articles = articles.filter(title__icontains=title)
        if category:
            articles = articles.filter(category=category)
        if tags:
         for tag in tags:
            articles = articles.filter(tags__icontains=tag)
        if publish_date:
            articles = articles.filter(publish_date=publish_date)
        if country:
            countries=Country.objects.filter(name=country).get()
            id=countries.id
            states=State.objects.filter(country_id=id).all()
            states_ids=states.values_list('id', flat=True)
            print(states_ids)
            cities=City.objects.filter(state_id__in=states_ids)
            city_ids=cities.values_list('id', flat=True)
            articles = articles.filter(city_id__in=city_ids)
        if state:
            states=State.objects.filter(name=state).get()
            id=states.id
            cities=City.objects.filter(state_id=id).all()
            city_ids = cities.values_list('id', flat=True)  # Extract only the 'id' field as a list
            articles = articles.filter(city_id__in=city_ids)
        if city:
            cities=City.objects.filter(name=city).get()
            id=cities.id
            articles=articles.filter(city_id=id) 
        # Order articles by latest
        articles = articles.order_by('-id')

        paginator = PublishedArticlePagination()
        paginated_articles = paginator.paginate_queryset(articles, request)
        serializer = ArticleSerializer(paginated_articles, many=True)

        return paginator.get_paginated_response(serializer.data)
    
class PublishedArticleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Allow any user, authenticated or not

    def get(self, request, id, *args, **kwargs):
        """
        Get a single published article by ID.
        """
        try:
            # Fetch the article with the given id and ensure the status is 'published'
            article = Article.objects.get(id=id, status='published')
        except Article.DoesNotExist:
            # If the article doesn't exist or its status is not published, return a 404 error
            raise NotFound("Article not found or not published.")

        # Serialize the article
        serializer = ArticleSerializer(article)

        # Return the serialized data as a response
        return Response(serializer.data)