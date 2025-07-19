from rest_framework.routers import DefaultRouter
from .views import CostsViewSet, PaymentViewSet, DebtViewSet

router = DefaultRouter()
router.register('costs', CostsViewSet, basename='costs')
router.register('payments', PaymentViewSet, basename='payments')
router.register('debts', DebtViewSet, basename='debts')

urlpatterns = router.urls