from django.apps import AppConfig
from django.db import connection


class WritersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.writers"
    label = "writers"

    def ready(self):
        try:
            with connection.cursor() as cursor:
                # PostgreSQL safe column add
                cursor.execute("""
                    DO $$ 
                    BEGIN 
                        BEGIN
                            ALTER TABLE writer_profiles ADD COLUMN gender VARCHAR(10) DEFAULT 'OTHER';
                        EXCEPTION
                            WHEN duplicate_column THEN NULL;
                        END;
                    END $$;
                """)
        except Exception:
            try:
                # SQLite fallback
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE writer_profiles ADD COLUMN gender VARCHAR(10) DEFAULT 'OTHER';")
            except Exception:
                pass
