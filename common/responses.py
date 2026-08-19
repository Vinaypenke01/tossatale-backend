"""
Common — Standard API Response Helpers
All API responses follow the format defined in §34.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Standard success response.
    {
        "success": true,
        "message": "...",
        "data": {}
    }
    """
    return Response(
        {
            "success": True,
            "message": message,
            "data": data if data is not None else {},
        },
        status=status_code,
    )


def created_response(data=None, message="Created successfully"):
    return success_response(data=data, message=message, status_code=status.HTTP_201_CREATED)


def no_content_response():
    return Response(status=status.HTTP_204_NO_CONTENT)


def paginated_response(serializer_data, paginator, message="Retrieved successfully"):
    """
    Standard paginated response per §34.
    {
        "success": true,
        "message": "...",
        "data": {
            "count": ...,
            "next": ...,
            "previous": ...,
            "page": ...,
            "page_size": ...,
            "results": [...]
        }
    }
    """
    return Response(
        {
            "success": True,
            "message": message,
            "data": serializer_data,
        },
        status=status.HTTP_200_OK,
    )
