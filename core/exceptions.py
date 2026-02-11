from rest_framework.views import exception_handler

def core_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        message = "Terjadi kesalahan pada sistem."
        data = response.data

        if isinstance(data, dict):
            if "detail" in data:
                message = data.pop("detail")
            else:
                message = "Validasi gagal."
        elif isinstance(data, list):
            message = data[0]

        response.data = {
            "status": "error",
            "message": str(message),
            "data": data if data else None
        }
    return response