from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.conf import settings
import json

from .models import Universe, Quest, ScoreCategory, Question
from .universe_service import generate_universe_assets, get_main_characters_migrated
from .quest_service import generate_quest_assets
from .universe_service import generate_universe

FRONTEND_URL = settings.FRONTEND_URL


@staff_member_required
def universe_details(request, universe_id):
    universe = get_object_or_404(Universe, id=universe_id)
    main_characters = get_main_characters_migrated(universe_id)
    generate_assets_url = reverse('admin:generator_universe_generate_assets', args=[universe_id])
    return render(request, 'admin/generator/universe/details.html', {
        'universe': universe, 
        'characters': main_characters,
        'generate_assets_url': generate_assets_url
    })

@staff_member_required
def generate_assets_sse(request, universe_id):
    def event_stream():
        try:
            for status in generate_universe_assets(universe_id):
                yield f"data: {json.dumps(status)}\n\n"
            yield "data: {\"status\": \"completed\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response



@staff_member_required
def generate_quest_assets_sse(request, quest_id):
    def event_stream():
        try:
            for status in generate_quest_assets(quest_id):
                yield f"data: {json.dumps(status)}\n\n"
            yield "data: {\"status\": \"completed\"}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@staff_member_required
def create_universe_sse(request):
    if request.method == 'POST':
        universe_prompt = request.POST.get('universe_prompt')
        
        def event_stream():
            try:
                for status in generate_universe(universe_prompt):
                    yield f"data: {json.dumps(status)}\n\n"
                    if 'universe_id' in status:
                        # If we have a universe_id, the creation is complete
                        yield f"data: {json.dumps({'status': 'completed', 'universe_id': status['universe_id']})}\n\n"
                        break
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    
    return render(request, 'admin/generator/universe/create.html')

@staff_member_required
def quest_details(request, quest_id):
    quest = get_object_or_404(Quest, id=quest_id)
    score_categories = ScoreCategory.objects.filter(quest=quest)
    generate_assets_url = reverse('admin:generator_quest_generate_assets', args=[quest_id])
    generate_question_url = reverse('admin:generator_quest_generate_question', args=[quest_id])
    
    # Check if there are any questions for this quest
    has_questions = Question.objects.filter(quest=quest).exists()
    
    # Get the frontend URL from settings (you'll need to add this to your settings.py)
    
    return render(request, 'admin/generator/quest/details.html', {
        'quest': quest,
        'main_characters': json.loads(quest.main_characters),
        'story_outline': json.loads(quest.story_outline),
        'score_categories': score_categories,
        'generate_assets_url': generate_assets_url,
        'generate_question_url': generate_question_url,
        'has_questions': has_questions,
        'frontend_url': FRONTEND_URL,
    })
