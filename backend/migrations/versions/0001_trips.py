"""Initial local-feature schema; no browser access to raw tables or checkpoints."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("trips",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("idempotency_key", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("model_metadata", sa.JSON(), nullable=False),
        sa.Column("current_node", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("resume_count", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key"))
    op.create_index("ix_trips_owner_created", "trips", ["user_id", "created_at", "id"])
    op.create_index("ix_trips_one_active", "trips", ["user_id"], unique=True,
                    postgresql_where=sa.text("status IN ('queued', 'running')"),
                    sqlite_where=sa.text("status IN ('queued', 'running')"))
    op.create_table("trip_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_trip_runs_trip_id", "trip_runs", ["trip_id"])
    op.create_table("trip_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_trip_events_replay", "trip_events", ["trip_id", "id"])
    op.create_table("daily_usage",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("day", sa.String(10), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE SCHEMA IF NOT EXISTS planner_internal")
        op.execute("REVOKE ALL ON SCHEMA planner_internal FROM PUBLIC")
        for table in ("trips", "trip_runs", "trip_events", "daily_usage"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # No anon/authenticated policies: only the trusted backend DB owner accesses data.


def downgrade():
    for name in ("trip_events", "trip_runs", "daily_usage", "trips"):
        op.drop_table(name)
    # Do not drop planner_internal implicitly: it may hold recoverable checkpoints.
