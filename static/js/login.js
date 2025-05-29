function togglePassword() {
            const passwordInput = document.getElementById('password');
            const toggleIcon = document.getElementById('toggleIcon');

            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                toggleIcon.textContent = '👁️';
            }
        }

        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('errorMessage');
            const successDiv = document.getElementById('successMessage');
            const btnText = document.getElementById('btnText');
            const loading = document.getElementById('loading');

            // Reset messages
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';

            // Show loading
            btnText.style.display = 'none';
            loading.style.display = 'block';

            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok) {
                    // Save token
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.user));

                    // Show success message
                    successDiv.textContent = 'Успешный вход! Перенаправление...';
                    successDiv.style.display = 'block';

                    // Redirect to dashboard
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    errorDiv.textContent = data.detail || 'Неверное имя пользователя или пароль';
                    errorDiv.style.display = 'block';

                    // Hide loading
                    btnText.style.display = 'block';
                    loading.style.display = 'none';
                }
            } catch (error) {
                errorDiv.textContent = 'Ошибка подключения к серверу';
                errorDiv.style.display = 'block';

                // Hide loading
                btnText.style.display = 'block';
                loading.style.display = 'none';
            }
        });

        // Auto-focus on username field
        window.onload = () => {
            document.getElementById('username').focus();
        };