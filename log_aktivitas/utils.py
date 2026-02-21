def catat_log(user, aksi, deskripsi, modul, ip_address=None):
    """
    Globally reusable generic logging function for Whistleblower System Audit Trails.
    This function should be called within views / services anytime a tracked model is created/modified.
    """
    from .models import LogAktivitas
    
    try:
        LogAktivitas.objects.create(
            pengguna=user,
            aksi=aksi,
            deskripsi=deskripsi,
            modul=modul,
            ip_address=ip_address
        )
    except Exception as e:
        # Failsafe non-blocking execution in case log DB throws exception
        print(f"Log Audit failed to save for {aksi}: {str(e)}")
