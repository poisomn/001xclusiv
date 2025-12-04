from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegistrationForm

class RegisterView(View):
    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'accounts/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:home')
        return render(request, 'accounts/register.html', {'form': form})

class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        orders = request.user.orders.all()
        return render(request, 'accounts/profile.html', {'orders': orders})
