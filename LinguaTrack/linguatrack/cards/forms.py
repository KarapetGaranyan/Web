from django import forms
from .models import Card

class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['word', 'translation', 'example', 'note', 'difficulty']
        widgets = {
            'word': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите слово на иностранном языке'
            }),
            'translation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите перевод'
            }),
            'example': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Пример использования (необязательно)'
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Примечание (необязательно)'
            }),
            'difficulty': forms.Select(attrs={'class': 'form-select'})
        }

class StudyForm(forms.Form):
    answer = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите перевод',
            'autofocus': True
        }),
        label='Ваш ответ'
    )

class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel файл',
        help_text='Загрузите .xlsx файл с колонками: слово, перевод',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )