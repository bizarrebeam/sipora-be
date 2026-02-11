from rest_framework.renderers import JSONRenderer

class CoreJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        # Jika data sudah diformat standar (oleh exception handler), langsung render
        if isinstance(data, dict) and 'status' in data and 'message' in data and 'data' in data:
            return super().render(data, accepted_media_type, renderer_context)

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