from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils.html import strip_tags
from django.conf import settings

from .services.search_engine import OERSearchEngine
from .services.rag import answer_with_rag, parse_citations


class SearchResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    url = serializers.CharField(allow_null=True)
    similarity_score = serializers.FloatField()
    quality_boost = serializers.FloatField()
    final_score = serializers.FloatField()
    match_reason = serializers.CharField()
    snippet = serializers.CharField(allow_blank=True)


class SearchAPIView(APIView):
    """Simple DRF endpoint that returns `OERSearchEngine` results as JSON."""

    def get(self, request, format=None):
        query = request.GET.get('q', '').strip()
        if not query:
            return Response({'results': []})

        try:
            limit = int(request.GET.get('limit', 20))
        except Exception:
            limit = 20

        # Basic filters support: expect a JSON-encoded filters param (optional)
        filters = None
        # TODO: add parsing of filters from request if needed

        engine = OERSearchEngine()
        results = engine.semantic_search(query, filters=filters, limit=limit)

        payload = []
        for r in results:
            snippet = ''
            try:
                snippet = strip_tags(getattr(r.resource, 'description', '') or '')[:300]
            except Exception:
                snippet = ''

            payload.append({
                'id': r.resource.id,
                'title': getattr(r.resource, 'title', ''),
                'url': getattr(r.resource, 'url', ''),
                'similarity_score': float(r.similarity_score),
                'quality_boost': float(r.quality_boost),
                'final_score': float(r.final_score),
                'match_reason': r.match_reason,
                'snippet': snippet,
            })

        serializer = SearchResultSerializer(payload, many=True)
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow anonymous users to ask questions; RAG is public-facing
def rag_answer_view(request):
    """
    RAG endpoint: POST {"query": "..."} to get LLM-synthesized answer with resource citations.
    
    Allows both authenticated and anonymous users (public-facing endpoint).
    
    Request body:
        {
            "query": "string - the user's question",
            "k": "int - optional, max resources to retrieve (default: 5)"
        }
    
    Response:
        {
            "answer": "string - the LLM-generated answer",
            "resource_ids": [1, 2, 3],
            "resources": [
                {
                    "id": 1,
                    "title": "...",
                    "url": "...",
                    "source": "...",
                    "similarity_score": 0.85
                },
                ...
            ]
        }
    """
    query = request.data.get('query', '').strip()
    k = request.data.get('k', 5)
    
    if not query:
        return Response(
            {'error': 'Missing or empty "query" field'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        k = int(k)
        if k < 1 or k > 20:
            k = 5
    except (ValueError, TypeError):
        k = 5
    
    try:
        result = answer_with_rag(query=query, k=k)
        
        # Parse citations in the answer text for client-side rendering
        result['answer_html'] = parse_citations(
            result['answer'],
            result['resource_ids']
        )
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {
                'error': 'RAG answer generation failed',
                'detail': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
