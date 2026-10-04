"""Add uploaded file hashes to databases created with the initial migration."""
from alembic import op
import sqlalchemy as sa
revision = '6a4f2e8b91d0'
down_revision = '5ff95bda6ec8'
branch_labels = None
depends_on = None

def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('uploaded_files')}
    if 'file_hash' not in columns:
        op.add_column('uploaded_files', sa.Column('file_hash', sa.String(), nullable=True))
    indexes = {i['name'] for i in sa.inspect(op.get_bind()).get_indexes('uploaded_files')}
    if 'ix_uploaded_files_file_hash' not in indexes:
        op.create_index('ix_uploaded_files_file_hash', 'uploaded_files', ['file_hash'])

def downgrade():
    op.drop_index('ix_uploaded_files_file_hash', table_name='uploaded_files')
    op.drop_column('uploaded_files', 'file_hash')
