from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Order, OrderItem
from products.models import PricePolicy


def get_user_price(product, user):
    try:
        policy = PricePolicy.objects.get(product=product, user=user)
        return policy.price
    except PricePolicy.DoesNotExist:
        return product.base_price


@transaction.atomic
def create_order(user, product, items_data, memo=''):
    """주문 접수 (견적서 방식 - 수량 × 단가 + 부가세 10%)"""
    unit_price = get_user_price(product, user)

    # 수량 필드 찾기 (is_quantity 플래그)
    qty_field = None
    for f in product.schema:
        if f.get('is_quantity'):
            qty_field = f['name']
            break

    # 총 수량 계산
    if qty_field:
        total_qty = sum(int(float(item.get(qty_field, 0) or 0)) for item in items_data)
    else:
        total_qty = len(items_data)

    supply_amount = unit_price * total_qty
    vat_amount = (supply_amount * Decimal('0.1')).quantize(Decimal('1'))
    total_amount = supply_amount + vat_amount

    # 마감일 계산 (최대 작업일 수 기준)
    deadline_date = timezone.now().date() + timedelta(days=product.max_work_days)

    # 주문 생성 (pk 기반 주문번호 — race condition 방지)
    order = Order.objects.create(
        order_number='TEMP',
        user=user,
        product=product,
        total_amount=total_amount,
        item_count=len(items_data),
        total_quantity=total_qty,
        deadline=deadline_date,
        memo=memo,
        status=Order.Status.SUBMITTED,
    )
    order.order_number = str(order.pk)
    order.save(update_fields=['order_number'])

    # 주문 항목 생성
    order_items = []
    for idx, data in enumerate(items_data, start=1):
        order_items.append(OrderItem(
            order=order,
            row_number=idx,
            data=data,
            unit_price=unit_price,
        ))
    OrderItem.objects.bulk_create(order_items)

    return order


@transaction.atomic
def confirm_payment(order, confirmed_by):
    """관리자가 입금 확인 처리"""
    if order.status != Order.Status.SUBMITTED:
        raise ValueError('접수완료 상태의 주문만 입금확인 처리할 수 있습니다.')

    order.status = Order.Status.PAID
    order.confirmed_at = timezone.now()
    order.confirmed_by = confirmed_by
    order.save(update_fields=['status', 'confirmed_at', 'confirmed_by', 'updated_at'])
    return order


@transaction.atomic
def cancel_order(order, cancelled_by):
    if order.status == Order.Status.CANCELLED:
        raise ValueError('이미 취소된 주문입니다.')

    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    return order


