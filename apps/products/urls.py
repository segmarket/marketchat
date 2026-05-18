from django.urls import path

from apps.products.views import (
    ProductDetailView,
    ProductDownloadTemplateView,
    ProductListView,
    ProductUploadConfirmView,
    ProductUploadPreviewView,
)

urlpatterns = [
    path("", ProductListView.as_view(), name="products-list"),
    path("download-template/", ProductDownloadTemplateView.as_view(), name="products-download-template"),
    path("upload-preview/", ProductUploadPreviewView.as_view(), name="products-upload-preview"),
    path("upload-confirm/", ProductUploadConfirmView.as_view(), name="products-upload-confirm"),
    path("<int:pk>/", ProductDetailView.as_view(), name="products-detail"),
]
