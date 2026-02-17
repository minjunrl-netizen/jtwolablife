from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', '총관리자'
        MANAGER = 'manager', '책임자'
        AGENCY = 'agency', '대행사'
        SELLER = 'seller', '셀러'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.SELLER,
        verbose_name='역할',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='상위 계정',
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal('0'),
        verbose_name='예치금 잔액',
    )
    company_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='회사명',
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='연락처',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='가입일')

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자'

    def __str__(self):
        return f"[{self.get_role_display()}] {self.company_name or self.username}"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_agency(self):
        return self.role == self.Role.AGENCY

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    def get_descendant_ids(self, _visited=None):
        """자신 하위 전체 유저 ID 목록 (재귀, 순환 방지)"""
        if _visited is None:
            _visited = set()
        if self.id in _visited:
            return []
        _visited.add(self.id)
        child_ids = list(User.objects.filter(parent=self).values_list('id', flat=True))
        all_ids = list(child_ids)
        for cid in child_ids:
            if cid not in _visited:
                all_ids.extend(User.objects.get(pk=cid).get_descendant_ids(_visited=_visited))
        return all_ids

    def get_all_order_user_ids(self):
        """주문 조회 시 포함할 전체 유저 ID (자신 포함)"""
        return [self.id] + self.get_descendant_ids()
