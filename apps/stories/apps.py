from django.apps import AppConfig
from django.db import connection


class StoriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stories"
    label = "stories"

    def ready(self):
        try:
            with connection.cursor() as cursor:
                # PostgreSQL safe column add
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        BEGIN
                            ALTER TABLE stories ADD COLUMN unauthenticated_like_attempts BIGINT DEFAULT 0;
                        EXCEPTION
                            WHEN duplicate_column THEN NULL;
                        END;
                    END $$;
                """)
        except Exception:
            try:
                # SQLite fallback
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE stories ADD COLUMN unauthenticated_like_attempts BIGINT DEFAULT 0;")
            except Exception:
                pass
