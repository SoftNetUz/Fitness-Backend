from rest_framework.routers import DefaultRouter
from .views import CostsViewSet, PaymentViewSet, DebtViewSet

router = DefaultRouter()
router.register('costs', CostsViewSet)
router.register('payments', PaymentViewSet)
router.register('debts', DebtViewSet)

urlpatterns = router.urls