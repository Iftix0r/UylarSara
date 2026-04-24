from django import forms
from .models import Property

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['title', 'description', 'price', 'location', 'rooms', 'area', 'category', 'property_type', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Sarlavha...'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Tavsif...'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Narxi ($)...'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Manzil...'}),
            'rooms': forms.NumberInput(attrs={'class': 'form-input'}),
            'area': forms.NumberInput(attrs={'class': 'form-input'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'property_type': forms.Select(attrs={'class': 'form-input'}),
            'image': forms.FileInput(attrs={'class': 'form-input'}),
        }
