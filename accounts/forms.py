from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'toss-input w-100',
            'placeholder': '아이디를 입력하세요',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'toss-input w-100',
            'placeholder': '비밀번호를 입력하세요',
        }),
    )


class UserForm(forms.ModelForm):
    password1 = forms.CharField(
        label='비밀번호',
        widget=forms.PasswordInput(attrs={'class': 'toss-input w-100'}),
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'company_name', 'first_name', 'phone', 'role', 'parent', 'is_active']
        labels = {
            'username': '아이디',
            'first_name': '이름/직급',
        }
        help_texts = {
            'phone': '연락 가능한 담당자 번호 작성 해주세요 *진행 누락 시 다이렉트 넘버',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'toss-input w-100'}),
            'company_name': forms.TextInput(attrs={'class': 'toss-input w-100'}),
            'first_name': forms.TextInput(attrs={'class': 'toss-input w-100'}),
            'phone': forms.TextInput(attrs={'class': 'toss-input w-100', 'placeholder': '연락 가능한 번호'}),
            'role': forms.Select(attrs={'class': 'toss-select w-100'}),
            'parent': forms.Select(attrs={'class': 'toss-select w-100'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        self.order_fields(['username', 'password1', 'company_name', 'first_name', 'phone', 'role', 'parent', 'is_active'])
        if self.request_user:
            if self.request_user.is_manager:
                self.fields['role'].choices = [('agency', '대행사')]
                self.fields.pop('parent')
            elif self.request_user.is_agency:
                self.fields['role'].choices = [('seller', '셀러')]
                self.fields.pop('parent')
        # parent 필드: 역할별 그룹 + 가나다순
        if 'parent' in self.fields:
            role_order = ['admin', 'manager', 'agency']
            role_labels = dict(User.Role.choices)
            users = User.objects.filter(is_active=True).order_by('company_name', 'username')
            grouped = {r: [] for r in role_order}
            for u in users:
                if u.role in grouped:
                    label = u.company_name or u.username
                    grouped[u.role].append((u.pk, label))
            choices = [('', '없음')]
            for role in role_order:
                if grouped[role]:
                    choices.append((role_labels.get(role, role), grouped[role]))
            self.fields['parent'].choices = choices
        if self.instance and self.instance.pk:
            self.fields['password1'].help_text = '변경시에만 입력'
            self.fields['username'].disabled = True

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if not self.instance.pk and not password:
            raise forms.ValidationError('신규 계정은 비밀번호를 반드시 입력해야 합니다.')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('password1')
        if pw:
            user.set_password(pw)
        if self.request_user and not self.instance.pk:
            if self.request_user.is_manager:
                user.parent = self.request_user
                user.role = User.Role.AGENCY
            elif self.request_user.is_agency:
                user.parent = self.request_user
                user.role = User.Role.SELLER
        if commit:
            user.save()
        return user
