"""Initial database schema

Revision ID: 0001
Revises:
Create Date: 2025-08-02 12:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create tours table
    op.create_table('tours',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_tours_name'), 'tours', ['name'], unique=False)
    op.create_index(op.f('ix_tours_slug'), 'tours', ['slug'], unique=False)

    # Create departures table
    op.create_table('departures',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tour_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('capacity_total', sa.Integer(), nullable=False),
        sa.Column('capacity_available', sa.Integer(), nullable=False),
        sa.Column('price_amount', sa.Integer(), nullable=False),
        sa.Column('price_currency', sa.String(length=3), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('capacity_total >= 0', name='ck_departure_capacity_total_non_negative'),
        sa.CheckConstraint('capacity_available >= 0', name='ck_departure_capacity_available_non_negative'),
        sa.CheckConstraint('capacity_available <= capacity_total', name='ck_departure_capacity_available_lte_total'),
        sa.CheckConstraint('price_amount >= 0', name='ck_departure_price_amount_non_negative'),
        sa.CheckConstraint('length(price_currency) = 3', name='ck_departure_price_currency_length'),
        sa.ForeignKeyConstraint(['tour_id'], ['tours.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departures_starts_at'), 'departures', ['starts_at'], unique=False)
    op.create_index(op.f('ix_departures_tour_id'), 'departures', ['tour_id'], unique=False)

    # Create holds table
    op.create_table('holds',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('departure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seats', sa.Integer(), nullable=False),
        sa.Column('customer_ref', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('seats > 0', name='ck_hold_seats_positive'),
        sa.CheckConstraint('seats <= 10', name='ck_hold_seats_max'),
        sa.CheckConstraint('length(customer_ref) > 0', name='ck_hold_customer_ref_not_empty'),
        sa.CheckConstraint('length(idempotency_key) > 0', name='ck_hold_idempotency_key_not_empty'),
        sa.ForeignKeyConstraint(['departure_id'], ['departures.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_holds_customer_ref'), 'holds', ['customer_ref'], unique=False)
    op.create_index(op.f('ix_holds_departure_id'), 'holds', ['departure_id'], unique=False)
    op.create_index(op.f('ix_holds_expires_at'), 'holds', ['expires_at'], unique=False)
    op.create_index(op.f('ix_holds_idempotency_key'), 'holds', ['idempotency_key'], unique=False)
    op.create_index(op.f('ix_holds_status'), 'holds', ['status'], unique=False)

    # Create bookings table
    op.create_table('bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('hold_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('departure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('seats', sa.Integer(), nullable=False),
        sa.Column('customer_ref', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('seats > 0', name='ck_booking_seats_positive'),
        sa.CheckConstraint('length(customer_ref) > 0', name='ck_booking_customer_ref_not_empty'),
        sa.CheckConstraint('length(code) > 0', name='ck_booking_code_not_empty'),
        sa.ForeignKeyConstraint(['departure_id'], ['departures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hold_id'], ['holds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('hold_id')
    )
    op.create_index(op.f('ix_bookings_code'), 'bookings', ['code'], unique=False)
    op.create_index(op.f('ix_bookings_customer_ref'), 'bookings', ['customer_ref'], unique=False)
    op.create_index(op.f('ix_bookings_departure_id'), 'bookings', ['departure_id'], unique=False)
    op.create_index(op.f('ix_bookings_hold_id'), 'bookings', ['hold_id'], unique=False)
    op.create_index(op.f('ix_bookings_status'), 'bookings', ['status'], unique=False)

    # Create waitlist_entries table
    op.create_table('waitlist_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('departure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_ref', sa.String(length=128), nullable=False),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('length(customer_ref) > 0', name='ck_waitlist_customer_ref_not_empty'),
        sa.ForeignKeyConstraint(['departure_id'], ['departures.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('departure_id', 'customer_ref', name='uq_waitlist_departure_customer')
    )
    op.create_index(op.f('ix_waitlist_entries_created_at'), 'waitlist_entries', ['created_at'], unique=False)
    op.create_index(op.f('ix_waitlist_entries_customer_ref'), 'waitlist_entries', ['customer_ref'], unique=False)
    op.create_index(op.f('ix_waitlist_entries_departure_id'), 'waitlist_entries', ['departure_id'], unique=False)

    # Create inventory_adjustments table
    op.create_table('inventory_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('departure_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('capacity_total_before', sa.Integer(), nullable=False),
        sa.Column('capacity_total_after', sa.Integer(), nullable=False),
        sa.Column('capacity_available_before', sa.Integer(), nullable=False),
        sa.Column('capacity_available_after', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('delta != 0', name='ck_inventory_adjustment_delta_nonzero'),
        sa.CheckConstraint('length(reason) > 0', name='ck_inventory_adjustment_reason_not_empty'),
        sa.CheckConstraint('length(actor) > 0', name='ck_inventory_adjustment_actor_not_empty'),
        sa.CheckConstraint('capacity_total_before >= 0', name='ck_inventory_adjustment_total_before_non_negative'),
        sa.CheckConstraint('capacity_total_after >= 0', name='ck_inventory_adjustment_total_after_non_negative'),
        sa.CheckConstraint('capacity_available_before >= 0', name='ck_inventory_adjustment_available_before_non_negative'),
        sa.CheckConstraint('capacity_available_after >= 0', name='ck_inventory_adjustment_available_after_non_negative'),
        sa.CheckConstraint('capacity_available_before <= capacity_total_before', name='ck_inventory_adjustment_available_lte_total_before'),
        sa.CheckConstraint('capacity_available_after <= capacity_total_after', name='ck_inventory_adjustment_available_lte_total_after'),
        sa.CheckConstraint('capacity_total_after = capacity_total_before + delta', name='ck_inventory_adjustment_total_delta_consistency'),
        sa.ForeignKeyConstraint(['departure_id'], ['departures.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_adjustments_created_at'), 'inventory_adjustments', ['created_at'], unique=False)
    op.create_index(op.f('ix_inventory_adjustments_departure_id'), 'inventory_adjustments', ['departure_id'], unique=False)

    # Create idempotency_records table
    op.create_table('idempotency_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=100), nullable=False),
        sa.Column('request_body_hash', sa.String(length=64), nullable=False),
        sa.Column('response_status_code', sa.Integer(), nullable=False),
        sa.Column('response_body', sa.Text(), nullable=False),
        sa.Column('response_headers', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('length(idempotency_key) > 0', name='ck_idempotency_key_not_empty'),
        sa.CheckConstraint('length(method) > 0', name='ck_idempotency_method_not_empty'),
        sa.CheckConstraint('length(request_body_hash) = 64', name='ck_idempotency_hash_length'),
        sa.CheckConstraint('response_status_code >= 100', name='ck_idempotency_status_code_valid'),
        sa.CheckConstraint('response_status_code <= 599', name='ck_idempotency_status_code_max'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', 'method', name='uq_idempotency_key_method')
    )
    op.create_index(op.f('ix_idempotency_records_expires_at'), 'idempotency_records', ['expires_at'], unique=False)
    op.create_index(op.f('ix_idempotency_records_idempotency_key'), 'idempotency_records', ['idempotency_key'], unique=False)
    op.create_index(op.f('ix_idempotency_records_method'), 'idempotency_records', ['method'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table('idempotency_records')
    op.drop_table('inventory_adjustments')
    op.drop_table('waitlist_entries')
    op.drop_table('bookings')
    op.drop_table('holds')
    op.drop_table('departures')
    op.drop_table('tours')
