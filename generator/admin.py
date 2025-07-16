# generator/admin.py

from django import forms
from django.contrib import admin
from django.contrib import messages
from .models import Universe, Quest, Question, Option, ScoreCategory, Collectible, Character, Trivia, TriviaQuestion, HomePage, News
from .service import generate_universe, generate_quest, generate_question
from .universe_service import get_generate_universe_prompt, get_main_characters_migrated, generate_universe_assets
from .quest_service import generate_quest_assets
from django.shortcuts import render, redirect
from django.urls import path, reverse
import json
from .admin_views import universe_details, generate_assets_sse, quest_details, generate_quest_assets_sse
from django.http import StreamingHttpResponse, HttpResponseBadRequest

class UniverseAdminForm(forms.ModelForm):
    universe_prompt = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 80}),
        required=True,
        help_text="Enter a detailed description or prompt for the universe you want to generate."
    )

    class Meta:
        model = Universe
        fields = []


class UniverseAdmin(admin.ModelAdmin):
    form = UniverseAdminForm
    list_display = ('universe_name', 'description')
    search_fields = ('universe_name', 'description')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:universe_id>/add_quest/', self.admin_site.admin_view(self.add_quest), name='generator_universe_add_quest'),
            path('<int:universe_id>/confirm_quest/', self.admin_site.admin_view(self.confirm_quest), name='generator_universe_confirm_quest'),
            path('add/', self.admin_site.admin_view(self.add_universe), name='generator_universe_add'),
            path('create/', self.admin_site.admin_view(self.create_universe_sse), name='generator_universe_create'),
            path('<int:universe_id>/details/', self.admin_site.admin_view(self.universe_details), name='generator_universe_details'),
            path('<int:universe_id>/generate_assets/', self.admin_site.admin_view(self.generate_assets_sse), name='generator_universe_generate_assets'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return self.universe_details(request, object_id)


    def confirm_universe(self, request):
        if request.method == 'POST':
            universe_prompt = request.session.get('universe_prompt')
            if universe_prompt:
                try:
                    universe_id = generate_universe(universe_prompt)
                except Exception as e:
                    messages.error(
                        request, f"Failed to generate universe: {str(e)}")
                    return redirect('admin:generator_universe_add')

                del request.session['universe_prompt']
                return redirect('admin:generator_universe_details', universe_id=universe_id)
        return redirect('admin:generator_universe_add')

    def generate_claude_prompt(self, user_prompt):
        # This method should return the prompt that will be sent to Claude
        return get_generate_universe_prompt(user_prompt)

    def generate_assets_sse(self, request, universe_id):
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

    def universe_details(self, request, universe_id):
        universe = Universe.objects.get(id=universe_id)
        generate_assets_url = reverse('admin:generator_universe_generate_assets', args=[universe_id])
        add_quest_url = reverse('admin:generator_universe_add_quest', args=[universe_id])
        main_characters = get_main_characters_migrated(universe_id)
        all_assets_generated = universe.thumbnail and all(character.get('image') for character in main_characters)

        return render(request, 'admin/generator/universe/details.html', {
            'universe': universe, 
            'characters': main_characters,
            'generate_assets_url': generate_assets_url,
            'add_quest_url': add_quest_url,
            'all_assets_generated': all_assets_generated
        })

    def add_quest(self, request, universe_id):
        universe = Universe.objects.get(id=universe_id)
        if request.method == 'POST':
            quest_prompt = request.POST.get('quest_prompt')
            max_questions = int(request.POST.get('max_questions', 9))
            request.session['quest_prompt'] = quest_prompt
            request.session['max_questions'] = max_questions
            return redirect('admin:generator_universe_confirm_quest', universe_id=universe_id)
        return render(request, 'admin/generator/quest/add_form.html', {'universe': universe})

    def confirm_quest(self, request, universe_id):
        universe = Universe.objects.get(id=universe_id)
        if request.method == 'POST':
            quest_prompt = request.session.get('quest_prompt')
            max_questions = request.session.get('max_questions', 9)
            if quest_prompt:
                try:
                    quest_id = generate_quest(universe_id, quest_prompt, max_questions)
                    del request.session['quest_prompt']
                    del request.session['max_questions']
                    self.message_user(request, "Quest generated successfully!", messages.SUCCESS)
                    return redirect('admin:generator_quest_change', object_id=quest_id)
                except Exception as e:
                    self.message_user(request, f"Failed to generate quest: {str(e)}", messages.ERROR)
            return redirect('admin:generator_universe_add_quest', universe_id=universe_id)
        quest_prompt = request.session.get('quest_prompt')
        max_questions = request.session.get('max_questions', 9)
        return render(request, 'admin/generator/quest/confirm.html', {
            'universe': universe,
            'quest_prompt': quest_prompt,
            'max_questions': max_questions
        })

    def generate_assets(self, request, universe_id):
        try:
            generate_universe_assets(universe_id)
            self.message_user(request, "Assets generated successfully!", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error generating assets: {str(e)}", messages.ERROR)
        return redirect('admin:generator_universe_details', universe_id=universe_id)


    def add_universe(self, request):
        if request.method == 'POST':
            form = self.form(request.POST)
            if form.is_valid():
                universe_prompt = form.cleaned_data['universe_prompt']
                request.session['universe_prompt'] = universe_prompt
                return render(request, 'admin/generator/universe/add_form.html', {'form': form, 'show_sse': True})
        else:
            form = self.form()

        return render(request, 'admin/generator/universe/add_form.html', {'form': form, 'show_sse': False})

    def create_universe_sse(self, request):
        universe_prompt = request.session.get('universe_prompt')
        if not universe_prompt:
            return HttpResponseBadRequest("No universe prompt found in session")

        def event_stream():
            try:
                for status in generate_universe(universe_prompt):
                    yield f"data: {json.dumps(status)}\n\n"
                    if 'universe_id' in status:
                        yield f"data: {json.dumps({'status': 'completed', 'universe_id': status['universe_id']})}\n\n"
                        break
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

class QuestAdminForm(forms.ModelForm):
    max_questions = forms.IntegerField(min_value=1, max_value=20, initial=9,
                                       help_text="Maximum number of questions for this quest")

    class Meta:
        model = Quest
        fields = ['universe']


class QuestAdmin(admin.ModelAdmin):
    list_display = ('quest_name', 'universe', 'description')
    list_filter = ('universe',)
    search_fields = ('quest_name', 'description')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:quest_id>/details/', self.admin_site.admin_view(quest_details), name='generator_quest_details'),
            path('<int:quest_id>/generate_assets/', self.admin_site.admin_view(generate_quest_assets_sse), name='generator_quest_generate_assets'),
            path('<int:quest_id>/generate_question/', self.admin_site.admin_view(self.generate_question_sse), name='generator_quest_generate_question'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return self.admin_site.admin_view(quest_details)(request, object_id)

    def generate_question_sse(self, request, quest_id):
        def event_stream():
            try:
                quest = Quest.objects.get(id=quest_id)
                yield f"data: {json.dumps({'status': 'Generating question'})}\n\n"
                question_id = generate_question(
                    quest_id=quest.id, 
                    prev_option_id=None,
                    num_of_options=2
                    )
                if question_id:
                    yield f"data: {json.dumps({'status': 'Question generated successfully'})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'Quest has reached max questions'})}\n\n"
                    
                yield f"data: {json.dumps({'status': 'completed', 'question_id': question_id})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    

class QuestionAdminForm(forms.ModelForm):
    num_options = forms.IntegerField(min_value=2, max_value=5, initial=2,
                                     help_text="Number of options for this question")

    class Meta:
        model = Question
        fields = ['quest']


admin.site.register(Universe, UniverseAdmin)
admin.site.register(Quest, QuestAdmin)
admin.site.register(Option)
admin.site.register(ScoreCategory)
admin.site.register(Collectible)
admin.site.register(Character)

admin.site.register(Trivia)
admin.site.register(TriviaQuestion)
admin.site.register(HomePage)
admin.site.register(News)