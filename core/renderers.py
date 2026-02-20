from rest_framework.renderers import JSONRenderer

class CoreJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get('response')

        # Jika data sudah diformat standar (oleh exception handler), langsung render
        if isinstance(data, dict) and 'status' in data and 'message' in data and 'data' in data:
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
                        messages.extend([str(m) for m in msgs])
                    elif key == 'detail':
                        messages.append(str(value))
                    else:
                        msgs = value if isinstance(value, list) else [value]
                        for m in msgs:
                            messages.append(str(m))
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