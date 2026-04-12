"""Django admin configuration for the konsultasi application.

Registers admin pages for:
- JadwalKonsultasi: Counseling availability slots created by guidance teachers.
- BookingKonsultasi: Student bookings for available counseling slots.

Includes:
- List views with key fields.
- Sidebar filters for faster navigation.
- Search by related user fields.
- Read-only identifiers and timestamps.
"""

from django.contrib import admin
from .models import JadwalKonsultasi, BookingKonsultasi


@admin.register(JadwalKonsultasi)
class JadwalKonsultasiAdmin(admin.ModelAdmin):
    """Admin configuration for JadwalKonsultasi records."""
    # Columns displayed in the admin changelist
    list_display = ('id', 'guru_bk', 'tanggal', 'waktu_mulai', 'waktu_selesai', 'status', 'dibuat_pada')

    # Right sidebar filters
    list_filter = ('status', 'tanggal')

    # Search box fields (including related user fields)
    search_fields = ('guru_bk__nama_lengkap', 'guru_bk__username')

    # Immutable fields shown as read-only
    readonly_fields = ('id', 'dibuat_pada', 'updated_at')



@admin.register(BookingKonsultasi)
class BookingKonsultasiAdmin(admin.ModelAdmin):
    """Admin configuration for BookingKonsultasi records."""
    # Columns displayed in the admin changelist
    list_display = ('id', 'siswa', 'jadwal', 'status', 'dibuat_pada')

    # Right sidebar filters
    list_filter = ('status', 'dibuat_pada')

    # Search box fields (including related user fields)
    search_fields = ('siswa__nama_lengkap', 'siswa__username')

    # Immutable fields shown as read-only
    readonly_fields = ('id', 'dibuat_pada', 'updated_at')