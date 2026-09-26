"""add authentication and rbac

Revision ID: ebea9a1ed93e
Revises: 5ea0d8ad73d0
Create Date: 2026-09-26 00:00:00.000000

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ebea9a1ed93e'
down_revision: Union[str, None] = '5ea0d8ad73d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ROLES = [
    (1, "Admin", "Full access to every folder, document and conversation"),
    (2, "HR", "Access to folders shared with the HR role"),
    (3, "Engineering", "Access to folders shared with the Engineering role"),
]


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)

    op.create_table(
        'folder_roles',
        sa.Column('folder_id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('folder_id', 'role_id'),
    )

    op.create_table(
        'document_permissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'role_id', name='uq_document_permissions'),
    )
    op.create_index(
        op.f('ix_document_permissions_document_id'),
        'document_permissions',
        ['document_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_document_permissions_role_id'),
        'document_permissions',
        ['role_id'],
        unique=False,
    )

    with op.batch_alter_table('chat_conversations') as batch_op:
        batch_op.add_column(
            sa.Column(
                'user_id',
                sa.String(length=36),
                sa.ForeignKey(
                    'users.id',
                    ondelete='CASCADE',
                    name='fk_chat_conversations_user_id',
                ),
                nullable=True,
            )
        )
    op.create_index(
        op.f('ix_chat_conversations_user_id'),
        'chat_conversations',
        ['user_id'],
        unique=False,
    )

    # seed the default roles
    roles = sa.table(
        'roles',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
    )
    op.bulk_insert(
        roles,
        [
            {"id": role_id, "name": name, "description": description}
            for role_id, name, description in DEFAULT_ROLES
        ],
    )

    # create the shared General folder, allowed for every role
    general_id = str(uuid.uuid4())
    folders = sa.table(
        'folders',
        sa.column('id', sa.String),
        sa.column('name', sa.String),
    )
    op.bulk_insert(folders, [{"id": general_id, "name": "General"}])

    folder_roles = sa.table(
        'folder_roles',
        sa.column('folder_id', sa.String),
        sa.column('role_id', sa.Integer),
    )
    op.bulk_insert(
        folder_roles,
        [
            {"folder_id": general_id, "role_id": role_id}
            for role_id, _name, _description in DEFAULT_ROLES
        ],
    )

    # every document belongs to a folder: backfill existing rows
    op.execute(
        sa.text("UPDATE documents SET folder_id = :general_id WHERE folder_id IS NULL"
                ).bindparams(general_id=general_id)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE documents SET folder_id = NULL WHERE folder_id IN "
            "(SELECT id FROM folders WHERE name = 'General')"
        )
    )
    op.drop_index(op.f('ix_chat_conversations_user_id'), table_name='chat_conversations')
    with op.batch_alter_table('chat_conversations') as batch_op:
        batch_op.drop_column('user_id')
    op.drop_index(
        op.f('ix_document_permissions_role_id'),
        table_name='document_permissions',
    )
    op.drop_index(
        op.f('ix_document_permissions_document_id'),
        table_name='document_permissions',
    )
    op.drop_table('document_permissions')
    op.drop_table('folder_roles')
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_table('roles')
