/* =====================================================
   Rent&Go — auth.js

   Authentication page driver: Phone OTP, Google sign-in,
   Email verification + email-only signup.

   API endpoints consumed:
     Phone:  POST /api/otp/send/  /verify/  /signup/
     Email:  POST /api/email/verify/send/  /confirm/
             POST /api/auth/email-signup/
     Google: POST /api/auth/google/
===================================================== */

(function () {
    'use strict';

    var phone       = '';
    var purpose     = 'login';
    var timer       = null;
    var timerLeft   = 0;
    var emailAddr   = '';

    function el(id) { return document.getElementById(id); }

    function csrfToken() {
        var input = document.querySelector('input[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    function apiFetch(url, data) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify(data),
        }).then(function (res) {
            return res.json().then(function (body) {
                return { status: res.status, body: body };
            });
        });
    }

    /* -------------------------------------------------
            Shared panel / hint helpers
    ------------------------------------------------- */

    function showPanel(panelId) {
        document.querySelectorAll('.auth-panel').forEach(function (panel) {
            panel.classList.toggle('active', panel.id === panelId);
        });
    }

    function setHint(id, text, isError) {
        var node = el(id);
        if (!node) return;
        node.textContent = text || '';
        node.classList.toggle('error', !!isError);
    }
    function clearHint(id) { setHint(id, ''); }

    function disableBtn(btn, label) {
        btn.disabled = true;
        btn.querySelector('span').textContent = label;
    }
    function enableBtn(btn, label) {
        btn.disabled = false;
        btn.querySelector('span').textContent = label;
    }

    /* -------------------------------------------------
            Shared 6-digit OTP box builder
    ------------------------------------------------- */

    function buildOtpInputs(containerId, onComplete) {
        var container = el(containerId);
        if (!container) return;
        container.innerHTML = '';

        for (var i = 0; i < 6; i++) {
            var input = document.createElement('input');
            input.type = 'text';
            input.maxLength = 1;
            input.setAttribute('inputmode', 'numeric');
            input.setAttribute('pattern', '[0-9]');
            input.className = 'otp-box';
            input.dataset.index = i;

            input.addEventListener('input', function () {
                this.value = this.value.replace(/\D/g, '');
                if (this.value && this.nextElementSibling) {
                    this.nextElementSibling.focus();
                }
                if (onComplete) onComplete(getOtpValue(containerId));
            });
            input.addEventListener('keydown', function (ev) {
                if (ev.key === 'Backspace' && !this.value && this.previousElementSibling) {
                    this.previousElementSibling.focus();
                }
            });
            input.addEventListener('paste', function (ev) {
                ev.preventDefault();
                var pasted = (ev.clipboardData || window.clipboardData)
                    .getData('text').replace(/\D/g, '').slice(0, 6);
                var boxes = container.querySelectorAll('.otp-box');
                for (var k = 0; k < pasted.length; k++) {
                    boxes[k].value = pasted[k];
                }
                if (pasted.length === 6) boxes[5].focus();
                if (onComplete) onComplete(getOtpValue(containerId));
            });
            container.appendChild(input);
        }
    }

    function getOtpValue(containerId) {
        var value = '';
        el(containerId).querySelectorAll('.otp-box').forEach(function (box) {
            value += box.value;
        });
        return value;
    }

    function focusFirstBox(containerId) {
        var first = el(containerId).querySelector('.otp-box');
        if (first) first.focus();
    }

    /* -------------------------------------------------
            Shared timer (resend countdown)
    ------------------------------------------------- */

    function startResendCountdown(seconds, timerId, timerTextId, btnId) {
        clearInterval(timer);
        timerLeft = seconds;
        var btn = el(btnId);
        var text = el(timerTextId);
        if (btn) btn.disabled = true;

        function tick() {
            if (text) text.textContent = timerLeft;
            if (timerLeft <= 0) {
                clearInterval(timer);
                if (btn) btn.disabled = false;
                if (text) text.textContent = 'now';
                return;
            }
            timerLeft--;
        }
        tick();
        timer = setInterval(tick, 1000);
    }

    /* -------------------------------------------------
            In-app code display (dev fallback)
    ------------------------------------------------- */

    function showInAppCode(containerId, code) {
        var box = el(containerId);
        var val = el(containerId + 'Value');
        if (!box || !val || !code) return;
        val.textContent = code;
        box.style.display = 'block';
    }
    function hideInAppCode(containerId) {
        var box = el(containerId);
        if (box) box.style.display = 'none';
    }

    /* ====================================================
        PHONE OTP FLOW
    ==================================================== */

    function onSendOtp(ev) {
        ev.preventDefault();
        var phoneInput = el('otpPhone');
        var raw = phoneInput.value.replace(/\D/g, '');
        if (raw.length !== 10) {
            setHint('phoneHint', 'Please enter a valid 10-digit mobile number.', true);
            return;
        }

        clearHint('phoneHint');
        disableBtn(el('sendOtpBtn'), 'Sending OTP…');

        apiFetch('/api/otp/send/', { phone: raw, purpose: purpose }).then(function (res) {
            enableBtn(el('sendOtpBtn'), 'Send OTP');
            if (res.status === 429 && res.body.cooldown) {
                setHint('phoneHint', res.body.error, true);
                startResendCountdown(res.body.cooldown, 'timer', 'timerText', 'resendOtpBtn');
                return;
            }
            if (!res.body.ok) {
                setHint('phoneHint', res.body.error || 'Failed to send OTP.', true);
                return;
            }

            phone = raw;
            if (res.body.delivered_sms) {
                hideInAppCode('inappOtp');
                el('otpTo').textContent = 'OTP sent by SMS to +91' +
                    raw.slice(0, 2) + '******' + raw.slice(-2) + '.';
                setHint('otpHint', 'Check your phone for the SMS with your OTP.');
            } else {
                showInAppCode('inappOtp', res.body.otp || '');
                el('otpTo').textContent = 'OTP sent to +91' +
                    raw.slice(0, 2) + '******' + raw.slice(-2) + '.';
                clearHint('otpHint');
            }
            buildOtpInputs('otpInputs', function () {
                var btn = el('verifyOtpBtn');
                var v = getOtpValue('otpInputs');
                btn.querySelector('span').textContent =
                    v.length === 6 ? 'Verify & Continue' : 'Enter the 6-digit OTP';
            });
            showPanel('stepOtp');
            focusFirstBox('otpInputs');
            startResendCountdown(60, 'timer', 'timerText', 'resendOtpBtn');
        });
    }

    function onVerifyOtp(ev) {
        ev.preventDefault();
        var otp = getOtpValue('otpInputs');
        if (otp.length !== 6) {
            setHint('otpHint', 'Please enter all 6 digits.', true);
            return;
        }

        clearHint('otpHint');
        disableBtn(el('verifyOtpBtn'), 'Verifying…');

        apiFetch('/api/otp/verify/', { phone: phone, otp: otp, purpose: purpose }).then(function (res) {
            enableBtn(el('verifyOtpBtn'), 'Verify & Continue');
            if (!res.body.ok) {
                setHint('otpHint', res.body.error || 'Verification failed.', true);
                return;
            }

            if (res.body.new_user) {
                if (purpose !== 'signup') {
                    purpose = 'signup';
                    el('otpTo').textContent = '+91' + phone.slice(0, 2) + '******' +
                        phone.slice(-2) + ' is not registered yet.';
                } else {
                    el('otpTo').textContent = "Great! Let's create your account.";
                }
                showPanel('stepSignup');
                return;
            }

            finishSuccess('Welcome back!', 'You have been signed in successfully.');
        });
    }

    function onResendOtp(ev) {
        ev.preventDefault();
        startResendCountdown(60, 'timer', 'timerText', 'resendOtpBtn');
        apiFetch('/api/otp/send/', { phone: phone, purpose: purpose }).then(function (res) {
            if (!res.body.ok) {
                setHint('otpHint', res.body.error || 'Could not resend OTP.', true);
                return;
            }
            if (res.body.delivered_sms) {
                hideInAppCode('inappOtp');
                setHint('otpHint', 'A fresh OTP has been sent by SMS. Check your phone.');
            } else {
                showInAppCode('inappOtp', res.body.otp || '');
                setHint('otpHint', 'A fresh OTP has been generated.');
            }
            buildOtpInputs('otpInputs');
        });
    }

    function onSignupSubmit(ev) {
        ev.preventDefault();
        var fullName = el('sFullName').value.trim();
        var username = el('sUsername').value.trim();
        var email    = el('sEmail').value.trim();
        var password = el('sPassword').value;

        var errNode = document.querySelector('#stepSignup .auth-hint');
        if (!fullName) {
            if (errNode) { errNode.textContent = 'Full name is required.'; errNode.classList.add('error'); }
            return;
        }
        if (!username) {
            if (errNode) { errNode.textContent = 'Please choose a username.'; errNode.classList.add('error'); }
            return;
        }
        if (password.length < 6) {
            if (errNode) { errNode.textContent = 'Password must be at least 6 characters.'; errNode.classList.add('error'); }
            return;
        }
        if (errNode) { errNode.textContent = 'Creating account…'; errNode.classList.remove('error'); }

        var btn = el('signupForm').querySelector('button[type=submit]');
        btn.disabled = true;

        apiFetch('/api/auth/signup/', {
            phone: phone,
            full_name: fullName,
            username: username,
            email: email,
            password: password,
        }).then(function (res) {
            btn.disabled = false;
            if (!res.body.ok) {
                if (errNode) { errNode.textContent = res.body.error || 'Could not create account.'; errNode.classList.add('error'); }
                return;
            }
            finishSuccess(
                'Account created!',
                'Welcome to Rent&Go, ' + (fullName.split(' ')[0] || username) + '!'
            );
        });
    }

    /* ====================================================
        EMAIL VERIFICATION FLOW
    ==================================================== */

    function onEmailSend(ev) {
        ev.preventDefault();
        var addr = el('emailAddr').value.trim().toLowerCase();
        if (!addr || addr.indexOf('@') < 1) {
            setHint('emailHint', 'Please enter a valid email address.', true);
            return;
        }

        clearHint('emailHint');
        disableBtn(el('emailSendBtn'), 'Sending code…');

        apiFetch('/api/email/verify/send/', { email: addr }).then(function (res) {
            enableBtn(el('emailSendBtn'), 'Send Verification Code');
            if (res.status === 429 && res.body.cooldown) {
                setHint('emailHint', res.body.error, true);
                startResendCountdown(res.body.cooldown, 'emailTimer', 'emailTimerText', 'emailResendBtn');
                return;
            }
            if (!res.body.ok) {
                setHint('emailHint', res.body.error || 'Failed to send code.', true);
                return;
            }

            emailAddr = addr;
            el('emailCodeTo').textContent = 'Code sent to ' + (res.body.email_mask || addr) + '.';

            if (res.body.email_delivered) {
                hideInAppCode('emailInappCode');
                setHint('emailCodeHint', 'Check your inbox for the verification code.');
            } else {
                showInAppCode('emailInappCode', res.body.code || '');
                clearHint('emailCodeHint');
            }
            buildOtpInputs('emailOtpInputs');
            showPanel('stepEmailCode');
            focusFirstBox('emailOtpInputs');
            startResendCountdown(60, 'emailTimer', 'emailTimerText', 'emailResendBtn');
        });
    }

    function onEmailVerify(ev) {
        ev.preventDefault();
        var code = getOtpValue('emailOtpInputs');
        if (code.length !== 6) {
            setHint('emailCodeHint', 'Please enter all 6 digits.', true);
            return;
        }

        clearHint('emailCodeHint');
        disableBtn(el('emailVerifyBtn'), 'Verifying…');

        apiFetch('/api/email/verify/confirm/', { email: emailAddr, code: code }).then(function (res) {
            enableBtn(el('emailVerifyBtn'), 'Verify Code');
            if (!res.body.ok) {
                setHint('emailCodeHint', res.body.error || 'Verification failed.', true);
                return;
            }

            // Email belongs to an existing account → server logged them in.
            if (res.body.logged_in) {
                finishSuccess('Welcome back!', 'Signed in as ' + (res.body.user || emailAddr) + '.');
                return;
            }

            // New email → offer email-only signup.
            el('eVerifiedEmail').value = emailAddr;
            el('emailSignupIntro').textContent =
                'Email verified! Now finish setting up your account.';
            showPanel('stepEmailSignup');
        });
    }

    function onEmailResend(ev) {
        ev.preventDefault();
        startResendCountdown(60, 'emailTimer', 'emailTimerText', 'emailResendBtn');
        apiFetch('/api/email/verify/send/', { email: emailAddr }).then(function (res) {
            if (!res.body.ok) {
                setHint('emailCodeHint', res.body.error || 'Could not resend code.', true);
                return;
            }
            if (res.body.email_delivered) {
                hideInAppCode('emailInappCode');
                setHint('emailCodeHint', 'A fresh code has been sent. Check your inbox.');
            } else {
                showInAppCode('emailInappCode', res.body.code || '');
                setHint('emailCodeHint', 'A fresh code has been generated.');
            }
            buildOtpInputs('emailOtpInputs');
        });
    }

    function onEmailSignupSubmit(ev) {
        ev.preventDefault();
        var fullName = el('eFullName').value.trim();
        var username = el('eUsername').value.trim();
        var password = el('ePassword').value;

        var errNode = document.querySelector('#stepEmailSignup .auth-hint');
        if (!fullName) {
            if (errNode) { errNode.textContent = 'Full name is required.'; errNode.classList.add('error'); }
            return;
        }
        if (!username) {
            if (errNode) { errNode.textContent = 'Please choose a username.'; errNode.classList.add('error'); }
            return;
        }
        if (password.length < 6) {
            if (errNode) { errNode.textContent = 'Password must be at least 6 characters.'; errNode.classList.add('error'); }
            return;
        }
        if (errNode) { errNode.textContent = 'Creating account…'; errNode.classList.remove('error'); }

        var btn = el('emailSignupForm').querySelector('button[type=submit]');
        btn.disabled = true;

        apiFetch('/api/auth/email-signup/', {
            email: emailAddr,
            full_name: fullName,
            username: username,
            password: password,
        }).then(function (res) {
            btn.disabled = false;
            if (!res.body.ok) {
                if (errNode) { errNode.textContent = res.body.error || 'Could not create account.'; errNode.classList.add('error'); }
                return;
            }
            finishSuccess(
                'Account created!',
                'Welcome to Rent&Go, ' + (fullName.split(' ')[0] || username) + '!'
            );
        });
    }

    /* ====================================================
        GOOGLE SIGN-IN
    ==================================================== */

    function handleGoogleCredential(credential) {
        apiFetch('/api/auth/google/', { id_token: credential }).then(function (res) {
            var hint = el('googleHint');
            if (!res.body.ok) {
                if (hint) { hint.textContent = res.body.error || 'Google sign-in failed.'; hint.classList.add('error'); }
                return;
            }
            var msg = res.body.new_user
                ? 'Welcome to Rent&Go, ' + (res.body.name || res.body.user) + '!'
                : 'Welcome back, ' + (res.body.name || res.body.user) + '!';
            finishSuccess(
                res.body.new_user ? 'Account created!' : 'Welcome back!',
                msg
            );
        });
    }

    // Make the callback accessible to Google's script.
    window.handleGoogleCredential = handleGoogleCredential;

    function initGoogleButton(containerId) {
        var config = el('authRoot');
        var clientId = config ? config.dataset.googleId : '';
        if (!clientId) {
            var gNote = el('googleNote');
            if (gNote) gNote.style.display = 'block';
            return;
        }

        function render() {
            if (!window.google || !google.accounts || !google.accounts.id) return;

            google.accounts.id.initialize({
                client_id: clientId,
                callback: window.handleGoogleCredential,
            });

            var opts = { theme: 'outline', size: 'large', text: 'signin_with', width: 300 };

            [containerId, 'googleFromEmailBtn'].forEach(function (cid) {
                var btn = el(cid);
                if (!btn) return;
                // Google will render its own button inside this element
                google.accounts.id.renderButton(btn, opts);
                btn.disabled = false;
            });
        }

        if (window.__gsiLoaded || (window.google && google.accounts)) {
            render();
        } else {
            document.addEventListener('gsi:loaded', render, { once: true });
            // Also try polling once in case the event already fired
            setTimeout(render, 1200);
        }
    }

    /* ====================================================
        SUCCESS
    ==================================================== */

    function finishSuccess(title, text) {
        el('successTitle').textContent = title;
        el('successText').textContent = text;
        showPanel('stepSuccess');
    }

    /* ====================================================
        NAVIGATION BINDINGS
    ==================================================== */

    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    ready(function () {
        var root = document.getElementById('authRoot');
        purpose = (root.dataset.mode === 'signup') ? 'signup' : 'login';

        // --- Phone OTP ---
        el('sendOtpBtn').addEventListener('click', onSendOtp);
        el('verifyOtpBtn').addEventListener('click', onVerifyOtp);
        el('resendOtpBtn').addEventListener('click', onResendOtp);
        el('signupForm').addEventListener('submit', onSignupSubmit);

        el('changeNumberBtn').addEventListener('click', function () {
            clearInterval(timer);
            showPanel('stepMethod');
            clearHint('otpHint');
            enableBtn(el('sendOtpBtn'), 'Send OTP');
        });
        el('backToOtpBtn').addEventListener('click', function () {
            purpose = 'login';
            buildOtpInputs('otpInputs');
            showPanel('stepOtp');
        });

        el('otpPhone').addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter') { ev.preventDefault(); onSendOtp(ev); }
        });

        // --- Method switcher ---
        el('switchEmailBtn').addEventListener('click', function () {
            clearInterval(timer);
            showPanel('stepEmail');
        });
        el('backToMethodBtn').addEventListener('click', function () {
            showPanel('stepMethod');
        });

        // --- Email verification ---
        el('emailSendBtn').addEventListener('click', onEmailSend);
        el('emailVerifyBtn').addEventListener('click', onEmailVerify);
        el('emailResendBtn').addEventListener('click', onEmailResend);
        el('emailSignupForm').addEventListener('submit', onEmailSignupSubmit);

        el('changeEmailBtn').addEventListener('click', function () {
            clearInterval(timer);
            showPanel('stepEmail');
            clearHint('emailCodeHint');
            enableBtn(el('emailSendBtn'), 'Send Verification Code');
        });
        el('backToEmailCodeBtn').addEventListener('click', function () {
            buildOtpInputs('emailOtpInputs');
            showPanel('stepEmailCode');
        });

        el('emailAddr').addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter') { ev.preventDefault(); onEmailSend(ev); }
        });

        // --- Google ---
        initGoogleButton('googleLoginBtn');

        // --- Success ---
        el('goHomeBtn').addEventListener('click', function () {
            window.location.href = '/';
        });
    });

})();
