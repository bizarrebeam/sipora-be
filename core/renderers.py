from rest_framework.renderers import JSONRenderer
import re

# Map common DRF English default errors to Bahasa Indonesia
_ERROR_TRANSLATIONS = {
    'This field may not be blank.': 'Kolom ini tidak boleh kosong.',
    'This field is required.': 'Kolom ini wajib diisi.',
    'This field may not be null.': 'Kolom ini tidak boleh kosong.',
    'A valid email address is required.': 'Alamat email tidak valid.',
    'Enter a valid email address.': 'Masukkan alamat email yang valid.',
    'A valid integer is required.': 'Masukkan angka yang valid.',
    'A valid number is required.': 'Masukkan angka yang valid.',
    'This password is too short.': 'Password terlalu pendek.',
    'This password is too common.': 'Password terlalu umum.',
    'This password is entirely numeric.': 'Password tidak boleh hanya berisi angka.',
    'The two password fields didn\'t match.': 'Password dan konfirmasi password tidak cocok.',
    'Unable to log in with provided credentials.': 'Kredensial tidak valid.',
    'User account is disabled.': 'Akun pengguna dinonaktifkan.',
    'Not found.': 'Data tidak ditemukan.',
    'Authentication credentials were not provided.': 'Autentikasi diperlukan.',
    'Given token not valid for any token type': 'Token tidak valid.',
    'Token is invalid or expired': 'Token tidak valid atau sudah kedaluwarsa.',
    'No active account found with the given credentials': 'Kredensial tidak valid.',
}

# Regex for: "Ensure this field has at least X characters (it has Y)."
_MIN_LENGTH_RE = re.compile(r'Ensure this (?:field|value) has at least (\d+) characters?')

def _translate_message(msg):
    """Translate a single error message from English DRF defaults to Indonesian."""
    s = str(msg)
    if s in _ERROR_TRANSLATIONS:
        return _ERROR_TRANSLATIONS[s]
    m = _MIN_LENGTH_RE.match(s)
    if m:
        return f'Kolom ini minimal {m.group(1)} karakter.'
    return s


class CoreJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get('response')

        # Jika data sudah diformat standar (oleh exception handler), langsung render
        if isinstance(data, dict) and 'status' in data and 'message' in data and 'data' in data:
            # Still translate the message in case it's English
            data['message'] = _translate_message(data['message'])
            return super().render(data, accepted_media_type, renderer_context)

        # Cek apakah response error (4xx / 5xx)
        is_error = response and response.status_code >= 400

        if is_error:
            # Format error: ambil pesan dari field-level errors
            error_message = "Terjadi kesalahan."
            if isinstance(data, dict):
                # Flatten field errors menjadi pesan yang mudah dibaca
                messages = []
                for key, value in data.items():
                    if key == 'non_field_errors':
                        msgs = value if isinstance(value, list) else [value]
                        messages.extend([_translate_message(m) for m in msgs])
                    elif key == 'detail':
                        messages.append(_translate_message(value))
                    else:
                        msgs = value if isinstance(value, list) else [value]
                        for m in msgs:
                            messages.append(_translate_message(m))
                if messages:
                    error_message = messages[0]  # Tampilkan error pertama sebagai message utama

            formatted_response = {
                "status": "error",
                "message": error_message,
                "data": data if data else None
            }
        else:
            # Standarisasi format untuk response sukses
            formatted_response = {
                "status": "success",
                "message": "Permintaan berhasil diproses.",
                "data": data
            }

            # Ekstrak pesan kustom jika view mengirimkan key 'message'
            if isinstance(data, dict):
                if "message" in data:
                    formatted_response["message"] = data.pop("message")
                if "data" in data:
                    formatted_response["data"] = data["data"]

        return super().render(formatted_response, accepted_media_type, renderer_context)