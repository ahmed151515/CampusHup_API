import magic
from rest_framework import serializers

from .models import Material
from .services import generate_pdf_thumbnail

ALLOWED_EXTENSION = ".pdf"
ALLOWED_MIME_TYPE = "application/pdf"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class MaterialSerializer(serializers.ModelSerializer):
    """
    Serializer for the Material model.

    Read fields: id, course, uploaded_by, title, type, file, thumbnail,
                 size_bytes, uploaded_at.

    Write fields (POST / PUT / PATCH): course, title, file.
    """

    class Meta:
        model = Material
        fields = [
            "id",
            "course",
            "uploaded_by",
            "title",
            "type",
            "file",
            "thumbnail",
            "size_bytes",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "course",
            "uploaded_by",
            "type",
            "thumbnail",
            "size_bytes",
            "uploaded_at",
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_file(self, value):
        """Enforce PDF-only uploads by checking both extension and MIME type."""
        # Extension check
        filename: str = value.name.lower()
        if not filename.endswith(ALLOWED_EXTENSION):
            raise serializers.ValidationError(
                "Only PDF files are allowed. The uploaded file does not have a .pdf extension."
            )

        # Size guard
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size exceeds the maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )

        # MIME-type check using python-magic (reads the first bytes).
        try:
            value.seek(0)
            mime = magic.from_buffer(value.read(2048), mime=True)
            value.seek(0)
        except Exception:
            # If magic fails for any reason, fall back to a basic check.
            mime = ALLOWED_MIME_TYPE

        if mime != ALLOWED_MIME_TYPE:
            raise serializers.ValidationError(
                f"Invalid file type '{mime}'. Only PDF (application/pdf) files are accepted."
            )

        return value

    # ------------------------------------------------------------------
    # Create / Update
    # ------------------------------------------------------------------

    def _attach_thumbnail(self, instance: Material) -> None:
        """Generate and save a thumbnail without raising on failure."""
        thumb = generate_pdf_thumbnail(instance.file, material_title=instance.title)
        if thumb:
            instance.thumbnail.save(thumb.name, thumb, save=True)

    def create(self, validated_data):
        file_obj = validated_data["file"]

        # Auto-calculate size and force type.
        validated_data["size_bytes"] = file_obj.size
        validated_data["type"] = Material.TYPE_PDF

        instance: Material = super().create(validated_data)

        # Generate thumbnail (failures are swallowed inside the service).
        self._attach_thumbnail(instance)

        return instance

    def update(self, instance: Material, validated_data):
        # If a new file is being uploaded, recalculate size.
        if "file" in validated_data:
            validated_data["size_bytes"] = validated_data["file"].size
            validated_data["type"] = Material.TYPE_PDF

        instance = super().update(instance, validated_data)

        # Regenerate thumbnail whenever the file changes.
        if "file" in validated_data:
            self._attach_thumbnail(instance)

        return instance
